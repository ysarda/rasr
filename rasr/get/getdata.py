import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    import os
    import requests
    import time
    from bs4 import BeautifulSoup, SoupStrainer
    from datetime import timedelta, date
    from rasr.get.scrape import *


def dateRange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + timedelta(n)


def runFunction(sites, dateList, timerange, static_dir):

    # Parse input
    origin_year = dateList[0]
    origin_month = dateList[1]
    origin_day = dateList[2]
    end_year = dateList[3]
    end_month = dateList[4]
    end_day = dateList[5]

    # Run Main
    try:
        product = 'AAL2'  # Level-II data include the original three meteorological base data quantities: reflectivity, mean radial velocity, and spectrum width,
        # as well as the dual-polarization base data of differential reflectivity, correlation coefficient, and differential phase.
        start_date = date(origin_year, origin_month, origin_day)
        end_date = date(end_year, end_month, end_day) # date(now.year, now.month, now.day+1)

        for single_date in dateRange(start_date, end_date): # --OPTION 2 DOWNLOAD WEATHER DATA FROM THE ORIGIN DATE TILL TODAY (usually run for the first time to download all the files, and then go to OPTION 2)
            dateN = single_date.strftime("%Y %m %d")
            date_arr = [int(s) for s in dateN.split() if s.isdigit()]
            year = date_arr[0]
            month = date_arr[1]
            day = date_arr[2]

            if month < 10: # formats the month to be 01,02,03,...09 for month < 10
                for i in range(1, 10):
                    if month == i:
                        month = '{num:02d}'.format(num=i)

            if day < 10: # formats the day variable to be 01,02,03,...09 for day < 10
                for i in range(1, 10):  # Having 9 as the max will cause a formatting and link problem, i.e. creating a folder with 07/9/xxxx instead of 07/09/xxxx
                    if day == i:
                        day = '{num:02d}'.format(num=i)

            print("\n")
            print("Downloading data as of", str(month) + "/" + str(day) + "/" + str(year))

            # This is a list of radar sites that have specific end dates and not among the list of "registered" radar sites,
            # usually are considered test sites or decommissioned sites: they usually start with a T for test sites,
            # the other letters for decommissioned sites

            # DAN1(05/26-2010-11/29/2016), DOP1(05/27/2010-09/30/2016),FOP1(06/09/2010-03/20/2018), KABQ(10/16/2003 - 10/23/2003),
            # KAFD(05/01/2003-05/24/2004), KBTV(03/19/2003-06/16/2003), KDOG(02/27/200-04/23/2004), KERI(01/15/2009-02/15/2017),
            # KILM(11/16/2000-03/13/2001), KJUA(02/27/2009-0826/2016), KLBF(02/01/2009-02/01/2009),KMES(02/23/2004-06/07/2004),
            # KNAW(06/08/2017-08/16/2018),LORT(03/17/2009-03/17/2009), KQYA(10/31/2017-10/31/2017), KUNR(04/26/2002-12/01/2003),
            # NOP3(10/10/2007-11/12/2014),NOP4(05/24/2010-09/29/2017),PGUM(09/16/2002-09/16/2002),ROP3(07/23/2012-01/03/2017),
            # ROP4(07/21/2010-07/30/2018),TIC(03/03/2009-03/03/2009),TJBQ(10/30/2017-06/28/2018),TJRV(10/30/2017-06/27/2018)
            # ,TLSX(03/03/2009-03/03/2009),TNAW(06/09/2017-08/16/2018),TTBW(03/03/2009-03/03/2009),KCRI(10/31/2014-10/31/2014)
            if sites == 'all':
                radarSites = ['KABR' ,'KENX', 'KABX', 'KAMA', 'PAHG', 'PGUA', 'KFFC', 'KBBX', 'PABC', 'KBLX', 'KBGM',
                              'PACG', 'KBMX', 'KBIS', 'KFCX', 'KCBX', 'KBOX',
                              'KBRO', 'KBUF', 'KCXX', 'RKSG', 'KFDX', 'KCBW', 'KICX', 'KGRK', 'KCLX', 'KRLX', 'KCYS',
                              'KLOT', 'KILN', 'KCLE', 'KCAE', 'KGWX',
                              'KCRP', 'KFTG', 'KDMX', 'KDTX', 'KDDC', 'KDOX', 'KDLH', 'KDYX', 'KEYX', 'KEPZ', 'KLRX',
                              'KBHX', 'KVWX', 'PAPD', 'KFSX', 'KSRX',
                              'KFDR', 'KHPX', 'KPOE', 'KEOX', 'KFWS', 'KAPX', 'KGGW', 'KGLD', 'KMVX', 'KGJX', 'KGRR',
                              'KTFX', 'KGRB', 'KGSP', 'KUEX', 'KHDX',
                              'KHGX', 'KHTX', 'KIND', 'KJKL', 'KDGX', 'KJAX', 'RODN', 'PHKM', 'KEAX', 'KBYX', 'PAKC',
                              'KMRX', 'RKJK', 'KARX', 'KLCH', 'KLGX',
                              'KESX', 'KDFX', 'KILX', 'KLZK', 'KVTX', 'KLVX', 'KLBB', 'KMQT', 'KMXX', 'KMAX', 'KMLB',
                              'KNQA', 'KAMX', 'PAIH', 'KMAF', 'KMKX',
                              'KMPX', 'KMBX', 'KMSX', 'KMOB', 'PHMO', 'KTYX', 'KVAX', 'KMHX', 'KOHX', 'KLIX', 'KOKX',
                              'PAEC', 'KLNX', 'KIWX', 'KEVX', 'KTLX',
                              'KOAX', 'KPAH', 'KPDT', 'KDIX', 'KIWA', 'KPBZ', 'KSFX', 'KGYX', 'KRTX', 'KPUX', 'KDVN',
                              'KRAX', 'KUDX', 'KRGX', 'KRIW', 'KJGX',
                              'KDAX', 'KMTX', 'KSJT', 'KEWX', 'KNKX', 'KMUX', 'KHNX', 'TJUA', 'KSOX', 'KATX', 'KSHV',
                              'KFSD', 'PHKI', 'PHWA', 'KOTX', 'KSGF',
                              'KLSX', 'KCCX', 'KLWX', 'KTLH', 'KTBW', 'KTWX', 'KEMX', 'KINX', 'KVNX', 'KVBX', 'KAKQ',
                              'KICT', 'KLTX', 'KYUX']
            else:
                radarSites = sites

            #for site_id in radarSites:
            #for key, site in sites.items():
            #for site in sites:
            site_id = sites
            print("Downloading data from radar: \"" + site_id + "\"")
            dirname = "{year}{month}{day}_{site_id}_{product}".format(
                year=year, month=month, day=day, site_id=site_id, product=product)
            page_url_base = ("https://www.ncdc.noaa.gov/nexradinv/bdp-download.jsp"
                             "?yyyy={year}&mm={month}&dd={day}&id={site_id}&product={product}")
            page_url = page_url_base.format(year=year, month=month, day=day,
                                            site_id=site_id, product=product)
            # page_url_base = ("https://noaa-nexrad-level2.s3.amazonaws.com/{year}/{month}/{day}/{site_id}/{site_id}{year}{month}{day}_")
            # page_url = page_url_base.format(year=year, month=str(month).zfill(2), day=str(day).zfill(2),
            #                                site_id=site_id, product=product)
            a = os.getcwd()

            try:
                if a == static_dir:
                    pass
                else:
                    os.chdir(os.getcwd() + '\\tmp')
            except:
                pass

            # Only get the last download link
            links = saveLinks(page_url, dirname)
            data_links_list = links
            perform_pass = False
            try:
                if len(links) == 0:
                    print('\nNot downloading data from ',radarSites, 'because no data available')
                    perform_pass = True
                    pass
                else:
                    link = data_links_list[len(data_links_list) - 1]
                    if link.split('_')[-1 == 'MDM']:
                        print('Ignoring MDM files')
                        link = data_links_list[len(data_links_list) - 2]
            except IndexError:
                raise Exception



            #link = data_links_list[-2] # workaround but works
            try:
                if perform_pass:
                    pass
                else:
                    downloadLink(link, timerange, data_links_list)
            except IndexError:
                print(link)
                raise Exception
            '''
            for link in links:
                # download_link(link, dirname, timerange)
                download_link(link, timerange) - works
            # if os.stat("tmp/data_links.txt").st_size == 0:
            '''

            '''
            if os.stat("data_links.txt").st_size == 0:
                print("THERE IS NO DATA AVAILABLE FOR THIS DATE\n")
                #os.remove("data_links.txt")
                open('data_links.txt', 'w').close()
            else:
                #os.remove("data_links.txt")
                open('data_links.txt', 'w').close()

            try:
                os.chdir(a)
            except FileNotFoundError:
                pass
            '''
            # end for loop if still debugging 'k' 'a' 'b' 'r'

    except KeyboardInterrupt:
        site_info = "The last data downloaded was from the site:  " + site_id
        date_info = "The last attempted download date was in the following format:" \
                    "  MONTH / DAY / YEAR:    " + str(month) + "/" + str(day) + "/" + str(year)
        note = "NOTE: Last download date usually means an incomplete download of all the weather files. " \
               "Set the new date to be one day before the last download date to ensure all files are downloaded."
        print("\n\n", site_info)
        print("\n", date_info)
        file = open("../data/last_download_date.txt", "w")
        file.write(site_info + "\n" + date_info + "\n" + note)
        file.close()
        print("\nExported the last known dates before program ended to last_download_date.txt "
              "located in the same directory as scraper.py")
        print("\nChange the origin_month, origin_day, and origin_year variables accordingly "
              "from the last_download_date.txt\n")
        print(note)

