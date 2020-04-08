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
    import os
    os.environ["PYART_QUIET"] = "1"
    from lib.Unwrapper import runFunction as filterFile 
    from multiprocessing import Pool, cpu_count, Lock
    import numpy as np
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
    fileloc = os.getcwd()+"/tmptest/"+filename
    filterFile(fileloc, filename, velMap, spwMap, colorCutoff, edgeIntensity, sizeFilter , colorCutoff, circularityFilter, fillFilter, lock, writeImgs)
    #os.remove(fileloc)
    
def init(l):
    global lock
    lock = l
    
if __name__== '__main__':
    #optional spec for num pool workers, else num cpu
    if len(sys.argv)>1:
        runnum = sys.argv[1]
    else:
        runnum = cpu_count()
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
        
    dirname = os.getcwd()+"/tmptest"
    if os.path.exists(dirname): 
        #instantiate outfile
        open(outfile, 'a').close

        velMap,spwMap = getMaps()
        all_files = os.listdir(dirname+"/")
        
        l = Lock()
            
        pool = Pool(processes=int(runnum), initializer=init, initargs=(l,))
        getDataPart = partial(getData, velMap=velMap, spwMap=spwMap, writeImgs=writeImgs)
        pool.map(getDataPart, all_files)
        pool.close
        pool.join
                
            











