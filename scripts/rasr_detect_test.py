
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

from motion import organizeData, stateVector, backProp, propVis
from output import pointOut, stringConvert, txtOut
from torchdet import detectFalls


##########################################################

# Relevant paths, confidence value, and visualization toggle:
fdir = 'test/data/'
outdir = 'test/falls/'
detdir = 'test/vis/'
cint = 0.75
vis = True     # Select True to print graphs and plots (good for debugging), and False to reduce file I/O.
               # True aby default for the test function

try:
    for file in os.listdir(outdir):
        os.remove(outdir + file)
    for file in os.listdir(detdir):
        os.remove(detdir + file)
except FileNotFoundError:
    pass

for file in os.listdir(fdir):
    name, date, btime, dtstr = stringConvert(file)
    print('\n')
    print('Checking ' + name + ' at ' + btime)

    r, dr, allr = [], [], []
    radar = pyart.io.read(fdir + file)
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
            canvas.draw()                                   # (1)
            buf, (w,h) = fig.canvas.print_to_buffer()
            img = np.frombuffer(buf,np.uint8).reshape((h, w, 4))
                                              # This whole segment is converting the data to a standard size
            if img.shape != ():
                img = np.delete(img, 3, 2)                          # and readable image using matplotlib (MPL)
            

                sweepangle = str(format(radar.fixed_angle['data'][x], ".2f"))
                print('Reading velocity at sweep angle: ', sweepangle)
                t = radar.time['data'][x]
                locDat = [xDat, yDat, t]
                v = detectFalls(radar, img, file, locDat, sweepangle, detdir, vis, cint)    # detect is a function from torchdet.py
                if v is not None:
                    vc, vall = v    # two types of output, for either point or square displays
                    vc.append(x)
                    r.append(vc)
                    allr.append(vall)
                plt.cla()
                plt.clf()
                plt.close('all')
            plt.cla()
            plt.clf()
            plt.close('all')
    if(len(r) >= 2):
        #squareout(file, radar, allr, outdir)
        pointOut(file, radar, r, outdir)
        rlsp = organizeData(r)
        rv = stateVector(rlsp)
        prop = backProp(rv,360)
        if vis:
            propVis(prop, detdir, name, dtstr)
        txtOut(prop, file, outdir)
