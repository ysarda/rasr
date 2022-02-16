"""
UNPACK ver 1.0
as of Jan 20, 2022

Conversion from PyART to numpy arrays

@author: Yash Sarda
"""

import os
import numpy as np
import pyart
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvas


def dat_to_img(radar):
    im_list = []
    for x in range(radar.nsweeps):
        plotter = pyart.graph.RadarDisplay(radar)
        fig = plt.figure(figsize=(25, 25), frameon=False)
        ax = plt.Axes(fig, [0.0, 0.0, 1.0, 1.0])
        fig.add_axes(ax)
        plotter.set_limits(xlim=(-250, 250), ylim=(-250, 250), ax=ax)
        data = plotter._get_data(
            "velocity", x, mask_tuple=None, filter_transitions=True, gatefilter=None
        )
        if np.any(data) > 0:
            x_dat, y_dat = plotter._get_x_y(x, edges=True, filter_transitions=True)
            data = data * (70 / np.max(np.abs(data)))
            ax.pcolormesh(x_dat, y_dat, data)
            canvas = FigureCanvas(fig)
            canvas.draw()
            buf, (w, h) = fig.canvas.print_to_buffer()
            img = np.frombuffer(buf, np.uint8).reshape((h, w, 4))
            # This whole segment is converting the data to a standard size
            if img.shape != ():
                img = np.delete(img, 3, 2)  # and readable image using matplotlib (MPL)
                sweep_angle = str(format(radar.fixed_angle["data"][x], ".2f"))
            t = radar.time["data"][x]
            loc_dat = [x_dat, y_dat, t]
            im_list.append([img, sweep_angle, loc_dat])
            plt.cla()
            plt.clf()
            plt.close("all")
    return im_list


def save_vis(im_list, file, save_dir):
    for img, sweep_angle, _ in im_list:
        imname = "vel_" + str(file[-23:]) + "_" + sweep_angle

        if os.path.exists(save_dir + imname + ".jpg"):
            print("Saving Velocity at sweep angle:", sweep_angle, "again")
            plt.imsave(save_dir + "/" + imname + "_2.jpg", img)
        else:
            print("Saving Velocity at sweep angle:", sweep_angle)
            plt.imsave(save_dir + "/" + imname + ".jpg", img)
