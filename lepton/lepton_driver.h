/**
 * @file lepton_driver.h
 * @brief FLIR Lepton 3.5 driver for MM6108-EKH05 board
 *
 * VoSPI (Video over SPI) using software bit-bang SPI on debug/spare pins.
 * CCI (Command and Control Interface) via shared I2C1.
 *
 * Pin assignments (EKH05 debug/spare pins):
 *   LEPTON_CS   -> PC13 (SPARE_GPIO_PC13)
 *   LEPTON_CLK  -> PD11 (SPARE_GPIO_PD11)
 *   LEPTON_MISO -> PD15 (SPARE_GPIO_PD15)
 *   LEPTON I2C  -> I2C1 (shared with onboard sensors)
 *
 * Compatible with SparkFun FLIR Lepton Breakout Board.
 *
 * Copyright 2024 - Lepton integration for EKH05 Demo
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef LEPTON_DRIVER_H
#define LEPTON_DRIVER_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>
#include "stm32u5xx_hal.h"

/* --------------------------------------------------------------------------
 * Lepton 3.5 Constants
 * ----------------------------------------------------------------------- */

/** Lepton 3.5 image dimensions */
#define LEPTON_WIDTH          160
#define LEPTON_HEIGHT         120

/** VoSPI packet format */
#define LEPTON_VOSPI_PACKET_SIZE   164   /* 4-byte header + 160 bytes payload */
#define LEPTON_VOSPI_HEADER_SIZE   4
#define LEPTON_VOSPI_PAYLOAD_SIZE  160   /* 80 pixels x 2 bytes (Raw14) */

/** Lepton 3.5 segment configuration */
#define LEPTON_PACKETS_PER_SEG     60
#define LEPTON_SEGMENTS_PER_FRAME  4
#define LEPTON_TOTAL_PACKETS       (LEPTON_PACKETS_PER_SEG * LEPTON_SEGMENTS_PER_FRAME)

/** Discard packet marker */
#define LEPTON_DISCARD_PACKET      0x0F

/** Segment number is in packet 20, bits [14:12] of the ID word */
#define LEPTON_SEG_NUM_PACKET      20

/** Frame buffer size: 160 x 120 x 2 bytes (Raw14) */
#define LEPTON_FRAME_SIZE          (LEPTON_WIDTH * LEPTON_HEIGHT * 2)

/** I2C address (7-bit) */
#define LEPTON_I2C_ADDR            0x2A

/* --------------------------------------------------------------------------
 * CCI Register Addresses
 * ----------------------------------------------------------------------- */
#define LEP_CCI_REG_STATUS         0x0002
#define LEP_CCI_REG_COMMAND        0x0004
#define LEP_CCI_REG_DATA_LENGTH    0x0006
#define LEP_CCI_REG_DATA_0         0x0008

/* CCI Status bits */
#define LEP_CCI_STATUS_BUSY_BIT    0x0001
#define LEP_CCI_STATUS_BOOT_BIT    0x0004
#define LEP_CCI_STATUS_ERROR_MASK  0xFF00

/* CCI Commands */
#define LEP_CID_AGC_ENABLE_STATE      0x0100  /* AGC module, Enable state */
#define LEP_CID_AGC_CALC_ENABLE       0x0148  /* AGC calc enable */
#define LEP_CID_SYS_FLIR_SERIAL       0x0208  /* SYS FLIR serial number */
#define LEP_CID_SYS_UPTIME            0x020C  /* SYS uptime */
#define LEP_CID_SYS_TELEMETRY_ENABLE  0x0218  /* SYS telemetry enable */
#define LEP_CID_SYS_STATS             0x0228  /* SYS scene stats */
#define LEP_CID_RAD_ENABLE            0x4E10  /* RAD enable */
#define LEP_CID_RAD_TLINEAR_ENABLE    0x4EC0  /* RAD TLinear enable */

/* CCI Command types (OR with command ID) */
#define LEP_CCI_CMD_GET               0x0000
#define LEP_CCI_CMD_SET               0x0001
#define LEP_CCI_CMD_RUN               0x0002

/* --------------------------------------------------------------------------
 * Pin Configuration (EKH05 debug/spare pins)
 * ----------------------------------------------------------------------- */

