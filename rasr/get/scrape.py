"""
RASR Scrape v1
as of Jan 17, 2022

See README for details
RASR_scrape contains functions for downloading and sorting radar data from available sources.

@authors: Benjamin Miller, Robby Keh, Yash Sarda and Carson Lansdowne
"""


import os
import requests
import time
from bs4 import BeautifulSoup, SoupStrainer


def saveLinks(page_url, dirname):
    # Record the data links on the page for this date or read already existing file
    # These will individually be pulled down and saved as files, as well as stored in a list
    link_time_num = []
    for i in range(000000, 235960):
        q = str(i).zfill(6)
        link_time_num.append(q)
    for i in enumerate(
        link_time_num
    ):  # previously for i in range(0, len(link_time_num)):
        # link_file = '{}/data_links.txt'.format(dirname)
        # link_file = '{}//data_links.txt'.format('tmp')
        link_file = "links/data_links.txt"
        a = os.getcwd()
        links = []
        # print('Writing links to {}'.format(link_file))
        response = requests.get(page_url)
        try:
            with open(link_file, "w") as f:
                for link in BeautifulSoup(
                    response.text, "html.parser", parse_only=SoupStrainer("a")
                ):
                    if (
                        link.has_attr("href")
                        and ("amazonaws" in link["href"])
                        or any(s in link for s in link_time_num)
                    ):
                        f.write("{}\n".format(link["href"]))
                        links.append(link["href"])
                        # else:
                        # print("\nThere is no link for this link:\n", link,"\n")
        except OSError:
            pass
            """
            a = (os.getcwd())
            b = (os.listdir())
            link_file = 'data_links.txt'
            with open(link_file, 'w') as f:
                for link in BeautifulSoup(response.text, 'html.parser', parse_only=SoupStrainer('a')):
                    if link.has_attr('href') and ('amazonaws' in link['href']) or any(s in link for s in link_time_num):
                        f.write('{}\n'.format(link['href']))
                        links.append(link['href'])
                        # else:
                        # print("\nThere is no link for this link:\n", link,"\n")
            """
        return links


def downloadContent(link, max_retries=5):
    # Try the url up to 5 times in case some error happens
    # Note: this is somewhat crude, as it will retry no matter what error happened
    num_retries = 0
    response = None
    while num_retries < max_retries:
        try:
            response = requests.get(link)
            break
        except Exception as e:
            print("{} errored {}: {}, retrying.".format(link, num_retries, e))
            num_retries += 1
            time.sleep(1)

    return response


def writeToFile(filename, dirname, response):
    with open(dirname + "/" + filename, "wb") as f:
        f.write(response.content)


# def download_link(link, dirname, timerange):
def downloadLink(link, dirname, timerange):
    # Grab the content from a specific radar link and save binary output to a file
    namer = link.split("links")[-1]
    # print(namer)
    namer_tmp = namer.split("_")[1]
    # if namer.split('.')[1] == 'gz': # MAJOR PROBLEM but can be fixed
    # if int(namer.split('_')[1]) in range(timerange[0], timerange[1]):
    if namer.split("_")[-1] == "MDM":
        # print('Not downloading file because of MDM summary file extension')
        # link = data_links_list[-2]
        namer = link.split("/")[-1]
        namer_tmp = namer.split("_")[1]
        pass
    elif (
        namer.split("_")[1] == "gz"
    ):  # MAJOR PROBLEM but can be fixed, some of the later files have no .gz attached, just blank
        # if int(namer.split('_')[1]) in range(timerange[0], timerange[1]):
        if int(namer_tmp.split(".")[0]) in range(timerange[0], timerange[1]):
            for downloadAttempt in range(1, 6):  # Try 5 times before raising exception
                response = downloadContent(link)
                if response:
                    break
            if not response:
                print("No response from http get")
                raise Exception  # Continue?
            # Use last part of the link as the filename (after the final slash)
            # "http://noaa-nexrad-level2.s3.amazonaws.com/2018/01/09/KABR/KABR20180109_000242_V06"
            # filename = '{}/{}'.format(dirname, link.split('/')[-1])
            # filename = '{}/{}'.format('tmp', link.split('/')[-1])
            filename = "{}/{}".format(link.split("/")[-1], ".gz")
            # print('Writing to file {}'.format(filename))
            writeToFile(filename, dirname, response)
    elif (
        namer.split(".")[0] != ""
    ):  # MAY NOT BE RIGHT for all other cases, not very robust
        # problem with this link as well http://noaa-nexrad-level2.s3.amazonaws.com/2005/01/01/KABR/NWS_NEXRAD_NXL2LG_KABR_20050101000000_20050101075959.tar
        try:
            if int(namer_tmp.split(".")[0]) in range(timerange[0], timerange[1]):
                response = downloadContent(link)
                if not response:
                    print("No response from http get")
                    raise Exception
                # Use last part of the link as the filename (after the final slash)
                # "http://noaa-nexrad-level2.s3.amazonaws.com/2018/01/09/KABR/KABR20180109_000242_V06"
                # filename = '{}/{}'.format(dirname, link.split('/')[-1])
                # filename = '{}/{}'.format('tmp', link.split('/')[-1])
                filename = link.split("/")[-1]
                # print('Writing to file {}'.format(filename))
                writeToFile(filename, dirname, response)
        except ValueError:  # This protects from the Nexrad .tar files which needs looking at
            print(
                "Not downloading due to filename extension error - '' file extension "
            )
            print(link)
            pass
    else:
        # problem with this link as well http://noaa-nexrad-level2.s3.amazonaws.com/2005/01/01/KABR/NWS_NEXRAD_NXL2LG_KABR_20050101000000_20050101075959.tar
        try:
            namer_tmp = link.split(".")[2]
            if int(namer_tmp.split("_")[4]) and int(namer_tmp.split("_")[5]) in range(
                timerange[0], timerange[1]
            ):  # for nexrad cases
                response = downloadContent(link)
                if not response:
                    print("No response from http get")
                    raise Exception
                # Use last part of the link as the filename (after the final slash)
                # "http://noaa-nexrad-level2.s3.amazonaws.com/2018/01/09/KABR/KABR20180109_000242_V06"
                # filename = '{}/{}'.format(dirname, link.split('/')[-1])
                # filename = '{}/{}'.format('tmp', link.split('/')[-1])
                filename = link.split("/")[-1]
                # print('Writing to file {}'.format(filename))
                writeToFile(filename, dirname, response)
        except ValueError:  # This protects from the Nexrad .tar files which needs looking at
            print(
                "Not downloading due to filename extension error - for all other file extensions"
            )
            print(link)
            pass
