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
    from lib.Unwrapper import runFunction as filterFile 
    from multiprocessing import Pool, cpu_count, Lock, get_context
    from multiprocessing.pool import ThreadPool
    import numpy as np
    import gc
    import time
    import matplotlib.colors as color
    from functools import partial
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
    colorCutoff = 100 
    edgeIntensity = 8#12 
    sizeFilter = 1*(10**-4)
    circularityFilter = 0.3 
    fillFilter = 30
    
    #run program
    #fileloc = filename
    f = filterFile(filename, filename, velMap, spwMap, colorCutoff, edgeIntensity, sizeFilter , colorCutoff, circularityFilter, fillFilter, lock, writeImgs)
    os.remove(filename)
    return f
    
def init(l):
    global lock
    lock = l

def getListOfFiles(dirName):
    listOfFile = os.listdir(dirName)
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
            











