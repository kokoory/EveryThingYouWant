"""
PID vs LQR vs SDRE 비교 시뮬레이션
====================================

Aerosonde 종방향 모델(4차)에서 세 제어기의 성능을 비교.
시나리오: 피치각 스텝 응답, 돌풍 외란, 대기동 (대각도 변화)

비교 지표:
  - 추종 오차 (RMSE)
  - 제어 에너지 (integral of u^2)
  - 정착 시간 (2% 기준)
  - 최대 오버슈트
"""

import numpy as np
from scipy import linalg
from scipy.integrate import solve_ivp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from aerosonde_model import AerosondeModel, compute_trim, longitudinal_model
from sdre_solver import solve_are_scipy, solve_are_newton_kleinman, SDREController


# ============================================================================
# 1. 종방향 시뮬레이션 환경
# ============================================================================

class LongitudinalSim:
    """Aerosonde 종방향 4차 모델 시뮬레이션."""

    def __init__(self):
        self.model = AerosondeModel()
        self.x_trim, self.u_trim = compute_trim(self.model, Va=35.0)
        self.A_trim, self.B_trim = longitudinal_model(
            self.model, self.x_trim, self.u_trim)

        # 종방향 상태 인덱스
        self.lon_idx = [0, 2, 4, 7]  # u, w, q, theta
        self.lon_u_idx = [0, 3]       # de, dt

        self.x_lon_trim = self.x_trim[self.lon_idx]
        self.u_lon_trim = self.u_trim[self.lon_u_idx]

    def dynamics_lon(self, dx_lon, du_lon):
        """종방향 선형 동역학: dx_dot = A*dx + B*du."""
        return self.A_trim @ dx_lon + self.B_trim @ du_lon


# ============================================================================
# 2. PID 제어기
# ============================================================================

class PIDController:
    """종방향 PID 피치각 제어기."""

    def __init__(self, kp=1.5, ki=0.3, kd=0.5, dt=0.01):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.dt = dt
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, theta_cmd, theta, q):
        """
        피치각 명령 추종.

        Parameters
        ----------
        theta_cmd : 목표 피치각 (rad, 트림 기준 편차)
        theta : 현재 피치각 편차
        q : 피치 각속도

        Returns
        -------
        de : 엘리베이터 편차
        """
        error = theta_cmd - theta
        self.integral += error * self.dt
        self.integral = np.clip(self.integral, -1.0, 1.0)
        derivative = -q  # 미분항은 q로 대체 (미분 킥 방지)

        de = self.kp * error + self.ki * self.integral + self.kd * derivative
        return np.clip(de, -0.4, 0.4)

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0


# ============================================================================
# 3. LQR 제어기 (고정 K)
# ============================================================================

class LQRController:
    """종방향 LQR 제어기 (트림 점에서 한 번 계산)."""

    def __init__(self, A, B, Q=None, R=None):
        n = A.shape[0]
        m = B.shape[1]
        if Q is None:
            Q = np.diag([1.0, 1.0, 10.0, 100.0])  # u, w, q, theta 가중
        if R is None:
            R = np.diag([1.0, 1.0])  # de, dt 가중

        P = linalg.solve_continuous_are(A, B, Q, R)
        self.K = np.linalg.solve(R, B.T @ P)
        self.Q = Q
        self.R = R

    def compute(self, dx):
        """
        Parameters
        ----------
        dx : (4,) 상태 편차 [du, dw, dq, dtheta]

        Returns
        -------
        du : (2,) 제어 편차 [dde, ddt]
        """
        du = -self.K @ dx
        du[0] = np.clip(du[0], -0.4, 0.4)  # 엘리베이터 제한
        du[1] = np.clip(du[1], -0.5, 0.5)  # 스로틀 제한
        return du


# ============================================================================
# 4. SDRE 제어기 (종방향)
# ============================================================================

class SDRELongController:
    """종방향 SDRE 제어기 (매 루프 K 갱신)."""

    def __init__(self, model, x_trim, u_trim, Q=None, R=None):
        self.model = model
        self.x_trim = x_trim
        self.u_trim = u_trim
        self.lon_idx = [0, 2, 4, 7]
        self.lon_u_idx = [0, 3]

        n = 4
        m = 2
        if Q is None:
            Q = np.diag([1.0, 1.0, 10.0, 100.0])
        if R is None:
            R = np.diag([1.0, 1.0])

        self.Q = Q
        self.R = R
        self.R_inv = np.linalg.inv(R)
        self.P_prev = None
        self.solve_times = []
        self.iterations = []

    def compute(self, dx):
        """
        Parameters
        ----------
        dx : (4,) 상태 편차

        Returns
        -------
        du : (2,) 제어 편차
        """
        import time

        # 현재 상태에서 A(x), B(x) 계산
        x_current = self.x_trim.copy()
        x_current[self.lon_idx] += dx

        from aerosonde_model import numerical_jacobian
        A_full, B_full = numerical_jacobian(
            lambda x, u: self.model.derivatives(x, u),
            x_current, self.u_trim
        )

        A = A_full[np.ix_(self.lon_idx, self.lon_idx)]
        B = B_full[np.ix_(self.lon_idx, self.lon_u_idx)]

        t0 = time.perf_counter()

        P, iters, _ = solve_are_newton_kleinman(
            A, B, self.Q, self.R,
            P0=self.P_prev, max_iter=20, tol=1e-8
        )

        dt_solve = time.perf_counter() - t0
        self.solve_times.append(dt_solve)
        self.iterations.append(iters)
        self.P_prev = P.copy()

        K = self.R_inv @ B.T @ P
        du = -K @ dx
        du[0] = np.clip(du[0], -0.4, 0.4)
        du[1] = np.clip(du[1], -0.5, 0.5)
        return du


