/**
 * @file demo_lepton.c
 * @brief Lepton 3.5 thermal camera demo - EKH05 integration
 *
 * Runs a FreeRTOS task that continuously captures thermal frames from the
 * Lepton 3.5, converts them to colored BMP images, and serves them via
 * the HTTP REST endpoints over Wi-Fi HaLow.
 *
 * Integrates into the existing EKH05 Demo application alongside the
 * visible-light camera, accelerometer, and temperature sensors.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "demo_lepton.h"
#include "lepton_driver.h"
#include "thermal_palette.h"
#include "mmosal.h"
#include "main.h"
#include <string.h>
#include <stdio.h>

/* --------------------------------------------------------------------------
 * BMP File Format Helpers
 * ----------------------------------------------------------------------- */

/** BMP file header (14 bytes) + DIB header (40 bytes) = 54 bytes total */
#define BMP_HEADER_SIZE     54
#define BMP_WIDTH           LEPTON_WIDTH   /* 160 */
#define BMP_HEIGHT          LEPTON_HEIGHT  /* 120 */
#define BMP_ROW_SIZE        (BMP_WIDTH * 3)  /* 480 bytes, already 4-byte aligned */
#define BMP_PIXEL_DATA_SIZE (BMP_ROW_SIZE * BMP_HEIGHT)
#define BMP_FILE_SIZE       (BMP_HEADER_SIZE + BMP_PIXEL_DATA_SIZE)

/** Write a 32-bit little-endian value to a byte array */
static inline void write_le32(uint8_t *p, uint32_t val)
{
    p[0] = (val >>  0) & 0xFF;
    p[1] = (val >>  8) & 0xFF;
    p[2] = (val >> 16) & 0xFF;
    p[3] = (val >> 24) & 0xFF;
}

/** Write a 16-bit little-endian value to a byte array */
static inline void write_le16(uint8_t *p, uint16_t val)
{
    p[0] = (val >> 0) & 0xFF;
    p[1] = (val >> 8) & 0xFF;
}

/**
 * @brief Write BMP header into buffer.
 *        24-bit uncompressed BMP, bottom-up row order.
 */
static void bmp_write_header(uint8_t *buf)
{
    memset(buf, 0, BMP_HEADER_SIZE);

    /* BMP file header (14 bytes) */
    buf[0] = 'B'; buf[1] = 'M';            /* Signature */
    write_le32(&buf[2], BMP_FILE_SIZE);     /* File size */
    write_le32(&buf[6], 0);                 /* Reserved */
    write_le32(&buf[10], BMP_HEADER_SIZE);  /* Pixel data offset */

    /* DIB header - BITMAPINFOHEADER (40 bytes) */
    write_le32(&buf[14], 40);               /* DIB header size */
    write_le32(&buf[18], BMP_WIDTH);        /* Width */
    write_le32(&buf[22], BMP_HEIGHT);       /* Height (positive = bottom-up) */
    write_le16(&buf[26], 1);                /* Color planes */
    write_le16(&buf[28], 24);               /* Bits per pixel */
    write_le32(&buf[30], 0);                /* Compression (none) */
    write_le32(&buf[34], BMP_PIXEL_DATA_SIZE); /* Image size */
    write_le32(&buf[38], 2835);             /* H resolution (72 DPI) */
    write_le32(&buf[42], 2835);             /* V resolution (72 DPI) */
    write_le32(&buf[46], 0);                /* Colors in palette */
    write_le32(&buf[50], 0);                /* Important colors */
}

/* --------------------------------------------------------------------------
 * Module State
 * ----------------------------------------------------------------------- */

static lepton_handle_t lepton;
static struct mmosal_semb *thermal_lock = NULL;
static struct mmosal_task *thermal_task_handle = NULL;
static bool lepton_running = false;

/** Grayscale buffer (160x120 = 19200 bytes) */
static uint8_t grayscale_buf[LEPTON_WIDTH * LEPTON_HEIGHT];

/** BMP output buffer (54 header + 160*120*3 = 57654 bytes) */
static uint8_t bmp_buf[BMP_FILE_SIZE];
static uint32_t bmp_valid_size = 0;

/** HTTP response state for chunked transfer */
static uint32_t http_bmp_offset = 0;

extern I2C_HandleTypeDef hi2c1;

/* --------------------------------------------------------------------------
 * Thermal Capture Task
 * ----------------------------------------------------------------------- */

/**
 * @brief FreeRTOS task: continuously capture Lepton frames and build BMP images.
 *        Runs at ~5-8 fps depending on SPI speed.
 */
static void thermal_capture_task(void *arg)
{
    (void)arg;

    printf("[Thermal] Capture task started\n");

    while (1)
    {
        /* Capture a frame */
        if (lepton_capture_frame(&lepton) == 0)
        {
            /* Convert raw14 to grayscale */
            lepton_frame_to_grayscale(&lepton, grayscale_buf);

            /* Build BMP with Ironbow palette */
            if (mmosal_semb_wait(thermal_lock, 500))
            {
                bmp_write_header(bmp_buf);

                /* BMP is bottom-up: row 0 in file = bottom row of image.
                 * Lepton frame is top-down: row 0 = top of image.
                 * So we flip vertically when writing to BMP. */
                for (int y = 0; y < BMP_HEIGHT; y++)
                {
                    int src_row = (BMP_HEIGHT - 1) - y; /* Flip */
                    thermal_apply_palette(
                        &grayscale_buf[src_row * BMP_WIDTH],
                        &bmp_buf[BMP_HEADER_SIZE + y * BMP_ROW_SIZE],
                        BMP_WIDTH,
                        palette_ironbow);
                }

                bmp_valid_size = BMP_FILE_SIZE;
                mmosal_semb_give(thermal_lock);
            }
        }
        else
        {
            printf("[Thermal] Frame capture failed, retrying...\n");
            HAL_Delay(500);
        }

        /* Small delay to yield CPU to other tasks */
        mmosal_task_sleep(10);
    }
}

