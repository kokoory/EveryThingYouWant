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

## 8. KV260 Development Environment Setup

### 8-1. Vitis/Vivado 설치

```bash
# 권장 버전: Vitis 2023.2 (KV260 공식 지원)
# 다운로드: https://www.xilinx.com/support/download/index.html/content/xilinx/en/downloadNav/vivado-design-tools.html

# Ubuntu 22.04 LTS 권장
sudo apt update
sudo apt install -y libtinfo5 libncurses5 xterm

# Vitis 통합 설치 (Vivado + Vitis HLS + PetaLinux 포함)
# 설치 용량: ~100GB
chmod +x Xilinx_Unified_2023.2_*_Lin64.bin
./Xilinx_Unified_2023.2_*_Lin64.bin
# 설치 시 "Vitis" 선택 (Vivado, HLS 자동 포함)

# 환경 설정
source /tools/Xilinx/Vitis/2023.2/settings64.sh
```

### 8-2. KV260 PetaLinux 이미지

```bash
# 공식 BSP 다운로드
# https://www.xilinx.com/support/download/index.html/content/xilinx/en/downloadNav/embedded-design-tools.html

# PetaLinux 프로젝트 생성
petalinux-create -t project -s xilinx-kv260-starterkit-v2023.2.bsp
cd xilinx-kv260-starterkit-v2023.2

# 빌드 (30분~1시간)
petalinux-build

# SD 카드 이미지 생성
petalinux-package --boot --u-boot
```

### 8-3. R5 Bare-metal 개발 (Vitis IDE)

```
1. Vitis IDE 실행
2. File -> New -> Application Project
3. Platform: kv260_custom (또는 기본 제공)
4. Processor: psu_cortexr5_0
5. OS: standalone (bare-metal)
6. Template: Empty Application

R5 프로젝트 구조:
  src/
  |-- main.c          # SDRE 메인 루프 (Timer ISR)
  |-- sdre_solver.c   # Newton-Kleinman C 구현
  |-- matrix_ops.c    # CMSIS-DSP 행렬 연산 래퍼
  |-- can_driver.c    # AXI CAN 드라이버
  |-- shared_mem.c    # A53과 공유 메모리 인터페이스
```

## 9. Vitis HLS Guide for SDRE

### 9-1. HLS용 C++ 행렬 연산

```cpp
// hls_matrix.h - HLS 합성 가능한 행렬 연산
#include <hls_math.h>

#define N_STATE 4   // 종방향 4차
#define N_INPUT 2

typedef float mat_t;

// 4x4 행렬 곱: C = A * B
void mat_mul_4x4(
    mat_t A[N_STATE][N_STATE],
    mat_t B[N_STATE][N_STATE],
    mat_t C[N_STATE][N_STATE]
) {
    #pragma HLS PIPELINE II=1
    #pragma HLS ARRAY_PARTITION variable=A complete dim=2
    #pragma HLS ARRAY_PARTITION variable=B complete dim=1

    for (int i = 0; i < N_STATE; i++) {
        for (int j = 0; j < N_STATE; j++) {
            mat_t sum = 0;
            for (int k = 0; k < N_STATE; k++) {
                sum += A[i][k] * B[k][j];
            }
            C[i][j] = sum;
        }
    }
}
```

### 9-2. Lyapunov 방정식 솔버 (HLS)

