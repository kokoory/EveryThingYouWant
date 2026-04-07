/**
 * @file lepton_driver.c
 * @brief FLIR Lepton 3.5 driver for MM6108-EKH05 board
 *
 * Software bit-bang SPI for VoSPI + shared I2C1 for CCI.
 * Based on GroupGets LeptonModule reference code, adapted for STM32U5 HAL
 * and the EKH05 evaluation kit.
 *
 * Reference: https://github.com/groupgets/LeptonModule
 * Lepton Datasheet: Lepton Engineering Datasheet Rev200
 *
 * Copyright 2024
 * SPDX-License-Identifier: Apache-2.0
 */

#include "lepton_driver.h"
#include <string.h>
#include <stdio.h>

/* --------------------------------------------------------------------------
 * Internal helpers
 * ----------------------------------------------------------------------- */

/** Short delay for SPI clock ~2-5 MHz.
 *  At 160MHz CPU, ~16-40 NOP cycles per half-period. */
static inline void spi_delay(void)
{
    /* ~20 NOPs gives roughly 4MHz SPI clock at 160MHz CPU */
    __NOP(); __NOP(); __NOP(); __NOP(); __NOP();
    __NOP(); __NOP(); __NOP(); __NOP(); __NOP();
    __NOP(); __NOP(); __NOP(); __NOP(); __NOP();
    __NOP(); __NOP(); __NOP(); __NOP(); __NOP();
}

static inline void lepton_cs_low(void)
{
    HAL_GPIO_WritePin(LEPTON_CS_PORT, LEPTON_CS_PIN, GPIO_PIN_RESET);
}

static inline void lepton_cs_high(void)
{
    HAL_GPIO_WritePin(LEPTON_CS_PORT, LEPTON_CS_PIN, GPIO_PIN_SET);
}

static inline void lepton_clk_low(void)
{
    HAL_GPIO_WritePin(LEPTON_CLK_PORT, LEPTON_CLK_PIN, GPIO_PIN_RESET);
}

static inline void lepton_clk_high(void)
{
    HAL_GPIO_WritePin(LEPTON_CLK_PORT, LEPTON_CLK_PIN, GPIO_PIN_SET);
}

static inline uint8_t lepton_miso_read(void)
{
    return (HAL_GPIO_ReadPin(LEPTON_MISO_PORT, LEPTON_MISO_PIN) == GPIO_PIN_SET) ? 1 : 0;
}

/* --------------------------------------------------------------------------
 * Software SPI (bit-bang) - SPI Mode 3 (CPOL=1, CPHA=1)
 *
 * Lepton uses SPI Mode 3:
 *   - CLK idle HIGH
 *   - Data set on falling edge, sampled on rising edge
 *   - MOSI not used (read-only from Lepton)
 * ----------------------------------------------------------------------- */

/**
 * @brief Read a single byte via software SPI (Mode 3, MSB first).
 */
static uint8_t sw_spi_read_byte(void)
{
    uint8_t byte = 0;

    for (int bit = 7; bit >= 0; bit--)
    {
        /* Falling edge - Lepton sets data */
        lepton_clk_low();
        spi_delay();

        /* Rising edge - we sample MISO */
        lepton_clk_high();
        if (lepton_miso_read())
        {
            byte |= (1 << bit);
        }
        spi_delay();
    }

    return byte;
}

/**
 * @brief Read a VoSPI packet (164 bytes) via software SPI.
 */
static void sw_spi_read_packet(uint8_t *buf)
{
    lepton_cs_low();

    for (int i = 0; i < LEPTON_VOSPI_PACKET_SIZE; i++)
    {
        buf[i] = sw_spi_read_byte();
    }

    lepton_cs_high();
}

/* --------------------------------------------------------------------------
 * GPIO Initialization
 * ----------------------------------------------------------------------- */

static void lepton_gpio_init(void)
{
    GPIO_InitTypeDef gpio = {0};

    /* Enable clocks for GPIOC and GPIOD */
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();

    /* CS pin - Output, Push-Pull, High (deasserted) */
    gpio.Pin   = LEPTON_CS_PIN;
    gpio.Mode  = GPIO_MODE_OUTPUT_PP;
    gpio.Pull  = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(LEPTON_CS_PORT, &gpio);
    lepton_cs_high();

    /* CLK pin - Output, Push-Pull, High (SPI Mode 3 idle) */
    gpio.Pin   = LEPTON_CLK_PIN;
    gpio.Mode  = GPIO_MODE_OUTPUT_PP;
    gpio.Pull  = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(LEPTON_CLK_PORT, &gpio);
    lepton_clk_high();  /* Idle HIGH for SPI Mode 3 */

    /* MISO pin - Input, Pull-Up */
    gpio.Pin   = LEPTON_MISO_PIN;
    gpio.Mode  = GPIO_MODE_INPUT;
    gpio.Pull  = GPIO_PULLUP;
    gpio.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(LEPTON_MISO_PORT, &gpio);
}

