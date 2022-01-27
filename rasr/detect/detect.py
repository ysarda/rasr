import pyart
from matplotlib import pyplot as plt

from rasr.util.fileio import clear_files
from rasr.util.unpack import dat_to_img
from rasr.detect.output import string_convert
from rasr.detect.torchdet import detect_falls


def run_detect(files, outdir, detdir, cint, modelname, vis):
    clear_files(outdir)
    clear_files(detdir)

    for file in files:
        name, date, btime, dtstr = string_convert(file)
        print("\n")
        print("Checking " + name + " at " + btime)

        radar = pyart.io.read(file)
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
