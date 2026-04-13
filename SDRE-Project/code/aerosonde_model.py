"""
Aerosonde UAV 6-DOF 동역학 모델
================================

Beard & McLain "Small Unmanned Aircraft" Appendix E.2 파라미터 기반.
- 비선형 6-DOF 운동 방정식
- 트림 계산 (수평 직선 비행)
- SDC 파라미터화: f(x) = A(x)*x + B(x)*u
- 종방향(4차) / 6-DOF(12차) 모델 지원
"""

import numpy as np
from scipy.optimize import fsolve
from scipy import linalg
from typing import Tuple, Optional


# ============================================================================
# 1. Aerosonde 물리 파라미터 (Beard & McLain Appendix E.2)
# ============================================================================

class AerosondeParams:
    """Aerosonde UAV 파라미터."""

    # --- 기체 물리량 ---
    mass = 13.5          # kg
    Jx = 0.8244          # kg*m^2
    Jy = 1.135           # kg*m^2
    Jz = 1.759           # kg*m^2
    Jxz = 0.1204         # kg*m^2

    S_wing = 0.55        # m^2 (날개 면적)
    b = 2.8956           # m (날개폭)
    c = 0.18994          # m (평균 시위)
    S_prop = 0.2027      # m^2 (프로펠러 면적)
    rho = 1.2682         # kg/m^3 (공기 밀도, 해수면)
    e = 0.9              # Oswald 효율 계수
    AR = b**2 / S_wing   # 종횡비

    k_motor = 80.0
    C_prop = 1.0

    g = 9.81             # m/s^2

    # --- 종방향 공력 계수 ---
    CL0 = 0.28;    CD0 = 0.03;    Cm0 = -0.02400
    CLalpha = 3.45; CDalpha = 0.30; Cmalpha = -0.38000
    CLq = 0.0;      CDq = 0.0;     Cmq = -3.60000
    CLde = 0.36;    CDde = 0.0;    Cmde = -0.50000
    M = 50.0        # 실속 전이 매개변수
    alpha0 = 0.4712 # 실속 각도 (rad)

    # --- 횡방향 공력 계수 ---
    CY0 = 0.0;   Cl0 = 0.0;   Cn0 = 0.0
    CYbeta = -0.98; Clbeta = -0.12; Cnbeta = 0.25
    CYp = 0.0;     Clp = -0.26;    Cnp = -0.022
    CYr = 0.0;     Clr = 0.14;     Cnr = -0.35
    CYda = 0.0;    Clda = 0.08;    Cnda = 0.06
    CYdr = -0.17;  Cldr = 0.105;   Cndr = -0.032

    # --- 관성 모멘트 유도량 ---
    Gamma = Jx * Jz - Jxz**2
    Gamma1 = (Jxz * (Jx - Jy + Jz)) / Gamma
    Gamma2 = (Jz * (Jz - Jy) + Jxz**2) / Gamma
    Gamma3 = Jz / Gamma
    Gamma4 = Jxz / Gamma
    Gamma5 = (Jz - Jx) / Jy
    Gamma6 = Jxz / Jy
    Gamma7 = ((Jx - Jy) * Jx + Jxz**2) / Gamma
    Gamma8 = Jx / Gamma


# ============================================================================
# 2. 비선형 6-DOF 운동 방정식
# ============================================================================

