import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    warnings.simplefilter("ignore", category=RuntimeWarning)

    import os

    import numpy as np

    import math

    import pymap3d as pm

    import matplotlib.pyplot as plt
    from mpl_toolkits import mplot3d

    import time
    import datetime
    from datetime import datetime, timedelta, date, time

    import scipy
    from scipy.integrate import odeint

####################################################################

def org(vec):
    rlsp = []
    tmp = []
    index = vec[0][4]

    for dat in vec:
        lat, lon, alt, t, n = dat
        x, y, z = lla2eci(lat, lon, alt, t)
        if(n <= index):
            tmp.append([round(float(x),2), round(float(y),2), round(float(z),2), t])
        elif(n > index):
            index = n
            rlsp.append(tmp)
            tmp = [[round(float(x),2), round(float(y),2), round(float(z),2), t]]

    rlsp.append(tmp)
    rlsp.reverse()
    return rlsp

def lla2eci(lat, lon, alt, t):
    x, y, z = pm.geodetic2eci(lat, lon, alt, t)
    return x, y, z



def kin(rlsp):
    single, rv = [], []
    for sweep in rlsp:
        single.append(sweep[0])

    for i in range(len(single)-1):
        x0, y0, z0 = single[i][0:3]
        x1, y1, z1 = single[i+1][0:3]
        dt = (single[i][3]-single[i+1][3]).total_seconds()
        u, v, w = (x1-x0)/dt, (y1-y0)/dt, (z1-z0)/dt,
        x, y, z = (x0+x1)/2, (y0+y1)/2, (z0+z1)/2
        rv.append([x, y, z, u, v, w])
    return rv


def backprop(rv,t):
    R = 6.371 * 10**6
    backtrak = []
    for vec in rv:
        m0 = vec
        t = np.linspace(0,t)
        out = odeint(dmdt,m0,t)
        backtrak.append([out])
        

def dmdt(m,t):
    x, y, z, u, v, w = m
    mu = 3.986004418 * 10**14
    norm = np.sqrt(x**2 + y**2 + z**2)
    a, b, c = -(x*mu)/(norm**3), -(y*mu)/(norm**3), -(z*mu)/(norm**3)
    mdot = [u, v, w, a, b, c]
    return mdot

#######################################################################
