"""
RASR Detect ver 3.0
as of Jan 09, 2021

See README for details

@authors: Benjamin Miller and Yash Sarda
"""


# from matplotlib.backends.backend_agg import FigureCanvas
# from matplotlib import pyplot as plt

# import pyart

# import os

# import sys

# import numpy as np

# from multiprocessing import Pool, cpu_count

# from functools import partial

# from rasr.util.fileio import get_list_of_files

# Relevant paths, confidence value, and visualization toggle:
# fdir = "data/"
# outdir = "falls/"
# detdir = "vis/"
# cint = 0.9
# vis = False  # Select True to print graphs and plots (good for debugging), and False to reduce file I/O.
# False by default for the main function

# if __name__ == "__main__":
#     optional spec for num pool workers, else num cpu
#     if len(sys.argv) > 1:
#         runnum = sys.argv[1]
#     else:
#         runnum = cpu_count()

#     allfiles = get_list_of_files(fdir)
#     pool = Pool(processes=int(runnum))
#     run_function_partial = partial(
#         readpyart, outdir=outdir, detdir=detdir, cint=cint, vis=vis
#     )
#     pool.map(run_function_partial, allfiles)
