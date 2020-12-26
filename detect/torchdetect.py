import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore",category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    warnings.simplefilter("ignore",category=RuntimeWarning)

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

    from multiprocessing import Pool, cpu_count, Lock, get_context
    from multiprocessing.pool import ThreadPool

    import json
##############################################################################################################################




def detect(file):
        global thresh, h, nd
        radar = pyart.io.read(file)
        name = file[32:36]
        date = file[40:42] + '/' + file[42:44] + '/' + file[36:40] + ' ' + file[45:47] + ':' + file[47:49] + ':' + file[49:51]
        print('Checking ' + name + ' at ' + date)
        for x in range(radar.nsweeps):
            plotter = pyart.graph.RadarDisplay(radar)
            fig = plt.figure(figsize=(25,25), frameon=False)
            ax = plt.Axes(fig, [0.,0.,1.,1.])
            ax.set_axis_off()
            fig.add_axes(ax)
            plotter.set_limits(xlim=(-150, 150), ylim=(-150, 150), ax=ax)
            vmin, vmax = pyart.graph.common.parse_vmin_vmax(radar, 'velocity', None, None)
            data = plotter._get_data('velocity', x, mask_tuple=None, filter_transitions=True, gatefilter=None)

            if np.any(data)>0:
                xDat, yDat = plotter._get_x_y(x, edges=True, filter_transitions=True)
                data = data*(70/np.max(np.abs(data)))
                ax.pcolormesh(xDat, yDat, data, vmin=-70, vmax=70)
                canvas = FigureCanvas(fig)
                fig.canvas.draw()
                img = np.array(canvas.renderer.buffer_rgba())

                plt.cla()
                plt.clf()
                plt.close('all')

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



if __name__== '__main__':
    #optional spec for num pool workers, else num cpu
    if len(sys.argv)>1:
        runnum = sys.argv[1]
    else:
        runnum = cpu_count()/4
    try:
        all_files = getListOfFiles(dirname)
    except:
        all_files = []
        print('ERROR: path not found')
    top = len(all_files)
    if top != 0:
        l = Lock()
        #replaces pool=Pool() per https://codewithoutrules.com/2018/09/04/python-multiprocessing/
        # to avoid future hang errors on memoryerror
        #Set to ThreadPool to limit resources
        n = int(runnum)
        for i in range(0,top,n):
            print('Batch '+str(int(i/n))+' of '+str(int(top/n))+', initializing pool...')
            with get_context("spawn").Pool(processes=int(runnum), initializer=init, initargs=(l,)) as pool:
            #with ThreadPool(processes=int(runnum), initializer=init, initargs=(l,)) as pool:
                print('   mapping...')
                for x in pool.imap(detect, all_files[i:i+n]):
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
