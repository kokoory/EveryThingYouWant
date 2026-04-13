"""
SDRE (State-Dependent Riccati Equation) 솔버 모듈
=================================================

ARE 솔버 두 가지 구현:
  1. scipy.linalg.solve_continuous_are 기반 직접 풀이
  2. Newton-Kleinman 반복법 (warm-start 지원)

SDRE 제어기 클래스:
  - 매 루프마다 SDC 파라미터 A(x), B(x) 계산
  - Newton-Kleinman으로 ARE를 warm-start하여 빠르게 풀기
  - 최적 제어 u = -K(x) * x 반환
"""

import numpy as np
from scipy import linalg
import time
from typing import Callable, Optional, Tuple


# ============================================================================
# 1. ARE 솔버: scipy 기반
# ============================================================================

def solve_are_scipy(A: np.ndarray, B: np.ndarray,
                    Q: np.ndarray, R: np.ndarray) -> np.ndarray:
    """
    scipy의 solve_continuous_are를 사용한 ARE 풀이.

    ARE: A^T P + P A - P B R^{-1} B^T P + Q = 0

    Parameters
    ----------
    A : (n, n) 시스템 행렬
    B : (n, m) 입력 행렬
    Q : (n, n) 상태 가중 행렬 (양의 준정치)
    R : (m, m) 제어 가중 행렬 (양의 정치)

    Returns
    -------
    P : (n, n) 리카티 방정식의 해 (대칭, 양의 정치)
    """
    P = linalg.solve_continuous_are(A, B, Q, R)
    return P


# ============================================================================
# 2. Newton-Kleinman 반복법
# ============================================================================

def solve_are_newton_kleinman(
    A: np.ndarray, B: np.ndarray,
    Q: np.ndarray, R: np.ndarray,
    P0: Optional[np.ndarray] = None,
    max_iter: int = 50,
    tol: float = 1e-10,
    verbose: bool = False
) -> Tuple[np.ndarray, int, float]:
    """
    Newton-Kleinman 반복법으로 ARE를 풂.

    알고리즘 (Banks & Ito 참조):
      1. 초기 안정화 게인 K_0 계산 (또는 P0에서 warm-start)
      2. 반복:
         S_i = A - B K_i
         S_i^T P_{i+1} + P_{i+1} S_i = -(Q + K_i^T R K_i)   (Lyapunov 방정식)
         K_{i+1} = R^{-1} B^T P_{i+1}
      3. ||P_{i+1} - P_i|| < tol 이면 수렴

    Warm-start 시 이전 P를 초기값으로 사용하면 1~3회 반복으로 수렴 가능.

    Parameters
    ----------
    A : (n, n) 시스템 행렬
    B : (n, m) 입력 행렬
    Q : (n, n) 상태 가중 행렬
    R : (m, m) 제어 가중 행렬
    P0 : (n, n) 초기 P 행렬 (warm-start용, None이면 자동 초기화)
    max_iter : 최대 반복 횟수
    tol : 수렴 판정 임계값
    verbose : True이면 반복 정보 출력

    Returns
    -------
    P : (n, n) 수렴된 리카티 방정식 해
    iterations : 실제 반복 횟수
    residual : 최종 잔차
    """
    n = A.shape[0]
    m = B.shape[1]
    R_inv = np.linalg.inv(R)

    # --- 초기 게인 K_0 결정 ---
    if P0 is not None:
        # Warm-start: 이전 P에서 K 계산
        K = R_inv @ B.T @ P0
    else:
        # 초기 안정화 게인: LQR로 한번 풀어서 시작하거나,
        # 간단한 극배치로 안정화
        # 여기서는 간단하게 P0 = Q로 시작
        P0 = Q.copy()
        K = R_inv @ B.T @ P0

    # 초기 S = A - BK가 안정한지 확인, 아니면 scipy로 초기값 계산
    S = A - B @ K
    eigvals = np.linalg.eigvals(S)
    if np.any(np.real(eigvals) >= 0):
        # 안정하지 않으면 scipy로 초기 P 계산
        try:
            P0 = linalg.solve_continuous_are(A, B, Q, R)
            K = R_inv @ B.T @ P0
        except np.linalg.LinAlgError:
            # scipy도 실패하면 큰 P로 시작
            P0 = 100.0 * np.eye(n)
            K = R_inv @ B.T @ P0

    P_prev = P0.copy()

    for i in range(max_iter):
        # S_i = A - B K_i (폐루프 행렬)
        S = A - B @ K

        # Lyapunov 방정식: S^T P + P S = -(Q + K^T R K)
        Q_lyap = -(Q + K.T @ R @ K)
        try:
            P = linalg.solve_continuous_lyapunov(S.T, Q_lyap)
        except np.linalg.LinAlgError:
            if verbose:
                print(f"  [NK] Lyapunov 풀이 실패 (반복 {i})")
            break

        # 대칭성 보장
        P = 0.5 * (P + P.T)

        # 수렴 확인
        residual = np.linalg.norm(P - P_prev, 'fro') / max(np.linalg.norm(P, 'fro'), 1e-12)

        if verbose:
            print(f"  [NK] 반복 {i+1}: 상대 잔차 = {residual:.3e}")

        if residual < tol:
            return P, i + 1, residual

        # 게인 갱신
        K = R_inv @ B.T @ P
        P_prev = P.copy()

    return P, max_iter, residual


