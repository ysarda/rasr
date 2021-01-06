import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    warnings.simplefilter("ignore", category=RuntimeWarning)

    import os

    import numpy as np

    import orekit

    import math

    import pyproj

    import matplotlib.pyplot as plt
    from mpl_toolkits import mplot3d
####################################################################

def org(vec):
    rlsp = []
    tmp = []
    index = vec[0][4]

    for dat in vec:
        lat, lon, alt, t, n = dat
        x, y, z = lla2ecef(lat, lon, alt)
        if(n <= index):
            tmp.append([round(float(x),2), round(float(y),2), round(float(z),2), t])
        elif(n > index):
            index = n
            rlsp.append(tmp)
            tmp = [[round(float(x),2), round(float(y),2), round(float(z),2), t]]

    rlsp.append(tmp)
    return rlsp

def lla2ecef(lat, lon, alt):
    ecef = pyproj.Proj(proj='geocent', ellps='WGS84', datum='WGS84')
    lla = pyproj.Proj(proj='latlong', ellps='WGS84', datum='WGS84')
    x, y, z = pyproj.transform(lla, ecef, lon, lat, alt, radians=False)
    return x, y, z



def orbit(rlsp):
    pass
