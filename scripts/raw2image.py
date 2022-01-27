"""
Raw to Image ver 1.0
as of Jan 09, 2021

Script for converting NOAA files to images for training

@authors: Yash Sarda
"""

import pyart

from rasr.util.fileio import get_list_of_files
from rasr.util.unpack import dat_to_img, save_vis

if __name__ == "__main__":

    raw_dir = "training/raw"
    im_dir = "training/im"

    all_files = get_list_of_files(raw_dir)
    for file in all_files:
        radar = pyart.io.read(file)
        im_list = dat_to_img(radar)
        save_vis(im_list, file, im_dir)