'''
def runFunction(dateList, timerange, sites):
    # Parse input
    origin_year = dateList[0]
    origin_month = dateList[1]
    origin_day = dateList[2]
    end_year = dateList[3]
    end_month = dateList[4]
    end_day = dateList[5]

    # Run Main
    try:
        product = 'AAL2'  # Level-II data include the original three meteorological base data quantities: reflectivity, mean radial velocity, and spectrum width,
        # as well as the dual-polarization base data of differential reflectivity, correlation coefficient, and differential phase.
        start_date = date(origin_year, origin_month, origin_day)
        end_date = date(end_year, end_month, end_day  )# date(now.year, now.month, now.day+1)

        for single_date in daterange(start_date, end_date): # --OPTION 2 DOWNLOAD WEATHER DATA FROM THE ORIGIN DATE TILL TODAY (usually run for the first time to download all the files, and then go to OPTION 2)
            dateN = single_date.strftime("%Y %m %d")
            date_arr = [int(s) for s in dateN.split() if s.isdigit()]
            year = date_arr[0]
            month = date_arr[1]
            day = date_arr[2]

            if month < 10: # formats the month to be 01,02,03,...09 for month < 10
                for i in range(1, 10):
                    if month == i:
                        month = '{num:02d}'.format(num=i)

            if day < 10: # formats the day variable to be 01,02,03,...09 for day < 10
                for i in range(1, 10):  # Having 9 as the max will cause a formatting and link problem, i.e. creating a folder with 07/9/xxxx instead of 07/09/xxxx
                    if day == i:
                        day = '{num:02d}'.format(num=i)

            print("\n----------------------------------------Downloading data as of", str(month) + "/" + str(day) + "/" + str(year) ,"----------------------------------------")

            # This is a list of radar sites that have specific end dates and not among the list of "registered" radar sites,
            # usually are considered test sites or decommissioned sites: they usually start with a T for test sites,
            # the other letters for decommissioned sites

            # DAN1(05/26-2010-11/29/2016), DOP1(05/27/2010-09/30/2016),FOP1(06/09/2010-03/20/2018), KABQ(10/16/2003 - 10/23/2003),
            # KAFD(05/01/2003-05/24/2004), KBTV(03/19/2003-06/16/2003), KDOG(02/27/200-04/23/2004), KERI(01/15/2009-02/15/2017),
            # KILM(11/16/2000-03/13/2001), KJUA(02/27/2009-0826/2016), KLBF(02/01/2009-02/01/2009),KMES(02/23/2004-06/07/2004),
            # KNAW(06/08/2017-08/16/2018),LORT(03/17/2009-03/17/2009), KQYA(10/31/2017-10/31/2017), KUNR(04/26/2002-12/01/2003),
            # NOP3(10/10/2007-11/12/2014),NOP4(05/24/2010-09/29/2017),PGUM(09/16/2002-09/16/2002),ROP3(07/23/2012-01/03/2017),
            # ROP4(07/21/2010-07/30/2018),TIC(03/03/2009-03/03/2009),TJBQ(10/30/2017-06/28/2018),TJRV(10/30/2017-06/27/2018)
            # ,TLSX(03/03/2009-03/03/2009),TNAW(06/09/2017-08/16/2018),TTBW(03/03/2009-03/03/2009),KCRI(10/31/2014-10/31/2014)
            if sites == 'all':
                radarSites = ['KABR' ,'KENX', 'KABX', 'KAMA', 'PAHG', 'PGUA', 'KFFC', 'KBBX', 'PABC', 'KBLX', 'KBGM',
                              'PACG', 'KBMX', 'KBIS', 'KFCX', 'KCBX', 'KBOX',
                              'KBRO', 'KBUF', 'KCXX', 'RKSG', 'KFDX', 'KCBW', 'KICX', 'KGRK', 'KCLX', 'KRLX', 'KCYS',
                              'KLOT', 'KILN', 'KCLE', 'KCAE', 'KGWX',
                              'KCRP', 'KFTG', 'KDMX', 'KDTX', 'KDDC', 'KDOX', 'KDLH', 'KDYX', 'KEYX', 'KEPZ', 'KLRX',
                              'KBHX', 'KVWX', 'PAPD', 'KFSX', 'KSRX',
                              'KFDR', 'KHPX', 'KPOE', 'KEOX', 'KFWS', 'KAPX', 'KGGW', 'KGLD', 'KMVX', 'KGJX', 'KGRR',
                              'KTFX', 'KGRB', 'KGSP', 'KUEX', 'KHDX',
                              'KHGX', 'KHTX', 'KIND', 'KJKL', 'KDGX', 'KJAX', 'RODN', 'PHKM', 'KEAX', 'KBYX', 'PAKC',
                              'KMRX', 'RKJK', 'KARX', 'KLCH', 'KLGX',
                              'KESX', 'KDFX', 'KILX', 'KLZK', 'KVTX', 'KLVX', 'KLBB', 'KMQT', 'KMXX', 'KMAX', 'KMLB',
                              'KNQA', 'KAMX', 'PAIH', 'KMAF', 'KMKX',
                              'KMPX', 'KMBX', 'KMSX', 'KMOB', 'PHMO', 'KTYX', 'KVAX', 'KMHX', 'KOHX', 'KLIX', 'KOKX',
                              'PAEC', 'KLNX', 'KIWX', 'KEVX', 'KTLX',
                              'KOAX', 'KPAH', 'KPDT', 'KDIX', 'KIWA', 'KPBZ', 'KSFX', 'KGYX', 'KRTX', 'KPUX', 'KDVN',
                              'KRAX', 'KUDX', 'KRGX', 'KRIW', 'KJGX',
                              'KDAX', 'KMTX', 'KSJT', 'KEWX', 'KNKX', 'KMUX', 'KHNX', 'TJUA', 'KSOX', 'KATX', 'KSHV',
                              'KFSD', 'PHKI', 'PHWA', 'KOTX', 'KSGF',
                              'KLSX', 'KCCX', 'KLWX', 'KTLH', 'KTBW', 'KTWX', 'KEMX', 'KINX', 'KVNX', 'KVBX', 'KAKQ',
                              'KICT', 'KLTX', 'KYUX']
            else:
                radarSites = sites
            script_path = os.path.dirname(os.path.realpath(__file__))

            for site_id in radarSites:
                if os.path.exists(site_id):
                    pass
                else:
                    make_directory(site_id)  # destination folder, path should be on the same directory as the script
                print("\nDownloading data from radar: \"" + site_id + "\"")
                dirname = "{year}{month}{day}_{site_id}_{product}".format(
                    year=year, month=month, day=day, site_id=site_id, product=product)
                os.chdir(site_id)
                if os.path.exists(dirname):
                    pass
                else:
                    make_directory(dirname)  # Data folder, path should be the directory of the Site_id folder
                page_url_base = ("https://www.ncdc.noaa.gov/nexradinv/bdp-download.jsp"
                                 "?yyyy={year}&mm={month}&dd={day}&id={site_id}&product={product}")
                page_url = page_url_base.format(year=year, month=month, day=day,
                                                site_id=site_id, product=product)
                # page_url_base = ("https://noaa-nexrad-level2.s3.amazonaws.com/{year}/{month}/{day}/{site_id}/{site_id}{year}{month}{day}_")
                # page_url = page_url_base.format(year=year, month=str(month).zfill(2), day=str(day).zfill(2),
                #                                site_id=site_id, product=product)
                links = save_links(page_url, dirname)
                for link in links:
                    download_link(link, dirname, timerange)
                os.chdir(dirname)
                if os.stat("data_links.txt").st_size == 0:
                    print("THERE IS NO DATA AVAILABLE FOR THIS DATE\n")
                    os.remove("data_links.txt")
                    os.chdir("..")
                    os.rmdir(dirname)
                    print("Deleted", dirname, 'because it has no data\n')
                else:
                    os.remove("data_links.txt")
                os.chdir(script_path)
                if not os.listdir(site_id):
                    os.rmdir(site_id)
    except KeyboardInterrupt:
        site_info = "The last data downloaded was from the site:  " + site_id
        date_info = "The last attempted download date was in the following format:" \
                    "  MONTH / DAY / YEAR:    " + str(month) + "/" + str(day) + "/" + str(year)
        note = "NOTE: Last download date usually means an incomplete download of all the weather files. " \
               "Set the new date to be one day before the last download date to ensure all files are downloaded."
        print("\n\n", site_info)
        print("\n", date_info)
        os.chdir(script_path)
        file = open("last_download_date.txt", "w")
        file.write(site_info + "\n" + date_info + "\n" + note)
        file.close()
        print("\nExported the last known dates before program ended to last_download_date.txt "
              "located in the same directory as scraper.py")
        print("\nChange the origin_month, origin_day, and origin_year variables accordingly "
              "from the last_download_date.txt\n")
        print(note)



import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore",category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    import os
    import sys
    from multiprocessing import Pool, cpu_count
    import boto3
    import datetime
    from functools import partial
'''

