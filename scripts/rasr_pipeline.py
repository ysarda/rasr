"""
RASR Pipeline ver 1.0
as of Jan 21, 2021

See README for details

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

    # create archive and current date folder
    folders = ["archive/", today]
    for folder in folders:
        make_dir(folder)

    output = ["data/", "falls/"]

    # move output to current date folder and clear output
    for file in output:
        shutil.copy(file, today)
        clear_files(file)

    # copy current date folder to archive
    shutil.copy(today, "archive/")
    # check old folder added and clear
    yesterdaypath = "archive/" + yesterday.strftime()
    if os.path.isfile(yesterdaypath):
        os.remove(yesterdaypath)

    # check for detections, run alert script for each one
    detections = get_list_of_files("falls/")
    # alert
