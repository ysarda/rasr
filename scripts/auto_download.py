"""
Auto-Downloader ver 1.0
as of Jan 09, 2021

Script for automatically downloading and converting current NOAA files to images for training

@authors: Yash Sarda
"""
import traceback
import time
from datetime import datetime, timedelta
import pyart

from rasr.get.get import run_get
from rasr.util.fileio import get_list_of_files, clear_files
from rasr.util.unpack import dat_to_img, save_vis
from rasr.util.sites import radar_sites
from multiprocessing import Pool, cpu_count
from functools import partial


def auto_download(sub_sites, delay, data_dir, images_dir, link_dir):
    next_time = time.time() + delay
    while True:
        time.sleep(max(0, next_time - time.time()))
        try:
            now = datetime.now()
            date_list = [
                now.year,
                now.month,
                now.day,
                now.year,
                now.month,
                now.day + 1,
            ]
            etime = int(datetime.now().strftime("%H%M%S"))
            stime = int((datetime.now() - timedelta(seconds=delay)).strftime("%H%M%S"))
            run_get(sub_sites, date_list, [stime, etime], data_dir, link_dir)
            all_files = get_list_of_files(data_dir)
            for file in all_files:
                radar = pyart.io.read(file)
                im_list = dat_to_img(radar, "velocity")
                save_vis(im_list, file, images_dir)
            clear_files(data_dir)
        except Exception:
            traceback.print_exc()
        next_time += (time.time() - next_time) // delay * delay + delay


if __name__ == "__main__":
    data_dir = "training/all/raw"
    images_dir = "training/all/images"
    link_dir = "links"
    product = "AAL2"
    run_num = cpu_count()
    delay = 60

    clear_files(link_dir)

    print(run_num)
    pool = Pool(processes=int(run_num))
    run_function_partial = partial(
        auto_download,
        delay=delay,
        data_dir=data_dir,
        images_dir=images_dir,
        link_dir=link_dir,
    )
    pool.map(run_function_partial, radar_sites)
