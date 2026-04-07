# Lepton 3.5 Integration Guide for MM6108-EKH05

## Hardware Wiring

### SparkFun Lepton Breakout -> EKH05 Debug/Spare Header

```
SparkFun Breakout     EKH05 Board (STM32U585)
┌─────────────┐       ┌──────────────────────┐
│ GND  ────────────── │ GND                  │
│ VIN  ────────────── │ 3.3V                 │
│ CLK  ────────────── │ PD11 (SPARE_GPIO)    │
│ MISO ────────────── │ PD15 (SPARE_GPIO)    │
│ MOSI ────────(NC)   │                      │
│ CS   ────────────── │ PC13 (SPARE_GPIO)    │
│ SDA  ────────────── │ I2C1_SDA (shared)    │
│ SCL  ────────────── │ I2C1_SCL (shared)    │
└─────────────┘       └──────────────────────┘
```

**Note:** MOSI is not used by Lepton (read-only). Leave unconnected or tie to GND.

### I2C Connection
The Lepton's CCI (I2C) shares the I2C1 bus with the onboard accelerometer
and temperature sensor. The Lepton I2C address is **0x2A** (7-bit),
which does not conflict with existing sensors.

## Software Integration

### Step 1: Add source files to your project

Copy all files from `lepton/` into your EKH05 Demo project:

```
Example/EKH05-Demo/
├── lepton_driver.h      (copy)
├── lepton_driver.c      (copy)
├── demo_lepton.h        (copy)
├── demo_lepton.c        (copy)
├── thermal_palette.h    (copy)
├── thermal_page.h       (copy)
├── peripherals.c        (modify)
├── http.c               (modify)
└── ...existing files...
```

### Step 2: Modify `peripherals.c`

Add the Lepton initialization in `periphs_start()`:

```c
// Add include at top of peripherals.c:
#include "demo_lepton.h"

// In periphs_start(), after BSP_CAMERA_Init():
void periphs_start(void)
{
    // ... existing init code ...

    MX_I2C1_Init();    // Already exists - shared with Lepton

    // ... existing camera init ...

    // ADD: Initialize Lepton 3.5 thermal camera
    lepton_demo_init();

    // ... rest of existing code ...
}
```

### Step 3: Modify `http.c`

Register the thermal REST endpoints:

```c
// Add include at top of http.c:
#include "demo_lepton.h"
#include "thermal_page.h"

// In app_init(), add REST endpoint registrations alongside existing ones:
void app_init(void)
{
    // ... existing endpoint registrations ...

    // ADD: Thermal camera endpoints
    restfs_register("/thermal.bmp",   rest_ep_get_thermal_bmp);
    restfs_register("/thermal.json",  rest_ep_get_thermal_json);
    restfs_register("/thermal_ffc",   rest_ep_thermal_ffc);

    // ADD: Thermal HTML page (static)
    // Register thermal_html_page as static file "/thermal.html"
    // using lwIP httpd fs or restfs mechanism

    // ... rest of existing code ...
}
```

### Step 4: Configure `main.h` pin definitions (optional)

The driver uses the pin definitions from `main.h`. If you want to change
pins, modify these defines in `lepton_driver.h`:

```c
#define LEPTON_CS_PORT       GPIOC
#define LEPTON_CS_PIN        GPIO_PIN_13
#define LEPTON_CLK_PORT      GPIOD
#define LEPTON_CLK_PIN       GPIO_PIN_11
#define LEPTON_MISO_PORT     GPIOD
#define LEPTON_MISO_PIN      GPIO_PIN_15
```

### Step 5: STM32CubeMX Configuration

If using CubeMX to regenerate code, ensure these pins are set to GPIO:
- PC13: GPIO_Output (CS)
- PD11: GPIO_Output (CLK)
- PD15: GPIO_Input (MISO)

These are already defined as SPARE_GPIO in the EKH05 default configuration.

## Build Configuration

Add the lepton source files to your build system (CMake/Makefile/Keil):

```makefile
# Add to source files
C_SOURCES += lepton_driver.c demo_lepton.c

# Add to include paths
C_INCLUDES += -I./lepton
```

## Usage

1. Power on the EKH05 board with Lepton 3.5 connected
2. Connect to the Wi-Fi HaLow network
3. Open browser: `http://<device-ip>/thermal.html`
4. Live thermal image will auto-refresh at ~5 fps

### REST API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/thermal.bmp` | GET | Latest thermal image (24-bit BMP, Ironbow palette) |
| `/thermal.json` | GET | Thermal statistics (JSON) |
| `/thermal_ffc` | GET | Trigger FFC shutter calibration |
| `/thermal.html` | GET | Live view web page |

### JSON Response Example (`/thermal.json`)
```json
{
  "running": true,
  "frames": 1234,
  "min": 7800,
  "max": 8200,
  "mean": 8050,
  "width": 160,
  "height": 120
}
```

## Performance

| Metric | Value |
|---|---|
| Resolution | 160 x 120 |
| Frame rate (capture) | ~8.7 fps |
| Frame rate (web) | ~5 fps |
| BMP image size | 57,654 bytes |
| Bandwidth needed | ~230 KB/s |
| Wi-Fi HaLow capacity | 32.5 Mbps |
| CPU overhead | ~15% (SW SPI bit-bang) |

## Troubleshooting

| Problem | Solution |
|---|---|
| "CCI communication failed" | Check I2C wiring (SDA/SCL), verify 3.3V power |
| "Sync failed after retries" | Check SPI wiring (CS/CLK/MISO), verify solder joints |
| Red/blank thermal image | Run FFC calibration, wait 2 min for sensor warmup |
| Low frame rate | Normal for SW SPI; HW SPI (MikroBus) would be faster |
| I2C conflicts | Lepton uses 0x2A; check no address collision with sensors |
