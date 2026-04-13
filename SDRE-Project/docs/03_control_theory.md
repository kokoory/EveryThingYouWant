# Control Theory Reference

## 1. Optimal Control Hierarchy

```
HJB (Hamilton-Jacobi-Bellman)     <-- 완전한 최적해, 직접 풀기 불가능
    |
    +-- ARE (Algebraic Riccati Equation)  <-- 선형 시스템 특수해
    |       |
    |       +-- LQR: ARE 한 번 풀기, K 고정
    |       +-- SDRE: ARE 반복 풀기, K(x) 매 루프 갱신
    |
    +-- MPC (Model Predictive Control)    <-- 유한 지평선 반복 최적화
    |
    +-- DDP / iLQR                        <-- 궤적 주변 2차 근사
    |
    +-- RL (Reinforcement Learning)       <-- 샘플 기반 V(x) 추정
```

## 2. Cost Function (성능 지수)

최적 제어의 목표: 비용 함수 J를 최소화하는 제어 입력 u를 찾기.

```
J = Phi(x(tf), tf) + integral[t0 to tf] L(x, u, t) dt

Phi: 종단 비용 (terminal cost)
L:   운용 비용 (running cost)
```

LQR/SDRE에서는:
```
L(x, u) = x^T Q x + u^T R u

Q: 상태 가중 행렬 (양의 준정치)
R: 제어 가중 행렬 (양의 정치)
```

## 3. HJB Equation (Hamilton-Jacobi-Bellman)

```
정상 상태 HJB:
  0 = min_u [ L(x, u) + (dV/dx)^T f(x, u) ]

V(x)    : 가치 함수 (value function)
L(x, u) : running cost
f(x, u) : 시스템 동역학 (x_dot = f(x, u))
dV/dx   : 가치 함수의 gradient
```

### HJB -> ARE 유도 (선형 시스템)

```
시스템: x_dot = Ax + Bu
비용:   L(x,u) = x^T Q x + u^T R u
가치함수 가정: V(x) = x^T P x  (이차 형식)

dV/dx = 2Px

최소화 조건:
d/du [ x^T Q x + u^T R u + 2x^T P^T(Ax+Bu) ] = 0
2Ru + 2B^T P x = 0
--> u* = -R^{-1} B^T P x = -Kx

HJB에 대입하여 정리:
  A^T P + PA - PBR^{-1}B^T P + Q = 0   <-- ARE
```

### 직접 풀 수 없는 이유

1. **차원의 저주**: n차원 -> 격자점 k^n개 (n=10이면 10^20)
2. **V(x) 형태 미지**: 비선형 편미분 방정식, 해석적 해 없음
3. **경계조건 비선형성**: u* = argmin 자체가 비선형

## 4. ARE (Algebraic Riccati Equation)

```
A^T P + PA - PBR^{-1}B^T P + Q = 0

A, B: 상수 행렬 (선형 시스템)
P:    풀어야 할 해 (대칭, 양의 정치)
K = R^{-1} B^T P  (최적 게인, 상수)
```

- **LQR에서**: 설계 시 한 번만 풀면 끝
- **풀이 방법**: Schur decomposition, Hamiltonian 행렬의 고유값

### Hamiltonian 행렬과 Schur 분해

```
H = [ A        -BR^{-1}B^T ]    (2n x 2n)
    [-Q        -A^T        ]

Schur 분해: H = Q T Q*
  Q  : 직교 행렬
  T  : 상삼각 행렬 (대각선 = 고유값)

음수 고유값만 선택 --> P 계산 --> K = R^{-1}B^T P
```

## 5. SDRE (State-Dependent Riccati Equation)

```
비선형 시스템: x_dot = f(x, u)
SDC 분할:     x_dot = A(x)x + B(x)u  (A, B가 상태 x의 함수)

SDRE:
  A(x)^T P + PA(x) - PB(x)R^{-1}B(x)^T P + Q = 0

--> 방정식 형태는 ARE와 동일
--> A(x), B(x)가 매 순간 바뀜
--> 매 루프마다 ARE를 새로 풀어야 함
--> K(x) = R^{-1} B(x)^T P(x) 도 매 루프 갱신
```

### ARE vs SDRE 핵심 차이

| 항목 | ARE (LQR) | SDRE |
|------|-----------|------|
| A, B | 상수 | x에 따라 변함 |
| P, K | 고정 | 매 루프 갱신 |
| ARE 풀기 | 설계 시 1회 | 매 루프 반복 |
| 비선형 대응 | 선형 범위 내에서만 | 비선형 전 구간 |
| 최적성 | 선형 시스템에서 최적 | 준최적 (HJB 근사) |

### SDRE가 HJB의 근사인 이유

```
HJB 완전해: V(x) 전체 함수를 구함 --> 불가능
SDRE 근사:  V(x) ~= x^T P(x) x     --> P(x)만 구하면 됨
오차:       고차 비선형 항 무시 --> 국소 최적, 전역 최적 미보장
```

### SDC 분할 (Factorization) 비유일성 문제

```
같은 비선형 시스템에 대해:
  f(x) = A1(x) * x = A2(x) * x = ... (무수히 많은 분할 가능)

어떤 A(x)를 선택하느냐에 따라:
  - SDRE 성능이 달라짐
  - 안정성 보장 여부가 달라짐
  - 최적 SDC 선택 기준은 아직 미해결 (연구 공백)
```

