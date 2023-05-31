"""
RASR Detect ver 3.0
as of Jan 27, 2022

See README for details

@authors: Benjamin Miller and Yash Sarda
"""

import sys
from functools import partial
from torch.multiprocessing import Pool, set_start_method, cpu_count

try:
    set_start_method("spawn")
except RuntimeError:
    pass

from rasr.util.fileio import get_list_of_files
from rasr.detect.detect import run_detect

if __name__ == "__main__":
    # Relevant paths, confidence value, and visualization toggle:
    file_dir = "data/"
    output_dir = "falls/"
    vis_dir = "vis/"
    conf_int = 0.75
    vis = True
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

    allfiles = [get_list_of_files(file_dir)]
    pool = Pool(processes=int(run_num))
    run_function_partial = partial(
        run_detect,
        file_dir=file_dir,
        output_dir=output_dir,
        vis_dir=vis_dir,
        conf_int=conf_int,
        model_name=model_name,
        vis=vis,
    )
    pool.map(run_function_partial, allfiles)
