# Simulation Guide

## 1. 환경 설정

### 1-1. Python 패키지 설치

```bash
cd SDRE-Project/code
pip install -r requirements.txt
```

requirements.txt:
```
numpy>=1.24.0
scipy>=1.10.0
matplotlib>=3.7.0
```

### 1-2. 프로젝트 구조

```
SDRE-Project/code/
|-- sdre_solver.py             # ARE 솔버 + Newton-Kleinman + SDRE 클래스
|-- aerosonde_model.py         # Aerosonde 6-DOF 모델 + 트림 + SDC
|-- lqr_vs_sdre_comparison.py  # PID/LQR/SDRE 비교 시뮬레이션
|-- requirements.txt
```

### 1-3. mavsim_python 설정 (선택사항)

```bash
git clone https://github.com/byu-magicc/mavsim_python.git
cd mavsim_python
pip install -e .
```

> 본 프로젝트 코드는 mavsim_python 없이도 독립 실행 가능.
> mavsim_python은 Beard & McLain 교재와 함께 학습할 때 사용.

## 2. Phase 1: SDRE 알고리즘 검증

### 2-1. Step 1: Aerosonde 트림 계산

```bash
python aerosonde_model.py
```

**검증할 것:**
- 트림 잔차 `||xdot|| < 1e-8` 이어야 함
- 트림 받음각 alpha ~= 2~5도 (합리적 범위)
- 트림 엘리베이터 de ~= -2~-5도 (기수 내림 경향 보상)
- A 행렬 고유값: 모든 실수부 < 0 (안정)

**기대 결과:**
```
트림 상태:
    u = ~34.9 m/s  (순항 속도의 x 성분)
    w = ~1.5 m/s   (작은 수직 성분 = 받음각)
    theta = ~0.04 rad (~2.5도)
```

### 2-2. Step 2: ARE 솔버 검증

```bash
python sdre_solver.py
```

**검증할 것:**
- scipy ARE와 Newton-Kleinman 해의 차이 < 1e-8
- 비선형 진자에서 SDRE가 다양한 상태에서 작동
- Warm-start 효과: 반복 횟수 감소 확인

**핵심 지표:**
```
4-state (종방향): ARE 풀이 시간 ~0.1ms (PC)
12-state (6-DOF): ARE 풀이 시간 ~1ms (PC)
Warm-start 반복: 1~3회 (cold-start 대비 5~10배 감소)
```

### 2-3. Step 3: PID vs LQR vs SDRE 비교

```bash
python lqr_vs_sdre_comparison.py
```

**3가지 시나리오:**

| # | 시나리오 | 목적 | 핵심 관찰 |
|---|---------|------|----------|
| 1 | 피치 5도 스텝 | 기본 추종 성능 | LQR vs SDRE 차이 작음 (선형 범위) |
| 2 | 돌풍 외란 | 외란 복원 | SDRE가 외란 후 빠른 복원 |
| 3 | 피치 20도 대기동 | 비선형 영역 | SDRE가 LQR 대비 우수 (A(x) 갱신 효과) |

**기대 결과:**

시나리오 1 (선형 범위):
```
PID  : RMSE ~0.01, 오버슈트 ~10%
LQR  : RMSE ~0.005, 오버슈트 ~5%
SDRE : RMSE ~0.005, 오버슈트 ~3%   (LQR과 비슷)
```

시나리오 3 (비선형 범위):
```
PID  : RMSE ~0.05, 불안정 가능
LQR  : RMSE ~0.02, 오버슈트 증가
SDRE : RMSE ~0.01, 안정적 추종   (차이가 확연히 남)
```

> **논문 핵심 데이터**: 시나리오 3에서 LQR vs SDRE 성능 차이가 논문의 핵심 기여.

### 2-4. Step 4: 게인 업데이트 주기 분석

양창덕(2008) 결과를 재현하는 실험.

```python
# lqr_vs_sdre_comparison.py에 추가하여 실험
update_periods = [1, 10, 50, 100, 200]  # dt 배수
# 각 주기에서 SDRE 시뮬레이션 실행
# RMSE, 제어 에너지, 안정성 비교
```

**기대 결과:**
- Tk = 100*dt 까지 성능 거의 동일
- Tk = 200*dt 에서 약간의 성능 저하 시작
- KV260 연산 부담 결정에 핵심 데이터

## 3. 표적 교전 시뮬레이션

### 3-1. 지상 고정 표적

```
초기 조건:
  UAV: (0, 0, -500m), Va=35m/s, heading=0
  표적: (2000, 0, 0)  (2km 전방 지상)

LOS angle:
  lambda_el = atan2(-pd - 0, sqrt((pn-2000)^2 + pe^2))
  lambda_az = atan2(pe, pn - 2000)

제어 목표:
  lambda_el -> descent angle
  lambda_az -> 0 (정면으로 수렴)

성공 기준: miss distance < 5m
```

### 3-2. 지상 이동 표적

```
표적 운동 모델:
  x_tgt(t) = x0 + vx*t + noise
  y_tgt(t) = y0 + vy*t + noise

Kalman Filter 상태:
  x_kf = [x_tgt, y_tgt, vx_tgt, vy_tgt]

PNG: a_cmd = N * Vc * lambda_dot
  N = 3~5
  Vc = 접근 속도 (GPS 기반)

Monte Carlo:
  100회 반복, 표적 속도 5~15 m/s 무작위
  miss distance 히스토그램 생성
```

