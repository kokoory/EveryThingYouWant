# PhD Thesis Roadmap

## 1. Research Gap (연구 공백)

### 이미 존재하는 것
- SDRE for 헬리콥터 경로 추종 (양창덕 2008)
- SDRE-IGC for 미사일 (Menon & Ohlmeyer 2001, 2007)
- SDRE for 고정익 UAV 추종 (Beard & McLain 계열)
- PNG + SDRE 결합 (미사일 분야)
- FPGA 기반 실시간 제어 (일반)
- 카메라 기반 표적 추적 (다수)

### 존재하지 않는 것 (연구 공백)
- **Vision-based IGC-SDRE**: 카메라 LOS 불확실성을 포함한 IGC-SDRE 설계 및 안정성 증명
- **FPGA SDRE 실시간 실증**: KV260 같은 임베디드 FPGA에서 SDRE 실시간 구현 및 비행 검증
- **다중 표적 모드 전환 안정성**: 단일 SDRE 프레임워크에서 3종 표적 통합 처리

## 2. Two-Phase Publication Strategy

### Phase A: 첫 논문 (석사 or 저널) - 1~2년

**핵심 질문**: "고정익 UAV에서 SDRE를 실시간으로 풀어 실제 비행 제어에 적용할 수 있는가?"

**제목 후보**:
```
"Real-Time SDRE Flight Control for Fixed-Wing UAV:
 FPGA Implementation and Flight Validation"

"FPGA 기반 실시간 SDRE 제어기의 고정익 UAV 비행 적용 및 검증"
```

**논문 구조**:
| Chapter | 내용 |
|---------|------|
| Ch1. 서론 | 실시간 SDRE의 기존 한계, FPGA 가속의 필요성 |
| Ch2. 모델 | Aerosonde 6-DOF 모델 및 SDC 분할 |
| Ch3. SDRE 설계 | Newton-Kleinman 수치 해법, 게인 업데이트 주기, 안정성 |
| Ch4. FPGA 구현 | KV260 Vitis HLS, 연산 시간 측정, 수치 안정성 |
| Ch5. 비행 실험 | 시뮬 + HITL + 실비행, PID vs LQR vs SDRE 비교 |
| Ch6. 결론 | 실시간 가능성 확인, 성능 개선 정도, 향후 연구 |

**증명해야 할 3가지**:
1. 실시간 가능성: KV260 ARE 연산 시간 < dt (1ms)
2. 비행 안정성: K(x) 매 루프 변경에도 안정 유지
3. 기존 대비 성능: PID vs LQR vs SDRE 비교 (추종 오차, 제어 에너지, 외란 복원)

### Phase B: 박사 논문 - 3년

**제목 후보**:
```
"Vision-Based Integrated Guidance and Control for Fixed-Wing UAV
 Engaging Multiple Target Categories Using State-Dependent Riccati
 Equation: Stability Analysis under LOS Measurement Uncertainty
 and Mode Switching"

"LOS 측정 불확실성과 모드 전환을 고려한 고정익 UAV의
 비전 기반 IGC-SDRE 설계 및 안정성 해석"
```

**학문적 기여 (4가지)**:

| # | 기여 | 핵심 |
|---|------|------|
| 1 | Vision-based LOS 불확실성 + IGC-SDRE | 카메라 노이즈가 있어도 안정한가? miss distance 상한 유도 |
| 2 | SDC 분할 선택 기준 | miss distance 최소화하는 A(x) 선택법 |
| 3 | FPGA 수치 안정성 조건 | 고정소수점에서 Newton-Kleinman 수렴 보장 비트폭 |
| 4 | 다중 표적 모드 전환 안정성 | Dwell time 조건, Switched system 안정성 |

**박사 논문 구조**:

| Chapter | 내용 | 대응 기여 |
|---------|------|----------|
| Ch1. 서론 | 기존 연구 한계 | - |
| Ch2. 고정익 모델 + SDC 분할 | Aerosonde, 교전 기하 | - |
| Ch3. 비전 LOS 불확실성 모델링 | 카메라 오차, YOLO 지연, EKF | 기여 1 준비 |
| Ch4. IGC-SDRE 설계 + 안정성 해석 | Lyapunov 증명, miss distance 상한 | **기여 1** |
| Ch5. 다중 표적 모드 전환 | Switched system, Dwell time | **기여 4** |
| Ch6. FPGA 실시간 구현 | 수치 안정성 조건 | **기여 3** |
| Ch7. 시뮬레이션 | 3종 표적, 노이즈 레벨별 | - |
| Ch8. 실기체 실험 | Skywalker X8 실비행 | - |
| Ch9. 결론 | | - |

