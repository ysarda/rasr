

import time
import datetime
from datetime import datetime, timedelta, date

import json

import numpy as np

import pyart

#####################################################################################################

def jsonpoint(file, radar, r, outdir):

    for det in r:
        x, y, z, t = det
        name, m, d, y, hh, mm, ss, date = stringed(file)
        btime = hh + ':' + mm + ':' + ss
        atime = str((datetime.strptime(btime, '%H:%M:%S') + timedelta(seconds=t)).time())[:-4]

        sitealt, sitelon, sitelat = float(radar.altitude['data']), float(
            radar.longitude['data']), float(radar.latitude['data'])
        lon, lat = np.around(pyart.core.cartesian_to_geographic_aeqd(x, y, sitelon, sitelat), 2)
        alt = round(z + sitealt, 1)

        print('Detection: ' + str(float(lon)) + ' degrees East,' + ' ' +
              str(float(lat)) + ' degrees North,' + ' ' + str(alt) + ' m above sea level, at ' + atime)
        data = {}
        data[date] = []
        data[date].append({
            'Time:': atime,
            'Altitude (m)': str(alt),
            'Longitude (deg East)': str(lon),
            'Latitude (deg North)': str(lat)
        })
        fname = outdir + name + ".json"
        with open(fname, 'a+') as outfile:
            json.dump(data, outfile)

def jsonsquare(file, radar, allr, outdir):
    
    for det in allr:
        x0, y0, x1, y1, z, t = det
        name, m, d, y, hh, mm, ss, date = stringed(file)
        btime = hh + ':' + mm + ':' + ss
        atime = str((datetime.strptime(btime, '%H:%M:%S') + timedelta(seconds=t)).time())[:-4]

        sitealt, sitelon, sitelat = float(radar.altitude['data']), float(
            radar.longitude['data']), float(radar.latitude['data'])
        lon0, lat0 = np.around(pyart.core.cartesian_to_geographic_aeqd(x0, y0, sitelon, sitelat), 3)
        lon1, lat1 = np.around(pyart.core.cartesian_to_geographic_aeqd(x1, y1, sitelon, sitelat), 3)
        alt = round(z + sitealt, 1)

        print('Detection centered at: ' + str(float(lon0 + lon1) / 2) + ' degrees East,' + ' ' +
              str(float(lat0 + lat1) / 2) + ' degrees North,' + ' ' + str(alt) + ' m above sea level, at ' + atime)
        data = {}
        data[date] = []
        data[date].append({
            'Time:': atime,
            'Altitude (m)': str(alt),
            'Longitude0 (NW)(deg East)': str(lon0),
            'Latitude0 (NW)(deg North)': str(lat0),
            'Longitude1 (SE)(deg East)': str(lon1),
            'Latitude1 (SE)(deg North)': str(lat1)
        })
        fname = outdir + name + ".json"
        with open(fname, 'a+') as outfile:
            json.dump(data, outfile)

def stringed(file):
    name = file[0:4]
    m, d, y, hh, mm, ss = file[8:10], file[10:12], file[4:8], file[13:15], file[15:17], file[17:19]
    date = m + '/' + d + '/' + y
    return name, m, d, y, hh, mm, ss, date
