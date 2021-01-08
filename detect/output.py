import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    warnings.simplefilter("ignore", category=RuntimeWarning)

    import json

    import numpy as np

#####################################################################################################


def jsonpoint(file, radar, r, outdir):

    for det in r:
        lat, lon, alt, t = det
        trounded = str(t)[:-4]
        name, m, d, y, hh, mm, ss, date = stringed(file)

        print('Detection: ' + str(float(lat)) + ' degrees North,' + ' ' + str(float(lon)) +
              ' degrees West,' + ' ' + str(alt) + ' m above sea level, at ' + trounded)
        data = {}
        data[date] = []
        data[date].append({
            'Time:': trounded,
            'Altitude (m)': str(alt),
            'Longitude (deg East)': str(lon),
            'Latitude (deg North)': str(lat)
        })
        fname = outdir + name + ".json"
        with open(fname, 'a+') as outfile:
            json.dump(data, outfile)


def jsonsquare(file, radar, allr, outdir):

    for det in allr:
        lat0, lon0, lat1, lon1, alt, t = det
        trounded = str(t)[:-4]
        name, m, d, y, hh, mm, ss, date = stringed(file)

        print('Detection centered at: ' + str(round(float(lat0 + lat1) / 2,4)) + ' degrees North,' + ' ' +
              str(round(float(lon0 + lon1) / 2,4)) + ' degrees West,' + ' ' + str(alt) + ' m above sea level, at ' + trounded)
        data = {}
        data[date] = []
        data[date].append({
            'Time:': trounded,
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
