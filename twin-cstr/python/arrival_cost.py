"""Shared EKF-style recursion for the jacketed-CSTR digital twin.

The recursion below (predict + linear update) is the exact computation
used by TwinEKF and by the moving-horizon estimator's arrival-cost filter.
It lives in one module so the two estimators cannot drift apart.

Nomenclature -- every symbol defined at first use; SI units throughout.
x       state mean vector, mixed units [mol/L, K, K, J/(s K)]
Pm      prior state covariance matrix, mixed^2
xp      predicted state mean vector, mixed units
Pp      predicted state covariance matrix, mixed^2
Phi     discrete-time state transition Jacobian, dimensionless
Q       process-noise covariance per sampling interval, mixed^2
y       measurement vector, mixed units
H       measurement Jacobian matrix, dimensionless
R       measurement-noise covariance matrix, mixed^2
r       measurement residual (innovation) vector, mixed units
S       residual covariance matrix, mixed^2
K       Kalman gain matrix, mixed
dt      sampling interval, s
"""

import numpy as np


def ekf_predict(x, Pm, transition, dt, Q):
    """One extended Kalman filter predict step.

    x is the prior state mean vector; Pm is the prior state covariance
    matrix. transition is a callable mapping (x, dt) to (xp, Phi), where
    xp is the propagated mean and Phi is the discrete-time transition
    Jacobian evaluated at the prediction. dt is the sampling interval in
    seconds; Q is the process-noise covariance per interval. Returns the
    predicted mean xp and predicted covariance Pp.
    """
    xp, Phi = transition(x, dt)
    Pp = Phi @ Pm @ Phi.T + Q
    return xp, Pp


def ekf_update(xp, Pp, y, H, R):
    """One linear(ized) Kalman update step.

    xp is the predicted state mean vector; Pp is the predicted covariance
    matrix. y is the measurement vector; H is the measurement Jacobian
    matrix; R is the measurement-noise covariance matrix. Returns the
    updated mean, the updated covariance, and the residual r = y - H xp.
    """
    r = y - H @ xp
    S = H @ Pp @ H.T + R
    K = Pp @ H.T @ np.linalg.inv(S)
    n = Pp.shape[0]
    return xp + K @ r, (np.eye(n) - K @ H) @ Pp, r
