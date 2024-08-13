from __future__ import annotations

import numpy as np
import numpy.typing as npt
from scipy.optimize import curve_fit


def fit_gaussian(curve: npt.NDArray) -> float:
    """
    Fits a Gaussian curve to the given data points.

    Args:
    curve: 1D array of float, representing the curve to be fitted.

    Returns:
    A float representing the mean of the fitted Gaussian curve.
    If the curve cannot be fitted, returns 0.
    """
    # Compute the maximum and standard deviation of the curve
    curve_max = np.max(curve)
    curve_std = np.nanstd(curve)

    # Check if the standard deviation is NaN or the curve max/std is zero
    if np.isnan(curve_std) or curve_max == 0 or curve_std == 0:
        return 0

    # Define the Gaussian function with amplitude, mean, and standard deviation
    def gaussian(x: npt.NDArray, amplitude: float, mean: float, stddev: float) -> npt.NDArray:
        return amplitude * np.exp(-((x - mean) ** 2) / (2 * stddev**2))

    # Generate x data points
    x_data = np.arange(curve.size)

    # Initial guess for curve fitting: amplitude, mean, stddev
    initial_guess = (curve_max, np.mean(x_data), curve_std)

    try:
        popt, _ = curve_fit(gaussian, x_data, curve, p0=initial_guess, maxfev=800)
    except RuntimeError:
        # If the curve fitting fails, return 0
        return 0
    else:
        # Return the mean of the fitted Gaussian curve
        return float(popt[1])
