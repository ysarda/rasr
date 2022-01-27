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
    file_dir = "test/data/"
    output_dir = "test/falls/"
    vis_dir = "test/vis/"
    conf_int = 0.75
    vis = eval(sys.argv[2])
    # Select True to print graphs and plots (good for debugging), and False to reduce file I/O,
    # True by default for the test function
    model_name = "RASRmodl.pth"

    if len(sys.argv) > 1:
        run_num = sys.argv[1]
    else:
        run_num = cpu_count()

    print(f"Running with {run_num} process(es) in parallel")
    print(f"File Directory: {file_dir}")
    print(f"Output Directory: {output_dir}")
    print(f"Visualizing: {vis}")
    print(f"Visualization Directory: {vis_dir}")
    print(f"Model: {model_name}")
    print(f"Confidence Level: {conf_int}")

    allfiles = get_list_of_files(file_dir)
    pool = Pool(processes=int(run_num))
    run_function_partial = partial(
        run_detect,
        output_dir=output_dir,
        vis_dir=vis_dir,
        conf_int=conf_int,
        model_name=model_name,
        vis=vis,
    )
    pool.map(run_function_partial, allfiles)
