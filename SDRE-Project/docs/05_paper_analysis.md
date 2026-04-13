# Paper Analysis

## Paper 1: arXiv 2503.01587

**Title**: "The State-Dependent Riccati Equation in Nonlinear Optimal Control:
Analysis, Error Estimation and Numerical Approximation"

**Author**: Luca Saluzzi (Sapienza, University of Rome)

**Date**: March 2025

**Link**: https://arxiv.org/abs/2503.01587

### One-Line Summary
SDRE 기법을 수학적으로 엄밀하게 분석하고, 최적해(HJB)와의 오차를 정량화하며,
두 가지 수치 계산법(Offline-Online vs Newton-Kleinman)을 비교한 논문.

### Core Contributions (3가지)

#### 1. SDRE와 HJB의 관계 + 오차 정량화

```
SDRE ansatz: V(x) = x^T P(x) x 를 HJB 방정식에 대입

첫째 항 = SDRE 자체 (~= 0)
나머지 항 = E(x)  <-- 준최적성(suboptimality)의 원인

E(x)가 작을수록 SDRE가 HJB에 가까움
```

- 피드백 제어 u_S는 안정화 준최적 제어를 제공
- 수정항 E(x)를 포함한 u~_S는 최적성이 중요할 때 더 정밀한 대안

#### 2. Optimal Semilinear Decomposition (최적 SDC 분할)

SDC 파라미터화 A(x)는 유일하지 않음. 이 논문은:
- SDC 분할 선택이 SDRE 정확도에 미치는 영향 분석
- **근사 오차를 최소화하는 최적 분해 전략 제안**

> "어떻게 A(x)를 쪼개야 오차가 가장 작냐?"에 대한 이론적 답

#### 3. 두 가지 수치해법 비교

| 방법 | 원리 | 장점 | 단점 |
|------|------|------|------|
| **Offline-Online** | 오프라인 1차 근사 선계산, 온라인 경량 연산 | 실시간 부담 최소 | 불안정 가능 |
| **Newton-Kleinman (C-NK)** | 이전 P를 초기값으로 반복 수렴 | 안정적, 정확 | 연산 비용 상대적으로 높음 |

**결론**: C-NK가 일관적으로 더 안정적이고 정확. Offline-Online은 특정 조건에서 안정화 실패.

### Newton-Kleinman (C-NK) 상세

```
Newton-Kleinman 핵심 트릭:
  비선형 항 PBR^{-1}B^T P 를 선형화
  --> 이차 방정식이 Lyapunov 방정식(선형)으로 변환
  --> 훨씬 빠르게 풀 수 있음

반복 과정:
  S_i = A - B*K_i
  S_i^T * P_{i+1} + P_{i+1} * S_i + P_i*B*R^{-1}*B^T*P_i + Q = 0
  K_{i+1} = R^{-1} * B^T * P_i

  --> 2차 수렴 속도 (Newton's method 특성)
```

**C-NK (Cascade)의 핵심**:
```
시간 t:   x(t)   --> Newton-Kleinman 수렴까지 반복 --> P*(x_t)
시간 t+1: x(t+1) --> 초기값 P_0 = P*(x_t) --> 1~2회 반복만으로 수렴

이유: 상태 x가 연속적으로 변하므로 P도 연속적으로 변함
     --> 이전 해가 이미 다음 해에 매우 가까움
```

### Numerical Validation
- **테스트**: 비선형 반응-확산 PDE의 최적 제어
- **결과**: C-NK가 계산 효율과 정확도 사이의 최적 트레이드오프 제공

### Project Relevance (프로젝트 연결)

| 논문 내용 | 프로젝트 활용 |
|-----------|-------------|
| 오차 E(x) 정량화 | SDRE 준최적성의 이론적 근거 |
| 최적 SDC 분할 | A(x) 선택 기준 (박사 기여 2) |
| C-NK 방법 | KV260 실시간 SDRE 구현의 핵심 알고리즘 |
| Offline-Online 비교 | 대안 방법의 한계 이해 |

---

