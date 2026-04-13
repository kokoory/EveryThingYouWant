# Hardware Configuration

## 1. Hardware Components

### Computing Boards

| 보드 | 역할 | 핵심 스펙 |
|------|------|----------|
| **KV260 (Kria)** | SDRE 실시간 제어 | Cortex-A53x4 + R5x2 + 256K Logic Cells + DSP 1,248개 |
| **Jetson Orin NX** | 비전 처리 (YOLO 락온) | CUDA, 이미 보유 |
| **Pixhawk 6C** | 일반 비행 제어 | PX4, EKF2, 내장 IMU (ICM-42688-P + ICM-20649) |

### Cameras (이중 구성)

| 카메라 | 용도 | 스펙 | 렌즈 | Jetson 연결 |
|--------|------|------|------|-------------|
| **Sony IMX219** | 탐색 (Search) | 8MP, 90fps | 광각 (FOV ~160deg) | CSI0 |
| **Sony IMX477** | 추적 (Track) | 12MP, 60fps | 16mm 망원 (FOV ~22deg) | CSI1 |

> OAK-D Lite를 사용하지 않는 이유: 스테레오 깊이 측정 유효 범위 ~35m, 원거리 표적에 부적합

### Servos & ESC

| 부품 | 프로토콜 | 비고 |
|------|----------|------|
| DroneCAN 서보 x3 | DroneCAN | delta_e, delta_a, delta_r |
| DroneCAN ESC x1 | DroneCAN | 추력 |
| 120ohm 종단저항 x2 | - | CAN 버스 양끝 필수 |

### Additional Components

| 부품 | 모델 | 용도 | 가격 |
|------|------|------|------|
| CAN 트랜시버 | SN65HVD230 | KV260 Pmod -> CAN 버스 | ~$2 |
| 실비행 기체 | Skywalker X8 | 날개폭 2.12m, 탑재 ~1kg | ~$300 |

### Optional IMU (Phase 5 이후 검토)

| 단계 | IMU | 가격 | 용도 |
|------|-----|------|------|
| Phase 1~4 | Pixhawk 내장 (MAVLink 경유) | 포함 | 알고리즘 개발 |
| Phase 5 (miss > 2m) | ADIS16470 | ~$100 | SPI 직결, 중간 성능 |
| Phase 5 (고기동 공중) | VectorNav VN-100 | ~$600 | 군용급 AHRS |

> 판단 기준: 공중 표적 miss distance > 2m이면 ADIS16470 먼저, 그래도 부족하면 VN-100

## 2. KV260 Internal Architecture

```
+=========================================================+
|                      KV260 Board                        |
|                                                         |
|  PS (Processing System)                                 |
|  +---------------------------------------------------+  |
|  | Cortex-A53 x4 (1.3GHz) - Linux                    |  |
|  |   - Jetson 통신 관리                               |  |
|  |   - MAVLink (Pixhawk) 관리                         |  |
|  |   - 모드 관리, 로깅                                |  |
|  +---------------------------------------------------+  |
|  | Cortex-R5 x2 (500MHz) - Bare-metal                 |  |
|  |   - SDRE 루프 전담 (1kHz)                          |  |
|  |   - Newton-Kleinman 반복                           |  |
|  |   - 레이턴시 deterministic                         |  |
|  +---------------------------------------------------+  |
|                                                         |
|  PL (Programmable Logic - FPGA)                         |
|  +---------------------------------------------------+  |
|  | Logic Cells: 256K                                  |  |
|  | DSP Slices:  1,248  --> 행렬 병렬 연산             |  |
|  | BRAM:        144                                   |  |
|  |                                                    |  |
|  | IP Blocks:                                         |  |
|  |   - AXI CAN IP (Xilinx 제공, 무료)                |  |
|  |   - Systolic Array (ARE 가속)                      |  |
|  |   - CORDIC IP (Givens Rotation)                    |  |
|  +---------------------------------------------------+  |
|                                                         |
|  External I/O                                           |
|  +---------------------------------------------------+  |
|  | J2 Pmod (12핀) - 유일한 범용 I/O                   |  |
|  | USB 3.0 x4                                         |  |
|  | Ethernet 1Gb                                       |  |
|  | J7, J8: IAS Camera (MIPI CSI-2 x4)                |  |
|  | J9: RPi Camera (MIPI CSI-2 x2)                    |  |
|  | HDMI / DP                                          |  |
|  +---------------------------------------------------+  |
+=========================================================+
```

## 3. KV260 Pmod J2 Pin Map (최종)