### 3-3. 공중 표적

```
3D 교전 기하:
  자기: (x1, y1, z1), V1 = 35 m/s
  표적: (x2, y2, z2), V2 = 20 m/s (기동)

3D PNG:
  a_y = N * Vc * lambda_dot_yaw
  a_z = N * Vc * lambda_dot_pitch

6-DOF SDRE 필수:
  x_IGC = [lambda_y, lambda_z, lambda_dot_y, lambda_dot_z,
           u, v, w, p, q, r, phi, theta]

성공 기준: miss distance < 3m
```

## 4. 성능 벤치마크 방법론

### 4-1. SDRE 연산 시간 측정

```python
import time

# 매 루프 시간 기록
times = []
for step in simulation:
    t0 = time.perf_counter()
    u = sdre_controller.compute(x)
    t1 = time.perf_counter()
    times.append(t1 - t0)

# 통계
print(f"평균: {np.mean(times)*1000:.4f} ms")
print(f"최대: {np.max(times)*1000:.4f} ms")
print(f"99th percentile: {np.percentile(times, 99)*1000:.4f} ms")
print(f"1kHz 가능: {np.percentile(times, 99) < 0.001}")
```

### 4-2. 비교 지표 수집

| 지표 | 수식 | 의미 |
|------|------|------|
| RMSE | sqrt(mean(error^2)) | 추종 정밀도 |
| 제어 에너지 | integral(u^2 dt) | 서보 부하 |
| 정착 시간 | t when error < 2% | 응답 속도 |
| miss distance | ||x_uav - x_tgt|| at impact | 타격 정밀도 |
| 솔버 시간 | perf_counter | 실시간성 |

### 4-3. 통계 분석

```python
# Monte Carlo 결과
miss_distances = np.array([...])  # 100회 결과

print(f"평균: {np.mean(miss_distances):.2f} m")
print(f"표준편차: {np.std(miss_distances):.2f} m")
print(f"최대: {np.max(miss_distances):.2f} m")
print(f"CEP (50%): {np.percentile(miss_distances, 50):.2f} m")
```

## 5. SITL (Software-In-The-Loop)

### 5-1. PX4 SITL 설정

```bash
# PX4 Autopilot 빌드
git clone https://github.com/PX4/PX4-Autopilot.git --recursive
cd PX4-Autopilot
make px4_sitl_default gazebo-classic

# Gazebo에서 고정익 모델 실행
make px4_sitl_default gazebo-classic_plane
```

### 5-2. SDRE -> PX4 SITL 연결

```python
# pymavlink으로 MAVLink 연결
from pymavlink import mavutil

master = mavutil.mavlink_connection('udp:127.0.0.1:14540')
master.wait_heartbeat()

# 상태 수신
while True:
    msg = master.recv_match(type='ATTITUDE', blocking=True, timeout=1)
    if msg:
        phi = msg.roll
        theta = msg.pitch
        psi = msg.yaw
        p = msg.rollspeed
        q = msg.pitchspeed
        r = msg.yawspeed

        # SDRE 계산
        x = np.array([...])
        u = sdre_controller.compute(x)

        # Offboard 명령 전송
        master.mav.set_attitude_target_send(
            0, master.target_system, master.target_component,
            0b00000111,  # body roll, pitch, yaw rate
            [1, 0, 0, 0],  # quaternion (무시)
            0, u[0], 0,  # roll_rate, pitch_rate, yaw_rate
            0.5  # thrust
        )
```

### 5-3. 테스트 비행 순서

```
1. PX4 SITL 시작 (Gazebo 고정익)
2. SDRE Python 스크립트 연결
3. ARM -> TAKEOFF -> 고도 안정화
4. SDRE 모드 전환 (Offboard)
5. 시나리오 실행:
   a. 피치 명령 추종
   b. 웨이포인트 비행 중 SDRE vs PID 비교
6. 데이터 로깅 -> 분석
```

## 6. HITL (Hardware-In-The-Loop)

### 6-1. KV260 + PX4 SITL 연결

```
[PC]                          [KV260]
  PX4 SITL                      R5: SDRE
  Gazebo                         A53: MAVLink parsing
     |                            |
     +--- USB/Ethernet -----------+
          MAVLink 115200
```

### 6-2. 실시간 성능 측정

```
측정 대상:
  1. MAVLink 메시지 수신 -> SDRE 계산 -> 명령 전송 총 레이턴시
  2. SDRE ARE 풀이 시간 (R5 bare-metal)
  3. AXI CAN 전송 지연
  4. 전체 루프 주기 실측

목표:
  총 레이턴시 < 1ms (1kHz)
  ARE 풀이 < 500us (R5) 또는 < 50us (PL 가속)
```

### 6-3. 판단 분기점

```
Phase 2 결과 (Teensy 또는 KV260 R5):
  ARE 풀이 < 1ms?
    YES -> Phase 3 FPGA 가속 불필요, PS만으로 진행
    NO  -> Phase 3 Vitis HLS 가속 필수

Phase 3 결과 (KV260 PL 가속):
  ARE 풀이 < 50us?
    YES -> 20kHz 여유, 1kHz 루프에 ARE + 여유 연산 가능
    NO  -> Systolic Array 최적화 또는 게인 업데이트 주기 완화 (5~10Hz)
```
