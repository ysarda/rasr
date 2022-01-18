"""
TORCHDET ver 1.0
as of Jan 09, 2021

Sub-function for Py-Torch based Convolutional Neural Network Object Detection of radar data

@author: Yash Sarda
"""


from detecto.core import Model

import numpy as np

from matplotlib import pyplot as plt
from matplotlib import patches

import pyart

import datetime
from datetime import datetime, timedelta

from output import stringConvert

#########################################################

def detectFalls(radar, img, file, locDat, sweep, detdir, vis, cint):
    model = Model.load('RASRmodl.pth', ['fall'])
    pred = model.predict(img)
    #print(max(pred[2]))
    for n in range(len(pred[1])):
        if(pred[2][n] > cint):
            bound = 0.5 # The unmapped location data is about 2x as far as it should be.
                        # I don't know why this, and this is a temp solution.
            xdat,ydat = bound*1000*locDat[0], bound*1000*locDat[1]

            t = round(locDat[2], 2)
            name, date, btime, dtstr = stringConvert(file)
            atime = (datetime.strptime(btime, '%m/%d/%Y %H:%M:%S') + timedelta(seconds=t))

            x0p, y0p, x1p, y1p = float(pred[1][n][0]), float(pred[1][n][1]), float(pred[1][n][2]), float(pred[1][n][3])
            xp, yp = (x1p+x0p)/2, (y1p+y0p)/2

            xdm = [np.amin(xdat),np.amax(xdat)]
            ydm = [np.amin(ydat),np.amax(ydat)]
            Xv = np.linspace(xdm[0],xdm[1],2500)
            Yv = np.linspace(ydm[1],ydm[0],2500)

            x,y = Xv[int(xp)], Yv[int(yp)]
            x0,y0 = Xv[int(x0p)], Yv[int(y0p)]
            x1,y1 = Xv[int(x1p)], Yv[int(y1p)]

            if (vis == True):   # Saves the image with a bounding box, detection type, and confidence level
                fig = plt.figure(figsize=(25, 25))
                ax = fig.add_axes([0, 0, 1, 1])
                ax.imshow(img)
                w, h = abs(x0p - x1p), abs(y0p - y1p)
                rect = patches.Rectangle((x0p, y0p), w, h, linewidth=1, edgecolor='r', facecolor='none')
                ax.add_patch(rect)
                detstr = pred[0][n] + ': ' + str(round(float(pred[2][n]), 2))
                plt.text(x0p + w / 2, y0p - 5, detstr, fontsize=8, color='red', ha='center')
                imname = detdir + file + '_' + sweep + '_detected' + '.png'
                plt.savefig(imname, bbox_inches='tight')

            # Finding Geodetic coordinates from relative distance to site:
            z = np.sqrt(x**2 + y**2) * np.tan(np.radians(float(sweep)))
            sitealt, sitelon, sitelat = float(radar.altitude['data']), float(radar.longitude['data']), float(radar.latitude['data'])
            lon, lat = np.around(pyart.core.cartesian_to_geographic_aeqd(x, y, sitelon, sitelat), 2)
            lon0, lat0 = np.around(pyart.core.cartesian_to_geographic_aeqd(x0, y0, sitelon, sitelat), 3)
            lon1, lat1 = np.around(pyart.core.cartesian_to_geographic_aeqd(x1, y1, sitelon, sitelat), 3)
            lon, lon0, lon1 = -lon, -lon0, -lon1
            alt = round(z + sitealt, 2)

            return [lat, lon, alt, atime], [lat0, lon0, lat1, lon1, alt, atime]
        else:
            pass