# ============================================================================
# 5. 시뮬레이션 실행
# ============================================================================

def run_simulation(sim, controller_type, theta_cmd_func, t_span=(0, 10),
                   dt=0.01, disturbance_func=None):
    """
    시뮬레이션 실행.

    Parameters
    ----------
    sim : LongitudinalSim
    controller_type : "pid", "lqr", "sdre"
    theta_cmd_func : t -> theta_cmd (목표 피치각 편차, rad)
    t_span : (t0, tf)
    dt : 시뮬레이션 스텝 (초)
    disturbance_func : t -> [du_dist, dw_dist, 0, 0] 외란

    Returns
    -------
    result : dict with 't', 'x', 'u', 'theta_cmd'
    """
    Q = np.diag([1.0, 1.0, 10.0, 100.0])
    R = np.diag([1.0, 1.0])

    if controller_type == "pid":
        ctrl = PIDController(kp=2.0, ki=0.5, kd=0.8, dt=dt)
    elif controller_type == "lqr":
        ctrl = LQRController(sim.A_trim, sim.B_trim, Q, R)
    elif controller_type == "sdre":
        ctrl = SDRELongController(sim.model, sim.x_trim, sim.u_trim, Q, R)
    else:
        raise ValueError(f"Unknown controller: {controller_type}")

    t0, tf = t_span
    times = np.arange(t0, tf, dt)
    n_steps = len(times)

    # 상태/제어 기록
    x_hist = np.zeros((n_steps, 4))
    u_hist = np.zeros((n_steps, 2))
    cmd_hist = np.zeros(n_steps)

    dx = np.zeros(4)  # 초기 상태 편차 = 0

    for i, t in enumerate(times):
        theta_cmd = theta_cmd_func(t)
        cmd_hist[i] = theta_cmd

        # 제어 계산
        if controller_type == "pid":
            de = ctrl.compute(theta_cmd, dx[3], dx[2])
            du = np.array([de, 0.0])
        else:
            du = ctrl.compute(dx)

        # 외란
        dist = np.zeros(4)
        if disturbance_func is not None:
            dist = disturbance_func(t)

        x_hist[i] = dx.copy()
        u_hist[i] = du.copy()

        # 상태 갱신 (Euler)
        dxdot = sim.A_trim @ dx + sim.B_trim @ du + dist
        dx = dx + dxdot * dt

    result = {
        't': times,
        'x': x_hist,
        'u': u_hist,
        'theta_cmd': cmd_hist,
    }

    if controller_type == "sdre":
        result['solve_times'] = np.array(ctrl.solve_times)
        result['iterations'] = np.array(ctrl.iterations)

    return result


# ============================================================================
# 6. 성능 지표 계산
# ============================================================================

def compute_metrics(result, dt=0.01):
    """성능 지표 계산."""
    theta = result['x'][:, 3]
    theta_cmd = result['theta_cmd']
    u_de = result['u'][:, 0]
    t = result['t']

    error = theta_cmd - theta

    # RMSE
    rmse = np.sqrt(np.mean(error**2))

    # 제어 에너지
    energy = np.sum(u_de**2) * dt

    # 정착 시간 (2% 기준)
    final_val = theta_cmd[-1] if theta_cmd[-1] != 0 else 1e-6
    settling_idx = len(t) - 1
    for i in range(len(t) - 1, -1, -1):
        if abs(error[i]) > 0.02 * abs(final_val):
            settling_idx = min(i + 1, len(t) - 1)
            break
    settling_time = t[settling_idx] - t[0]

    # 최대 오버슈트
    if abs(final_val) > 1e-8:
        overshoot = (np.max(theta) - final_val) / abs(final_val) * 100
    else:
        overshoot = 0.0

    return {
        'RMSE (rad)': rmse,
        '제어 에너지': energy,
        '정착 시간 (s)': settling_time,
        '최대 오버슈트 (%)': max(overshoot, 0),
    }


# ============================================================================
# 7. 시나리오 정의 + 실행 + 시각화
# ============================================================================