/* --------------------------------------------------------------------------
 * CCI (I2C) Functions
 * ----------------------------------------------------------------------- */

/**
 * @brief Write a 16-bit value to a CCI register.
 */
static int cci_write_reg(lepton_handle_t *handle, uint16_t reg, uint16_t value)
{
    uint8_t data[4];
    data[0] = (reg >> 8) & 0xFF;
    data[1] = reg & 0xFF;
    data[2] = (value >> 8) & 0xFF;
    data[3] = value & 0xFF;

    HAL_StatusTypeDef ret = HAL_I2C_Master_Transmit(
        handle->hi2c, LEPTON_I2C_ADDR << 1, data, 4, 1000);

    return (ret == HAL_OK) ? 0 : -1;
}

/**
 * @brief Read a 16-bit value from a CCI register.
 */
static int cci_read_reg(lepton_handle_t *handle, uint16_t reg, uint16_t *value)
{
    uint8_t reg_buf[2];
    uint8_t data[2];

    reg_buf[0] = (reg >> 8) & 0xFF;
    reg_buf[1] = reg & 0xFF;

    HAL_StatusTypeDef ret;

    ret = HAL_I2C_Master_Transmit(handle->hi2c, LEPTON_I2C_ADDR << 1,
                                  reg_buf, 2, 1000);
    if (ret != HAL_OK) return -1;

    ret = HAL_I2C_Master_Receive(handle->hi2c, LEPTON_I2C_ADDR << 1,
                                 data, 2, 1000);
    if (ret != HAL_OK) return -1;

    *value = ((uint16_t)data[0] << 8) | data[1];
    return 0;
}

/**
 * @brief Wait for CCI to be ready (not busy).
 */
static int cci_wait_ready(lepton_handle_t *handle, uint32_t timeout_ms)
{
    uint32_t start = HAL_GetTick();
    uint16_t status;

    while ((HAL_GetTick() - start) < timeout_ms)
    {
        if (cci_read_reg(handle, LEP_CCI_REG_STATUS, &status) != 0)
        {
            HAL_Delay(10);
            continue;
        }
        if (!(status & LEP_CCI_STATUS_BUSY_BIT))
        {
            /* Check for errors */
            if (status & LEP_CCI_STATUS_ERROR_MASK)
            {
                printf("[Lepton] CCI error: 0x%04X\n", status);
                return -2;
            }
            return 0;
        }
        HAL_Delay(1);
    }
    return -1; /* Timeout */
}

/**
 * @brief Execute a CCI command (GET/SET/RUN).
 */
static int cci_command(lepton_handle_t *handle, uint16_t cmd_id, uint16_t cmd_type,
                       uint16_t *data, uint16_t data_words)
{
    /* Wait for CCI ready */
    if (cci_wait_ready(handle, 5000) != 0)
    {
        printf("[Lepton] CCI not ready\n");
        return -1;
    }

    /* For SET commands, write data first */
    if (cmd_type == LEP_CCI_CMD_SET && data != NULL && data_words > 0)
    {
        for (int i = 0; i < data_words; i++)
        {
            if (cci_write_reg(handle, LEP_CCI_REG_DATA_0 + (i * 2), data[i]) != 0)
                return -1;
        }
        /* Set data length */
        if (cci_write_reg(handle, LEP_CCI_REG_DATA_LENGTH, data_words) != 0)
            return -1;
    }

    /* For GET commands, set data length */
    if (cmd_type == LEP_CCI_CMD_GET && data_words > 0)
    {
        if (cci_write_reg(handle, LEP_CCI_REG_DATA_LENGTH, data_words) != 0)
            return -1;
    }

    /* Issue command */
    uint16_t full_cmd = cmd_id | cmd_type;
    if (cci_write_reg(handle, LEP_CCI_REG_COMMAND, full_cmd) != 0)
        return -1;

    /* Wait for completion */
    if (cci_wait_ready(handle, 5000) != 0)
        return -1;

    /* For GET commands, read data */
    if (cmd_type == LEP_CCI_CMD_GET && data != NULL && data_words > 0)
    {
        for (int i = 0; i < data_words; i++)
        {
            if (cci_read_reg(handle, LEP_CCI_REG_DATA_0 + (i * 2), &data[i]) != 0)
                return -1;
        }
    }

    return 0;
}

