"""
RASR Detect Test ver 3.0
as of Jan 09, 2021

See README for details

@authors: Benjamin Miller and Yash Sarda
"""
from rasr.util.fileio import get_list_of_files
from rasr.detect.detect import run_detect

if __name__ == "__main__":

    # Relevant paths, confidence value, and visualization toggle:
    fdir = "test/data/"
    outdir = "test/falls/"
    detdir = "test/vis/"
    cint = 0.75
    vis = True
    # Select True to print graphs and plots (good for debugging), and False to reduce file I/O,
    # True by default for the test function
    modelname = "RASRmodl.pth"
    files = get_list_of_files(fdir)

    print(f"File Directory: {fdir}")
    print(f"Output Directory: {outdir}")
    print(f"Visualizing: {vis}")
    print(f"Visualization Directory: {detdir}")
    print(f"Model: {modelname}")
    print(f"Confidence Level: {cint}")

    run_detect(files, outdir, detdir, cint, modelname, vis)
