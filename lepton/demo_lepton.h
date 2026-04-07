/**
 * @file demo_lepton.h
 * @brief Lepton 3.5 thermal camera demo integration for EKH05
 *
 * Integrates the Lepton driver with the EKH05 Demo application,
 * adding HTTP REST endpoints to serve thermal images via Wi-Fi HaLow.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef DEMO_LEPTON_H
#define DEMO_LEPTON_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

/**
 * @brief Initialize the Lepton thermal camera subsystem.
 *        Sets up the driver and starts the capture task.
 *        Call this from periphs_start() after MX_I2C1_Init().
 */
void lepton_demo_init(void);

/**
 * @brief Get a pointer to the latest thermal BMP image.
 *
 * @param size  Output: size of the BMP image in bytes
 * @return Pointer to BMP data, or NULL if no image available
 */
const uint8_t *lepton_demo_get_bmp(uint32_t *size);

/**
 * @brief Get a pointer to the latest thermal raw grayscale data.
 *
 * @param width   Output: image width
 * @param height  Output: image height
 * @return Pointer to grayscale data (width*height bytes)
 */
const uint8_t *lepton_demo_get_grayscale(int *width, int *height);

/**
 * @brief Check if the Lepton is initialized and running.
 */
bool lepton_demo_is_running(void);

/**
 * @brief Get the current frame count.
 */
uint32_t lepton_demo_get_frame_count(void);

/**
 * @brief Trigger FFC (shutter calibration).
 */
void lepton_demo_run_ffc(void);

/* --------------------------------------------------------------------------
 * HTTP REST Endpoint Handlers
 *
 * These functions follow the lwIP httpd CGI/SSI pattern used by the
 * EKH05 Demo. Register them in http.c alongside existing endpoints.
 * ----------------------------------------------------------------------- */

/**
 * @brief REST endpoint: GET /thermal.bmp
 *        Returns the latest thermal image as a 24-bit BMP file.
 *
 * Usage in http.c restfs registration:
 *   { "/thermal.bmp", rest_ep_get_thermal_bmp }
 *
 * @param buf      Output buffer
 * @param buf_len  Buffer size
 * @param more     Set to true if more data to send
 * @return Number of bytes written to buf
 */
uint16_t rest_ep_get_thermal_bmp(char *buf, uint16_t buf_len, bool *more);

/**
 * @brief REST endpoint: GET /thermal.json
 *        Returns thermal statistics as JSON.
 *
 * @param buf      Output buffer
 * @param buf_len  Buffer size
 * @param more     Set to true if more data to send
 * @return Number of bytes written to buf
 */
uint16_t rest_ep_get_thermal_json(char *buf, uint16_t buf_len, bool *more);

/**
 * @brief REST endpoint: GET /thermal_ffc
 *        Triggers FFC calibration and returns status.
 */
uint16_t rest_ep_thermal_ffc(char *buf, uint16_t buf_len, bool *more);

#ifdef __cplusplus
}
#endif

#endif /* DEMO_LEPTON_H */
