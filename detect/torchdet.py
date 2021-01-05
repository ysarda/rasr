from detecto.core import Model, Dataset, DataLoader
from detecto.visualize import plot_prediction_grid
from detecto.utils import read_image

import numpy as np

import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvas
from matplotlib import pyplot as plt
from matplotlib import patches
matplotlib.use("TKagg")

#########################################################


def detect(radar, img, file, locDat, sweep):
    cint = 0.85
    model = Model.load('RASRmodl.pth', ['fall'])
    pred = model.predict(img)
    for n in range(len(pred[1])):
        if(pred[2][n] > cint):
            x0p, y0p, x1p, y1p = float(pred[1][n][0]), float(pred[1][n][1]), float(pred[1][n][2]), float(pred[1][n][3])
            w,h = (x0p-x1p),(y0p-y1p)
            ipix, jpix = round(x0p + w / 2, 2), round(y0p + h / 2, 2)
            norm = locDat[0].shape
            x, y = 1000 * locDat[0][int(norm[0] * ipix / 2500)][0], 1000 * locDat[1][0][int(norm[1] * jpix / 2500)]
            x0, y0 = 1000 * locDat[0][int(norm[0] * x0p / 2500)][0], 1000 * locDat[1][0][int(norm[1] * y0p / 2500)]
            x1, y1 = 1000 * locDat[0][int(norm[0] * x1p / 2500)][0], 1000 * locDat[1][0][int(norm[1] * y1p / 2500)]
            z = np.sqrt(x**2 + y**2) * np.tan(np.radians(sweep))
            t = round(locDat[2], 2)
            return [x, y, z, t], [x0, y0, x1, y1, z, t]
        else:
            pass

def detectvis(radar, img, file, locDat, sweep, detdir):
    cint = 0.8
    model = Model.load('RASRmodl.pth', ['fall'])
    pred = model.predict(img)
    fig = plt.figure(figsize=(25, 25))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis('off')
    for n in range(len(pred[1])):
        if(pred[2][n] > cint):
            ax.imshow(img)
            x0p, y0p, x1p, y1p = float(pred[1][n][0]), float(pred[1][n][1]), float(pred[1][n][2]), float(pred[1][n][3])
            w, h = abs(x0p - x1p), abs(y0p - y1p)
            rect = patches.Rectangle((x0p, y0p), w, h, linewidth=1, edgecolor='r', facecolor='none')
            ax.add_patch(rect)
            detstr = pred[0][n] + ': ' + str(round(float(pred[2][n]), 2))
            plt.text(x0p + w / 2, y0p - 5, detstr, fontsize=8, color='red', ha='center')
            imname = detdir + file + '_' + sweep + '_detected' + '.png'
            plt.savefig(imname, bbox_inches='tight')
            ipix, jpix = round(x0p + w / 2, 2), round(y0p + h / 2, 2)
            norm = locDat[0].shape
            x, y = 1000 * locDat[0][int(norm[0] * ipix / 2500)][0], 1000 * locDat[1][0][int(norm[1] * jpix / 2500)]
            x0, y0 = 1000 * locDat[0][int(norm[0] * x0p / 2500)][0], 1000 * locDat[1][0][int(norm[1] * y0p / 2500)]
            x1, y1 = 1000 * locDat[0][int(norm[0] * x1p / 2500)][0], 1000 * locDat[1][0][int(norm[1] * y1p / 2500)]
            z = np.sqrt(x**2 + y**2) * np.tan(np.radians(float(sweep)))
            t = round(locDat[2], 2)
            return [x, y, z, t], [x0, y0, x1, y1, z, t]
        else:
            pass
