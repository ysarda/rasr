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

    import sys

    import numpy as np

    import json

    from multiprocessing import Pool, cpu_count, Lock, get_context
    from multiprocessing.pool import ThreadPool

    from functools import partial

    import gc

    import time
##############################################################################################################################


def readpyart(file):
    file = file[len(fdir):]
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
            sweepangle = format(float(radar.fixed_angle['data'][x]), ".2f")
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
    if(len(r) >= 2):
        kinematics(r)
        jsonsquare(file, radar, allr)
        #jsonpoint(file, r)


def detect(radar, img, file, locDat, sweep):
    pred = model.predict(img)
    for n in range(len(pred[1])):
        if(pred[2][n] > cint):
            x0p, y0p, x1p, y1p = float(pred[1][n][0]), float(pred[1][n][1]), float(pred[1][n][2]), float(pred[1][n][3])
            w,h = (x0p-x1p),(y0p-y1p)
            ipix, jpix = round(x0p + w / 2, 2), round(y0p + h / 2, 2)
            norm = locDat[0].shape
            x, y = 1000 * locDat[0][int(norm[0] * ipix / 2500)][0], 1000 * locDat[1][0][int(norm[1] * jpix / 2500)]
            x0, y0 = 1000 * locDat[0][int(norm[0] * x0p / 2500)][0], 1000 * locDat[1][0][int(norm[1] * y0p / 2500)]
            x1, y1 = 1000 * locDat[0][int(norm[0] * x1p / 2500)][0], 1000 * locDat[1][0][int(norm[1] * y1p / 2500)]
            z = np.sqrt(x**2 + y**2) * np.tan(np.radians(sweep))
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


def getListOfFiles(dirName):
    listOfFile = os.listdir(dirName)
    allFiles = list()
    for entry in listOfFile:
        fullPath = os.path.join(dirName, entry)
        if os.path.isdir(fullPath):
            allFiles = allFiles + getListOfFiles(fullPath)
        else:
            allFiles.append(fullPath)
    # Reducing process size, will require mutliple iteration
    if len(allFiles) > 160:
        all_files = allFiles[:160]
    else:
        all_files = allFiles
    return all_files


def init(l):
    global lock
    lock = l


###############################################################################################################################
cint = 0.85
fdir = 'data/'
outdir = 'falls/json/'
model = Model.load('RASRmodl.pth', ['fall'])


if __name__ == '__main__':
    # optional spec for num pool workers, else num cpu
    if len(sys.argv) > 1:
        runnum = sys.argv[1]
    else:
        runnum = cpu_count() / 4
    try:
        all_files = getListOfFiles(fdir)
    except:
        all_files = []
        print('ERROR: path not found')
    top = len(all_files)
    if top != 0:
        l = Lock()
        n = int(runnum)
        for i in range(0, top, n):
            print('Batch ' + str(int(i / n)) + ' of ' + str(int(top / n)) + ', initializing pool...')
            with get_context("spawn").Pool(processes=int(runnum), initializer=init, initargs=(l,)) as pool:
                print('   mapping...')
                for x in pool.imap(readpyart, all_files[i:i + n]):
                    # print(x)
                    gc.collect()  # clear each step
                #results = pool.map(getDataPart, all_files[i:i+n])
                time.sleep(1)  # should permit maxtasksperchild=1
                print('   closing batch...')
                pool.close()  # close chunk
                print('joining batch...')
                pool.join()  # join chunk to clean
            # pool.terminate() #terminate chunk
            print('   batch closed')
            gc.collect()  # clear at end
    else:
        print('ERROR: path not found')

#print ("Program took", time.time() - start_time, "to run")
