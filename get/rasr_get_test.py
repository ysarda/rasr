# -*- coding: utf-8 -*-
"""
Created on Thu Jan 17 12:58:28 2019
ver 1.0 as of Feb 01, 2019

See README for details

@author: Benjamin Miller and Robby
"""

import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    import os
    import sys
    from multiprocessing import Pool, cpu_count
    #import boto3
    from datetime import date, datetime, timedelta
    from getData import runFunction
    from functools import partial

if __name__ == '__main__':

    # Configurable Parameters
    if(input('Custom Date? (y/n): ') == 'y'):
        year = 2018
        month = 11
        day = 10
        timerange = [104000, 110300]
        now = datetime.strptime(str(year) + '-' + str(month) + '-' + str(day) + ' ' + str(timerange[0]),'%Y-%m-%d %H%M%S')
        today = now
        then = today + timedelta(1)

    else:
        print('Defaulting to today')
        now = datetime.now()
        today = datetime.today()
        then = today + timedelta(1)
    # Get the data for today

    # Default
    #dateList = [yesterday.year, yesterday.month, yesterday.day, now.year, now.month, now.day]
    #timerange = [0, 235959]

    # Test
    dateList = [now.year, now.month, now.day, then.year, then.month, then.day]



    # optional spec for num pool workers, else num cpu
    if len(sys.argv) > 1:
        runnum = sys.argv[1]
    else:
        runnum = cpu_count()


    sites = ['KDGX']

             #'KABR','KENX','KABX','KAMA','PAHG','PGUA','KFFC','KBBX','PABC','KBLX','KBGM','PACG','KBMX','KBIS','KFCX','KCBX','KBOX',
             #'KBRO','KBUF','KCXX','RKSG','KFDX','KCBW','KICX','KGRK','KCLX','KRLX','KCYS','KLOT','KILN','KCLE','KCAE','KGWX',
             #'KCRP','KFTG','KDMX','KDTX','KDDC','KDOX','KDLH','KDYX','KEYX','KEPZ','KLRX','KBHX','KVWX','PAPD','KFSX','KSRX',
             #'KFDR','KHPX','KPOE','KEOX','KFWS','KAPX','KGGW','KGLD','KMVX','KGJX','KGRR','KTFX','KGRB','KGSP','KUEX','KHDX',
             #'KHGX','KHTX','KIND','KJKL','KDGX','KJAX','RODN','PHKM','KEAX','KBYX','PAKC','KMRX','RKJK','KARX','KLCH','KLGX',
             #'KESX','KDFX','KILX','KLZK','KVTX','KLVX','KLBB','KMQT','KMXX','KMAX','KMLB','KNQA','KAMX','PAIH','KMAF','KMKX',
             #'KMPX','KMBX','KMSX','KMOB','PHMO','KTYX','KVAX','KMHX','KOHX','KLIX','KOKX','PAEC','KLNX','KIWX','KEVX','KTLX',
             #'KOAX','KPAH','KPDT','KDIX','KIWA','KPBZ','KSFX','KGYX','KRTX','KPUX','KDVN','KRAX','KUDX','KRGX','KRIW','KJGX',
             #'KDAX','KMTX','KSJT','KEWX','KNKX','KMUX','KHNX','TJUA','KSOX','KATX','KSHV','KFSD','PHKI','PHWA','KOTX','KSGF',
             #'KLSX','KCCX','KLWX','KTLH','KTBW','KTWX','KEMX','KINX','KVNX','KVBX','KAKQ','KICT','KLTX','KYUX']

    # Create Storage Directory CHANGE TO BACKSLASHES FOR LINUX
    dirname = os.getcwd() + "//tmp" # for windows

    if not os.path.exists(dirname):
        try:
            os.mkdir(dirname)
            #os.chdir(dirname)
            #f = open('data_links.txt', 'wb')
        except FileExistsError:
            os.chdir(dirname)
            if os.path.exists('data_links.txt'):
                pass
            else:
                f = open('data_links.txt', 'wb')

    static_dir = os.getcwd() + '//tmp'

    #runFunction(dateList, timerange, sites, static_dir)

    if len(sys.argv)>1:
        runnum = sys.argv[1]
    else:
        runnum = cpu_count()

    pool = Pool(processes=int(runnum))  # Pool(processes=#)
    #runFunctionPart = partial(runFunction)
    runFunctionPart = partial(runFunction, dateList=dateList, timerange=timerange, static_dir=static_dir)
    #pool.map(runFunction(dateList, timerange, static_dir, sites), iterable=sites)
    pool.map(runFunctionPart, sites)


    '''
    pool = Pool(processes=int(runnum))  # Pool(processes=#)
    runFunctionPart = partial(runFunction, dateList=dateList, timerange=timerange, static_dir=static_dir)
    pool.map(runFunctionPart(dateList, timerange, static_dir), iterable=sites)
    '''

    # consider deleting
    try:
        os.remove('data_links.txt')
    except:
        pass
    # Deleting the data.txt?
    print('Done')