'''
def getData(site, keylist):
    # https://www.nsstc.uah.edu/users/brian.freitag/AWS_Radar_with_Python.html
    # Set up Amazon AWS connections for client and environment

    s3conn = boto3.client(
        's3',
        aws_access_key_id=str(keylist[0]),
        aws_secret_access_key=str(keylist[1])
    )
    # use boto to connect to the immediate AWS nexrad bucket list for the current date
    # now = datetime.datetime.utcnow()
    # date = ("{:4d}".format(now.year) + '/' + "{:02d}".format(now.month) + '/' +
    #        "{:02d}".format(now.day) + '/'+str(site)+'/')
    date = '2009/02/15/KFWS/'

    # get the most recent data for the selected site (if site exists)
    objs = s3conn.list_objects_v2(Bucket='noaa-nexrad-level2', Prefix=date, Delimiter='/')
    if 'Contents' in objs:
        last_added = max(objs['Contents'], key=lambda x: x['LastModified'])
        # check that we dont use _MDM files
        if not last_added['Key'].endswith("_MDM"):
            # Get name
            fname = '2009/02/15/KFWS/KFWS20090215_165332_V03.gz'
            # fname = last_added['Key']
            printname = fname.split('/')[-1]
            printname = printname[0:19]
            localfile = os.getcwd() + "/tmp/" + printname
            # Confirm new file
            if not os.path.exists(localfile):
                # get file and store to temporary file for analysis (cannot direct load in current version)
                obj = boto3.resource('s3').Bucket('noaa-nexrad-level2').Object(fname)
                with open(localfile, 'wb') as data:
                    obj.download_fileobj(data)
                    # localfile.close() is implicit with "with" structure
                # os.remove(localfile.name)
'''
