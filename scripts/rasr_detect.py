"""
RASR Detect ver 3.0
as of Jan 27, 2022

See README for details

@authors: Benjamin Miller and Yash Sarda
"""

import sys
from functools import partial
from multiprocessing import Pool, cpu_count

from rasr.util.fileio import get_list_of_files
from rasr.detect.detect import run_detect

if __name__ == "__main__":

    # Relevant paths, confidence value, and visualization toggle:
    fdir = "test/data/"
    outdir = "test/falls/"
    detdir = "test/vis/"
    cint = 0.75
    vis = eval(sys.argv[2])
    # Select True to print graphs and plots (good for debugging), and False to reduce file I/O,
    # True by default for the test function
    modelname = "RASRmodl.pth"

    if len(sys.argv) > 1:
        runnum = sys.argv[1]
    else:
        runnum = cpu_count()

    print(f"Running with {runnum} process(es) in parallel")
    print(f"File Directory: {fdir}")
    print(f"Output Directory: {outdir}")
    print(f"Visualizing: {vis}")
    print(f"Visualization Directory: {detdir}")
    print(f"Model: {modelname}")
    print(f"Confidence Level: {cint}")

    allfiles = get_list_of_files(fdir)
    pool = Pool(processes=int(runnum))
    run_function_partial = partial(
        run_detect,
        outdir=outdir,
        detdir=detdir,
        cint=cint,
        modelname=modelname,
        vis=vis,
    )
    pool.map(run_function_partial, allfiles)
