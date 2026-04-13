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

## 7. Software Architecture Detail

### KV260 Cortex-A53 (Linux) - 통신/관리

```
[systemd services]
  |
  +-- mavlink_bridge.service
  |     pymavlink으로 Pixhawk USB MAVLink 파싱
  |     ATTITUDE, LOCAL_POSITION_NED 메시지 수신
  |     공유 메모리(shared memory)로 R5에 전달
  |
  +-- jetson_comm.service
  |     UART 115200으로 Jetson LOS 데이터 수신
  |     프로토콜: [header][lambda][lambda_dot][target_state][checksum]
  |     공유 메모리로 R5에 전달
  |
  +-- mode_manager.service
  |     모드 상태 머신 관리
  |     Jetson 락온 신호 수신 -> 공격 모드 트리거
  |     R5에 모드 전환 명령
  |
  +-- logger.service
        비행 데이터 로깅 (CSV/binary)
        post-flight 분석용
```

### KV260 Cortex-R5 (Bare-metal) - SDRE 실시간 루프

```
main_loop() @ 1kHz (Timer Interrupt):
  |
  +-- 1. read_shared_memory()
  |       MAVLink 상태 (phi, theta, psi, p, q, r, u, v, w)
  |       Jetson LOS 데이터 (lambda, lambda_dot)
  |       현재 모드
  |
  +-- 2. if (mode == ATTACK):
  |       compute_sdc(x)         --> A(x), B(x)
  |       newton_kleinman(A, B)  --> P, K
  |       u = -K * x             --> 서보 명령
  |       can_send(u)            --> DroneCAN 전송
  |
  |   elif (mode == NORMAL):
  |       // Pixhawk가 CAN 마스터, R5는 모니터링만
  |       pass
  |
  +-- 3. log_to_shared_memory()
          P 행렬, K 행렬, u, 풀이 시간 기록
```

### Jetson Orin NX (Linux) - 비전 처리

```
[main pipeline]
  |
  +-- camera_manager (thread 1)
  |     CSI0: IMX219 광각 캡처 (30fps)
  |     CSI1: IMX477 망원 캡처 (30fps)
  |     모드에 따라 활성 카메라 전환
  |
  +-- yolo_detector (thread 2)
  |     TensorRT 최적화 YOLO
  |     입력: 카메라 프레임
  |     출력: bounding box, confidence, class
  |
  +-- los_calculator (thread 3)
  |     픽셀 좌표 -> LOS angle 변환
  |     연속 프레임 차분 -> LOS rate 계산
  |     Kalman filter로 노이즈 제거
  |
  +-- uart_sender (thread 4)
        KV260으로 LOS 데이터 전송 @ 100Hz
```

## 8. State Machine for Mode Transitions

```
                    +--------+
         power on   |  INIT  |  하드웨어 초기화, 센서 체크
                    +---+----+
                        |
                        v
                    +--------+
         RC 입력    | MANUAL |  조종기 직접 제어 (Pixhawk PID)
                    +---+----+
                        |  스위치 전환
                        v
                  +-----------+
                  | ALT_HOLD  |  고도 유지 (Pixhawk)
                  +-----+-----+
                        |  AUTO 스위치
                        v
                  +-----------+
                  | AUTO_NAV  |  웨이포인트 비행 (Pixhawk)
                  +-----+-----+
                        |  표적 영역 진입
                        v
                  +-----------+
                  |  SEARCH   |  IMX219 광각으로 표적 탐색 (Jetson YOLO)
                  +-----+-----+
                        |  YOLO 검출 성공 (confidence > 0.7)
                        v
                  +-----------+
                  |  TRACK    |  IMX477 망원으로 정밀 추적
                  |           |  LOS rate 안정화 대기
                  +-----+-----+
                        |  LOS rate 안정 + 거리 < threshold
                        v
                  +-----------+
                  |  ATTACK   |  KV260 SDRE 제어권 인수
                  |           |  DroneCAN 마스터 전환
                  |           |  PNG + SDRE 교전
                  +-----+-----+
                        |  교전 완료 or 실패
                        v
                  +-----------+
                  |   RTL     |  Pixhawk 제어권 복귀
                  |           |  Return to Launch
                  +-----------+

페일세이프 전환 (어느 상태에서든):
  RC 신호 끊김      --> RTL
  배터리 < 20%      --> RTL
  IMU 이상          --> MANUAL (RC 우선)
  SDRE 발산 감지    --> ALT_HOLD (Pixhawk PID 복귀)
  CAN 버스 에러     --> MANUAL
```

### 전환 조건 상세

| From | To | 조건 | 타임아웃 |
|------|----|------|---------|
| SEARCH | TRACK | YOLO confidence > 0.7, 3프레임 연속 | 60초 탐색 실패 -> RTL |
| TRACK | ATTACK | LOS rate 분산 < threshold, 거리 < 1km | 30초 안정화 실패 -> SEARCH |
| ATTACK | RTL | miss distance 계산 완료 or 고도 < 50m | 교전 시간 > 30초 -> RTL |