```cpp
// Newton-Kleinman 1 iteration을 HLS로 가속
// S^T * P + P * S = -RHS  (Lyapunov)
// Bartels-Stewart 알고리즘의 단순화 버전

void lyapunov_solve_4x4(
    mat_t S[N_STATE][N_STATE],      // 입력: 폐루프 행렬
    mat_t RHS[N_STATE][N_STATE],    // 입력: -(Q + K^T R K)
    mat_t P[N_STATE][N_STATE]       // 출력: 해 P
) {
    #pragma HLS INTERFACE s_axilite port=return
    #pragma HLS INTERFACE m_axi port=S
    #pragma HLS INTERFACE m_axi port=RHS
    #pragma HLS INTERFACE m_axi port=P

    // Schur decomposition of S -> Q * T * Q^T
    // (실제 구현에서는 Xilinx QR IP 또는 직접 Givens rotation)
    // 여기서는 간략화

    // 4x4의 경우 직접 반복법으로도 충분히 빠름
    mat_t P_new[N_STATE][N_STATE];
    mat_t P_old[N_STATE][N_STATE];

    // 초기화
    for (int i = 0; i < N_STATE; i++)
        for (int j = 0; j < N_STATE; j++)
            P_old[i][j] = RHS[i][j];

    // 반복법 (fixed-point iteration)
    for (int iter = 0; iter < 50; iter++) {
        #pragma HLS PIPELINE
        // P_new = S^T * P_old + P_old * S + RHS 를 0으로
        // ... (실제 구현)
    }
}
```

### 9-3. 합성 보고서 해석

```
합성 후 확인할 것:

1. Latency (클럭 사이클)
   - 4x4 Lyapunov: 목표 < 500 cycles @ 300MHz = 1.67us
   - 12x12 Lyapunov: 목표 < 5000 cycles = 16.7us

2. Resource Usage
   - DSP: < 200 (총 1,248개 중)
   - BRAM: < 20 (총 144개 중)
   - LUT: < 50K (총 256K 중)

3. Timing
   - 목표 클럭: 300MHz (3.33ns)
   - Timing met? (WNS > 0)

4. II (Initiation Interval)
   - 파이프라인 II=1: 매 클럭 새 데이터 처리 가능
```

## 10. Bill of Materials (BOM)

| # | 부품 | 모델 | 수량 | 단가 | 소계 | 비고 |
|---|------|------|------|------|------|------|
| 1 | FPGA 보드 | AMD Kria KV260 | 1 | $250 | $250 | 메인 제어 |
| 2 | 비전 보드 | Jetson Orin NX (이미 보유) | 1 | $0 | $0 | 보유 |
| 3 | 비행 컨트롤러 | Pixhawk 6C | 1 | $250 | $250 | PX4, 내장 IMU |
| 4 | 광각 카메라 | Sony IMX219 모듈 | 1 | $25 | $25 | 탐색용 |
| 5 | 망원 카메라 | RPi HQ Camera (IMX477) | 1 | $50 | $50 | 추적용 |
| 6 | 망원 렌즈 | 16mm C-mount (10MP) | 1 | $30 | $30 | HQ Cam용 |
| 7 | 광각 렌즈 | 6mm C-mount (3MP) | 1 | $20 | $20 | HQ Cam용 |
| 8 | CAN 트랜시버 | SN65HVD230 | 2 | $2 | $4 | KV260 + 예비 |
| 9 | DroneCAN 서보 | Hitec D-Series x3 | 3 | $80 | $240 | de, da, dr |
| 10 | DroneCAN ESC | Zubax Myxa | 1 | $150 | $150 | 추력 |
| 11 | 종단저항 | 120ohm | 2 | $1 | $2 | CAN 버스 양끝 |
| 12 | 기체 | Skywalker X8 | 1 | $300 | $300 | 실비행용 |
| 13 | RC 수신기 | FrSky R-XSR | 1 | $30 | $30 | Pixhawk SBUS |
| 14 | RC 송신기 | FrSky Taranis (보유 가정) | 1 | $0 | $0 | |
| 15 | 배터리 | 4S 5000mAh LiPo | 2 | $50 | $100 | |
| 16 | SD 카드 | 32GB UHS-I | 2 | $10 | $20 | KV260 + 로깅 |
| | | | | **합계** | **~$1,471** | |

### Phase별 구매 순서

```
Phase 1 (Python 시뮬): 추가 구매 없음 ($0)
Phase 2 (C++ 포팅):    Teensy 4.1 ($30) - 선택사항
Phase 3 (FPGA):        KV260 ($250)
Phase 4 (비전 통합):   카메라 x2 + 렌즈 ($125)
Phase 5 (실비행):      Pixhawk + 서보 + ESC + 기체 + 배터리 (~$1,070)
```
