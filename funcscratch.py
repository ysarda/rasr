import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    warnings.simplefilter("ignore", category=RuntimeWarning)

    import sys
    import imp
    import gc
    import os
    os.environ["PYART_QUIET"] = "1"

    import numpy as np

    import pyart

    import matplotlib
    import matplotlib.pyplot as plt
    matplotlib.use("TKagg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvas


#########################################################################################################################

def pix2coord(i,j,radar,sweep,name,date):
    #NOTE: i and j are pixel coords from image, x and y are meter distance from site, and lat and lon are, well, lat and lon.
    x,y = i,j #Conversion to meters, somehow. Working on it.
    sitealt, sitelon, sitelat = float(radar.altitude['data']), float(radar.longitude['data']), float(radar.latitude['data']) #Site data
    lon, lat = pyart.core.cartesian_to_geographic_aeqd(x,y,sitelon,sitelat) #Conversion function from meter distance to lat/lon
    alt = sqrt(x^2 + y^2)*tan(radians(sweep)) #Lil bit of trig

    data = {}
    data[date] = []
    data[date].append({
        'Altitude': str(alt),
        'Longitude': str(lon),
        'Latitude': str(lat)
        })
    fname = "out/" + name + ".json"
    with open(fname, 'a') as outfile:
        json.dump(data, outfile)





###################################################################################################################################
