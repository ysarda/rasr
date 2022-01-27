"""
RASR Get Test ver 1.0
as of Jan 09, 2021

See README for details

@authors: Benjamin Miller, Robby Keh, and Yash Sarda
"""
import os
from datetime import datetime, timedelta, date

from rasr.util.fileio import make_dir, clear_files
from rasr.get.scrape import save_links, download_link
from rasr.get.getdata import date_range

if __name__ == "__main__":

    folders = ["links", "test/data", "test/vis", "test/falls"]
    for folder in folders:
        make_dir(folder)

    product = "AAL2"
    # Level-II data include the original three meteorological base data quantities: reflectivity, mean radial velocity,
    # and spectrum width, as well as the dual-polarization base data of differential reflectivity, correlation
    # coefficient, and differential phase.
    now = datetime.now()
    yri = 2020
    monthi = 3
    dayi = 26
    stime = 33000
    etime = 50000
    radar_sites = ["KATX", "KOTX", "KRTX", "KPDT"]

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
            # else:
            # month = str(month)
        if day < 10:  # formats the day variable to be 01,02,03,...09 for day < 10
            for i in range(1, 10):
                # Having 9 as the max will cause a formatting and link problem,
                # i.e. creating a folder with 07/9/xxxx instead of 07/09/xxxx
                if day == i:
                    day = "{num:02d}".format(num=i)

        print("Downloading data as of", str(month) + "/" + str(day) + "/" + str(year))

        for site_id in radar_sites:
            print('Downloading data from radar: "' + site_id + '"')
            dirname = "test/data"
            linkname = "links"
            page_url_base = (
                "https://www.ncdc.noaa.gov/nexradinv/bdp-download.jsp"
                "?yyyy={year}&mm={month}&dd={day}&id={site_id}&product={product}"
            )
            page_url = page_url_base.format(
                year=year, month=month, day=day, site_id=site_id, product=product
            )
            if os.path.exists("links/data_links.txt"):
                os.remove("links/data_links.txt")
            links = save_links(page_url, linkname)

            for link in links:
                download_link(link, dirname, [stime, etime])

    clear_files("links")
