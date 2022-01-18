
import os
import numpy as np

import pyart

import matplotlib
import matplotlib.pyplot as plt
matplotlib.use("TKagg")
from matplotlib.backends.backend_agg import FigureCanvas

def datToVel(file, imdir):
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
            if os.path.exists(imdir + imname + '.jpg'):
                plt.savefig(imdir + imname + '_2.jpg')
            else:
                plt.savefig(imdir + imname + '.jpg')
            plt.cla()
            plt.clf()
            plt.close('all')
    input("\nHit enter for the next file\n")