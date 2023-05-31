"""
TORCHDET ver 1.0
as of March 3, 2022

Sub-function for Py-Torch based Convolutional Neural Network Object Detection of radar data

@author: Yash Sarda, Carson Lansdowne
"""

from detecto.core import Model
import numpy as np
from matplotlib import pyplot as plt
from matplotlib import patches
import pyart
from datetime import datetime, timedelta

from rasr.detect.output import string_convert

#########################################################


def evaluate_falls(img, radar, file, locdat, sweep, vis_dir, vis, conf_int, model_name):
    model = Model.load(model_name, ["fall"])
    pred = model.predict(img)
    # print(max(pred[2]))
    for n in range(len(pred[1])):
        if pred[2][n] > conf_int:
            bound = (
                # The unmapped location data from ARES appears about 2x as far as it should be.
                1
            )
            # Bound normalized
            xdat, ydat = bound * 1000 * locdat[0], bound * 1000 * locdat[1]

            t = round(locdat[2], 2)
            name, date, b_time, dt_str = string_convert(file)
            atime = datetime.strptime(b_time, "%m/%d/%Y %H:%M:%S") + timedelta(
                seconds=t
            )

            x0p, y0p, x1p, y1p = (
                float(pred[1][n][0]),
                float(pred[1][n][1]),
                float(pred[1][n][2]),
                float(pred[1][n][3]),
            )
            xp, yp = (x1p + x0p) / 2, (y1p + y0p) / 2  # center of detection

            xdm = [np.amin(xdat), np.amax(xdat)]
            ydm = [np.amin(ydat), np.amax(ydat)]
            xv = np.linspace(xdm[0], xdm[1], 2500)
            yv = np.linspace(ydm[1], ydm[0], 2500)

            x, y = xv[int(xp)], yv[int(yp)]
            x0, y0 = xv[int(x0p)], yv[int(y0p)]
            x1, y1 = xv[int(x1p)], yv[int(y1p)]

            w, h = abs(x0p - x1p), abs(y0p - y1p)

            if vis:
                # Saves the image with a bounding box, detection type, and confidence level
                fig = plt.figure(figsize=(25, 25))
                ax = fig.add_axes([0, 0, 1, 1])
                ax.imshow(img)
                ax.set_xticks([0, 500, 1000, 1500, 2000])
                ax.set_xticks([0, 500, 1000, 1500, 2000])
                ax.set_xticklabels([-250, -150, -50, 50, 150])
                ax.set_yticklabels([0, 250, 150, 50, -50, -150])
                rect = patches.Rectangle(
                    (x0p, y0p), w, h, linewidth=1, edgecolor="r", facecolor="none"
                )
                ax.add_patch(rect)
                detstr = pred[0][n] + ": " + str(round(float(pred[2][n]), 2))
                boxsize = str(round(float(w), 2)) + ", " + str(round(float(h), 2)) + "m"
                plt.text(
                    x0p + w / 2, y0p - 15, detstr, fontsize=8, color="red", ha="center"
                )
                plt.text(
                    x0p + w / 2, y0p - 5, boxsize, fontsize=8, color="red", ha="center"
                )
                imname = vis_dir + file + "_" + sweep + "_detected" + ".png"
                plt.savefig(imname, bbox_inches="tight")

            # Finding Geodetic coordinates from relative distance to site:
            z = np.sqrt(x**2 + y**2) * np.tan(np.radians(float(sweep)))
            sitealt, sitelon, sitelat = (
                float(radar.altitude["data"]),
                float(radar.longitude["data"]),
                float(radar.latitude["data"]),
            )

            lon0, lat0 = np.around(
                pyart.core.cartesian_to_geographic_aeqd(x0, y0, sitelon, sitelat), 3
            )
            lon1, lat1 = np.around(
                pyart.core.cartesian_to_geographic_aeqd(x1, y1, sitelon, sitelat), 3
            )
            lon0, lon1 = -lon0, -lon1
            alt = round(z + sitealt, 2)

            return [lat0, lon0, lat1, lon1, alt, atime, w, h]
        else:
            pass