/* --------------------------------------------------------------------------
 * VoSPI Frame Capture (Lepton 3.5 with segments)
 * ----------------------------------------------------------------------- */

/**
 * @brief Perform VoSPI resync by deasserting CS for >185ms.
 *        This resets the Lepton's VoSPI state machine.
 */
static void vospi_resync(void)
{
    lepton_cs_high();
    HAL_Delay(200);
}

/**
 * @brief Capture one complete Lepton 3.5 frame (4 segments x 60 packets).
 *
 * Lepton 3.5 outputs 160x120 image in 4 segments.
 * Each segment has 60 packets, each packet has 164 bytes:
 *   [ID_MSB][ID_LSB][CRC_MSB][CRC_LSB][80 pixels x 2 bytes]
 *
 * Packet ID format:
 *   Bits [11:0] = packet number (0-59)
 *   Bit [15:12] in packet 20 = segment number (1-4)
 *   0x_F in upper nibble of ID_MSB = discard packet
 */
int lepton_capture_frame(lepton_handle_t *handle)
{
    uint8_t packet[LEPTON_VOSPI_PACKET_SIZE];
    int segments_captured = 0;
    int sync_errors = 0;
    const int MAX_SYNC_RETRIES = 5;

    handle->state = LEPTON_STATE_SYNCING;

    while (segments_captured < LEPTON_SEGMENTS_PER_FRAME)
    {
        if (sync_errors >= MAX_SYNC_RETRIES)
        {
            printf("[Lepton] Sync failed after %d retries\n", MAX_SYNC_RETRIES);
            handle->state = LEPTON_STATE_ERROR;
            return -1;
        }

        /* Read packets for one segment */
        int seg_num = -1;
        bool seg_valid = true;

        for (int pkt = 0; pkt < LEPTON_PACKETS_PER_SEG; pkt++)
        {
            sw_spi_read_packet(packet);

            uint16_t id_word = ((uint16_t)packet[0] << 8) | packet[1];
            int packet_num = id_word & 0x0FFF;

            /* Check for discard packet */
            if ((packet[0] & 0x0F) == LEPTON_DISCARD_PACKET)
            {
                /* Discard - need to resync */
                if (pkt == 0)
                {
                    /* Normal - just retry */
                    pkt = -1; /* Will be incremented to 0 */
                    continue;
                }
                else
                {
                    /* Lost sync mid-segment */
                    seg_valid = false;
                    break;
                }
            }

            /* Verify packet number */
            if (packet_num != pkt)
            {
                seg_valid = false;
                break;
            }

            /* Extract segment number from packet 20 */
            if (pkt == LEPTON_SEG_NUM_PACKET)
            {
                seg_num = (id_word >> 12) & 0x07;
                /* Segment numbers are 1-4 */
                if (seg_num < 1 || seg_num > 4)
                {
                    seg_valid = false;
                    break;
                }
                /* Check if this is the segment we need */
                if (seg_num != (segments_captured + 1))
                {
                    seg_valid = false;
                    break;
                }
            }

            /* Copy pixel data to frame buffer.
             * Segment N (1-4) contains rows (N-1)*30 to N*30-1.
             * Each packet has 80 pixels (160 bytes) = one row of the image. */
            int row = (segments_captured * LEPTON_PACKETS_PER_SEG) + pkt;
            if (row < LEPTON_HEIGHT)
            {
                memcpy(&handle->frame_buf[row * LEPTON_VOSPI_PAYLOAD_SIZE],
                       &packet[LEPTON_VOSPI_HEADER_SIZE],
                       LEPTON_VOSPI_PAYLOAD_SIZE);
            }
        }

        if (seg_valid && seg_num > 0)
        {
            segments_captured++;
            sync_errors = 0;
        }
        else
        {
            /* Resync */
            vospi_resync();
            segments_captured = 0;
            sync_errors++;
        }
    }

    handle->frame_valid = true;
    handle->frame_count++;
    handle->state = LEPTON_STATE_READY;

    return 0;
}

/* --------------------------------------------------------------------------
 * Public API
 * ----------------------------------------------------------------------- */

