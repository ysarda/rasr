import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    warnings.simplefilter("ignore", category=RuntimeWarning)

    from detecto.core import Model, Dataset, DataLoader
    from detecto.visualize import plot_prediction_grid
    from detecto.utils import read_image

    import matplotlib
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvas
    from matplotlib import pyplot as plt
    from matplotlib import patches
    matplotlib.use("TKagg")

    import pyart

    import os

    import numpy as np

    import json

    import time
    import datetime
    from datetime import datetime, timedelta, date
########################################################


def readpyart(file):
    #file = file[len(fdir):]
    radar = pyart.io.read(fdir + file)
    name, m, d, y, hh, mm, ss, date = stringed(file)
    print('Checking ' + name + ' at ' + date)
    r, dr, allr = [], [], []
    for x in range(radar.nsweeps):
        plotter = pyart.graph.RadarDisplay(radar)
        fig = plt.figure(figsize=(25, 25), frameon=False)
        ax = plt.Axes(fig, [0., 0., 1., 1.])
        fig.add_axes(ax)
        plotter.set_limits(xlim=(-250, 250), ylim=(-250, 250), ax=ax)
        data = plotter._get_data('velocity', x, mask_tuple=None, filter_transitions=True, gatefilter=None)
        if np.any(data) > 0:
            xDat, yDat = plotter._get_x_y(x, edges=True, filter_transitions=True)
            data = data * (70 / np.max(np.abs(data)))
            ax.pcolormesh(xDat, yDat, data)
            canvas = FigureCanvas(fig)
            fig.canvas.draw()
            img = np.array(canvas.renderer.buffer_rgba())
            img = np.delete(img, 3, 2)
            sweepangle = str(format(radar.fixed_angle['data'][x], ".2f"))
            print('Reading Velocity at sweep angle: ', sweepangle)
            t = radar.time['data'][x]
            locDat = [xDat, yDat, t]
            v = detect(radar, img, file, locDat, sweepangle)
            if v is not None:
                vc, vall = v
                vc.append(x)
                r.append(vc)
                allr.append(vall)
            plt.cla()
            plt.clf()
            plt.close('all')
    kinematics(r)
    if(len(r) >= 2):
        jsonsquare(file, radar, allr)
        #jsonpoint(file, r)


def detect(radar, img, file, locDat, sweep):
    pred = model.predict(img)
    fig = plt.figure(figsize=(25, 25))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis('off')
    for n in range(len(pred[1])):
        if(pred[2][n] > cint):
            ax.imshow(img)
            x0p, y0p, x1p, y1p = float(pred[1][n][0]), float(pred[1][n][1]), float(pred[1][n][2]), float(pred[1][n][3])
            w, h = abs(x0p - x1p), abs(y0p - y1p)
            rect = patches.Rectangle((x0p, y0p), w, h, linewidth=1, edgecolor='r', facecolor='none')
            ax.add_patch(rect)
            detstr = pred[0][n] + ': ' + str(round(float(pred[2][n]), 2))
            plt.text(x0p + w / 2, y0p - 5, detstr, fontsize=8, color='red', ha='center')
            imname = detdir + file + '_' + sweep + '_detected' + '.png'
            plt.savefig(imname, bbox_inches='tight')
            ipix, jpix = round(x0p + w / 2, 2), round(y0p + h / 2, 2)
            norm = locDat[0].shape
            x, y = 1000 * locDat[0][int(norm[0] * ipix / 2500)][0], 1000 * locDat[1][0][int(norm[1] * jpix / 2500)]
            x0, y0 = 1000 * locDat[0][int(norm[0] * x0p / 2500)][0], 1000 * locDat[1][0][int(norm[1] * y0p / 2500)]
            x1, y1 = 1000 * locDat[0][int(norm[0] * x1p / 2500)][0], 1000 * locDat[1][0][int(norm[1] * y1p / 2500)]
            z = np.sqrt(x**2 + y**2) * np.tan(np.radians(float(sweep)))
            t = round(locDat[2], 2)
            return [x, y, z, t], [x0, y0, x1, y1, z, t]
        else:
            pass


def kinematics(vec):
    rlsp = []
    tmp = []
    index = vec[0][4]
    for dat in vec:
        x, y, z, t, n = dat
        if(n == index):
            tmp.append([x, y, z, t])
        elif(n > index):
            index = n
            rlsp.append(tmp)
            tmp = [[x, y, z, t]]
    rlsp.append(tmp)


def jsonpoint(file, r):
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


def jsonsquare(file, radar, allr):
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


##########################################################
cint = 0.8
fdir = 'test/raw/'
detdir = 'test/detections/'
outdir = 'test/out/'
model = Model.load('RASRmodl.pth', ['fall'])

for file in os.listdir(outdir):
    os.remove(outdir + file)
for file in os.listdir(fdir):
    readpyart(file)
