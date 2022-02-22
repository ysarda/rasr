# -*- coding: utf-8 -*-
"""
RASR Get ver 1.0
as of Jan 09, 2021

See README for details

@authors: Benjamin Miller and Robby Keh
"""

import os
import sys
from datetime import datetime, timedelta
from functools import partial
from multiprocessing import Pool, cpu_count

from rasr.get.get import run_get
from rasr.util.fileio import make_dir


if __name__ == "__main__":

    folders = ["links", "data", "vis", "falls"]
    for folder in folders:
        make_dir(folder)

    # Configurable Parameters
    now = datetime.now()
    today = datetime.today()
    yesterday = today - timedelta(1)

    # Get the most updated values from yesterday
    date_list = [
        yesterday.year,
        yesterday.month,
        yesterday.day,
        now.year,
        now.month,
        now.day,
    ]

    timerange = [0, 235959]

    # optional spec for num pool workers, else num cpu
    if len(sys.argv) > 1:
        run_num = sys.argv[1]
    else:
        run_num = cpu_count()

    sites = [
        ["KATX",
         "KABR",
         "KENX",
         "KABX",
         "KAMA",
         "PAHG",
         "PGUA",
         "KFFC",
         "KBBX",
         "PABC",
         "KBLX",
         "KBGM",
         "PACG",
         "KBMX",
         "KBIS",
         "KFCX",
         "KCBX",
         "KBOX",
         "KBRO",
         "KBUF",
         "KCXX",
         "RKSG",
         "KFDX",
         "KCBW",
         "KICX",
         "KGRK",
         "KCLX",
         "KRLX",
         "KCYS",
         "KLOT",
         "KILN",
         "KCLE",
         "KCAE",
         "KGWX",
         "KCRP",
         "KFTG",
         "KDMX",
         "KDTX",
         "KDDC",
         "KDOX",
         "KDLH",
         "KDYX",
         "KEYX",
         "KEPZ",
         "KLRX",
         "KBHX",
         "KVWX",
         "PAPD",
         "KFSX",
         "KSRX",
         "KFDR",
         "KHPX",
         "KPOE",
         "KEOX",
         "KFWS",
         "KAPX",
         "KGGW",
         "KGLD",
         "KMVX",
         "KGJX",
         "KGRR",
         "KTFX",
         "KGRB",
         "KGSP",
         "KUEX",
         "KHDX",
         "KHGX",
         "KHTX",
         "KIND",
         "KJKL",
         "KDGX",
         "KJAX",
         "RODN",
         "PHKM",
         "KEAX",
         "KBYX",
         "PAKC",
         "KMRX",
         "RKJK",
         "KARX",
         "KLCH",
         "KLGX",
         "KESX",
         "KDFX",
         "KILX",
         "KLZK",
         "KVTX",
         "KLVX",
         "KLBB",
         "KMQT",
         "KMXX",
         "KMAX",
         "KMLB",
         "KNQA",
         "KAMX",
         "PAIH",
         "KMAF",
         "KMKX",
         "KMPX",
         "KMBX",
         "KMSX",
         "KMOB",
         "PHMO",
         "KTYX",
         "KVAX",
         "KMHX",
         "KOHX",
         "KLIX",
         "KOKX",
         "PAEC",
         "KLNX",
         "KIWX",
         "KEVX",
         "KTLX",
         "KOAX",
         "KPAH",
         "KPDT",
         "KDIX",
         "KIWA",
         "KPBZ",
         "KSFX",
         "KGYX",
         "KRTX",
         "KPUX",
         "KDVN",
         "KRAX",
         "KUDX",
         "KRGX",
         "KRIW",
         "KJGX",
         "KDAX",
         "KMTX",
         "KSJT",
         "KEWX",
         "KNKX",
         "KMUX",
         "KHNX",
         "TJUA",
         "KSOX",
         "KATX",
         "KSHV",
         "KFSD",
         "PHKI",
         "PHWA",
         "KOTX",
         "KSGF",
         "KLSX",
         "KCCX",
         "KLWX",
         "KTLH",
         "KTBW",
         "KTWX",
         "KEMX",
         "KINX",
         "KVNX",
         "KVBX",
         "KAKQ",
         "KICT",
         "KLTX",
         "KYUX"]
    ]

    # Create storage directory
    link_dir = "../links/"
    data_dir = "../data/"

    if not os.path.exists(data_dir):
        try:
            os.mkdir(data_dir)

        except FileExistsError:
            os.chdir(data_dir)
            if os.path.exists("links/data_links.txt"):
                pass
            else:
                f = open("links/data_links.txt", "wb")

    if len(sys.argv) > 1:
        run_num = sys.argv[1]
    else:
        run_num = cpu_count()

    for site in sites:
        print(site)
    print(run_num)

    pool = Pool(processes=int(run_num))
    run_function_partial = partial(run_get,
                                   date_list=date_list,
                                   time_range=timerange,
                                   data_dir=data_dir,
                                   link_dir=link_dir)
    pool.map(run_function_partial, sites)

    #run_get(sites, date_list=date_list, time_range=timerange, data_dir=data_dir, link_dir=link_dir)