int lepton_init(lepton_handle_t *handle, I2C_HandleTypeDef *hi2c)
{
    memset(handle, 0, sizeof(lepton_handle_t));
    handle->hi2c = hi2c;
    handle->state = LEPTON_STATE_UNINIT;

    /* Initialize GPIO pins for software SPI */
    lepton_gpio_init();

    printf("[Lepton] GPIO initialized (CS=PC13, CLK=PD11, MISO=PD15)\n");

    /* Wait for Lepton to boot (typically ~950ms after power-up) */
    HAL_Delay(1000);

    /* Check CCI communication */
    uint16_t status;
    if (cci_read_reg(handle, LEP_CCI_REG_STATUS, &status) != 0)
    {
        printf("[Lepton] CCI communication failed\n");
        handle->state = LEPTON_STATE_ERROR;
        return -1;
    }

    /* Wait for boot complete */
    int boot_retries = 50;
    while (!(status & LEP_CCI_STATUS_BOOT_BIT) && boot_retries-- > 0)
    {
        HAL_Delay(100);
        cci_read_reg(handle, LEP_CCI_REG_STATUS, &status);
    }

    if (!(status & LEP_CCI_STATUS_BOOT_BIT))
    {
        printf("[Lepton] Boot timeout, status=0x%04X\n", status);
        handle->state = LEPTON_STATE_ERROR;
        return -2;
    }

    printf("[Lepton] Booted OK, status=0x%04X\n", status);

    /* Enable AGC by default for better visual output */
    lepton_set_agc(handle, LEPTON_AGC_ENABLE);

    /* Perform initial VoSPI sync */
    vospi_resync();

    handle->state = LEPTON_STATE_READY;
    printf("[Lepton] Driver initialized successfully\n");

    return 0;
}

const uint8_t *lepton_get_frame(const lepton_handle_t *handle)
{
    return handle->frame_buf;
}

bool lepton_frame_valid(const lepton_handle_t *handle)
{
    return handle->frame_valid;
}

int lepton_set_agc(lepton_handle_t *handle, lepton_agc_mode_t mode)
{
    uint16_t data = (uint16_t)mode;
    int ret = cci_command(handle, LEP_CID_AGC_ENABLE_STATE, LEP_CCI_CMD_SET, &data, 1);
    if (ret == 0)
    {
        printf("[Lepton] AGC %s\n", mode ? "enabled" : "disabled");
    }
    return ret;
}

int lepton_get_scene_stats(lepton_handle_t *handle, lepton_scene_stats_t *stats)
{
    uint16_t data[4]; /* min, max, mean, num_pixels */
    int ret = cci_command(handle, LEP_CID_SYS_STATS, LEP_CCI_CMD_GET, data, 4);
    if (ret == 0)
    {
        stats->min_val  = data[0];
        stats->max_val  = data[1];
        stats->mean_val = data[2];
        handle->stats = *stats;
    }
    return ret;
}

int lepton_run_ffc(lepton_handle_t *handle)
{
    printf("[Lepton] Running FFC (Flat-Field Correction)...\n");
    uint16_t cmd_id = 0x0242; /* SYS FFC (Run) */
    int ret = cci_command(handle, cmd_id, LEP_CCI_CMD_RUN, NULL, 0);
    if (ret == 0)
    {
        /* FFC takes ~1 second */
        HAL_Delay(1500);
        printf("[Lepton] FFC complete\n");
    }
    return ret;
}

void lepton_frame_to_grayscale(const lepton_handle_t *handle, uint8_t *out_buf)
{
    const uint8_t *raw = handle->frame_buf;
    uint16_t min_val = 0xFFFF;
    uint16_t max_val = 0;

    /* First pass: find min/max for auto-scaling */
    for (int i = 0; i < LEPTON_WIDTH * LEPTON_HEIGHT; i++)
    {
        uint16_t pixel = ((uint16_t)raw[i * 2] << 8) | raw[i * 2 + 1];
        pixel &= 0x3FFF; /* Mask to 14 bits */
        if (pixel < min_val) min_val = pixel;
        if (pixel > max_val) max_val = pixel;
    }

    uint16_t range = max_val - min_val;
    if (range == 0) range = 1; /* Prevent division by zero */

    /* Second pass: scale to 0-255 */
    for (int i = 0; i < LEPTON_WIDTH * LEPTON_HEIGHT; i++)
    {
        uint16_t pixel = ((uint16_t)raw[i * 2] << 8) | raw[i * 2 + 1];
        pixel &= 0x3FFF;
        out_buf[i] = (uint8_t)(((uint32_t)(pixel - min_val) * 255) / range);
    }
}