## 3. Study Roadmap (학습 계획)

### Required Knowledge Layers

```
[Layer 1] 수학 기초
    |-- 행렬 이론 (양의 정치, 고유값, Schur complement)
    |-- 미분방정식 (ODE, 평형점, 안정성)
    v
[Layer 2] 최적 제어
    |-- 변분법 (Calculus of Variations)
    |-- Pontryagin 최소 원리
    |-- HJB 방정식
    |-- LQR 유도 (ARE)
    v
[Layer 3] 비선형 제어 ★ 가장 중요
    |-- Lyapunov 직접법 (V>0, V_dot<0)
    |-- Input-to-State Stability (ISS) --> LOS 노이즈 분석 핵심
    |-- La Salle 불변 원리
    v
[Layer 4] SDRE 이론
    |-- SDC 분할 방법 및 비유일성
    |-- Cloutier (1997), Cimen (2008) 논문
    |-- Newton-Kleinman 수치 해법
    v
[Layer 5] 비행 동역학 + 유도
    |-- 6-DOF 방정식, 공력 계수
    |-- PNG, IGC 개념
    v
[Layer 6] Switched Systems ★ 기여 4 핵심
    |-- Dwell time 조건
    |-- Multiple Lyapunov Functions
    |-- Common Quadratic Lyapunov Function (LMI)
    v
[Layer 7] 비전/EKF ★ 기여 1 핵심
    |-- 핀홀 카메라 모델, LOS 오차 모델
    |-- Extended Kalman Filter
    |-- Stochastic stability
```

### Recommended Textbooks

| 단계 | 교재 | 용도 |
|------|------|------|
| Layer 2 | Kirk, "Optimal Control Theory" (Dover) | 입문: 변분법 -> HJB |
| Layer 2 | Anderson & Moore, "Optimal Control: Linear Quadratic Methods" (Dover) | LQR/ARE 공학적 이해 |
| Layer 3 | **Slotine & Li, "Applied Nonlinear Control"** | Lyapunov 직관. 먼저 읽기 |
| Layer 3 | **Khalil, "Nonlinear Systems" 3rd ed** | Lyapunov 엄밀한 증명. 이후 읽기 |
| Layer 5 | Beard & McLain, "Small Unmanned Aircraft" | 고정익 동역학 + 파라미터 |
| Layer 5 | Zarchan, "Tactical and Strategic Missile Guidance" (AIAA) | PNG, miss distance |
| Layer 6 | **Liberzon, "Switching in Systems and Control"** | Switched systems 표준 |
| Layer 7 | Bar-Shalom et al., "Estimation with Applications to Tracking" | 표적 추적 EKF |
| 수치 | Golub & Van Loan, "Matrix Computations" | Riccati 수치 해법 |

### Recommended Lectures (검증된 것만)

| 강의 | 플랫폼 | 대상 Layer | 특징 |
|------|--------|-----------|------|
| **Slotine MIT 비선형 제어** | MIT 공식 | Layer 3 | 직관 우선, 수식 뒤 |
| Liberzon ECE 553 강의노트 | Illinois 공식 | Layer 2 | 최적 제어 수학적 정리 |
| **Steve Brunton 제어 이론** | YouTube | Layer 2-3 | LQR 시리즈 탁월 |
| Brian Douglas 제어 시스템 | YouTube | Layer 2 | 애니메이션, 기초 복습 |
| MIT 6.832 Underactuated Robotics | MIT OCW | Layer 3-4 | 비선형 제어 실제 적용 |

> 링크:
> - Slotine MIT: https://web.mit.edu/nsl/www/videos/lectures.html
> - Liberzon 강의노트: https://liberzon.csl.illinois.edu/teaching/Liberzon-LectureNotes.pdf
> - Liberzon 교재: http://liberzon.csl.illinois.edu/teaching.html

### Must-Read Papers

| 논문 | 내용 | 용도 |
|------|------|------|
| Cloutier (1997) | "SDRE Techniques: An Overview" | SDRE 원조, 필독 |
| Cimen (2008) | "SDRE Control: A Survey" | 서론 작성 필수 |
| Menon & Ohlmeyer (2001, 2007) | "Numerical SDRE for Missile IGC" | IGC 핵심 |
| Menon et al. (2002) | "Real-time Computational Methods for SDRE" | COTS에서 2kHz 실증 |
| 양창덕 외 (2008) | "SDRE 헬리콥터 비선형 최적제어기" | SDC 분할법, Newton-Kleinman |
| Saluzzi (2025) | arXiv:2503.01587 | SDRE 오차 정량화, C-NK |
| Banks & Ito (1985) | NASA CR178207 Newton-Kleinman | NK 수치 해법 원전 |