## 9. DroneCAN Bus Master Handover Protocol

```
일반 비행 시:
  Pixhawk: Node ID 1 (마스터), 서보 명령 전송 @ 50Hz
  KV260:   Node ID 2 (리스너), 버스 모니터링만

공격 모드 전환 과정 (5단계):
  1. KV260 A53 -> R5: ATTACK 모드 명령
  2. KV260 -> Pixhawk: MAVLink COMMAND_LONG (SDRE_TAKEOVER)
  3. Pixhawk: 서보 명령 전송 중지, 리스너로 전환
  4. KV260 R5: DroneCAN 서보 명령 전송 시작 @ 200Hz
  5. KV260 -> Pixhawk: MAVLink HEARTBEAT에 SDRE_ACTIVE 플래그

복귀 과정 (역순):
  1. KV260: 교전 완료 판단
  2. KV260: 서보 명령 전송 중지
  3. KV260 -> Pixhawk: MAVLink COMMAND_LONG (SDRE_RELEASE)
  4. Pixhawk: 서보 명령 재개, 마스터 복귀
  5. 모드 -> RTL

CAN 버스 에러 처리:
  Bus-off 감지: KV260 AXI CAN IP의 에러 카운터 모니터링
  복구: 자동 bus-off recovery (128회 11-recessive bit 후)
  타임아웃: 서보 명령 100ms 미수신 시 -> 페일세이프
```

## 10. Timing Analysis (WCET)

```
1kHz 제어 루프 타이밍 버짓 (최악 case):

[0us]     Timer interrupt 발생
[10us]    Shared memory 읽기 (MAVLink + LOS 데이터)
[60us]    A(x), B(x) 수치 야코비안 (12x12)
[560us]   Newton-Kleinman ARE (R5 software, worst case 3 iterations)
  or
[110us]   Newton-Kleinman ARE (PL FPGA 가속)
[570us]   K = R^{-1} B^T P 계산 (행렬 곱)
[580us]   u = -Kx 계산
[680us]   DroneCAN 프레임 구성 + 전송
[700us]   로깅 데이터 기록
[700us]   ========= 루프 완료 =========

여유: 300us (S/W) or 890us (FPGA)
Jitter 버짓: < 50us (Timer interrupt 지터)
```

### MAVLink 메시지 스케줄링

```
Pixhawk 전송 주기:
  ATTITUDE:            200Hz (5ms)   --> phi, theta, psi, p, q, r
  LOCAL_POSITION_NED:   50Hz (20ms)  --> x, y, z, vx, vy, vz
  VFR_HUD:             50Hz (20ms)  --> airspeed, groundspeed

KV260 A53 수신 + 파싱:
  USB bulk transfer latency: ~1ms
  파싱 + shared memory 쓰기: ~0.5ms
  총 레이턴시: ~1.5ms

R5 SDRE는 최신 MAVLink 데이터를 사용하되,
새 데이터가 없으면 이전 값을 재사용 (200Hz 수신, 1kHz 사용)
```

## 11. Data Logging Architecture

### Phase별 로깅 대상

| Phase | 로깅 대상 | 형식 | 저장 위치 |
|-------|----------|------|----------|
| Phase 1 (Python) | 전체 상태, 제어, P, K, 풀이시간 | CSV/numpy | PC |
| Phase 4 (HITL) | R5 루프 타이밍, CAN 메시지, MAVLink | binary | KV260 SD |
| Phase 5 (비행) | 위와 동일 + GPS, IMU raw, 카메라 LOS | binary + video | KV260 SD |

### 로그 포맷

```
Binary log record (고정 크기, 빠른 쓰기):
  [timestamp_us: uint64]      8 bytes
  [state[12]: float32]       48 bytes  (u,v,w,p,q,r,phi,theta,psi,pn,pe,pd)
  [control[4]: float32]      16 bytes  (de,da,dr,dt)
  [P_diag[12]: float32]      48 bytes  (P 대각 성분)
  [K_flat[48]: float32]     192 bytes  (K 전체, 4x12)
  [solve_time_us: uint32]     4 bytes
  [nk_iterations: uint8]      1 byte
  [mode: uint8]               1 byte
  [los_lambda: float32]       4 bytes
  [los_lambda_dot: float32]   4 bytes
  ---
  Total: 326 bytes/record
  @ 1kHz = 326 KB/s = ~1.1 GB/hour
```

### Post-flight 분석 파이프라인

```
1. 바이너리 로그 -> Python 파서 -> pandas DataFrame
2. 시간 동기화 (MAVLink timestamp 기준)
3. 분석:
   - 상태 추적 오차 (RMSE, 시계열)
   - 제어 입력 히스토그램
   - SDRE 풀이 시간 분포
   - P, K 행렬 변화 추이
   - LOS rate 수렴 그래프 (표적 교전 시)
4. 그래프 생성 (matplotlib)
5. 논문 Figure로 직접 사용
```
