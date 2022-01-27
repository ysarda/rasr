"""
MOTION ver 2.0
as of Jan 27, 2022

Module for kinematic analysis and back-propagation of detected falls

@author: Yash Sarda
"""


import numpy as np
import pymap3d as pm
import matplotlib.pyplot as plt
from scipy.integrate import odeint
from typing import Any, List, Tuple


def organize_data(vec: List[Tuple[float]]) -> List[List[Tuple[float]]]:
    """Organizes the detection data into a real space (rlsp) order"""

    rl_sp = []
    tmp = []
    index = vec[0][4]

    for dat in vec:
        lat, lon, alt, t, n = dat
        x, y, z = lla_to_eci(lat, lon, alt, t)
        # Conversion from Geodetic to ECI frame
        if n <= index:
            tmp.append([round(float(x), 2), round(float(y), 2), round(float(z), 2), t])
        elif n > index:
            index = n
            rl_sp.append(tmp)
            tmp = [[round(float(x), 2), round(float(y), 2), round(float(z), 2), t]]

    rl_sp.append(tmp)
    rl_sp.reverse()
    return rl_sp


def lla_to_eci(lat: float, lon: float, alt: float, t: float) -> Tuple[float]:
    """Converts from Lat/Lon/Alt to ECI Coordinate Frame"""

    x, y, z = pm.geodetic2eci(lat, lon, alt, t)
    return x, y, z


def state_vector(rl_sp: List[List[List[float]]]) -> List[float]:
    """Creates a state vector from two detections"""

    single = []
    file_name = "fallvel.txt"
    for sweep in rl_sp:
        single.append(sweep[0])
    x0, y0, z0 = single[0][0:3]
    x1, y1, z1 = single[1][0:3]
    dt = (single[1][3] - single[0][3]).total_seconds()
    u, v, w = (x1 - x0) / dt, (y1 - y0) / dt, (z1 - z0) / dt
    rv = [x0, y0, z0, u, v, w]
    drdt = np.sqrt(u ** 2 + v ** 2 + w ** 2)
    with open(file_name, "a") as file:
        file.write(str(drdt))
        file.write("\n")

    return rv


def back_prop(rv: List[float], t: float) -> Any:
    """Solves a differential model to back-propagate the detected fall"""

    m0 = rv
    time = np.linspace(-t, 0, 1000)
    prop = odeint(dmdt, m0, time)
    print("Kinematic propagation complete: " + str(t) + " seconds backwards")
    return prop


def dmdt(m: List[float], t: float) -> Tuple[float]:
    """Differential model for reentry dynamics"""

    x, y, z, u, v, w = m
    r = np.sqrt(x ** 2 + y ** 2 + z ** 2)
    rho, _, _ = atmo(r)
    k = rho * 5
    mu = 3.986004418 * 10 ** 14
    a, b, c = (
        -(x * mu) / (r ** 3) + k * u ** 2,
        -(y * mu) / (r ** 3) + k * v ** 2,
        -(z * mu) / (r ** 3) + k * w ** 2,
    )
    return u, v, w, a, b, c


def prop_vis(prop: Any, vis_dir: str, name: str, dt_str: str) -> None:
    """Visualize the back-propagation"""

    radius = 6.371 * 10 ** 6
    x_prop, y_prop, z_prop = prop[:, 0], prop[:, 1], prop[:, 2]
    ax = plt.axes(projection="3d")
    ax.scatter3D(x_prop, y_prop, z_prop)

    u, v = np.mgrid[0 : 2 * np.pi : 20j, 0 : np.pi : 10j]
    x = radius * np.cos(u) * np.sin(v)
    y = radius * np.sin(u) * np.sin(v)
    z = radius * np.cos(v)
    ax.plot_wireframe(x, y, z, color="r")
    lim = 10 * 10 ** 6
    ax.set_xlim3d(-lim, lim)
    ax.set_ylim3d(-lim, lim)
    ax.set_zlim3d(-lim, lim)

    file_name = vis_dir + name + dt_str + "propagation.png"
    plt.savefig(file_name)


def atmo(h: float) -> Tuple[float]:
    """Atmospheric density model"""

    if h > 25000:
        temp = -131.21 + 0.00299 * h + 273.15
        p = 2.488 * (temp / 216.6) ** (-11.388)
    elif 11000 <= h <= 25000:
        temp = -56.46 + 273.15
        p = 22.65 * np.exp(1.73 - 0.000157 * h)
    elif h < 11000:
        temp = 15.04 - 0.00649 * h + 273.15
        p = 101.29 * (temp / 288.08) ** (5.256)

    rho = p / (0.2869 * temp)

    return rho, temp, p
