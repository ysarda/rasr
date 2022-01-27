"""
RASR Detect Test ver 3.0
as of Jan 09, 2021

See README for details

@authors: Benjamin Miller and Yash Sarda
"""


from matplotlib import pyplot as plt
import pyart
import os

from rasr.detect.output import string_convert
from rasr.detect.torchdet import detect_falls
from rasr.util.unpack import dat_to_img
from rasr.util.fileio import clear_files

if __name__ == "__main__":

    # Relevant paths, confidence value, and visualization toggle:
    fdir = "test/data/"
    outdir = "test/falls/"
    detdir = "test/vis/"
    cint = 0.75
    vis = True
    # Select True to print graphs and plots (good for debugging), and False to reduce file I/O,
    # True by default for the test function
    modelname = "RASRmodl.pth"

    clear_files(outdir)
    clear_files(detdir)

    for file in os.listdir(fdir):
        name, date, btime, dtstr = string_convert(file)
        print("\n")
        print("Checking " + name + " at " + btime)

        r, dr, allr = [], [], []
        radar = pyart.io.read(fdir + file)
        im_list = dat_to_img(radar)

        for img, sweep_angle, loc_dat in im_list:
            print("Reading velocity at sweep angle:", sweep_angle)
            v = detect_falls(
                img,
                radar,
                file,
                loc_dat,
                sweep_angle,
                detdir,
                vis,
                cint,
                modelname,
            )
            if v is not None:
                print(v)
        plt.cla()
        plt.clf()
        plt.close("all")
