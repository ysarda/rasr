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
    file_dir = "test/data/"
    output_dir = "test/falls/"
    vis_dir = "test/vis/"
    conf_int = 0.75
    vis = True
    # Select True to print graphs and plots (good for debugging), and False to reduce file I/O,
    # True by default for the test function
    model_name = "RASRmodl.pth"
    files = get_list_of_files(file_dir)

    print(f"File Directory: {file_dir}")
    print(f"Output Directory: {output_dir}")
    print(f"Visualizing: {vis}")
    print(f"Visualization Directory: {vis_dir}")
    print(f"Model: {model_name}")
    print(f"Confidence Level: {conf_int}")

    run_detect(files, output_dir, vis_dir, conf_int, model_name, vis)
