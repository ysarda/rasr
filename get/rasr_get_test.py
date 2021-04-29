"""
RASR Get Test ver 1.0
as of Jan 09, 2021

See README for details

@authors: Benjamin Miller, Robby Keh, and Yash Sarda
"""

import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    warnings.simplefilter("ignore", category=RuntimeWarning)

    import sys
    import imp
    import gc
    import os
    os.environ["PYART_QUIET"] = "1"

    import numpy as np

    import requests
    import time
    from bs4 import BeautifulSoup, SoupStrainer
    from datetime import datetime, timedelta, date

#########################################################################################################################


def make_directory(dirname):
    print('\nMaking directory {}'.format(dirname))
    try:
        os.mkdir(dirname)
    except FileExistsError:
        pass


def save_links(page_url, dirname):
    link_time_num = []
    for i in range(0, 235960):
        q = str(i).zfill(6)
        link_time_num.append(q)
    # previously for i in range(0, len(link_time_num)):
    for i in enumerate(link_time_num):
        link_file = '{}/data_links.txt'.format(dirname)
        # Either read a file if we've already downloaded
        if os.path.isfile(link_file):
            print('Using links stored in {}'.format(link_file))
            with open(link_file, 'r') as f:
                links = f.read().splitlines()
        else:  # Or read from the page and record the links
            links = []
            print('Writing links to {}'.format(link_file))
            response = requests.get(page_url)
            with open(link_file, 'w') as f:
                for link in BeautifulSoup(response.text, 'html.parser', parse_only=SoupStrainer('a')):
                    # if link.has_attr('href') and ('amazonaws' in link['href']) and ('2018' in link['href']):
                    # if link.has_attr('href') and ('amazonaws' in link['href']
                    # if link.has_attr('href') and ('amazonaws' in link['href'] and any(s in link for s in link_time_num)):
                    if link.has_attr('href') and ('amazonaws' in link['href']) or any(s in link for s in link_time_num):
                        f.write('{}\n'.format(link['href']))
                        links.append(link['href'])
                        # print(link)
                    # else:
                    # print("\nThere is no link for this link:\n", link,"\n")
        return links


def download_content(link, max_retries=5):
    # Try the url up to 5 times in case some error happens
    # Note: this is somewhat crude, as it will retry no matter what error happened
    num_retries = 0
    response = None
    while num_retries < max_retries:
        try:
            response = requests.get(link)
            break
        except Exception as e:
            print('{} errored {}: {}, retrying.'.format(link, num_retries, e))
            num_retries += 1
            time.sleep(1)

    return response


def write_to_file(filename, response):
    with open(filename, 'wb') as f:
        f.write(response.content)


def download_link(link, dirname, stime, etime):
    '''Grab the content from a specific radar link and save binary output to a file'''

    response = download_content(link)
    if not response:
        raise Exception
    # Use last part of the link as the filename (after the final slash)
    # "http://noaa-nexrad-level2.s3.amazonaws.com/2018/01/09/KABR/KABR20180109_000242_V06"
    filename = '{}/{}'.format(dirname, link.split('/')[-1])
    t = int(filename[23:29])
    if(stime < t < etime and filename[-3:] != 'MDM'):
        print('Writing to file {}'.format(filename))
        write_to_file(filename, response)


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)

def getListOfFiles(dirName):
    listOfFile = os.listdir(dirName)
    allFiles = list()
    for entry in listOfFile:
        fullPath = os.path.join(dirName, entry)
        if os.path.isdir(fullPath):
            allFiles = allFiles + getListOfFiles(fullPath)
        else:
            allFiles.append(fullPath)
    # Reducing process size, will require mutliple iteration
    if len(allFiles) > 160:
        all_files = allFiles[:160]
    else:
        all_files = allFiles
    return all_files


########################################################################################################################
folders = ['links','test/data','test/vis','test/falls']
for folder in folders:
    if not os.path.exists(folder):
        os.makedirs(folder)

product = 'AAL2'  # Level-II data include the original three meteorological base data quantities: reflectivity, mean radial velocity, and spectrum width,
# as well as the dual-polarization base data of differential reflectivity, correlation coefficient, and differential phase.
now = datetime.now()
yri = 2020
monthi = 3
dayi = 26
stime = 33000
etime = 50000
radarSites = ["KATX","KOTX","KRTX","KPDT"]


start_date = date(yri, monthi, dayi)
end_date = start_date + timedelta(1)  # date(now.year, now.month, now.day+1)

for single_date in daterange(start_date, end_date):
    date = single_date.strftime("%Y %m %d")
    date_arr = [int(s) for s in date.split() if s.isdigit()]
    year = date_arr[0]
    month = date_arr[1]
    day = date_arr[2]

    if month < 10:  # formats the month to be 01,02,03,...09 for month < 10
        for i in range(1, 10):
            if month == i:
                month = '{num:02d}'.format(num=i)
        # else:
            # month = str(month)
    if day < 10:  # formats the day variable to be 01,02,03,...09 for day < 10
        for i in range(1, 10):  # Having 9 as the max will cause a formatting and link problem, i.e. creating a folder with 07/9/xxxx instead of 07/09/xxxx
            if day == i:
                day = '{num:02d}'.format(num=i)

    print("Downloading data as of", str(month) +
          "/" + str(day) + "/" + str(year))

    for site_id in radarSites:
        print("Downloading data from radar: \"" + site_id + "\"")
        dirname = "test/data"
        linkname = "links"
        page_url_base = ("https://www.ncdc.noaa.gov/nexradinv/bdp-download.jsp"
                         "?yyyy={year}&mm={month}&dd={day}&id={site_id}&product={product}")
        page_url = page_url_base.format(year=year, month=month, day=day,
                                        site_id=site_id, product=product)
        if os.path.exists('links/data_links.txt'):
          os.remove('links/data_links.txt')
        links = save_links(page_url, linkname)

        for link in links:
            download_link(link, dirname, stime, etime)
