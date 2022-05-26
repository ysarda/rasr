"""
Raw to Image ver 1.0
as of April 11, 2022

Script for converting NOAA files to images for training

@authors: Yash Sarda, Carson Lansdowne
"""

import pyart

from rasr.util.fileio import get_list_of_files, make_dir
from rasr.util.unpack import dat_to_img, save_vis, save_vis_compare

if __name__ == "__main__":

    make_dir("training/im")

    # raw_dir = "test/data"
    base_dir = "training/2500/Reflectivity/all/"
    raw_dir = "training/2500/All_raw_detections/"
    im_dir = "training/all_fields/corrected/"
    # raw_dir = "training/test_null/"
    # im_dir = "training/all_data_experiment/test_null/"

    # radar objects prior to 2011 do not have all fields
    fields = ['velocity',
              # 'differential_reflectivity',
              # 'differential_phase',
              # 'cross_correlation_ratio']
              'reflectivity',
              'spectrum_width']

    all_files = get_list_of_files(raw_dir)

    # Script for creating new files for other fields

    compare_files = get_list_of_files(base_dir)

    for i, file in enumerate(compare_files):
        file_short = file.split('/')
        compare_files[i] = file_short[-1][:-4]

    for file in all_files:
        for field in fields:
            make_dir(im_dir + field)
            radar = pyart.io.read(file)
            im_list = dat_to_img(radar, field)
            save_vis_compare(im_list, file, im_dir +
                             field, compare_files, field)
