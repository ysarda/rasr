"""
Auto-Downloader ver 1.0
as of Jan 09, 2021

Script for automatically downloading and converting current NOAA files to images for training

@authors: Yash Sarda
"""

import time
from datetime import datetime, timedelta
import pyart
import resource
import multiprocessing
from multiprocessing import Pool, cpu_count
from functools import partial

from rasr.get.get import run_get
from rasr.util.fileio import get_list_of_files, clear_files
from rasr.util.unpack import dat_to_img, save_vis
from rasr.util.sites import radar_sites


def download(sub_sites, delay, data_dir, images_dir, link_dir, stime, etime, date_list):
    run_get(sub_sites, date_list, [stime, etime], data_dir, link_dir)
    all_files = get_list_of_files(data_dir)
    for file in all_files:
        radar = pyart.io.read(file)
        im_list = dat_to_img(radar, "velocity")
        save_vis(im_list, file, images_dir)
    clear_files(data_dir)


if __name__ == "__main__":
    start_time = time.time()
    data_dir = "test/raw"
    images_dir = "test/images"
    link_dir = "links"
    product = "AAL2"
    run_num = cpu_count() / 4
    delay = 300

    clear_files(link_dir)
    now = datetime.now()
    date_list = [
        now.year,
        now.month,
        now.day,
        now.year,
        now.month,
        now.day + 1,
    ]
    print(f"Current Time: {datetime.now()}")
    print(f"Checking {delay} seconds back with {run_num} processes")
    print(f"CPUs available: {multiprocessing.cpu_count()}")
    etime = int(datetime.now().strftime("%H%M%S"))
    stime = int((datetime.now() - timedelta(seconds=delay)).strftime("%H%M%S"))
    pool = Pool(processes=int(run_num))
    run_function_partial = partial(
        download,
        delay=delay,
        data_dir=data_dir,
        images_dir=images_dir,
        link_dir=link_dir,
        stime=stime,
        etime=etime,
        date_list=date_list,
    )
    pool.map(run_function_partial, radar_sites)
    pool.close()
    print(
        "--- %s megabytes ---"
        % (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000)
    )
    print("--- %s seconds ---" % (time.time() - start_time))
