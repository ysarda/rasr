"""
OUTPUT ver 1.0
as of March 3, 2022

Converts any relevant data into useful/displayable file types for ASTRIAGraph

@author: Yash Sarda, Carson Lansdowne
"""

import geojson
from geojson import Point, Feature, FeatureCollection, dump

import numpy as np

#####################################################################################################


def point_out(file, r, output_dir):
    for det in r:
        lat, lon, alt, t, sweep = det
        t_rounded = str(t)[:-4]
        name, dt_str = string_convert(file)

        print(
            "Detection: "
            + str(float(lat))
            + " degrees North,"
            + " "
            + str(float(lon))
            + " degrees West,"
            + " "
            + str(alt)
            + " m above sea level, at "
            + t_rounded
        )

        point = Point((int(-lon), int(lat), int(alt)))
        features = []
        features.append(Feature(geometry=point))
        feature_collection = FeatureCollection(features)

        file_name = output_dir + name + dt_str + "-" + str(sweep) + ".geojson"
        with open(file_name, "a+") as outfile:
            dump(feature_collection, outfile)


def square_out(file, all_r, output_dir):
    for det in all_r:
        lat0, lon0, lat1, lon1, alt, t, w, h = det
        t_rounded = str(t)[:-4]
        name, _, _, dt_str = string_convert(file)

        print(
            "Detection centered at: "
            + str(round(float(lat0 + lat1) / 2, 4))
            + " degrees North,"
            + " "
            + str(round(float(lon0 + lon1) / 2, 4))
            + " degrees West,"
            + " "
            + str(alt)
            + " m above sea level, at "
            + t_rounded
        )
        data = {}
        data[t_rounded] = []
        data[t_rounded].append(
            {
                "Altitude (m)": str(alt),
                "Longitude0 (NW)(deg East)": str(lon0),
                "Latitude0 (NW)(deg North)": str(lat0),
                "Longitude1 (SE)(deg East)": str(lon1),
                "Latitude1 (SE)(deg North)": str(lat1),
                "Width of Detection Box (m East-West)": str(w),
                "Height of Detection Box (m North-South)": str(h)
            }
        )
        file_name = output_dir + name + dt_str + ".json"
        with open(file_name, "a+") as out_file:
            geojson.dump(data, out_file)


def string_convert(file):
    radar_name = file[0:4]
    m, d, y, hh, mm, ss = (
        file[8:10],
        file[10:12],
        file[4:8],
        file[13:15],
        file[15:17],
        file[17:19],
    )
    date = m + "/" + d + "/" + y
    b_time = m + "/" + d + "/" + y + " " + hh + ":" + mm + ":" + ss
    dt_str = m + d + y + "-" + hh + mm + ss
    return radar_name, date, b_time, dt_str


def text_out(prop, file, output_dir):
    name, _, _, dt_str = string_convert(file)
    file_name = file_name = output_dir + name + dt_str + ".csv"
    np.savetxt(file_name, prop, delimiter=",")