### 3-Year Timeline

```
Year 1 (기초 구축):
  Month 1-2:   Slotine MIT 강의 + Slotine 책
  Month 3-4:   Khalil Ch1-5 (안정성)
  Month 5-6:   Anderson & Moore (LQR/ARE)
  Month 7-8:   Beard & McLain + mavsim_python 구현
  Month 9-12:  SDRE 논문들 정독 + Phase 1 시뮬레이션

Year 2 (논문 핵심):
  Month 1-4:   Liberzon Switched Systems
  Month 5-8:   EKF + LOS 불확실성 모델링
  Month 9-12:  Phase 2-3 구현 (C++ 포팅, KV260)

Year 3 (실험 + 집필):
  Month 1-6:   Phase 4-5 실기체 실험
  Month 7-12:  논문 집필
```

## 4. Searching Keywords

논문 검색 시 사용할 키워드 조합:

```
"SDRE" + "integrated guidance and control" + "UAV"
"State-Dependent Riccati" + "intercept" + "fixed-wing"
"IGC" + "LOS rate" + "optimal control"
"Menon Ohlmeyer" + "SDRE guidance"
"FPGA" + "Riccati" + "real-time"
"vision-based" + "guidance" + "UAV" + "LOS"
"switched systems" + "stability" + "guidance"
```

검색 DB: Google Scholar, Semantic Scholar, AIAA arc, IEEE Xplore

## 5. Detailed Study Guide by Layer

### Layer 2: 최적 제어 - 구체적 공부 방법

**Kirk 교재 읽기 순서:**
- Ch 4: Variational calculus (변분법) - 오일러-라그랑주 방정식 유도를 손으로 해볼 것
- Ch 5: Pontryagin minimum principle - 공역 변수(costate) 개념 이해
- Ch 6: LQ problem - ARE가 왜 나오는지 직접 유도
- Ch 7: Dynamic programming - HJB 방정식의 직관

**Anderson & Moore 교재:**
- Ch 1-3: LQR 기본, ARE 해의 존재성/유일성
- Ch 4: 수치 해법 (Schur decomposition)
- Appendix: Riccati 방정식 성질 정리 (SDRE 공부 시 계속 참조)

**손으로 풀어볼 연습 문제:**
```
1. 1차 시스템 x_dot = ax + bu, J = integral(qx^2 + ru^2)dt
   -> ARE를 직접 풀어 K 계산, 시스템 응답 스케치

2. 2차 진자 시스템:
   x_dot = [0 1; -g/l 0]x + [0; 1]u
   Q = diag(10, 1), R = 1
   -> scipy로 P, K 계산 후 손으로 검증

3. HJB에서 ARE 유도:
   V(x) = x^T P x 가정하고 HJB에 대입
   -> 최적 u* = -R^{-1}B^T P x 유도 과정 전체를 수기로 작성
```

**자기 점검:** ARE 유도 과정을 보지 않고 20분 안에 수기로 완성할 수 있으면 합격.

### Layer 3: 비선형 제어 - 가장 핵심적인 레이어

**Slotine & Li 교재 읽기 (먼저):**
- Ch 3: Phase plane analysis - 비선형 시스템의 직관
- Ch 4: Lyapunov stability - **핵심 중의 핵심**
  - 4.1: Lyapunov 직접법 정의
  - 4.2: La Salle 불변 원리
  - 4.3: 수렴 속도 분석
- Ch 5: Feedback linearization
- Ch 9: Adaptive control (SDRE와 비교 관점)

**Khalil 교재 읽기 (이후):**
- Ch 3: 기본 성질 (존재성, 유일성)
- **Ch 4: Lyapunov stability** - Theorem 4.1~4.9 증명 숙지
  - Theorem 4.1: 국소 안정성
  - Theorem 4.2: 전역 안정성
  - Theorem 4.4: La Salle 정리
- **Ch 4.6: ISS (Input-to-State Stability)** - 논문 기여 1의 핵심
  - ISS gain function
  - 노이즈 바운드 -> 상태 바운드 관계
- Ch 9: 입력-출력 안정성
- Ch 14: 피드백 선형화

