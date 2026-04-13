# SDRE-IGC: Vision-Based Fixed-Wing UAV Optimal Control Project

## Project Overview

SDRE(State-Dependent Riccati Equation) 기반 실시간 최적제어를 고정익 UAV에 적용하여
3종 표적(지상 고정, 지상 이동, 공중)을 타격하는 통합 유도-제어(IGC) 시스템 개발 프로젝트.

## Core Concept

```
카메라 (락온) --> 상대 위치/속도 추정 --> ARE 실시간 풀기 --> 최적 제어 입력 --> 서보/추력
     |                |                      |                    |
 IMX219/IMX477    Kalman Filter         SDRE on KV260       DroneCAN Servos
 (광각/망원)       LOS rate              Newton-Kleinman      Pixhawk 연동
```

## Key Technical Decisions

| 항목 | 선택 | 이유 |
|------|------|------|
| 제어 방법 | SDRE (ARE 반복) | 비선형 전 구간 최적, 1kHz 실현 가능 |
| 메인 컴퓨팅 | KV260 FPGA | DSP 1,248개 병렬, R5 실시간 코어 |
| 비전 | Jetson Orin NX | YOLO 실시간 락온 |
| 카메라 | 이중 (IMX219 광각 + IMX477 망원) | 탐색-추적 모드 분리 |
| 서보 통신 | DroneCAN | 단일 버스, 노이즈 면역, 피드백 가능 |
| 비행 제어 | Pixhawk 6C + PX4 | Alt Hold, EKF2, 페일세이프 기존 검증 |
| 기체 모델 | Aerosonde (Beard & McLain) | 공개 파라미터, 학술 표준 |
| 실비행 기체 | Skywalker X8 | 탑재 중량 1kg, 안정적 |

## Document Structure

```
SDRE-Project/
|-- README.md                          # 이 파일 (프로젝트 개요)
|-- docs/
|   |-- 01_system_architecture.md      # 전체 시스템 아키텍처
|   |-- 02_hardware_configuration.md   # 하드웨어 구성 및 핀맵
|   |-- 03_control_theory.md           # 제어 이론 정리 (ARE/SDRE/HJB/MPC)
|   |-- 04_phd_thesis_roadmap.md       # 박사 논문 방향 및 학습 로드맵
|   |-- 05_paper_analysis.md           # 핵심 논문 분석 (arXiv 2503.01587 등)
```

## Development Phases

| Phase | 목표 | 환경 | 핵심 산출물 |
|-------|------|------|------------|
| **Phase 1** | 알고리즘 검증 | PC (Python) | SDRE 시뮬레이션, 3종 표적 시나리오 |
| **Phase 2** | C++ 포팅 | Teensy 4.1 | 1kHz 달성 여부 판단 |
| **Phase 3** | FPGA 가속 | KV260 | Vitis HLS, 50us/ARE 목표 |
| **Phase 4** | 비전 통합 | Jetson + KV260 | SITL -> HITL |
| **Phase 5** | 실기체 검증 | Aerosonde/Skywalker X8 | PID vs LQR vs SDRE 비교 |

> **판단 분기점**: Phase 2에서 Teensy 1kHz 달성 시 -> KV260 PL 가속 불필요, PS만으로 진행 가능

## References

### Core Papers
- Menon & Ohlmeyer (2001, 2007) - "Numerical SDRE Approach for Missile IGC"
- Cloutier (1997) - "SDRE Techniques: An Overview"
- Cimen (2008) - "SDRE Control: A Survey"
- Saluzzi (2025) - arXiv:2503.01587 "SDRE in Nonlinear Optimal Control"
- Yang et al. (2008) - "SDRE 기법을 이용한 헬리콥터 비선형 최적제어기 설계"

### Core Textbooks
- Beard & McLain - "Small Unmanned Aircraft: Theory and Practice"
- Khalil - "Nonlinear Systems" 3rd ed
- Slotine & Li - "Applied Nonlinear Control"
- Liberzon - "Switching in Systems and Control"

### Key Repositories
- https://github.com/byu-magicc/mavsim_python (Aerosonde 파라미터)
- https://github.com/Daniboy370/Missile-Guidance (유도 법칙)

## Source Conversations
- [SDRE 최적제어 + 하드웨어 설계 대화](https://claude.ai/share/9e6daafb-673c-4341-b4b9-c415f0f6dc6f)
- [논문 분석 (arXiv 2503.01587)](https://claude.ai/share/7b9554a3-a862-44cc-a9f9-c9eda5a87e29)
