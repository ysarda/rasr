"""
Training Preparation ver 1.0
as of Jan 09, 2021

Script for downloading and converting NOAA files to images for training

@authors: Yash Sarda
"""

import time
from datetime import datetime, timedelta, date
import pyart

from rasr.get.get import run_get
from rasr.util.fileio import get_list_of_files, clear_files
from rasr.util.unpack import dat_to_img, save_vis

if __name__ == "__main__":
    data_dir = "training/data"
    im_dir = "training/im"
    link_dir = "links"

    clear_files(link_dir)
    start_time = time.time()

    product = "AAL2"
    # Level-II data include the original three meteorological base data quantities: reflectivity,
    # mean radial velocity, and spectrum width, as well as the dual-polarization base data of differential
    # reflectivity, correlation coefficient, and differential phase.
    now = datetime.now()
    man = input("Manual Input? (y/n): ")
    if man == "y":
        yri = int(input("Year: "))
        monthi = int(input("Month: "))
        dayi = int(input("Day: "))
        stime = int(input("Start Time: ") + "00")
        etime = int(input("End Time: ") + "00")
        nsites = int(input("Number of Sites: "))
        radar_sites = []
        for i in range(1, nsites + 1):
            text = "Site " + str(i) + ": "
            s = input(text)
            radar_sites.append(s)
    else:
        yri = 2017
        monthi = 2
        dayi = 6
        stime = 72000
        etime = 72200
        radar_sites = ["KMKX"]

    start_date = date(yri, monthi, dayi)
    end_date = start_date + timedelta(1)  # date(now.year, now.month, now.day+1)

    date_list = [
        start_date.year,
        start_date.month,
        start_date.day,
        end_date.year,
        end_date.month,
        end_date.day,
    ]

    run_get(radar_sites, date_list, [stime, etime], data_dir, link_dir)

    input("\nDump the files you don't need! Then hit enter\n")

    all_files = get_list_of_files(data_dir)
    for file in all_files:
        radar = pyart.io.read(file)
        im_list = dat_to_img(radar)
        save_vis(im_list, file, im_dir)