**핵심 개념 체크리스트:**
```
[ ] Lyapunov 함수 V(x) 조건: V(0)=0, V(x)>0, V_dot(x)<0
[ ] 안정 vs 점근 안정 vs 지수 안정 차이 설명 가능
[ ] La Salle 불변 원리: V_dot<=0 (등호 허용) 일 때 사용법
[ ] ISS 정의: ||x(t)|| <= beta(||x(0)||,t) + gamma(sup||w||)
[ ] Lyapunov 함수 구성법: 에너지 함수, 이차형식 x^T P x
[ ] 간접법 vs 직접법 차이와 각각의 한계
```

**연습: Lyapunov 함수 구성 방법론**

```
Step 1: 시스템 구조 파악
  x_dot = f(x) 에서 에너지 관련 항 식별

Step 2: 후보 V(x) 선택
  가장 간단한 것부터: V = x^T P x (P > 0)
  또는 에너지 함수: V = 운동에너지 + 위치에너지

Step 3: V_dot 계산
  V_dot = (dV/dx)^T * f(x)
  항별로 부호 분석

Step 4: 부호 확인
  V_dot < 0 인지 확인
  안 되면 V 수정 또는 La Salle 적용
```

### Layer 4: SDRE 이론 심화

**논문 읽기 순서 (반드시 이 순서):**
1. Cloutier (1997) - SDRE 개요 (전체 그림 파악)
2. Cimen (2008) - 서베이 (기존 연구 지도)
3. 양창덕 (2008) - SDC 분할 수치 방법, Newton-Kleinman
4. Menon & Ohlmeyer (2001) - IGC-SDRE 미사일 적용
5. Saluzzi (2025) - 오차 정량화, C-NK, 최적 SDC

**SDC 분할 비유일성 예시 (2차 시스템으로 이해):**

```
비선형 시스템: x_dot = -x^3

SDC 분할 방법 1: A(x) = -x^2
  -> x_dot = (-x^2) * x = A(x) * x

SDC 분할 방법 2: A(x) = -|x| * x (다른 분할)
  -> 수학적으로는 같지만 SDRE에서 다른 P(x) 생성

어떤 분할이 더 좋은가?
  -> Saluzzi (2025)가 부분적으로 답을 제시
  -> 완전한 해답은 아직 연구 공백 (박사 기여 가능)
```

**Newton-Kleinman 수치 예시 (2x2):**

```
A = [0 1; -2 -3], B = [0; 1], Q = diag(10,1), R = [1]

Iteration 0:
  P_0 = Q = diag(10,1)
  K_0 = R^{-1} B^T P_0 = [0 1] * [10 0; 0 1] = [0, 1]
  S_0 = A - B*K_0 = [0 1; -2 -3] - [0;1]*[0,1] = [0 1; -2 -4]

  Lyapunov: S_0^T P_1 + P_1 S_0 = -(Q + K_0^T R K_0)
  -> scipy.linalg.solve_continuous_lyapunov(S_0.T, RHS) -> P_1

Iteration 1:
  K_1 = R^{-1} B^T P_1
  ... (보통 2~3회면 수렴)
```

### Layer 6: Switched Systems

**Liberzon 교재:**
- Ch 1: 개요 및 동기
- **Ch 2: Stability under arbitrary switching** - Common Lyapunov Function
- **Ch 3: Stability under constrained switching** - Dwell time 조건
  - Theorem 3.1: 평균 체류 시간 조건
  - 이 정리가 논문 기여 4의 핵심 도구

**Dwell time 정리 (직관적 이해):**
```
모드 1: V_1(x) 감소, 모드 2: V_2(x) 감소
전환 순간: V가 점프할 수 있음 (다른 Lyapunov 함수)

V_2(x(t_switch)) <= mu * V_1(x(t_switch))   (mu >= 1)

충분히 오래 한 모드에 머무르면 (dwell time > tau_D):
  V 감소량 > 전환 시 V 점프량
  -> 전체적으로 안정

tau_D > ln(mu) / lambda_min
  mu: 전환 시 V 점프 비율
  lambda_min: 가장 느린 모드의 감소율
```

**3종 표적 모드 전환에 적용:**
```
모드 A (지상 고정): V_A(x) = x^T P_A x, 감소율 lambda_A
모드 B (지상 이동): V_B(x) = x^T P_B x, 감소율 lambda_B
모드 C (공중):      V_C(x) = x^T P_C x, 감소율 lambda_C

전환 시 점프: mu_AB, mu_BC, mu_AC (P 행렬 차이에 의존)

안정성 조건:
  모드 A에 최소 tau_A 이상 머물러야 함
  모드 B에 최소 tau_B 이상 머물러야 함
  ...
  
이 tau 값들을 유도하는 것이 논문 기여 4
```

