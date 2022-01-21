"""
CNN Test ver 1.0
as of Jan 21, 2022

CNN Testing Script

@authors: Yash Sarda
"""

import os

os.environ["PYART_QUIET"] = "1"
import pyart

from rasr.util.fileio import getListOfFiles
from rasr.util.unpack import datToImg
from rasr.network.CRNN2D import CRNN2D

#########################################################################################################################

if __name__ == "__main__":

    rawDir = "training/raw"
    model = CRNN2D()  # .to("cuda")

    all_files = getListOfFiles(rawDir)
    for file in all_files:
        radar = pyart.io.read(file)
        imList = datToImg(radar)
        for img, _, _ in imList[0:1]:
            img2 = model.forward(img)

