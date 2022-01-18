"""
Raw to Image ver 1.0
as of Jan 09, 2021

Script for converting NOAA files to images for training

@authors: Benjamin Miller and Yash Sarda
"""

import os
os.environ["PYART_QUIET"] = "1"

import numpy as np

import pyart

import matplotlib
import matplotlib.pyplot as plt
matplotlib.use("TKagg")
from matplotlib.backends.backend_agg import FigureCanvas


#########################################################################################################################

def dat2vel(file, imdir):
    global thresh, h, nd
    radar = pyart.io.read(file)
    for x in range(radar.nsweeps):
        plotter = pyart.graph.RadarDisplay(radar)
        fig = plt.figure(figsize=(25, 25), frameon=False)
        ax = plt.Axes(fig, [0., 0., 1., 1.])
        fig.add_axes(ax)
        plotter.set_limits(xlim=(-250, 250), ylim=(-250, 250), ax=ax)
        data = plotter._get_data(
            'velocity', x, mask_tuple=None, filter_transitions=True, gatefilter=None)
        if np.any(data) > 0:
            xDat, yDat = plotter._get_x_y(
                x, edges=True, filter_transitions=True)
            data = data * (70 / np.max(np.abs(data)))
            ax.pcolormesh(xDat, yDat, data)
            canvas = FigureCanvas(fig)
            fig.canvas.draw()
            img = np.array(canvas.renderer.buffer_rgba())
            sweepangle = str(round(radar.fixed_angle['data'][x], 2))
            imname = 'vel_' + str(file[40:-1]) + '_' + sweepangle
            print('Saving Velocity at sweep angle: ', sweepangle)
            if os.path.exists(imdir + imname + 'jpg'):
                plt.savefig(imdir + imname + '_2.jpg')
            else:
                plt.savefig(imdir + imname + '.jpg')
            plt.cla()
            plt.clf()
            plt.close('all')
    input('hit enter for next file')

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


########################################################################################################################


cpath = os.getcwd()
rawdir = cpath + 'training/raw/'
imdir = cpath + 'training/im/'
all_files = getListOfFiles(rawdir)
for file in all_files:
    dat2vel(file, imdir)