### Layer 7: Vision/EKF

**핀홀 카메라 LOS 변환:**
```
픽셀 좌표 (u_px, v_px) -> LOS 각도 (lambda_az, lambda_el)

lambda_az = atan2(u_px - cx, fx)
lambda_el = atan2(v_px - cy, fy)

fx, fy: 초점 거리 (픽셀 단위)
cx, cy: 주점 (principal point)

LOS rate:
  lambda_dot = (lambda(t) - lambda(t-dt)) / dt  (1차 차분)
  또는 EKF로 추정 (노이즈 제거)
```

**EKF for 표적 추적:**
```
상태: x_kf = [x_tgt, y_tgt, vx_tgt, vy_tgt]

프로세스 모델 (등속 가정):
  x_kf(k+1) = F * x_kf(k) + w
  F = [1 0 dt 0; 0 1 0 dt; 0 0 1 0; 0 0 0 1]

측정 모델:
  z = h(x_kf) + v
  z = [lambda_az, lambda_el]  (카메라에서 직접 측정)
  h(x) = [atan2(y_tgt, x_tgt), atan2(-z_tgt, sqrt(x^2+y^2))]

주요 튜닝:
  Q_kf: 프로세스 노이즈 (표적 기동성에 비례)
  R_kf: 측정 노이즈 (카메라 해상도와 YOLO 정밀도에 의존)
```

## 6. Milestone Checkpoints

### Year 1: 기초 구축

| Month | 목표 | 자기 점검 |
|-------|------|----------|
| 1-2 | Slotine MIT 강의 완강 | Lyapunov 함수를 간단한 시스템에 직접 구성 가능? |
| 3-4 | Khalil Ch4 안정성 | ISS 정의를 보지 않고 설명 가능? |
| 5-6 | Anderson & Moore LQR/ARE | ARE를 HJB에서 유도하는 과정을 수기로 완성? |
| 7-8 | Beard & McLain + 코드 | Aerosonde 트림 계산 + SDRE 시뮬 직접 실행? |
| 9-10 | SDRE 논문 5편 정독 | SDC 분할 비유일성을 예시로 설명 가능? |
| 11-12 | Phase 1 시뮬 완성 | PID vs LQR vs SDRE 비교 그래프 생성? |

### Year 2: 논문 핵심

| Month | 목표 | 자기 점검 |
|-------|------|----------|
| 1-2 | Liberzon Ch2-3 | Dwell time 정리를 증명 스케치 가능? |
| 3-4 | LMI 프로그래밍 | MATLAB/Python으로 Common Lyapunov Function 계산? |
| 5-6 | EKF 설계 + 구현 | 표적 추적 EKF가 시뮬에서 동작? |
| 7-8 | LOS 불확실성 모델링 | 카메라 노이즈 -> miss distance 관계 수식화? |
| 9-10 | Phase 2-3 (C++ + KV260) | KV260 R5에서 SDRE 1kHz 달성? |
| 11-12 | 학회 논문 투고 | 첫 논문 draft 완성? |

### Year 3: 실험 + 집필

| Month | 목표 | 자기 점검 |
|-------|------|----------|
| 1-3 | Phase 4 (HITL) | Jetson+KV260+Pixhawk 통합 동작? |
| 4-6 | Phase 5 (실비행) | Skywalker X8에서 SDRE 비행 성공? |
| 7-9 | 논문 집필 | Ch1-6 draft 완성? |
| 10-12 | 수정 + 투고 | 최종 논문 제출? |

## 7. Mathematical Prerequisites Quick Reference

### 행렬 양의 정치 (Positive Definite)

```
P > 0 (양의 정치) <==>
  1. 모든 고유값 > 0
  2. x^T P x > 0 for all x != 0
  3. 모든 leading principal minor > 0 (Sylvester)
  4. P = L L^T 형태로 Cholesky 분해 가능

P >= 0 (양의 준정치):
  고유값 >= 0 (0 허용)
```

### Schur Complement

```
행렬 M = [A B; C D]

M > 0 <==> A > 0 and (D - C A^{-1} B) > 0
       <==> D > 0 and (A - B D^{-1} C) > 0

LMI (선형 행렬 부등식) 문제에서 핵심 도구
```

### Lyapunov 방정식

```
연속: A^T P + P A = -Q   (A 안정, Q > 0 -> P > 0 유일해)
이산: A^T P A - P = -Q

풀이: scipy.linalg.solve_continuous_lyapunov(A, Q)
```
