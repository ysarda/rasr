"""
RASR Get Test   ver 1.0
as of Jan 09, 2021

See README for details

@authors: Benjamin Miller, Robby Keh, and Yash Sarda
"""
from datetime import timedelta, date

from rasr.util.fileio import make_dir, clear_files
from rasr.get.get import run_get

import time
import resource

if __name__ == "__main__":
    time_start = time.perf_counter()
    link_dir = "links/"
    data_dir = "test/data"
    folders = [link_dir, data_dir, "test/falls", "test/vis"]
    for folder in folders:
        make_dir(folder)

    product = "AAL2"
    # Level-II data include the original three meteorological base data quantities: reflectivity, mean radial velocity,
    # and spectrum width, as well as the dual-polarization base data of differential reflectivity, correlation
    # coefficient, and differential phase.
    yri = 2022
    monthi = 3
    dayi = 21
    stime = 33000
    etime = 60000
    sites = ["KATX", "KOTX", "KRTX", "KPDT"]

    start_date = date(yri, monthi, dayi)
    # date(now.year, now.month, now.day+1)
    end_date = start_date + timedelta(1)
    date_list = [
        start_date.year,
        start_date.month,
        start_date.day,
        end_date.year,
        end_date.month,
        end_date.day,
    ]
    run_get(sites, date_list, [stime, etime], data_dir, link_dir)

    time_elapsed = time.perf_counter() - time_start
    memMb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0 / 1024.0
    print("%5.1f secs %5.1f MByte" % (time_elapsed, memMb))

    clear_files("links")
