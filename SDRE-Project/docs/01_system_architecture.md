# System Architecture

## 1. Overall Data Flow

```
=== SENSOR LAYER ===

[IMX219 광각 카메라]     [IMX477 망원 카메라]     [Pixhawk 6C]
  CSI0 (Jetson)            CSI1 (Jetson)           내장 IMU (ICM-42688-P)
  FOV ~160deg              FOV ~22deg              EKF2 센서 퓨전
  표적 탐색용              정밀 추적용             자세/위치/속도
        |                        |                       |
        +----------+-------------+                       |
                   |                                     |
                   v                                     |
=== PROCESSING LAYER ===                                 |
                                                         |
[Jetson Orin NX - Linux]                                 |
  YOLO 표적 검출                                         |
  모드 전환 (탐색 -> 추적)                               |
  LOS angle / LOS rate 계산                              |
  Kalman Filter (표적 상태 추정)                         |
  거리 추정: R = h / tan(lambda_elevation)               |
        |                                                |
        | UART (Pmod Pin 3,4)                            |
        v                                                |
[KV260 - Cortex-A53 Linux]  <--- MAVLink (USB) ---------+
  Jetson 통신 관리
  모드 관리 (일반/공격)
  로깅
        |
        v
[KV260 - Cortex-R5 Bare-metal]
  SDRE 실시간 루프 (1kHz 목표)
  Newton-Kleinman 반복
  상태 갱신: A(x), B(x) -> ARE -> K(x) -> u = -Kx
        |
        | AXI4
        v
[KV260 - PL FPGA]
  ARE 가속 (Systolic Array)
  AXI CAN IP (DroneCAN)
  PWM 생성 (필요 시)
        |
        | Pmod Pin 1,2 -> SN65HVD230 트랜시버
        v
=== ACTUATOR LAYER ===

[DroneCAN Bus] --- 120ohm 종단저항
  |--- DroneCAN 서보 x3 (delta_e, delta_a, delta_r)
  |--- DroneCAN ESC x1 (추력)
  |--- Pixhawk 6C (버스 리스너/마스터)
```

## 2. Control Authority Transfer (제어권 전환)

```
일반 비행 모드:
  Pixhawk = CAN 버스 마스터 (PX4 PID 제어)
  KV260   = CAN 버스 리스너 (모니터링)
        |
        | 공격 모드 트리거 (Jetson 락온 성공)
        v
공격 모드:
  KV260   = CAN 버스 마스터 (SDRE 직접 제어)
  Pixhawk = CAN 버스 리스너 (상태 정보 제공)
        |
        | 교전 완료 또는 페일세이프
        v
일반 비행 모드 복귀
```

> **핵심**: MUX 하드웨어 불필요. DroneCAN 버스 마스터 전환으로 소프트웨어적 제어권 이양.

## 3. Three Target Scenarios (3종 표적)

### 3-1. 지상 고정 표적

```
표적 좌표 (GPS/카메라) --> 거리/방위각 계산
                              |
                   종방향 SDRE --> 강하각 제어
                   횡방향 SDRE --> 방위각 제어
                              |
                         표적 위로 수렴
```
- **난이도**: ★★
- **SDRE 모델**: 종횡 분리 4차 (가능)
- **유도 법칙**: LOS angle -> 0 수렴

### 3-2. 지상 이동 표적

```
카메라 --> 표적 위치 추적
              |
        Kalman Filter (위치 + 속도 추정)
              |
        PNG: a_cmd = N * Vc * lambda_dot
              |
        SDRE --> 서보 명령
```
- **난이도**: ★★★
- **SDRE 모델**: 종횡 분리 4차 (가능)
- **추가 요소**: Kalman Filter (표적 속도 추정)

### 3-3. 공중 표적

```
3D 교전 기하:
  PNG 3D:
    a_cmd_y = N * Vc * lambda_dot_yaw
    a_cmd_z = N * Vc * lambda_dot_pitch
        |
  6-DOF SDRE 필수
  표적 기동 추정 필수
  Collision triangle 계산
```
- **난이도**: ★★★★★
- **SDRE 모델**: 6-DOF 통합 (9차 이상) 필수
- **추가 요소**: 3D PNG, 기동 추정

### 통합 모드 전환

```
[모드 선택]
    |
    +-- 고정 표적 --> LOS angle 수렴 모드 (분리 4차 SDRE)
    |
    +-- 이동 표적 --> PNG + Kalman 모드 (분리 4차 SDRE)
    |
    +-- 공중 표적 --> 3D PNG + 기동 추정 모드 (6-DOF SDRE)
```

> Q, R 가중치와 모델만 바꿔서 세 모드 전환 가능

## 4. Camera Dual-Mode Operation

```
[탐색 모드 - IMX219 광각]
  YOLO 표적 검출
  FOV ~160deg
  해상도: 8MP / 90fps
      |
      | 락온 성공
      v
[추적 모드 - IMX477 망원]
  정밀 LOS rate 계산
  FOV ~22deg (16mm 렌즈)
  해상도: 12MP / 60fps
  픽셀당 각도 분해능 높음
```

거리 추정 (깊이 센서 없이):
- **기하학**: `R = h / tan(lambda_elevation)` (자기 고도 + LOS angle)
- **광류**: 표적 픽셀 크기 변화율
- **알려진 크기**: `R = (실제크기 * 초점거리) / 픽셀크기`

## 5. State Variables

### 종횡 분리 모델 (4차 + 4차)

```
종방향 (앞뒤/상하):              횡방향 (좌우):
x = [u, w, q, theta]            x = [v, p, r, phi]
     전진속도                         횡속도
     수직속도                         롤율
     피치율                           요율
     피치각                           롤각

--> 엘리베이터 제어               --> 에일러론 + 러더 제어
```

### 6-DOF 통합 모델 (공중 표적용)

```
x = [u, v, w, p, q, r, phi, theta, psi]  (9차 이상)
     전부 커플링 되어 있음
--> 엘리베이터/에일러론/러더/추력 통합 제어
```

### IGC 상태 변수 (Menon & Ohlmeyer 방식)

```
x_IGC = [lambda, lambda_dot, phi, theta, psi, p, q, r, ...]
         LOS 각도/각속도 포함
--> lambda_dot -> 0 수렴 = 표적으로 수렴 (타격)
```

## 6. SDRE Real-Time Strategy

### Newton-Kleinman with Warm Start

```
매 루프 (1kHz):
  1. 현재 상태 x(t) 읽기 (Pixhawk MAVLink)
  2. A(x), B(x) 갱신 (비선형 모델 -> 현재 점에서 SDC 분할)
  3. ARE 풀기:
     - 초기값: 이전 루프의 P(x_{t-1})  <-- Warm Start
     - Newton-Kleinman 1~3회 반복 (2차 수렴)
  4. K = R^{-1} * B^T * P 계산
  5. u = -Kx 출력 --> DroneCAN 서보
```

### Gain Update Frequency (양창덕 2008 논문 결과)

```
Tk = 200*dt 까지 성능 차이 거의 없음
dt = 0.001초 기준 --> 200*dt = 0.2초 = 5Hz
--> 매 루프 ARE 풀 필요 없이 5~10Hz로도 충분
--> KV260 연산 부담 대폭 감소
```