/** Software SPI pins for VoSPI */
#define LEPTON_CS_PORT       GPIOC
#define LEPTON_CS_PIN        GPIO_PIN_13   /* SPARE_GPIO_PC13 */

#define LEPTON_CLK_PORT      GPIOD
#define LEPTON_CLK_PIN       GPIO_PIN_11   /* SPARE_GPIO_PD11 */

#define LEPTON_MISO_PORT     GPIOD
#define LEPTON_MISO_PIN      GPIO_PIN_15   /* SPARE_GPIO_PD15 */

/* --------------------------------------------------------------------------
 * Data Types
 * ----------------------------------------------------------------------- */

/** Lepton driver state */
typedef enum {
    LEPTON_STATE_UNINIT = 0,
    LEPTON_STATE_READY,
    LEPTON_STATE_SYNCING,
    LEPTON_STATE_CAPTURING,
    LEPTON_STATE_ERROR,
} lepton_state_t;

/** AGC mode */
typedef enum {
    LEPTON_AGC_DISABLE = 0,
    LEPTON_AGC_ENABLE  = 1,
} lepton_agc_mode_t;

/** Scene statistics from Lepton */
typedef struct {
    uint16_t min_val;
    uint16_t max_val;
    uint16_t mean_val;
} lepton_scene_stats_t;

/** Lepton driver handle */
typedef struct {
    I2C_HandleTypeDef *hi2c;        /**< Shared I2C handle for CCI */
    lepton_state_t     state;       /**< Current driver state */
    uint8_t            frame_buf[LEPTON_FRAME_SIZE]; /**< Raw14 frame buffer */
    bool               frame_valid; /**< True when frame_buf has valid data */
    uint32_t           frame_count; /**< Total frames captured */
    lepton_scene_stats_t stats;     /**< Cached scene statistics */
} lepton_handle_t;

/* --------------------------------------------------------------------------
 * Public API
 * ----------------------------------------------------------------------- */

/**
 * @brief Initialize the Lepton driver.
 *        Sets up GPIO for software SPI, and configures Lepton via I2C CCI.
 *
 * @param handle  Pointer to driver handle
 * @param hi2c    Pointer to HAL I2C handle (I2C1, shared)
 * @return 0 on success, negative on error
 */
int lepton_init(lepton_handle_t *handle, I2C_HandleTypeDef *hi2c);

/**
 * @brief Capture one complete thermal frame.
 *        Blocks until a full frame (4 segments, 240 packets) is received.
 *
 * @param handle  Pointer to driver handle
 * @return 0 on success, -1 on sync timeout
 */
int lepton_capture_frame(lepton_handle_t *handle);

/**
 * @brief Get pointer to the raw 14-bit frame buffer.
 *
 * @param handle  Pointer to driver handle
 * @return Pointer to frame data (160x120 uint16, big-endian)
 */
const uint8_t *lepton_get_frame(const lepton_handle_t *handle);

/**
 * @brief Check if a valid frame is available.
 */
bool lepton_frame_valid(const lepton_handle_t *handle);

/**
 * @brief Enable or disable AGC (Automatic Gain Control).
 *
 * @param handle  Pointer to driver handle
 * @param mode    LEPTON_AGC_ENABLE or LEPTON_AGC_DISABLE
 * @return 0 on success
 */
int lepton_set_agc(lepton_handle_t *handle, lepton_agc_mode_t mode);

/**
 * @brief Read scene statistics (min, max, mean pixel values).
 *
 * @param handle  Pointer to driver handle
 * @param stats   Output statistics
 * @return 0 on success
 */
int lepton_get_scene_stats(lepton_handle_t *handle, lepton_scene_stats_t *stats);

/**
 * @brief Perform FFC (Flat-Field Correction / shutter calibration).
 *
 * @param handle  Pointer to driver handle
 * @return 0 on success
 */
int lepton_run_ffc(lepton_handle_t *handle);

/**
 * @brief Convert raw14 frame to 8-bit grayscale with auto-scaling.
 *
 * @param handle   Pointer to driver handle
 * @param out_buf  Output buffer (LEPTON_WIDTH * LEPTON_HEIGHT bytes)
 */
void lepton_frame_to_grayscale(const lepton_handle_t *handle, uint8_t *out_buf);

#ifdef __cplusplus
}
#endif

#endif /* LEPTON_DRIVER_H */