class AerosondeModel:
    """Aerosonde 6-DOF 비선형 동역학 모델."""

    def __init__(self):
        self.p = AerosondeParams()

    def forces_moments(self, state: np.ndarray, delta: np.ndarray,
                       Va: float, alpha: float, beta: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        공력 + 추력에 의한 힘과 모멘트 계산.

        Parameters
        ----------
        state : [u, v, w, p, q, r, phi, theta, psi, pn, pe, pd] (12차)
        delta : [de, da, dr, dt] (엘리베이터, 에일러론, 러더, 스로틀)
        Va    : 대기속도 (m/s)
        alpha : 받음각 (rad)
        beta  : 미끄럼각 (rad)

        Returns
        -------
        force : [fx, fy, fz] (body 좌표계)
        moment : [l, m, n] (body 좌표계)
        """
        p = self.p
        u, v, w = state[0], state[1], state[2]
        pp, q, r = state[3], state[4], state[5]
        phi, theta, psi = state[6], state[7], state[8]
        de, da, dr, dt = delta[0], delta[1], delta[2], delta[3]

        qbar = 0.5 * p.rho * Va**2  # 동압

        # --- 양력/항력 계수 ---
        CL = p.CL0 + p.CLalpha * alpha
        CD = p.CD0 + p.CDalpha * alpha

        if Va > 1e-6:
            CL += p.CLq * (p.c / (2.0 * Va)) * q
            CD += p.CDq * (p.c / (2.0 * Va)) * q

        CL += p.CLde * de
        CD += p.CDde * de

        # 양력/항력 -> body force
        ca = np.cos(alpha)
        sa = np.sin(alpha)
        F_lift = qbar * p.S_wing * CL
        F_drag = qbar * p.S_wing * CD

        fx_aero = -F_drag * ca + F_lift * sa
        fz_aero = -F_drag * sa - F_lift * ca

        # --- 횡방향 힘 ---
        CY = p.CY0 + p.CYbeta * beta
        if Va > 1e-6:
            CY += p.CYp * (p.b / (2.0 * Va)) * pp + p.CYr * (p.b / (2.0 * Va)) * r
        CY += p.CYda * da + p.CYdr * dr
        fy_aero = qbar * p.S_wing * CY

        # --- 추력 ---
        fx_prop = 0.5 * p.rho * p.S_prop * p.C_prop * (
            (p.k_motor * dt)**2 - Va**2
        )

        # --- 중력 ---
        fx_grav = -p.mass * p.g * np.sin(theta)
        fy_grav = p.mass * p.g * np.cos(theta) * np.sin(phi)
        fz_grav = p.mass * p.g * np.cos(theta) * np.cos(phi)

        force = np.array([
            fx_aero + fx_prop + fx_grav,
            fy_aero + fy_grav,
            fz_aero + fz_grav,
        ])

        # --- 모멘트 ---
        Cl = p.Cl0 + p.Clbeta * beta
        Cm = p.Cm0 + p.Cmalpha * alpha
        Cn = p.Cn0 + p.Cnbeta * beta

        if Va > 1e-6:
            Cl += p.Clp * (p.b / (2.0 * Va)) * pp + p.Clr * (p.b / (2.0 * Va)) * r
            Cm += p.Cmq * (p.c / (2.0 * Va)) * q
            Cn += p.Cnp * (p.b / (2.0 * Va)) * pp + p.Cnr * (p.b / (2.0 * Va)) * r

        Cl += p.Clda * da + p.Cldr * dr
        Cm += p.Cmde * de
        Cn += p.Cnda * da + p.Cndr * dr

        moment = np.array([
            qbar * p.S_wing * p.b * Cl,
            qbar * p.S_wing * p.c * Cm,
            qbar * p.S_wing * p.b * Cn,
        ])

        return force, moment

    def derivatives(self, state: np.ndarray, delta: np.ndarray) -> np.ndarray:
        """
        6-DOF 상태 미분: dx/dt = f(x, u).

        state = [u, v, w, p, q, r, phi, theta, psi, pn, pe, pd]
        delta = [de, da, dr, dt]
        """
        p = self.p
        u, v, w = state[0], state[1], state[2]
        pp, q, r = state[3], state[4], state[5]
        phi, theta, psi = state[6], state[7], state[8]

        # 대기속도, 받음각, 미끄럼각
        Va = np.sqrt(u**2 + v**2 + w**2)
        Va = max(Va, 1e-6)
        alpha = np.arctan2(w, max(u, 1e-6))
        beta = np.arcsin(np.clip(v / Va, -1.0, 1.0))

        force, moment = self.forces_moments(state, delta, Va, alpha, beta)
        fx, fy, fz = force
        ell, m, n = moment

        # --- 병진 운동 방정식 ---
        u_dot = r * v - q * w + fx / p.mass
        v_dot = pp * w - r * u + fy / p.mass
        w_dot = q * u - pp * v + fz / p.mass

        # --- 회전 운동 방정식 ---
        p_dot = p.Gamma1 * pp * q - p.Gamma2 * q * r + p.Gamma3 * ell + p.Gamma4 * n
        q_dot = p.Gamma5 * pp * r - p.Gamma6 * (pp**2 - r**2) + m / p.Jy
        r_dot = p.Gamma7 * pp * q - p.Gamma1 * q * r + p.Gamma4 * ell + p.Gamma8 * n

        # --- 운동학 (오일러각) ---
        phi_dot = pp + np.tan(theta) * (q * np.sin(phi) + r * np.cos(phi))
        theta_dot = q * np.cos(phi) - r * np.sin(phi)
        psi_dot = (q * np.sin(phi) + r * np.cos(phi)) / max(np.cos(theta), 1e-6)

        # --- 위치 (NED) ---
        ct = np.cos(theta); st = np.sin(theta)
        cp = np.cos(phi);   sp = np.sin(phi)
        cs = np.cos(psi);   ss = np.sin(psi)

        pn_dot = (ct*cs)*u + (sp*st*cs - cp*ss)*v + (cp*st*cs + sp*ss)*w
        pe_dot = (ct*ss)*u + (sp*st*ss + cp*cs)*v + (cp*st*ss - sp*cs)*w
        pd_dot = (-st)*u + (sp*ct)*v + (cp*ct)*w

        return np.array([
            u_dot, v_dot, w_dot,
            p_dot, q_dot, r_dot,
            phi_dot, theta_dot, psi_dot,
            pn_dot, pe_dot, pd_dot
        ])


# ============================================================================
# 3. 트림 계산 (수평 직선 비행)
# ============================================================================

def compute_trim(model: AerosondeModel, Va: float = 35.0,
                 gamma: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    수평 직선 비행 트림 상태 및 제어 입력 계산.

    Parameters
    ----------
    model : AerosondeModel 인스턴스
    Va    : 목표 대기속도 (m/s)
    gamma : 비행 경로각 (rad), 0 = 수평

    Returns
    -------
    x_trim : (12,) 트림 상태 벡터
    u_trim : (4,) 트림 제어 입력 [de, da, dr, dt]
    """
    p = model.p

    def trim_residual(opt_vars):
        alpha, de, dt = opt_vars

        # 트림 상태 구성
        u0 = Va * np.cos(alpha)
        w0 = Va * np.sin(alpha)
        theta0 = alpha + gamma

        x_trim = np.array([u0, 0, w0, 0, 0, 0, 0, theta0, 0, 0, 0, 0])
        u_trim = np.array([de, 0, 0, dt])

        xdot = model.derivatives(x_trim, u_trim)

        # 잔차: u_dot, w_dot, q_dot 이 0이어야 함
        return [xdot[0], xdot[2], xdot[4]]

    # 초기 추정
    alpha0 = 0.05
    de0 = -0.05
    dt0 = 0.5

    sol = fsolve(trim_residual, [alpha0, de0, dt0], full_output=True)
    alpha_t, de_t, dt_t = sol[0]

    u0 = Va * np.cos(alpha_t)
    w0 = Va * np.sin(alpha_t)
    theta0 = alpha_t + gamma

    x_trim = np.array([u0, 0.0, w0, 0.0, 0.0, 0.0, 0.0, theta0, 0.0, 0.0, 0.0, 0.0])
    u_trim = np.array([de_t, 0.0, 0.0, np.clip(dt_t, 0.0, 1.0)])

    return x_trim, u_trim


# ============================================================================
# 4. SDC 파라미터화 (수치 야코비안)
# ============================================================================

def numerical_jacobian(func, x, u, dx=1e-6):
    """
    수치 야코비안 계산: df/dx, df/du.

    Parameters
    ----------
    func : x, u -> xdot
    x : (n,) 상태
    u : (m,) 입력
    dx : 섭동 크기

    Returns
    -------
    A : (n, n) df/dx
    B : (n, m) df/du
    """
    n = len(x)
    m = len(u)
    f0 = func(x, u)

    A = np.zeros((n, n))
    for i in range(n):
        x_plus = x.copy()
        x_plus[i] += dx
        A[:, i] = (func(x_plus, u) - f0) / dx

    B = np.zeros((n, m))
    for j in range(m):
        u_plus = u.copy()
        u_plus[j] += dx
        B[:, j] = (func(x, u_plus) - f0) / dx

    return A, B


def sdc_parameterization(model: AerosondeModel, x: np.ndarray, u: np.ndarray,
                         x_trim: np.ndarray, u_trim: np.ndarray
                         ) -> Tuple[np.ndarray, np.ndarray]:
    """
    SDC 파라미터화: 현재 상태 x에서 A(x), B(x) 계산.

    양창덕(2008) 논문의 수치적 방법 사용:
    트림 상태 근방에서 수치 야코비안으로 A, B 추정.

    Returns
    -------
    A : (n, n) 상태 의존 시스템 행렬
    B : (n, m) 상태 의존 입력 행렬
    """
    A, B = numerical_jacobian(
        lambda xx, uu: model.derivatives(xx, uu),
        x, u
    )
    return A, B


# ============================================================================
# 5. 종방향 모델 (4차 축소)
# ============================================================================

def longitudinal_model(model: AerosondeModel, x_full: np.ndarray,
                       u_full: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    종방향 4차 모델 추출.

    상태: x_lon = [u, w, q, theta]
    입력: u_lon = [de, dt]

    Returns
    -------
    A_lon : (4, 4)
    B_lon : (4, 2)
    """
    A_full, B_full = numerical_jacobian(
        lambda xx, uu: model.derivatives(xx, uu),
        x_full, u_full
    )

    # 종방향 인덱스: u(0), w(2), q(4), theta(7)
    lon_idx = [0, 2, 4, 7]
    # 종방향 입력: de(0), dt(3)
    lon_u_idx = [0, 3]

    A_lon = A_full[np.ix_(lon_idx, lon_idx)]
    B_lon = B_full[np.ix_(lon_idx, lon_u_idx)]

    return A_lon, B_lon


def lateral_model(model: AerosondeModel, x_full: np.ndarray,
                  u_full: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    횡방향 4차 모델 추출.

    상태: x_lat = [v, p, r, phi]
    입력: u_lat = [da, dr]

    Returns
    -------
    A_lat : (4, 4)
    B_lat : (4, 2)
    """
    A_full, B_full = numerical_jacobian(
        lambda xx, uu: model.derivatives(xx, uu),
        x_full, u_full
    )

    # 횡방향 인덱스: v(1), p(3), r(5), phi(6)
    lat_idx = [1, 3, 5, 6]
    # 횡방향 입력: da(1), dr(2)
    lat_u_idx = [1, 2]

    A_lat = A_full[np.ix_(lat_idx, lat_idx)]
    B_lat = B_full[np.ix_(lat_idx, lat_u_idx)]

    return A_lat, B_lat


# ============================================================================
# 메인: 트림 계산 + SDC 파라미터 확인
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Aerosonde UAV 모델 테스트")
    print("=" * 60)

    model = AerosondeModel()

    # --- 트림 계산 ---
    print("\n[1] 트림 계산 (Va=35 m/s, 수평비행)")
    x_trim, u_trim = compute_trim(model, Va=35.0)

    print(f"  트림 상태:")
    labels = ['u', 'v', 'w', 'p', 'q', 'r', 'phi', 'theta', 'psi', 'pn', 'pe', 'pd']
    for i, (label, val) in enumerate(zip(labels, x_trim)):
        unit = "rad" if i >= 6 and i <= 8 else "m/s" if i <= 2 else "rad/s" if i <= 5 else "m"
        print(f"    {label:>5} = {val:10.6f} {unit}")

    print(f"\n  트림 제어:")
    u_labels = ['de', 'da', 'dr', 'dt']
    for label, val in zip(u_labels, u_trim):
        print(f"    {label:>3} = {val:10.6f}")

    # --- 트림 검증 ---
    xdot_trim = model.derivatives(x_trim, u_trim)
    print(f"\n  트림 잔차 (||xdot||): {np.linalg.norm(xdot_trim[:6]):.2e}")

    # --- 수치 야코비안 (전체 12x12) ---
    print("\n[2] 전체 6-DOF 야코비안 (12x12)")
    A_full, B_full = numerical_jacobian(
        lambda x, u: model.derivatives(x, u), x_trim, u_trim)

    eigvals = np.linalg.eigvals(A_full)
    print(f"  A 행렬 고유값 (실수부):")
    for i, ev in enumerate(sorted(eigvals, key=lambda x: x.real)):
        print(f"    {i+1:2d}: {ev.real:+10.4f} {ev.imag:+10.4f}j")

    # --- 종방향 모델 ---
    print("\n[3] 종방향 모델 (4x4)")
    A_lon, B_lon = longitudinal_model(model, x_trim, u_trim)
    print(f"  A_lon:\n{np.array2string(A_lon, precision=4, suppress_small=True)}")
    print(f"  B_lon:\n{np.array2string(B_lon, precision=4, suppress_small=True)}")
    eigvals_lon = np.linalg.eigvals(A_lon)
    print(f"  고유값: {[f'{e.real:.4f}{e.imag:+.4f}j' for e in eigvals_lon]}")

    # --- 횡방향 모델 ---
    print("\n[4] 횡방향 모델 (4x4)")
    A_lat, B_lat = lateral_model(model, x_trim, u_trim)
    print(f"  A_lat:\n{np.array2string(A_lat, precision=4, suppress_small=True)}")
    print(f"  B_lat:\n{np.array2string(B_lat, precision=4, suppress_small=True)}")
    eigvals_lat = np.linalg.eigvals(A_lat)
    print(f"  고유값: {[f'{e.real:.4f}{e.imag:+.4f}j' for e in eigvals_lat]}")

    # --- SDRE용 SDC 함수 테스트 ---
    print("\n[5] SDC 파라미터화 테스트 (트림 상태에서)")
    A_sdc, B_sdc = sdc_parameterization(model, x_trim, u_trim, x_trim, u_trim)
    print(f"  A_sdc shape: {A_sdc.shape}")
    print(f"  B_sdc shape: {B_sdc.shape}")
    print(f"  A_sdc == A_full 차이: {np.linalg.norm(A_sdc - A_full):.2e}")
