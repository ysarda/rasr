# -*- coding: utf-8 -*-
"""
Created on Thu Jan 17 12:58:28 2019
ver 1.0 as of Feb 01, 2019

See README for details

@author: Benjamin Miller 
"""
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore",category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    warnings.simplefilter("ignore",category=RuntimeWarning)
    import os
    os.environ["PYART_QUIET"] = "1"
    import pyart
    import matplotlib 
    import matplotlib.pyplot as plt
    import matplotlib.colors as color
    matplotlib.use("agg") 
    from lib.Locator import DetectMeteors    
    from multiprocessing import Pool, cpu_count, Lock, get_context
    from multiprocessing.pool import ThreadPool
    import numpy as np
    import gc
    import time
    from functools import partial
    import random
    import sys



#SEE README FOR OPERATING INSTRUCTIONS
#West,TX             : KFWS 2/15/2009 16:53:32
#Battle Mountain, NV : KLRX 8/22/2012 06:03:05
#stations = [sys.argv[1]]
# ADVANCED INPUT, see readme and demo
#Constaints array for:
#TX: [100,12,1e-4,0.3,30]
#NV: [100,12,1e-4,0.0,30]
    
def getMaps():
    #Set velocity colormap 
    cmaplist = np.array([[255,0,0],#-70
                         [255,0,0],#-60
                         [210,0,0],#-50
                         [180,0,0],#-40
                         [150,0,0],#-30
                         [115,0,0],#-20
                         [70,40,40],#-10
                         [70,70,70],#0
                         [40,70,40],#10
                         [0,115,0],#20
                         [0,150,0],#30
                         [0,180,0],#40
                         [0,210,0],#50
                         [0,255,0],#60
                         [0,255,0]])/255#70
    cmaplist = np.flip(cmaplist,axis=0)
    velMap = color.LinearSegmentedColormap.from_list('velMap',cmaplist,N=256)
    
    #Set spectrum width colormap
    cmaplist = np.array([[20,20,20],#0
                         [40,40,40],#6
                         [40,150,40],#12 40 150
                         [150,40,40],#18 150 40
                         [150,70,0],#24
                         [255,255,0]])/255#30
    spwMap = color.LinearSegmentedColormap.from_list('spwMap',cmaplist,N=256)
    return velMap, spwMap

def getData(filename, velMap, spwMap, writeImgs):
    cutoff = 100 
    edgeFilter = 8#12 
    areaFraction = 1*(10**-4)
    circRatio = 0.3 
    fillFilt = 30
    colorIntensity = cutoff
    date=filename
        
    #Instantiate RadarData dictionary and lists
    RadarData = {}
    RadarData['velocity'] = []
    RadarData['spectrum_width'] = []
    
    #Read in radar archive
    RADAR_NAME = filename;  
    radar = pyart.io.read_nexrad_archive(RADAR_NAME, exclude_fields='reflectivity')
    plotter = pyart.graph.RadarDisplay(radar)  
    plotter = pyart.graph.RadarDisplay(radar)

    
    for x in range(radar.nsweeps):
        # Instantiate figure
        fig = plt.figure(figsize=(25,25), frameon=False)
        ax = plt.Axes(fig, [0.,0.,1.,1.])
        ax.set_axis_off()
        fig.add_axes(ax)
        plotter.set_limits(xlim=(-150, 150), ylim=(-150, 150), ax=ax)
        #Get velocity data
        vmin, vmax = pyart.graph.common.parse_vmin_vmax(radar, 'velocity', None, None) 
        data = plotter._get_data('velocity', x, mask_tuple=None, filter_transitions=True, gatefilter=None)
        #Check for empty altitude cuts
        if np.any(data)>0:
            xDat, yDat = plotter._get_x_y(x, edges=True, filter_transitions=True)
            data = data*(70/np.max(np.abs(data)))
            #Format data for passing to Locator
            ax = ax.pcolormesh(xDat, yDat, data, vmin=-70, vmax=70, cmap=velMap)
            #NOTE: Color reduces data range, but required for openCV processing,
            #      and may correct later to deeper resolution if necessary.
            fig.canvas.draw()
            img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
            img = img.reshape(fig.canvas.get_width_height()[::1]+(3,))
            img = np.flip(img,axis=2)
            img.setflags(write=1)
            img[np.where((img==[255,255,255]).all(axis=2))] = [0,0,0] 
            #Attatch data to dictionary variable for passing
            RadarData['velocity'].append(img)
            plt.close(fig)
            plt.clf()
            plt.cla()
            gc.collect()
    
            # Instantiate figure 
            fig = plt.figure(figsize=(25,25), frameon=False)
            ax = plt.Axes(fig, [0.,0.,1.,1.])
            ax.set_axis_off()
            fig.add_axes(ax)
            plotter.set_limits(xlim=(-150, 150), ylim=(-150, 150), ax=ax)
            #Get spectrum width data
            vmin, vmax = pyart.graph.common.parse_vmin_vmax(radar, 'spectrum_width', None, None) 
            data = plotter._get_data('spectrum_width', x, mask_tuple=None, filter_transitions=True, gatefilter=None)
            xDat, yDat = plotter._get_x_y(x, edges=True, filter_transitions=True)
            data = data*(30/np.max(data))
            #Format data for passing to Locator
            ax = ax.pcolormesh(xDat, yDat, data, vmin=0, vmax=30, cmap=spwMap)
            fig.canvas.draw()
            img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
            img = img.reshape(fig.canvas.get_width_height()[::1]+(3,))
            img = np.flip(img,axis=2) #convert to bgr
            img.setflags(write=1)
            img[np.where((img==[255,255,255]).all(axis=2))] = [0,0,0] 
            #Attatch data to dictionary variable for passing
            RadarData['spectrum_width'].append(img)
            plt.close(fig)
            plt.clf()
            plt.cla()
            gc.collect()

        #Update for empty data scans
        else:
            plt.close(fig)
            plt.clf()
            plt.cla()
            gc.collect()
            
    #Double-check figure closing
    del img
       
    #Run Locator
    #pyRadarData, cutoff, edgeFilter, areaFraction, colorIntensity, circRatio
    fallCount, fallId, xy= DetectMeteors(RadarData,cutoff, edgeFilter, areaFraction, colorIntensity, circRatio, fillFilt, RADAR_NAME, writeImgs)

    #Update user on any detections and get positions
    if fallCount>0:    
        fallId = list(map(int,fallId))
        #print('\n   FALLS DETECTED AT SCAN(S): '+str(fallId))
        lonlat0 = [radar.longitude['data'],radar.latitude['data']]
        lla = []
        for ind, r in enumerate(xy, start=0):
            lon,lat = pyart.core.cartesian_to_geographic_aeqd(r[0],r[1],lonlat0[0],lonlat0[1])
            dist = np.sqrt(np.abs(r[0])**2+np.abs(r[1])**2)
            el = radar.get_elevation(fallId[ind])
            alt = dist*np.tan(el[0]*np.pi/180)
            lla.append([lat.item(),lon.item(),alt])
            #print(date+' '+str([lat.item(),lon.item(),alt]))
            outstr = str(date+' '+str(lat.item())+' '+str(lon.item())+' '+str(alt)+"\n")
            #write to opened script
            lock.acquire()
            outfile = os.getcwd()+"/out/out.txt"
            outfilewrite = open(outfile,'a')
            outfilewrite.write(outstr)
            outfilewrite.close
            lock.release()
    os.remove(filename)
    return filename
    
