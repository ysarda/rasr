"""
OUTPUT ver 1.0
as of Jan 09, 2021

Converts any relevant data into useful/displayable file types for ASTRIAGraph

@author: Yash Sarda
"""

import geojson
from geojson import Point, Feature, FeatureCollection, dump

import numpy as np

#####################################################################################################


def pointOut(file, r, outdir):
    for det in r:
        lat, lon, alt, t, sweep = det
        trounded = str(t)[:-4]
        name, dtstr = stringConvert(file)

        print('Detection: ' + str(float(lat)) + ' degrees North,' + ' ' + str(float(lon)) +
              ' degrees West,' + ' ' + str(alt) + ' m above sea level, at ' + trounded)

        point = Point((int(-lon), int(lat), int(alt)))
        features = []
        features.append(Feature(geometry=point))
        feature_collection = FeatureCollection(features)

        fname = outdir + name + dtstr + '-' + str(sweep) + ".geojson"
        with open(fname, 'a+') as outfile:
            dump(feature_collection, outfile)

def squareOut(file, allr, outdir):
    for det in allr:
        lat0, lon0, lat1, lon1, alt, t = det
        trounded = str(t)[:-4]
        name, dtstr = stringConvert(file)

        print('Detection centered at: ' + str(round(float(lat0 + lat1) / 2,4)) + ' degrees North,' + ' ' +
              str(round(float(lon0 + lon1) / 2,4)) + ' degrees West,' + ' ' + str(alt) + ' m above sea level, at ' + trounded)
        data = {}
        data[trounded] = []
        data[trounded].append({
            'Altitude (m)': str(alt),
            'Longitude0 (NW)(deg East)': str(lon0),
            'Latitude0 (NW)(deg North)': str(lat0),
            'Longitude1 (SE)(deg East)': str(lon1),
            'Latitude1 (SE)(deg North)': str(lat1)
        })
        fname = outdir + name + dtstr + ".json"
        with open(fname, 'a+') as outfile:
            geojson.dump(data, outfile)

def stringConvert(file):
    radarname = file[0:4]
    m, d, y, hh, mm, ss = file[8:10], file[10:12], file[4:8], file[13:15], file[15:17], file[17:19]
    date = m + '/' + d + '/' + y
    btime = m +'/' + d + '/' + y + ' ' + hh + ':' + mm + ':' + ss
    dtstr = m + d + y + '-' + hh + mm + ss
    return radarname, date, btime, dtstr

def txtOut(prop, file, outdir):
    name, date, btime, dtstr = stringConvert(file)
    fname = fname = outdir + name + dtstr + ".csv"
    np.savetxt(fname,prop,delimiter=',')
