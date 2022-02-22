from datetime import timedelta, date

from rasr.get.scrape import save_links, download_link
from rasr.util.fileio import clear_files


def date_range(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def run_get(sites, date_list, time_range, data_dir, link_dir):

    # Parse input
    origin_year = date_list[0]
    origin_month = date_list[1]
    origin_day = date_list[2]
    end_year = date_list[3]
    end_month = date_list[4]
    end_day = date_list[5]

    # Run Main
    try:
        product = "AAL2"
        # Level-II data include the original three meteorological base data quantities: reflectivity,
        # mean radial velocity, and spectrum width, as well as the dual-polarization base data of differential
        # reflectivity, correlation coefficient, and differential phase.
        start_date = date(origin_year, origin_month, origin_day)
        end_date = date(
            end_year, end_month, end_day
        )  # date(now.year, now.month, now.day+1)

        for single_date in date_range(start_date, end_date):
            # --OPTION 2 DOWNLOAD WEATHER DATA FROM THE ORIGIN DATE TILL TODAY (usually run for the first time to
            # download all the files, and then go to OPTION 2)
            date_n = single_date.strftime("%Y %m %d")
            date_arr = [int(s) for s in date_n.split() if s.isdigit()]
            year = date_arr[0]
            month = date_arr[1]
            day = date_arr[2]

            if month < 10:  # formats the month to be 01,02,03,...09 for month < 10
                for i in range(1, 10):
                    if month == i:
                        month = "{num:02d}".format(num=i)

            if day < 10:  # formats the day variable to be 01,02,03,...09 for day < 10
                for i in range(1, 10):
                    # Having 9 as the max will cause a formatting and link problem,
                    # i.e. creating a folder with 07/9/xxxx instead of 07/09/xxxx
                    if day == i:
                        day = "{num:02d}".format(num=i)

            print("\n")
            print(
                "\n----------------------------------------Downloading data as of",
                str(month) + "/" + str(day) + "/" + str(year),
                "----------------------------------------",
            )

            # This is a list of radar sites that have specific end dates and not among the list of "registered" radar
            # sites, usually are considered test sites or decommissioned sites: they usually start with a T for test
            # sites, the other letters for decommissioned sites

            # DAN1(05/26-2010-11/29/2016), DOP1(05/27/2010-09/30/2016),FOP1(06/09/2010-03/20/2018),
            # KABQ(10/16/2003 - 10/23/2003), KAFD(05/01/2003-05/24/2004), KBTV(03/19/2003-06/16/2003),
            # KDOG(02/27/200-04/23/2004), KERI(01/15/2009-02/15/2017), KILM(11/16/2000-03/13/2001),
            # KJUA(02/27/2009-0826/2016), KLBF(02/01/2009-02/01/2009),KMES(02/23/2004-06/07/2004),
            # KNAW(06/08/2017-08/16/2018),LORT(03/17/2009-03/17/2009), KQYA(10/31/2017-10/31/2017),
            # KUNR(04/26/2002-12/01/2003), NOP3(10/10/2007-11/12/2014),NOP4(05/24/2010-09/29/2017),
            # PGUM(09/16/2002-09/16/2002),ROP3(07/23/2012-01/03/2017), ROP4(07/21/2010-07/30/2018),
            # TIC(03/03/2009-03/03/2009),TJBQ(10/30/2017-06/28/2018),TJRV(10/30/2017-06/27/2018),
            # TLSX(03/03/2009-03/03/2009),TNAW(06/09/2017-08/16/2018),TTBW(03/03/2009-03/03/2009),KCRI(10/31/2014-10/31/2014)

            #radar_sites = sites

            for site_id in sites:
                print('\nDownloading data from radar: "' + site_id + '"')
                page_url_base = (
                    "https://www.ncdc.noaa.gov/nexradinv/bdp-download.jsp"
                    "?yyyy={year}&mm={month}&dd={day}&id={site_id}&product={product}"
                )
                print(page_url_base)
                page_url = page_url_base.format(
                    year=year, month=month, day=day, site_id=site_id, product=product
                )
                print(page_url)
                links = save_links(page_url)

                for link in links:
                    download_link(link, data_dir, time_range)

                clear_files(link_dir)

    except KeyboardInterrupt:
        site_info = "The last data downloaded was from the site:  " + site_id
        date_info = (
            "The last attempted download date was in the following format:"
            "  MONTH / DAY / YEAR:    " +
            str(month) + "/" + str(day) + "/" + str(year)
        )
        note = (
            "NOTE: Last download date usually means an incomplete download of all the weather files. "
            "Set the new date to be one day before the last download date to ensure all files are downloaded."
        )
        print("\n\n", site_info)
        print("\n", date_info)
        file = open("../data/last_download_date.txt", "w")
        file.write(site_info + "\n" + date_info + "\n" + note)
        file.close()
        print(
            "\nExported the last known dates before program ended to last_download_date.txt "
            "located in the same directory as scraper.py"
        )
        print(
            "\nChange the origin_month, origin_day, and origin_year variables accordingly "
            "from the last_download_date.txt\n"
        )
        print(note)
