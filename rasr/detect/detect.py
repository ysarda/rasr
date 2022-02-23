import pyart
from matplotlib import pyplot as plt

from rasr.util.fileio import clear_files
from rasr.util.unpack import dat_to_img
from rasr.detect.output import string_convert, square_out
from rasr.detect.eval import evaluate_falls


def run_detect(files, file_dir, output_dir, vis_dir, conf_int, model_name, vis):
    clear_files(output_dir)
    clear_files(vis_dir)

    for file in files:
        allr = []  # declare output array for display

        file = file[len(file_dir):]

        name, _, b_time, _ = string_convert(file)
        print("\n")
        print("Checking " + name + " at " + b_time)

        radar = pyart.io.read(file_dir + file)
        im_list = dat_to_img(radar)

        for img, sweep_angle, loc_dat in im_list:
            print("Reading velocity at sweep angle:", sweep_angle)
            v = evaluate_falls(
                img,
                radar,
                file,
                loc_dat,
                sweep_angle,
                vis_dir,
                vis,
                conf_int,
                model_name,
            )
            if v is not None:
                print(v)
        plt.cla()
        plt.clf()
        plt.close("all")

        if(len(allr) >= 2):
            # output JSON of detection bounding data
            square_out(file, allr, output_dir)