# ============================================================================
# 3. SDRE 제어기 클래스
# ============================================================================

class SDREController:
    """
    SDRE (State-Dependent Riccati Equation) 제어기.

    비선형 시스템 x_dot = f(x, u)를 SDC 분할:
        x_dot = A(x) x + B(x) u

    매 제어 루프마다:
      1. 현재 상태 x에서 A(x), B(x) 계산
      2. ARE를 Newton-Kleinman으로 풀기 (이전 P로 warm-start)
      3. 최적 게인 K(x) = R^{-1} B(x)^T P(x)
      4. 제어 입력 u = -K(x) x 반환
    """

    def __init__(
        self,
        sdc_func: Callable[[np.ndarray], Tuple[np.ndarray, np.ndarray]],
        Q: np.ndarray,
        R: np.ndarray,
        solver: str = "newton_kleinman",
        nk_max_iter: int = 20,
        nk_tol: float = 1e-8,
        verbose: bool = False
    ):
        """
        Parameters
        ----------
        sdc_func : callable
            상태 x를 받아 (A(x), B(x)) 튜플을 반환하는 함수.
            SDC 파라미터화 함수.
        Q : (n, n) 상태 가중 행렬
        R : (m, m) 제어 가중 행렬
        solver : "newton_kleinman" 또는 "scipy"
        nk_max_iter : Newton-Kleinman 최대 반복 (solver="newton_kleinman"일 때)
        nk_tol : Newton-Kleinman 수렴 임계값
        verbose : 디버그 출력 여부
        """
        self.sdc_func = sdc_func
        self.Q = Q.copy()
        self.R = R.copy()
        self.R_inv = np.linalg.inv(R)
        self.solver = solver
        self.nk_max_iter = nk_max_iter
        self.nk_tol = nk_tol
        self.verbose = verbose

        # Warm-start용 이전 P 저장
        self.P_prev: Optional[np.ndarray] = None

        # 성능 기록
        self.solve_times = []
        self.iterations_log = []

    def compute_control(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        현재 상태 x에서 최적 제어 입력을 계산.

        Parameters
        ----------
        x : (n,) 현재 상태 벡터

        Returns
        -------
        u : (m,) 최적 제어 입력
        K : (m, n) 최적 게인 행렬
        """
        # SDC 파라미터 계산
        A, B = self.sdc_func(x)

        t_start = time.perf_counter()

        if self.solver == "scipy":
            P = solve_are_scipy(A, B, self.Q, self.R)
            iterations = 1
        elif self.solver == "newton_kleinman":
            P, iterations, residual = solve_are_newton_kleinman(
                A, B, self.Q, self.R,
                P0=self.P_prev,
                max_iter=self.nk_max_iter,
                tol=self.nk_tol,
                verbose=self.verbose
            )
        else:
            raise ValueError(f"알 수 없는 솔버: {self.solver}")

        t_elapsed = time.perf_counter() - t_start

        # 성능 기록
        self.solve_times.append(t_elapsed)
        self.iterations_log.append(iterations)

        # Warm-start를 위해 현재 P 저장
        self.P_prev = P.copy()

        # 최적 게인 및 제어 입력
        K = self.R_inv @ B.T @ P
        u = -K @ x

        return u, K

    def reset(self):
        """Warm-start 상태 초기화."""
        self.P_prev = None
        self.solve_times.clear()
        self.iterations_log.clear()

    def get_performance_stats(self) -> dict:
        """솔버 성능 통계를 반환."""
        if not self.solve_times:
            return {}
        times = np.array(self.solve_times)
        iters = np.array(self.iterations_log)
        return {
            "평균 풀이 시간 (ms)": np.mean(times) * 1000,
            "최대 풀이 시간 (ms)": np.max(times) * 1000,
            "최소 풀이 시간 (ms)": np.min(times) * 1000,
            "표준편차 (ms)": np.std(times) * 1000,
            "평균 반복 횟수": np.mean(iters),
            "총 호출 횟수": len(times),
        }


# ============================================================================
# 4. 성능 비교: scipy ARE vs Newton-Kleinman
# ============================================================================

def benchmark_solvers(n_states: int = 6, n_inputs: int = 3,
                      n_trials: int = 100, warm_start: bool = True):
    """
    scipy ARE와 Newton-Kleinman 솔버의 성능을 비교.

    무작위 안정 시스템을 생성하여 두 솔버의 풀이 시간을 측정.

    Parameters
    ----------
    n_states : 상태 차원
    n_inputs : 입력 차원
    n_trials : 반복 시행 횟수
    warm_start : Newton-Kleinman에서 warm-start 사용 여부
    """
    print(f"\n{'='*60}")
    print(f"ARE 솔버 성능 비교 (상태={n_states}, 입력={n_inputs}, 시행={n_trials})")
    print(f"{'='*60}")

    # 안정한 무작위 시스템 생성 (고유값이 음수 실수부를 갖도록)
    np.random.seed(42)

    # 기본 안정 시스템 생성
    A_base = -np.eye(n_states) + 0.5 * np.random.randn(n_states, n_states)
    # 안정성 보장: A를 Hurwitz로 만듦
    eigvals = np.linalg.eigvals(A_base)
    if np.any(np.real(eigvals) >= 0):
        A_base = A_base - (np.max(np.real(eigvals)) + 1.0) * np.eye(n_states)

    B = np.random.randn(n_states, n_inputs)
    Q = np.eye(n_states)
    R = np.eye(n_inputs)

    # --- scipy 타이밍 ---
    scipy_times = []
    for i in range(n_trials):
        # 상태 변화를 시뮬레이션: A에 작은 섭동 추가
        perturbation = 0.01 * np.random.randn(n_states, n_states)
        A = A_base + perturbation

        t0 = time.perf_counter()
        P_scipy = solve_are_scipy(A, B, Q, R)
        t1 = time.perf_counter()
        scipy_times.append(t1 - t0)

    # --- Newton-Kleinman 타이밍 ---
    nk_times = []
    nk_iters = []
    P_prev = None

    for i in range(n_trials):
        perturbation = 0.01 * np.random.randn(n_states, n_states)
        A = A_base + perturbation

        t0 = time.perf_counter()
        P_nk, iters, _ = solve_are_newton_kleinman(
            A, B, Q, R,
            P0=P_prev if warm_start else None,
            max_iter=50,
            tol=1e-10
        )
        t1 = time.perf_counter()
        nk_times.append(t1 - t0)
        nk_iters.append(iters)

        if warm_start:
            P_prev = P_nk

    scipy_times = np.array(scipy_times)
    nk_times = np.array(nk_times)
    nk_iters = np.array(nk_iters)

    # --- 정확도 검증 ---
    # 마지막 시행에서 두 솔버의 해 비교
    A_test = A_base + 0.01 * np.random.randn(n_states, n_states)
    P_ref = solve_are_scipy(A_test, B, Q, R)
    P_nk_test, _, _ = solve_are_newton_kleinman(A_test, B, Q, R, P0=P_prev)
    err = np.linalg.norm(P_ref - P_nk_test, 'fro') / np.linalg.norm(P_ref, 'fro')

    print(f"\n--- scipy ARE ---")
    print(f"  평균: {np.mean(scipy_times)*1000:.4f} ms")
    print(f"  표준편차: {np.std(scipy_times)*1000:.4f} ms")
    print(f"  최소: {np.min(scipy_times)*1000:.4f} ms")
    print(f"  최대: {np.max(scipy_times)*1000:.4f} ms")

    print(f"\n--- Newton-Kleinman {'(warm-start)' if warm_start else '(cold-start)'} ---")
    print(f"  평균: {np.mean(nk_times)*1000:.4f} ms")
    print(f"  표준편차: {np.std(nk_times)*1000:.4f} ms")
    print(f"  최소: {np.min(nk_times)*1000:.4f} ms")
    print(f"  최대: {np.max(nk_times)*1000:.4f} ms")
    print(f"  평균 반복: {np.mean(nk_iters):.1f} 회")
    print(f"  최대 반복: {np.max(nk_iters)} 회")

    print(f"\n--- 비교 ---")
    speedup = np.mean(scipy_times) / np.mean(nk_times)
    print(f"  속도비 (scipy/NK): {speedup:.2f}x")
    print(f"  해 오차 (상대): {err:.2e}")
    print(f"{'='*60}\n")

    return scipy_times, nk_times, nk_iters


# ============================================================================
# 메인: 예제 실행
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SDRE 솔버 모듈 테스트")
    print("=" * 60)

    # --- 1. 간단한 ARE 풀이 테스트 ---
    print("\n[테스트 1] 2차 시스템 ARE 풀이")
    A = np.array([[ 0.0, 1.0],
                  [-2.0, -3.0]])
    B = np.array([[0.0],
                  [1.0]])
    Q = np.diag([10.0, 1.0])
    R = np.array([[1.0]])

    P_scipy = solve_are_scipy(A, B, Q, R)
    P_nk, iters, res = solve_are_newton_kleinman(A, B, Q, R, verbose=True)

    print(f"\nscipy P:\n{P_scipy}")
    print(f"\nNewton-Kleinman P (반복 {iters}회, 잔차 {res:.2e}):\n{P_nk}")
    print(f"차이: {np.linalg.norm(P_scipy - P_nk):.2e}")

    K_scipy = np.linalg.solve(R, B.T @ P_scipy)
    K_nk = np.linalg.solve(R, B.T @ P_nk)
    print(f"\nscipy K: {K_scipy.flatten()}")
    print(f"NK K:    {K_nk.flatten()}")

    # --- 2. SDRE 제어기 테스트 (비선형 진자) ---
    print("\n\n[테스트 2] 비선형 진자 SDRE 제어")

    def pendulum_sdc(x):
        """
        비선형 진자의 SDC 파라미터화.
        x_dot = [x2, -g/l * sin(x1) - b*x2 + u/m*l^2]

        SDC: A(x) x + B u  형태로 분할
        """
        g, l, b_damp, ml2 = 9.81, 1.0, 0.1, 1.0
        theta, omega = x[0], x[1]

        # sinc 함수를 이용한 SDC 분할: sin(theta)/theta
        if abs(theta) > 1e-8:
            sinc_val = np.sin(theta) / theta
        else:
            sinc_val = 1.0  # lim(sin(x)/x) = 1

        A = np.array([[0.0, 1.0],
                      [-g / l * sinc_val, -b_damp]])
        B = np.array([[0.0],
                      [1.0 / ml2]])
        return A, B

    Q_pend = np.diag([100.0, 10.0])
    R_pend = np.array([[1.0]])

    # SDRE 제어기 생성
    ctrl_nk = SDREController(pendulum_sdc, Q_pend, R_pend,
                              solver="newton_kleinman", verbose=False)
    ctrl_scipy = SDREController(pendulum_sdc, Q_pend, R_pend,
                                 solver="scipy", verbose=False)

    # 여러 상태에서 제어 입력 비교
    test_states = [
        np.array([0.1, 0.0]),
        np.array([0.5, 0.2]),
        np.array([1.0, -0.5]),
        np.array([np.pi / 2, 0.0]),    # 90도
        np.array([np.pi - 0.1, 0.0]),  # 거의 역립
    ]

    print(f"\n{'상태 (theta, omega)':<28} {'u (NK)':<14} {'u (scipy)':<14} {'차이':<12}")
    print("-" * 68)
    for x in test_states:
        u_nk, _ = ctrl_nk.compute_control(x)
        u_sp, _ = ctrl_scipy.compute_control(x)
        diff = abs(u_nk[0] - u_sp[0])
        print(f"({x[0]:6.3f}, {x[1]:6.3f})          "
              f"{u_nk[0]:10.4f}    {u_sp[0]:10.4f}    {diff:.2e}")

    print("\n--- NK 성능 통계 ---")
    stats = ctrl_nk.get_performance_stats()
    for key, val in stats.items():
        print(f"  {key}: {val:.4f}" if isinstance(val, float) else f"  {key}: {val}")

    # --- 3. 성능 벤치마크 ---
    print("\n\n[테스트 3] 솔버 성능 벤치마크")

    # 소규모 시스템
    benchmark_solvers(n_states=4, n_inputs=2, n_trials=200, warm_start=True)

    # 중규모 시스템
    benchmark_solvers(n_states=12, n_inputs=4, n_trials=100, warm_start=True)

    # Warm-start vs Cold-start 비교
    print("\n[테스트 4] Warm-start vs Cold-start 비교 (12-state)")
    _, nk_warm, iters_warm = benchmark_solvers(
        n_states=12, n_inputs=4, n_trials=100, warm_start=True)
    _, nk_cold, iters_cold = benchmark_solvers(
        n_states=12, n_inputs=4, n_trials=100, warm_start=False)

    print(f"\nWarm-start 평균 시간: {np.mean(nk_warm)*1000:.4f} ms, "
          f"평균 반복: {np.mean(iters_warm):.1f}")
    print(f"Cold-start 평균 시간: {np.mean(nk_cold)*1000:.4f} ms, "
          f"평균 반복: {np.mean(iters_cold):.1f}")
    print(f"Warm-start 속도 향상: {np.mean(nk_cold)/np.mean(nk_warm):.2f}x")
