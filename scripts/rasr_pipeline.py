"""
RASR Pipeline ver 1.0
as of Jan 21, 2021

See README for details

@authors: Carson Lansdowne
"""

import shutil
from datetime import datetime, timedelta
from rasr.util.fileio import clear_files, make_dir

########################################################

if __name__ == "__main__":

    # Configurable Parameters
    now = datetime.now()
    today = datetime.today()
    yesterday = today - timedelta(1)

    folders = ["archive/", today]
    for folder in folders:
        make_dir(folder)

    output = ["data/", "falls/"]

    for file in output:
        shutil.copy(file, today)
        clear_files(file)

    shutil.copy(today, "archive/")
