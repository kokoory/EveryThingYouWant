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
