import os
from datetime import timedelta, date
from rasr.get.scrape import save_links, download_link


def date_range(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def run_function(sites, date_list, timerange, static_dir):

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
                "Downloading data as of", str(month) + "/" + str(day) + "/" + str(year)
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

            if sites == "all":
                radar_sites = [
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
                    "KYUX",
                ]
            else:
                radar_sites = sites

            site_id = sites
            print('Downloading data from radar: "' + site_id + '"')
            dirname = "{year}{month}{day}_{site_id}_{product}".format(
                year=year, month=month, day=day, site_id=site_id, product=product
            )
            page_url_base = (
                "https://www.ncdc.noaa.gov/nexradinv/bdp-download.jsp"
                "?yyyy={year}&mm={month}&dd={day}&id={site_id}&product={product}"
            )
            page_url = page_url_base.format(
                year=year, month=month, day=day, site_id=site_id, product=product
            )
            a = os.getcwd()

            if a == static_dir:
                pass
            else:
                os.chdir(os.getcwd() + "\\tmp")

            # Only get the last download link
            links = save_links(page_url, dirname)
            data_links_list = links
            perform_pass = False
            try:
                if len(links) == 0:
                    print(
                        "\nNot downloading data from ",
                        radar_sites,
                        "because no data available",
                    )
                    perform_pass = True
                    pass
                else:
                    link = data_links_list[len(data_links_list) - 1]
                    if link.split("_")[-1 == "MDM"]:
                        print("Ignoring MDM files")
                        link = data_links_list[len(data_links_list) - 2]
            except IndexError:
                raise Exception

            # link = data_links_list[-2] # workaround but works
            try:
                if perform_pass:
                    pass
                else:
                    download_link(link, timerange, data_links_list)
            except IndexError:
                print(link)
                raise Exception
            """
            for link in links:
                # download_link(link, dirname, timerange)
                download_link(link, timerange) - works
            # if os.stat("tmp/data_links.txt").st_size == 0:
            """

            """
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
            """
            # end for loop if still debugging 'k' 'a' 'b' 'r'

    except KeyboardInterrupt:
        site_info = "The last data downloaded was from the site:  " + site_id
        date_info = (
            "The last attempted download date was in the following format:"
            "  MONTH / DAY / YEAR:    " + str(month) + "/" + str(day) + "/" + str(year)
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
