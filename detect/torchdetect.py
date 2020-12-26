import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore",category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    warnings.simplefilter("ignore",category=RuntimeWarning)

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
        print(file,fdir)
        radar = pyart.io.read(fdir+file)
        name = file[0:4]
        m,d,y,hh,mm,ss = file[8:10], file[10:12], file[4:8], file[13:15], file[15:17], file[17:19]
        date = m + '/' + d + '/' + y + ' ' + hh + ':' + mm + ':' + ss
        print('Checking ' + name + ' at ' + date)
        for x in range(radar.nsweeps):
            plotter = pyart.graph.RadarDisplay(radar)
            fig = plt.figure(figsize=(25, 25), frameon=False)
            ax = plt.Axes(fig, [0., 0., 1., 1.])
            fig.add_axes(ax)
            plotter.set_limits(xlim=(-250, 250), ylim=(-250, 250), ax=ax)
            data = plotter._get_data(
                'velocity', x, mask_tuple=None, filter_transitions=True, gatefilter=None)
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
                locDat = [xDat, yDat]
                detect(radar, img, file, locDat, sweepangle)
                plt.cla()
                plt.clf()
                plt.close('all')

def detect(radar, img, file, locDat, sweep):
    pred = model.predict(img)
    fig = plt.figure(figsize=(25,25))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis('off')
    for n in range(len(pred[1])):
            if(pred[2][n] > cint):
                ax.imshow(img)
                x,y,x1,y1 = float(pred[1][n][0]),float(pred[1][n][1]),float(pred[1][n][2]),float(pred[1][n][3])
                w,h = abs(x-x1),abs(y-y1)
                rect = patches.Rectangle((x,y),w,h,linewidth=1,edgecolor='r',facecolor='none')
                ax.add_patch(rect)
                detstr = pred[0][n] + ': ' + str(round(float(pred[2][n]),2))
                plt.text(x+w/2,y-5, detstr, fontsize = 8, color='red', ha='center')
                imname = detdir + file + '_detected' + '.png'
                plt.savefig(imname, bbox_inches='tight')
                ipix, jpix = round(x+w/2, 2), round(y+h/2, 2)
                norm = locDat[0].shape
                x, y = locDat[0][int(norm[0]*ipix/2500)][0],locDat[1][0][int(norm[1]*jpix/2500)]
                sitealt, sitelon, sitelat = float(radar.altitude['data']), float(radar.longitude['data']), float(radar.latitude['data'])
                lon, lat = np.around(pyart.core.cartesian_to_geographic_aeqd(x,y,sitelon,sitelat),4)
                alt = round(np.sqrt(x**2 + y**2)*np.tan(np.radians(float(sweep))) + sitealt,3)
                print('Detection at ' + str(float(lon)) + ' degrees East,' + ' ' + str(float(lat)) + ' degrees North,' + ' ' + str(alt) + ' m above sea level')
                fall2json(lat, lon, alt, file)


def fall2json(lat, lon, alt, file):
    name = file[0:4]
    m,d,y,hh,mm,ss = file[8:10], file[10:12], file[4:8], file[13:15], file[15:17], file[17:19]
    date = m + '/' + d + '/' + y + ' ' + hh + ':' + mm + ':' + ss
    data = {}
    data[date] = []
    data[date].append({
        'Altitude (m)': str(alt),
        'Longitude (deg East)': str(lon),
        'Latitude (deg North)': str(lat)
        })
    fname = outdir + name + ".json"
    with open(fname, 'a+') as outfile:
        json.dump(data, outfile)


def getListOfFiles(dirName):
    listOfFile = os.listdir(dirName)
    allFiles = list()
    for entry in listOfFile:
        fullPath = os.path.join(dirName,entry)
        if os.path.isdir(fullPath):
            allFiles = allFiles + getListOfFiles(fullPath)
        else:
            allFiles.append(fullPath)
    #Reducing process size, will require mutliple iteration
    if len(allFiles)>160:
        all_files = allFiles[:160]
    else:
        all_files = allFiles
    return all_files

def init(l):
    global lock
    lock = l



###############################################################################################################################

cint = 0.8
fdir = '../data/'
detdir = '../falls/imgs/'
outdir = "../falls/json/"
model = Model.load('RASRmodl.pth', ['fall'])


if __name__== '__main__':
    #optional spec for num pool workers, else num cpu
    if len(sys.argv)>1:
        runnum = sys.argv[1]
    else:
        runnum = cpu_count()/4
    try:
        all_files = getListOfFiles(fdir)
    except:
        all_files = []
        print('ERROR: path not found')
    top = len(all_files)
    if top != 0:
        l = Lock()
        n = int(runnum)
        for i in range(0,top,n):
            print('Batch '+str(int(i/n))+' of '+str(int(top/n))+', initializing pool...')
            with get_context("spawn").Pool(processes=int(runnum), initializer=init, initargs=(l,)) as pool:
                print('   mapping...')
                for x in pool.imap(readpyart, all_files[i:i+n]):
                    #print(x)
                    gc.collect() #clear each step
                #results = pool.map(getDataPart, all_files[i:i+n])
                time.sleep(1) #should permit maxtasksperchild=1
                print('   closing batch...')
                pool.close() #close chunk
                print('joining batch...')
                pool.join() #join chunk to clean
            #pool.terminate() #terminate chunk
            print('   batch closed')
            gc.collect() #clear at end
    else:
        print('ERROR: path not found')

#print ("Program took", time.time() - start_time, "to run")
