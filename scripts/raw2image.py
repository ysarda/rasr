"""
Raw to Image ver 1.0
as of Jan 09, 2021

Script for converting NOAA files to images for training

@authors: Benjamin Miller and Yash Sarda
"""

import os

os.environ["PYART_QUIET"] = "1"
import pyart

from rasr.util.fileio import getListOfFiles
from rasr.util.unpack import datToImg, saveVis

#########################################################################################################################

if __name__ == "__main__":

    rawDir = "training/raw"
    imDir = "training/im"

    all_files = getListOfFiles(rawDir)
    for file in all_files:
        radar = pyart.io.read(file)
        imList = datToImg(radar)
        saveVis(imList, file, imDir)
