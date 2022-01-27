"""
Training Preparation ver 1.0
as of Jan 09, 2021

Script for downloading and converting NOAA files to images for training

@authors: Yash Sarda
"""

import time
from datetime import datetime, timedelta, date
import pyart

from rasr.get.scrape import save_links, download_link
from rasr.get.getdata import date_range
from rasr.util.fileio import get_list_of_files, clear_files
from rasr.util.unpack import dat_to_img, save_vis

if __name__ == "__main__":
    raw_dir = "training/raw"
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

    for single_date in date_range(start_date, end_date):
        date = single_date.strftime("%Y %m %d")
        date_arr = [int(s) for s in date.split() if s.isdigit()]
        year = date_arr[0]
        month = date_arr[1]
        day = date_arr[2]

        if month < 10:  # formats the month to be 01,02,03,...09 for month < 10
            for i in range(1, 10):
                if month == i:
                    month = "{num:02d}".format(num=i)

        if day < 10:  # formats the day variable to be 01,02,03,...09 for day < 10
            for i in range(1, 10):
                # Having 9 as the max will cause a formatting and link problem,
                # i.e. creating a folder with 07/9/xxxx instead of 07/09/xxxx
                if day == i:
                    day = "{num:02d}".format(num=i)

        print(
            "\n----------------------------------------Downloading data as of",
            str(month) + "/" + str(day) + "/" + str(year),
            "----------------------------------------",
        )

        for site_id in radar_sites:
            print('\nDownloading data from radar: "' + site_id + '"')
            page_url_base = (
                "https://www.ncdc.noaa.gov/nexradinv/bdp-download.jsp"
                "?yyyy={year}&mm={month}&dd={day}&id={site_id}&product={product}"
            )
            page_url = page_url_base.format(
                year=year, month=month, day=day, site_id=site_id, product=product
            )
            links = save_links(page_url)

            for link in links:
                download_link(link, raw_dir, [stime, etime])

            clear_files(link_dir)

    input("\nDump the files you don't need! Then hit enter\n")

    all_files = get_list_of_files(raw_dir)
    for file in all_files:
        radar = pyart.io.read(file)
        im_list = dat_to_img(radar)
        save_vis(im_list, file, im_dir)
