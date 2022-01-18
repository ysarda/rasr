"""
Raw to Image ver 1.0
as of Jan 09, 2021

Script for converting NOAA files to images for training

@authors: Benjamin Miller and Yash Sarda
"""

import os

os.environ["PYART_QUIET"] = "1"

from rasr.util.fileio import getListOfFiles
from rasr.util.unpack import datToVel

#########################################################################################################################

cpath = os.getcwd()
rawdir = cpath + "training/raw/"
imdir = cpath + "training/im/"
all_files = getListOfFiles(rawdir)
for file in all_files:
    datToVel(file, imdir)
