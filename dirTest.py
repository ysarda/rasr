# -*- coding: utf-8 -*-
"""
Created on Tue Aug  6 10:10:25 2019

@author: Ben
"""

import os
import sys

def getListOfFiles(dirName):
    listOfFile = os.listdir(dirName)
    allFiles = list()
    for entry in listOfFile:
        fullPath = os.path.join(dirName,entry)
        if os.path.isdir(fullPath):
            allFiles = allFiles + getListOfFiles(fullPath)
        else:
            allFiles.append(fullPath)
    return allFiles

if __name__== '__main__':
    #dirname = os.getcwd()+"/tmp"
    dirname = '/scratch/06582/bgmiller/gpfs/corral3/repl/utexas/MOST/NOAA_Data_Collection/'
    os.environ['PATH'] += ':'+dirname
    sys.path.append(dirname)
    
    
    #instantiate outfile
    try:
        all_files = getListOfFiles(dirname)
        print(len(all_files))
    except:
        all_files = []
        print('ERROR: path not found')
        
        