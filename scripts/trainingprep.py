"""
Training Preparation ver 1.0
as of Jan 09, 2021

Script for downloading and converting NOAA files to images for training

@authors: Yash Sarda
"""


import os

os.environ["PYART_QUIET"] = "1"

import time
from datetime import datetime, timedelta, date

from rasr.get.scrape import saveLinks, downloadLink
from rasr.get.getdata import dateRange
from rasr.util.fileio import getListOfFiles, clearFiles
from rasr.util.unpack import datToImg

########################################################################################################################

if __name__ == "__main__":

    clearFiles("links/")
    start_time = time.time()

    product = "AAL2"  # Level-II data include the original three meteorological base data quantities: reflectivity, mean radial velocity, and spectrum width,
    # as well as the dual-polarization base data of differential reflectivity, correlation coefficient, and differential phase.
    now = datetime.now()
    man = input("Manual Input? (y/n): ")
    if man == "y":
        yri = int(input("Year: "))
        monthi = int(input("Month: "))
        dayi = int(input("Day: "))
        stime = int(input("Start Time: ") + "00")
        etime = int(input("End Time: ") + "00")
        nsites = int(input("Number of Sites: "))
        radarSites = []
        for i in range(1, nsites + 1):
            text = "Site " + str(i) + ": "
            s = input(text)
            radarSites.append(s)
    else:
        yri = 2017
        monthi = 2
        dayi = 6
        stime = 72000
        etime = 72200
        radarSites = ["KMKX"]

    start_date = date(yri, monthi, dayi)
    end_date = start_date + timedelta(1)  # date(now.year, now.month, now.day+1)

    for single_date in dateRange(start_date, end_date):
        date = single_date.strftime("%Y %m %d")
        date_arr = [int(s) for s in date.split() if s.isdigit()]
        year = date_arr[0]
        month = date_arr[1]
        day = date_arr[2]

        if month < 10:  # formats the month to be 01,02,03,...09 for month < 10
            for i in range(1, 10):
                if month == i:
                    month = "{num:02d}".format(num=i)
            # else:
            # month = str(month)
        if day < 10:  # formats the day variable to be 01,02,03,...09 for day < 10
            for i in range(
                1, 10
            ):  # Having 9 as the max will cause a formatting and link problem, i.e. creating a folder with 07/9/xxxx instead of 07/09/xxxx
                if day == i:
                    day = "{num:02d}".format(num=i)

        print(
            "\n----------------------------------------Downloading data as of",
            str(month) + "/" + str(day) + "/" + str(year),
            "----------------------------------------",
        )

        for site_id in radarSites:
            print('\nDownloading data from radar: "' + site_id + '"')
            dirname = "raw"
            linkname = "../links"
            page_url_base = (
                "https://www.ncdc.noaa.gov/nexradinv/bdp-download.jsp"
                "?yyyy={year}&mm={month}&dd={day}&id={site_id}&product={product}"
            )
            page_url = page_url_base.format(
                year=year, month=month, day=day, site_id=site_id, product=product
            )
            print(page_url)
            links = saveLinks(page_url, linkname)

            for link in links:
                downloadLink(link, dirname, stime, etime)

            if os.path.exists("../links/data_links.txt"):
                os.remove("../links/data_links.txt")

    input("\nDump the files you don't need\n")

    cpath = os.getcwd()
    rawdir = cpath + "training/raw/"
    imdir = cpath + "training/im/"
    all_files = getListOfFiles(rawdir)
    for file in all_files:
        print("Reading file: ", file)
        datToImg(file, imdir)