## Paper 2: 양창덕 외 (2008)

**Title**: "SDRE 기법을 이용한 헬리콥터 비선형 최적제어기 설계 연구"

**Authors**: 양창덕 외 (건국대학교)

### Key Findings

#### SDC 분할 방법 (수치적)
```
제어 미분 행렬: B(x) = dF~/du~   (식 23)
상태 미분 행렬: A~(x~) = FX^T (XX^T)^{-1}  (식 25)

x 주위 2n개 데이터 포인트로 최소자승법 사용
--> 해석적 미분 없이 A(x) 수치 계산 가능
```

#### Banks-Newton-Kleinman 반복
```
Step 1: Chandrasekhar 시스템으로 초기 K_0 계산
Step 2: Newton-Kleinman 반복 (2차 수렴)
  S_i = A - B*K_i
  S_i^T P_i + P_i S_i = -Q - K_i^T R K_i
  K_i = R^{-1} B^T P_{i-1}
```

#### 게인 업데이트 주기 (핵심 발견)
```
Tk = dt        (매 스텝)     --> 기준
Tk = 10*dt     (10스텝마다)  --> 성능 거의 동일
Tk = 100*dt    (100스텝마다) --> 성능 거의 동일
Tk = 200*dt    (200스텝마다) --> 성능 거의 동일!

dt = 0.001초 기준: 200*dt = 0.2초 = 5Hz로도 충분
```

> **프로젝트 영향**: KV260 연산 부담 대폭 감소. FPGA 가속 없이도 가능할 수 있음.

#### 논문 한계 (프로젝트에서 극복할 점)
- PC 시뮬레이션만 수행 (실제 하드웨어 미실장)
- 헬리콥터 경로 추종만 (표적 타격 없음)
- 유도 법칙 없음 (IGC 아님)

---

## Paper 3: Menon et al. (2002)

**Title**: "Real-time Computational Methods for SDRE Nonlinear Control of Missiles"

**Venue**: American Control Conference

### Key Findings
- COTS 프로세서(당시 기준)에서 SDRE 2kHz 달성
- 미사일 비행 제어에 실시간 적용 실증
- FPGA가 아닌 소프트웨어 구현

> KV260 (2020년대 FPGA)에서는 이보다 훨씬 빠를 수 있다는 근거

---

## Related Repositories

| 레포 | 용도 | 링크 |
|------|------|------|
| mavsim_python | Aerosonde 파라미터, 6-DOF 시뮬 | https://github.com/byu-magicc/mavsim_python |
| rosplane | ROS 기반 고정익 오토파일럿 | https://github.com/byu-magicc/rosplane |
| Missile-Guidance | PNG, LQ Guidance (MATLAB) | https://github.com/Daniboy370/Missile-Guidance |
| MissileSimulation | 6-DOF 미사일 모델 (MATLAB) | https://github.com/JohannesAutenrieb/MissileSimulation |
| PythonRobotics | 로보틱스 알고리즘 모음 (LQR 등) | https://github.com/AtsushiSakai/PythonRobotics |

> **주의**: PythonRobotics에는 Fixed Wing SDRE 예제가 없음. 쿼드로터/로켓만 있음.

---

## Summary: What Exists vs What's New

| 레포/논문 | SDRE | 고정익 | 유도법칙 | 표적타격 | 카메라 | FPGA |
|-----------|------|--------|---------|---------|--------|------|
| mavsim_python | X (LQR) | O | X | X | X | X |
| Missile-Guidance | X (PNG/LQ) | X | O | O | X | X |
| MATLAB SDRE 예제 | O | X (미사일) | O | O | X | X |
| 양창덕 2008 | O | X (헬리) | X | X | X | X |
| Menon 2002 | O | X (미사일) | O | O | X | X |
| Saluzzi 2025 | O (이론) | X | X | X | X | X |
| **이 프로젝트** | **O** | **O** | **O (IGC)** | **O (3종)** | **O** | **O** |

> 이 프로젝트는 6개 요소를 모두 통합하는 최초 시도.
