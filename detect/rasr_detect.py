import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    warnings.simplefilter("ignore", category=RuntimeWarning)

    import matplotlib
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvas
    from matplotlib import pyplot as plt
    from matplotlib import patches
    matplotlib.use("TKagg")

    import pyart

    import os

    import time

    import sys

    import numpy as np

    from multiprocessing import Pool, cpu_count, Lock, get_context
    from multiprocessing.pool import ThreadPool

    from functools import partial

    import gc

    from kinematics import org
    from jsonoutput import jsonsquare, jsonpoint, stringed
    from torchdet import detect
##############################################################################################################################


def readpyart(file, outdir):
    file = file[len(fdir):]
    radar = pyart.io.read(fdir + file)
    name, m, d, y, hh, mm, ss, date = stringed(file)
    print('Checking ' + name + ' at ' + date)
    r, dr, allr = [], [], []
    detdir = []
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
            #print('Reading Velocity at sweep angle: ', sweepangle)
            t = radar.time['data'][x]
            locDat = [xDat, yDat, t]
            vis = False
            v = detect(radar, img, file, locDat, sweepangle, detdir, vis)
            if v is not None:
                vc, vall = v
                vc.append(x)
                r.append(vc)
                allr.append(vall)
            plt.cla()
            plt.clf()
            plt.close('all')
    if(len(r) >= 2):
        stsp = org(r)
        jsonsquare(file, radar, allr, outdir)
        #jsonpoint(file, radar, r, outdir)

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
fdir = 'data/'
outdir = 'falls/json/'


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
        partreadpyart = partial(readpyart, outdir=outdir)
        for i in range(0, top, n):
            print('Batch ' + str(int(i / n)) + ' of ' + str(int(top / n)) + ', initializing pool...')
            with get_context("spawn").Pool(processes=int(runnum), initializer=init, initargs=(l,)) as pool:
                print('   mapping...')
                for x in pool.imap(partreadpyart, all_files[i:i + n]):
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
