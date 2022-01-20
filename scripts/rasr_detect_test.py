"""
RASR Detect Test ver 3.0
as of Jan 09, 2021

See README for details

@authors: Benjamin Miller and Yash Sarda
"""

from matplotlib.backends.backend_agg import FigureCanvas
from matplotlib import pyplot as plt

import pyart

import os

import numpy as np

from rasr.detect.motion import organizeData, stateVector, backProp, propVis
from rasr.detect.output import pointOut, stringConvert, txtOut
from rasr.detect.torchdet import detectFalls
from rasr.util.unpack import datToImg
from rasr.util.fileio import clearFiles

##########################################################

# Relevant paths, confidence value, and visualization toggle:
fdir = "test/data/"
outdir = "test/falls/"
detdir = "test/vis/"
cint = 0.75
vis = True  # Select True to print graphs and plots (good for debugging), and False to reduce file I/O, True by default for the test function
modelname = "RASRmodl.pth"

clearFiles(outdir)
clearFiles(detdir)

for file in os.listdir(fdir):
    name, date, btime, dtstr = stringConvert(file)
    print("\n")
    print("Checking " + name + " at " + btime)

    r, dr, allr = [], [], []
    radar = pyart.io.read(fdir + file)
    imList = datToImg(radar)

    for img, sweepangle, locDat in imList:
        print("Reading velocity at sweep angle:", sweepangle)
        v = detectFalls(
            img, radar, file, locDat, sweepangle, detdir, vis, cint, modelname,
        )  # detectFalls is a function from torchdet.py
        if v is not None:
            print(v)
    plt.cla()
    plt.clf()
    plt.close("all")