def init(l):
    global lock
    lock = l

def getListOfFiles(dirName):
    listOfFile = os.listdir(dirName)
    random.shuffle(listOfFile)
    #NOTE: os.listdir returns arbitary values
    # cant use sorted(os.listdir()) for numeric order either  
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
    
if __name__== '__main__':
    #optional spec for num pool workers, else num cpu
    if len(sys.argv)>1:
        runnum = sys.argv[1]
    else:
        runnum = cpu_count()/4 #11 of 68/6?  or 17 of 68/4?
        #runnum = 17
    if len(sys.argv)>2:
        if str(sys.argv[2]) == 'True':
            writeImgs = True
        else:
            writeImgs=False
    else:
        writeImgs = False
        
    outdir = os.getcwd()+"/out"
    outfile = outdir+"/out.txt"
    if not os.path.exists(outdir):                 
        try:
                os.mkdir(outdir)
        except FileExistsError:
                pass
        
    #dirname = os.getcwd()+"/tmp"
    dirname = '/scratch/06582/bgmiller/gpfs/corral3/repl/utexas/MOST/NOAA_Data_Collection/'
    os.environ['PATH'] += ':'+dirname
    sys.path.append(dirname)
    
    
    #instantiate outfile
    try:
        all_files = getListOfFiles(dirname)
    except:
        all_files = []
        print('ERROR: path not found')
        
    if len(all_files) != 0: #os.path.exists(dirname): 
        open(outfile, 'a').close
        velMap,spwMap = getMaps()
        getDataPart = partial(getData, velMap=velMap, spwMap=spwMap, writeImgs=writeImgs)
        l = Lock()

        #replaces pool=Pool() per https://codewithoutrules.com/2018/09/04/python-multiprocessing/
        # to avoid future hang errors on memoryerror
        #Set to ThreadPool to limit resources 
        n = int(runnum) 
        for i in range(0,len(all_files),n):
            print('Batch '+str(int(i/n))+' of '+str(int(len(all_files)/n))+', initializing pool...')
            with get_context("spawn").Pool(processes=int(runnum), initializer=init, initargs=(l,)) as pool:#, maxtasksperchild=4) as pool:  
                #removed max tasks per child 
            #with ThreadPool(processes=int(runnum), initializer=init, initargs=(l,)) as pool:    
                #threadpool functions, but still too slow, need the processing pool
                #currently 1/4 cpu's looping 1/4 sites 4 times.  1/8 load to close
                print('   mapping...')
                for x in pool.imap(getDataPart, all_files[i:i+n]):
                    print(x)
                    gc.collect() #clear each step
                #results = pool.map(getDataPart, all_files[i:i+n])
                
                #INTRODUCE ONCE I SOLVE HANG ERROR 
                #supposedly sleep(1) will allow tasks 
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
            











