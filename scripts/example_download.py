"""
Example Download ver 1.0
as of Jan 09, 2021

Script for downloading and unpacking an example detection

@authors: Yash Sarda
"""

from datetime import timedelta, date
import pyart

from rasr.get.get import run_get
from rasr.util.fileio import get_list_of_files, clear_files
from rasr.util.unpack import dat_to_img, save_vis

if __name__ == "__main__":
    data_dir = "test/raw"
    im_dir = "test/images"
    link_dir = "links"
    product = "AAL2"

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

    clear_files(link_dir)
    run_get(radar_sites, date_list, [stime, etime], data_dir, link_dir)

    all_files = get_list_of_files(data_dir)
    for file in all_files:
        radar = pyart.io.read(file)
        im_list = dat_to_img(radar, "velocity")
        save_vis(im_list, file, im_dir)
