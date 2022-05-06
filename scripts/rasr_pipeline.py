"""
RASR Pipeline ver 1.0
as of Jan 21, 2022

Script for porting all detections and processed radar data into separate archives

@authors: Carson Lansdowne
"""

import os
import shutil
from datetime import datetime, timedelta
from rasr.util.fileio import clear_files, get_list_of_files, make_dir

########################################################

if __name__ == "__main__":

    # Configurable Parameters
    now = datetime.now()
    today = datetime.today()
    yesterday = today - timedelta(1)

    # create archive
    folders = ["/work/07965/clans/ls6/Spring_RASR/rasr/archive/", "/work/07965/clans/ls6/Spring_RASR/rasr/archive/" +
               today.strftime("%m:%d:%Y"), "/work/07965/clans/ls6/Spring_RASR/rasr/" + today.strftime("%m:%d:%Y")]
    for folder in folders:
        make_dir(folder)

    # get falls
    fall_files = get_list_of_files(
        "/work/07965/clans/ls6/Spring_RASR/rasr/falls/")

    # get vis
    vis_files = get_list_of_files(
        "/work/07965/clans/ls6/Spring_RASR/rasr/vis/")

    # move output to current date folder and clear output
    for file in vis_files:
        shutil.copy(file, today.strftime("%m:%d:%Y") + "/vis/")
        # copy current date folder to archive
        shutil.copy(
            file, "/work/07965/clans/ls6/Spring_RASR/rasr/archive/" + today.strftime("%m:%d:%Y") + "/vis")
    clear_files("/work/07965/clans/ls6/Spring_RASR/rasr/vis/")
    for file in fall_files:
        shutil.copy(file, today.strftime("%m:%d:%Y") + "/falls/")
        # copy current date folder to archive
        shutil.copy
            file, "/work/07965/clans/ls6/Spring_RASR/rasr/archive/" + today.strftime("%m:%d:%Y") + "/falls")
    clear_files("/work/07965/clans/ls6/Spring_RASR/rasr/falls/")

    # check old folder added and clear
    yesterdaypath = yesterday.strftime("%m:%d:%Y")

    if os.path.isdir("/work/07965/clans/ls6/Spring_RASR/rasr/" + yesterdaypath):
        shutil.rmtree(
            "/work/07965/clans/ls6/Spring_RASR/rasr/" + yesterdaypath)
        print(yesterdaypath + " removed")
    # check for detections, run alert script for each one
    detections = get_list_of_files("falls/")
    # alert