```
Pmod J2 (12핀: 8 signal + 4 power)
+-------+--------+----------+------------------+
| Pin   | FPGA   | 용도     | 연결 대상        |
+-------+--------+----------+------------------+
| Pin 1 | H12    | CAN TX   | SN65HVD230 TXD   |
| Pin 2 | B10    | CAN RX   | SN65HVD230 RXD   |
| Pin 3 | E10    | UART TX  | Jetson RX         |
| Pin 4 | E12    | UART RX  | Jetson TX         |
| Pin 5 | D10    | (예비)   | VN-100 SPI CLK    |
| Pin 6 | D11    | (예비)   | VN-100 SPI MOSI   |
| Pin 7 | C11    | (예비)   | VN-100 SPI MISO   |
| Pin 8 | B11    | (예비)   | VN-100 SPI CS     |
+-------+--------+----------+------------------+
| Pin 9 |  ---   | GND      |                   |
| Pin 10|  ---   | GND      |                   |
| Pin 11|  ---   | 3.3V     |                   |
| Pin 12|  ---   | 3.3V     |                   |
+-------+--------+----------+------------------+

Pin 5-8: 현재 미사용. VN-100/ADIS16470 장착 시 SPI 연결용으로 예약.
```

## 4. Full Wiring Diagram

```
+------------------+                    +------------------+
|  Jetson Orin NX  |                    |   Pixhawk 6C     |
|                  |                    |                  |
| CSI0: IMX219     |                    | 내장 IMU x2      |
| CSI1: IMX477     |   UART 115200     | EKF2             |
|                  |<------------------>| RC 수신기         |
| YOLO 락온        |  Pmod Pin 3,4     | Alt Hold         |
| LOS rate 계산    |                    | 페일세이프        |
| Kalman Filter    |                    |                  |
+------------------+                    +--------+---------+
                                                 |
                                          USB (MAVLink)
                                                 |
                                        +--------+---------+
                                        |     KV260        |
                                        |                  |
                                        | A53: 통신/모드   |
                                        | R5:  SDRE 1kHz   |
                                        | PL:  ARE 가속    |
                                        |      AXI CAN IP  |
                                        +--------+---------+
                                                 |
                                          Pmod Pin 1,2
                                                 |
                                        +--------+---------+
                                        |   SN65HVD230     |
                                        |  CAN 트랜시버    |
                                        +--------+---------+
                                                 |
                              DroneCAN Bus (120ohm 종단저항)
                    +--------+--------+--------+--------+
                    |        |        |        |        |
                 서보1    서보2    서보3     ESC    Pixhawk
                (delta_e) (delta_a) (delta_r) (추력)  (리스너)
```

## 5. SDRE Loop Timing Budget

```
제어 루프 주기: 1ms (1kHz)

+-- MAVLink 상태 수신 ----------- ~200us (500Hz, 2루프에 1회) --+
|                                                               |
+-- A(x), B(x) 갱신 ------------ ~50us                       --+
|                                                               |
+-- Newton-Kleinman ARE --------- ~50us (FPGA 가속 시)        --+
|   (Warm-start, 1~3회 반복)     ~500us (R5 소프트웨어 시)      |
|                                                               |
+-- K = R^-1 * B^T * P ---------- ~10us                       --+
|                                                               |
+-- u = -Kx 계산 ---------------- ~5us                        --+
|                                                               |
+-- DroneCAN 전송 --------------- ~100us                      --+
|                                                               |
= 총 ~415us (FPGA) 또는 ~865us (S/W only)
  여유: ~585us (FPGA) 또는 ~135us (S/W only)
```

## 6. Performance Comparison by Platform

| 하드웨어 | Schur 분해 시간 (12x12) | 루프 주파수 |
|----------|------------------------|------------|
| STM32H7 (480MHz) | ~20ms | ~50Hz |
| Teensy 4.1 (600MHz) | ~10ms | ~100Hz |
| Jetson Orin NX (CUDA) | ~1ms | ~1kHz |
| KV260 PL (FPGA) | ~50us | ~20kHz |
| Zynq UltraScale+ | ~10us | ~100kHz |

## 7. MAVLink Data Requirements

KV260 SDRE에 필요한 Pixhawk 상태 데이터:

| 상태 변수 | MAVLink 메시지 | 전송 주기 |
|-----------|---------------|----------|
| phi, theta, psi (오일러각) | ATTITUDE | 200Hz |
| p, q, r (각속도) | ATTITUDE | 200Hz |
| u, v, w (속도) | VFR_HUD + LOCAL_POSITION_NED | 200Hz |
| x, y, z (위치) | LOCAL_POSITION_NED | 50Hz |

PX4 파라미터 설정:
```
MAV_DATA_STREAM_EXTRA1 -> ATTITUDE 200Hz
MAV_DATA_STREAM_RAWSENSORS -> 200Hz
```
