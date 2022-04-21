"""
CNN Test ver 1.0
as of Jan 21, 2022

Model Testing Script

@authors: Yash Sarda
"""

import pyart

from rasr.util.fileio import get_list_of_files
from rasr.util.unpack import dat_to_img
from rasr.network.rcnn import RCNN2D

if __name__ == "__main__":

    raw_dir = "data/"
    model = RCNN2D()  # .to("cuda")

    all_files = get_list_of_files(raw_dir)
    for file in all_files[0:1]:
        radar = pyart.io.read(file)
        im_list = dat_to_img(radar)
        for img, _, _ in im_list[0:1]:
            img2 = model.forward(img)