## 6. Newton-Kleinman Method (ARE 수치 해법)

### Banks-Newton-Kleinman 반복

```
Step 1: 초기 K_0 계산 (Chandrasekhar 시스템)

Step 2: Newton-Kleinman 반복
  S_i = A - B*K_i
  S_i^T * P_i + P_i * S_i = -Q - K_i^T * R * K_i  (Lyapunov 방정식)
  K_{i+1} = R^{-1} * B^T * P_i

--> P는 2차(quadratic) 속도로 수렴
--> Warm-start: 이전 P를 초기값으로 사용하면 1~3회 반복으로 충분
```

### C-NK (Cascade Newton-Kleinman) - arXiv 2503.01587

```
시간 t:   x(t)   --> P*(x_t) 계산 (수렴까지)
시간 t+1: x(t+1) --> 초기값 P_0 = P*(x_t)로 시작
                     --> 1~2회만 반복해도 수렴 (상태 변화가 연속적)
```

## 7. MPC vs SDRE Comparison

| 항목 | SDRE | MPC (선형) | NMPC (비선형) |
|------|------|-----------|--------------|
| 풀이 방법 | 매 순간 ARE | 매 순간 QP | 매 순간 NLP |
| 제약 처리 | 어려움 | 자연스러움 | 자연스러움 |
| 연산량 | 낮음 (행렬 연산) | 중간 | 높음 |
| 실시간성 | 쉬움 (1kHz) | FPGA로 1kHz 가능 | 100Hz 한계 |
| 비선형 대응 | SDC 분할로 직접 | 선형 근사 필요 | 직접 처리 |
| 예측 능력 | 없음 | T 구간 예측 | T 구간 예측 |

### FPGA MPC 실측 성능 (논문 기반)

| 논문 | FPGA | 달성 속도 |
|------|------|----------|
| Wang & Boyd (2010, Stanford) | - | 소형 QP: 1kHz+ |
| Jerez et al. (2011, Imperial) | Virtex-6 | 수백 Hz |
| ITER (2021) | Alveo U250 | Fast Gradient: 90kHz |
| Iowa State (Zynq) | Zynq-7020 | ADMM: CPU 대비 27x |

> 선형 MPC는 FPGA로 1kHz 가능하지만, 비선형 기동 구간에서 선형화 오차 발생.
> SDRE는 비선형 동역학을 직접 다루면서 1kHz 달성 --> 논문 차별점.

## 8. Guidance Laws (유도 법칙)

### PNG (Proportional Navigation Guidance)

```
a_cmd = N * Vc * lambda_dot

N:          항법 상수 (보통 3~5)
Vc:         접근 속도
lambda_dot: LOS 각속도
```

### 3D PNG (공중 표적)

```
a_cmd_y = N * Vc * lambda_dot_yaw
a_cmd_z = N * Vc * lambda_dot_pitch
```

### IGC (Integrated Guidance and Control)

```
기존 분리 설계:
  유도 --> a_cmd (가속도 명령)
  제어 --> delta_e, delta_a, delta_r (서보 명령)
  문제: 유도와 제어가 따로 놀아서 비효율

IGC:
  유도 + 제어를 단일 SDRE 루프에 통합
  상태: [LOS 각도, 기체 자세, 각속도, ...] 전부 포함
  출력: 서보 명령 직접
  장점: miss distance 40~50% 개선 (JHU APL 실증)
```

## 9. Aerosonde UAV Model Parameters (Beard & McLain)

```
기체 물리량:
  질량:       m  = 13.5 kg
  날개면적:   S  = 0.55 m^2
  날개폭:     b  = 2.8896 m
  평균시위:   c  = 0.18994 m
  관성모멘트: Jx = 0.8244,  Jy = 1.135,  Jz = 1.759  [kg*m^2]
             Jxz = 0.1204 [kg*m^2]

공력 계수 (종방향):
  CL0 = 0.28,   CD0 = 0.03,   Cm0 = -0.024
  CLa = 3.45,   CDa = 0.30,   Cma = -0.38
  CLq = 0.00,   CDq = 0.00,   Cmq = -3.60
  CLde= 0.36,   CDde= 0.00,   Cmde= -0.50

공력 계수 (횡방향):
  CY0  = 0.00,  Cl0  = 0.00,  Cn0  =  0.00
  CYb  =-0.98,  Clb  =-0.12,  Cnb  =  0.25
  CYp  = 0.00,  Clp  =-0.26,  Cnp  = -0.022
  CYr  = 0.00,  Clr  = 0.14,  Cnr  = -0.35
  CYda = 0.00,  Clda = 0.08,  Cnda =  0.06
  CYdr =-0.17,  Cldr = 0.105, Cndr = -0.032

추력/프로펠러:
  Sprop  = 0.2027 m^2
  Cprop  = 1.0
  kmotor = 80

기준 순항: Va = 35 m/s
```

> 참고: Aerosonde는 V-tail 형상. 교재 모델은 이미 믹싱된 상태로 단순화.
> 실비행은 Skywalker X8 사용, 실측 파라미터로 교체.
