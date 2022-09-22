import pyart
from matplotlib import pyplot as plt
import shutil

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
        im_list = dat_to_img(radar, 'velocity')

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
                print("Detection!")
                allr.append(v)


shutil.copy(file, output_dir)
plt.cla()
plt.clf()
plt.close("all")

if(len(allr) >= 1):
    # output JSON of detection bounding data
    square_out(file, allr, output_dir)

# Script for checking individual file detections
# if __name__ == "__main__":

#     # Relevant paths, confidence value, and visualization toggle:
#     file_dir = "data/"
#     output_dir = "falls/"
#     vis_dir = "vis/"
#     conf_int = 0.1
#     vis = True
#     img = "training/experiments/2500/test/vel_KLOT20030327_054711.g_14.7.jpg"
#     model_name = "RASRmodl.pth"
#     filedir = "training/2500/All_raw_detections/"
#     file = "KLOT20030327_054711"
#     radar = pyart.io.read(filedir + file)
#     im_list = dat_to_img(radar, 'velocity')
#     for img, sweep_angle, loc_dat in im_list[7:]:
#         print("Reading velocity at sweep angle:", sweep_angle)
#         v = evaluate_falls(
#             img,
#             radar,
#             file,
#             loc_dat,
#             sweep_angle,
#             vis_dir,
#             vis,
#             conf_int,
#             model_name,
#         )