/* --------------------------------------------------------------------------
 * Public API
 * ----------------------------------------------------------------------- */

void lepton_demo_init(void)
{
    printf("[Thermal] Initializing Lepton 3.5...\n");

    /* Create lock semaphore */
    thermal_lock = mmosal_semb_create("thermal_lock");
    mmosal_semb_give(thermal_lock);

    /* Initialize Lepton driver (uses I2C1 shared with other sensors) */
    if (lepton_init(&lepton, &hi2c1) != 0)
    {
        printf("[Thermal] ERROR: Lepton init failed!\n");
        printf("[Thermal] Check wiring: CS=PC13, CLK=PD11, MISO=PD15, I2C1\n");
        return;
    }

    /* Start capture task */
    thermal_task_handle = mmosal_task_create(
        thermal_capture_task, NULL,
        MMOSAL_TASK_PRI_LOW, 2048, "thermal");

    if (thermal_task_handle == NULL)
    {
        printf("[Thermal] ERROR: Failed to create capture task\n");
        return;
    }

    lepton_running = true;
    printf("[Thermal] Lepton 3.5 ready - endpoints: /thermal.bmp, /thermal.json\n");
}

const uint8_t *lepton_demo_get_bmp(uint32_t *size)
{
    if (!lepton_running || bmp_valid_size == 0)
    {
        *size = 0;
        return NULL;
    }
    *size = bmp_valid_size;
    return bmp_buf;
}

const uint8_t *lepton_demo_get_grayscale(int *width, int *height)
{
    *width = LEPTON_WIDTH;
    *height = LEPTON_HEIGHT;
    return grayscale_buf;
}

bool lepton_demo_is_running(void)
{
    return lepton_running;
}

uint32_t lepton_demo_get_frame_count(void)
{
    return lepton.frame_count;
}

void lepton_demo_run_ffc(void)
{
    if (lepton_running)
    {
        lepton_run_ffc(&lepton);
    }
}

/* --------------------------------------------------------------------------
 * HTTP REST Endpoints
 *
 * These follow the EKH05 Demo restfs pattern.
 * The restfs callback is called repeatedly until *more is false.
 * ----------------------------------------------------------------------- */

uint16_t rest_ep_get_thermal_bmp(char *buf, uint16_t buf_len, bool *more)
{
    /* First call: lock and reset offset */
    if (http_bmp_offset == 0)
    {
        if (!lepton_running || bmp_valid_size == 0)
        {
            /* No image available - return error */
            const char *err = "HTTP/1.1 503 Service Unavailable\r\n"
                              "Content-Type: text/plain\r\n\r\n"
                              "Thermal camera not ready";
            uint16_t len = strlen(err);
            if (len > buf_len) len = buf_len;
            memcpy(buf, err, len);
            *more = false;
            return len;
        }
        mmosal_semb_wait(thermal_lock, 1000);
    }

    /* Calculate how much data to send */
    uint32_t remaining = bmp_valid_size - http_bmp_offset;
    uint16_t chunk = (remaining > buf_len) ? buf_len : (uint16_t)remaining;

    memcpy(buf, &bmp_buf[http_bmp_offset], chunk);
    http_bmp_offset += chunk;

    if (http_bmp_offset >= bmp_valid_size)
    {
        /* All data sent */
        http_bmp_offset = 0;
        mmosal_semb_give(thermal_lock);
        *more = false;
    }
    else
    {
        *more = true;
    }

    return chunk;
}

uint16_t rest_ep_get_thermal_json(char *buf, uint16_t buf_len, bool *more)
{
    *more = false;

    lepton_scene_stats_t stats = {0};
    if (lepton_running)
    {
        lepton_get_scene_stats(&lepton, &stats);
    }

    int len = snprintf(buf, buf_len,
        "{"
        "\"running\":%s,"
        "\"frames\":%lu,"
        "\"min\":%u,"
        "\"max\":%u,"
        "\"mean\":%u,"
        "\"width\":%d,"
        "\"height\":%d"
        "}",
        lepton_running ? "true" : "false",
        (unsigned long)lepton.frame_count,
        stats.min_val,
        stats.max_val,
        stats.mean_val,
        LEPTON_WIDTH,
        LEPTON_HEIGHT);

    return (uint16_t)((len > buf_len) ? buf_len : len);
}

uint16_t rest_ep_thermal_ffc(char *buf, uint16_t buf_len, bool *more)
{
    *more = false;

    if (lepton_running)
    {
        lepton_run_ffc(&lepton);
        int len = snprintf(buf, buf_len,
            "{\"status\":\"ok\",\"message\":\"FFC calibration triggered\"}");
        return (uint16_t)len;
    }
    else
    {
        int len = snprintf(buf, buf_len,
            "{\"status\":\"error\",\"message\":\"Thermal camera not running\"}");
        return (uint16_t)len;
    }
}
