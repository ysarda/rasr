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
    folders = ["archive/", "archive/" +
               today.strftime("%m:%d:%Y"), today.strftime("%m:%d:%Y")]
    for folder in folders:
        make_dir(folder)

    files = get_list_of_files("falls")

    # move output to current date folder and clear output
    for file in files:
        shutil.copy(file, today.strftime("%m:%d:%Y"))
        # copy current date folder to archive
        shutil.copy(file, "archive/" + today.strftime("%m:%d:%Y"))
        clear_files(file)

    # check old folder added and clear
    yesterdaypath = yesterday.strftime("%m:%d:%Y")

    if os.path.isfile(yesterdaypath):
        os.remove(yesterdaypath)
    print(yesterdaypath)
    # check for detections, run alert script for each one
    detections = get_list_of_files("falls/")
    # alert