def run_all_scenarios():
    """세 가지 시나리오에서 PID/LQR/SDRE 비교."""

    sim = LongitudinalSim()
    print(f"트림 계산 완료: Va=35 m/s")
    print(f"  A_lon 고유값: {np.linalg.eigvals(sim.A_trim)}")

    controllers = ['pid', 'lqr', 'sdre']
    colors = {'pid': 'red', 'lqr': 'blue', 'sdre': 'green'}

    # --- 시나리오 1: 피치각 5도 스텝 응답 ---
    print("\n" + "="*60)
    print("시나리오 1: 피치각 5도 스텝 응답")
    print("="*60)

    theta_step = np.deg2rad(5.0)
    step_cmd = lambda t: theta_step if t >= 1.0 else 0.0

    results_1 = {}
    for ctrl in controllers:
        print(f"  {ctrl.upper()} 시뮬레이션 중...")
        results_1[ctrl] = run_simulation(sim, ctrl, step_cmd, t_span=(0, 10))

    # --- 시나리오 2: 돌풍 외란 ---
    print("\n" + "="*60)
    print("시나리오 2: 수평 비행 중 돌풍 (3초~4초)")
    print("="*60)

    def gust(t):
        if 3.0 <= t <= 4.0:
            return np.array([5.0, 3.0, 0.0, 0.0])  # u, w 방향 돌풍
        return np.zeros(4)

    results_2 = {}
    for ctrl in controllers:
        print(f"  {ctrl.upper()} 시뮬레이션 중...")
        results_2[ctrl] = run_simulation(
            sim, ctrl, lambda t: 0.0, t_span=(0, 10), disturbance_func=gust)

    # --- 시나리오 3: 대기동 (피치 20도) ---
    print("\n" + "="*60)
    print("시나리오 3: 대기동 (피치 20도 명령)")
    print("="*60)

    theta_large = np.deg2rad(20.0)
    large_cmd = lambda t: theta_large if t >= 1.0 else 0.0

    results_3 = {}
    for ctrl in controllers:
        print(f"  {ctrl.upper()} 시뮬레이션 중...")
        results_3[ctrl] = run_simulation(sim, ctrl, large_cmd, t_span=(0, 15))

    # --- 성능 비교 표 ---
    all_scenarios = [
        ("스텝 응답 5deg", results_1),
        ("돌풍 외란", results_2),
        ("대기동 20deg", results_3),
    ]

    print("\n" + "="*70)
    print("성능 비교 결과")
    print("="*70)

    for scenario_name, results in all_scenarios:
        print(f"\n--- {scenario_name} ---")
        print(f"{'제어기':<8} {'RMSE(rad)':<12} {'제어에너지':<12} {'정착시간(s)':<12} {'오버슈트(%)':<12}")
        print("-" * 56)
        for ctrl in controllers:
            m = compute_metrics(results[ctrl])
            print(f"{ctrl.upper():<8} {m['RMSE (rad)']:<12.6f} {m['제어 에너지']:<12.4f} "
                  f"{m['정착 시간 (s)']:<12.2f} {m['최대 오버슈트 (%)']:<12.1f}")

    # --- SDRE 솔버 성능 ---
    if 'solve_times' in results_1['sdre']:
        st = results_1['sdre']['solve_times']
        it = results_1['sdre']['iterations']
        print(f"\n--- SDRE 솔버 성능 (시나리오 1) ---")
        print(f"  평균 풀이 시간: {np.mean(st)*1000:.4f} ms")
        print(f"  최대 풀이 시간: {np.max(st)*1000:.4f} ms")
        print(f"  평균 반복 횟수: {np.mean(it):.1f}")
        print(f"  1kHz 달성 가능: {'YES' if np.max(st) < 0.001 else 'NO'} (최대 {np.max(st)*1000:.2f}ms)")

    # --- 그래프 생성 ---
    fig, axes = plt.subplots(3, 3, figsize=(18, 14))
    fig.suptitle('PID vs LQR vs SDRE Comparison - Aerosonde Longitudinal', fontsize=14)

    for col, (scenario_name, results) in enumerate(all_scenarios):
        # 피치각 응답
        ax = axes[0, col]
        for ctrl in controllers:
            ax.plot(results[ctrl]['t'], np.rad2deg(results[ctrl]['x'][:, 3]),
                    color=colors[ctrl], label=ctrl.upper(), linewidth=1.5)
        ax.plot(results['pid']['t'], np.rad2deg(results['pid']['theta_cmd']),
                'k--', label='CMD', linewidth=1)
        ax.set_title(scenario_name)
        ax.set_ylabel('Pitch (deg)')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

        # 엘리베이터 입력
        ax = axes[1, col]
        for ctrl in controllers:
            ax.plot(results[ctrl]['t'], np.rad2deg(results[ctrl]['u'][:, 0]),
                    color=colors[ctrl], label=ctrl.upper(), linewidth=1.5)
        ax.set_ylabel('Elevator (deg)')
        ax.grid(True, alpha=0.3)

        # 추종 오차
        ax = axes[2, col]
        for ctrl in controllers:
            error = results[ctrl]['theta_cmd'] - results[ctrl]['x'][:, 3]
            ax.plot(results[ctrl]['t'], np.rad2deg(error),
                    color=colors[ctrl], label=ctrl.upper(), linewidth=1.5)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Error (deg)')
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('/home/user/EveryThingYouWant/SDRE-Project/code/comparison_results.png',
                dpi=150, bbox_inches='tight')
    print(f"\n그래프 저장: comparison_results.png")
    plt.close()


if __name__ == "__main__":
    run_all_scenarios()
