import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore",category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    warnings.simplefilter("ignore",category=RuntimeWarning)

import os
os.environ["PYART_QUIET"] = "1"

import numpy as np

import pyart

import matplotlib
import matplotlib.pyplot as plt
matplotlib.use("TKagg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvas

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import datasets, layers, models

#########################################################################

model = models.Sequential()
model.add(layers.Conv2D(2500, (4, 4), activation='relu', input_shape=(2500, 2500, 4)))
#model.add(layers.MaxPooling2D((2, 2)))
#model.add(layers.Conv2D(500, (4, 4), activation='relu'))
#model.add(layers.MaxPooling2D((2, 2)))
#model.add(layers.Conv2D(64, (3, 3), activation='relu'))
#model.add(layers.Flatten())
model.add(layers.Dense(32, activation='relu'))
model.add(layers.Dense(1))
model.summary()
#model.load_weights('meteormodel')


def evaluate(img,radar):
    img = np.reshape(img, [-1, 2500, 2500, 4])
    print(img.shape)
    predict = model.predict(img)
    #print(predict)
    input('press enter to continue')




def detect():
    for file in os.listdir('../data'):
        print(file)
        radar = pyart.io.read('../data/' + file)
        os.system('rm -r img/*')

        for x in range(radar.nsweeps):
            plotter = pyart.graph.RadarDisplay(radar)
            fig = plt.figure(figsize=(25,25), frameon=False)
            ax = plt.Axes(fig, [0.,0.,1.,1.])
            ax.set_axis_off()
            fig.add_axes(ax)
            plotter.set_limits(xlim=(-150, 150), ylim=(-150, 150), ax=ax)
            vmin, vmax = pyart.graph.common.parse_vmin_vmax(radar, 'reflectivity', None, None)
            data = plotter._get_data('reflectivity', x, mask_tuple=None, filter_transitions=True, gatefilter=None)

            if np.any(data)>0:
                xDat, yDat = plotter._get_x_y(x, edges=True, filter_transitions=True)
                data = data*(70/np.max(np.abs(data)))
                ax.pcolormesh(xDat, yDat, data, vmin=-70, vmax=70)

                canvas = FigureCanvas(fig)
                fig.canvas.draw()
                X = np.array(canvas.renderer.buffer_rgba())
                evaluate(X,radar)

            plt.cla()
            plt.clf()
            plt.close()

        input('hit enter for next site')








detect()
