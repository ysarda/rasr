"""
Raw to Image v2.0
as of 2025

Script for converting NOAA files to images for training

@authors: Yash Sarda, Carson Lansdowne
"""

import pyart
import sys
import os

from rasr.config import get_config
from rasr.util.fileio import get_list_of_files, make_dir
from rasr.util.unpack import dat_to_img, save_vis, save_vis_compare

if __name__ == "__main__":
    # Load configuration
    config = get_config()

    # Use command line arguments or default paths
    if len(sys.argv) >= 4:
        raw_dir = sys.argv[1]
        base_dir = sys.argv[2]
        output_dir = sys.argv[3]
    else:
        raw_dir = input("Enter raw data directory (e.g., 'training/2500/All_raw_detections/'): ").strip()
        base_dir = input("Enter base comparison directory (e.g., 'training/2500/Reflectivity/all/'): ").strip()
        output_dir = input("Enter output directory (e.g., 'training/all_fields/corrected/'): ").strip()

    # Ensure directories exist
    make_dir(output_dir)

    # Radar fields to process (prior to 2011 radar objects may not have all fields)
    fields = [
        "velocity",
        "reflectivity",
        "spectrum_width",
        # Uncomment if needed:
        # "differential_reflectivity",
        # "differential_phase",
        # "cross_correlation_ratio"
    ]

    print(f"Processing files from: {raw_dir}")
    print(f"Using base directory: {base_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Fields to process: {fields}")

    all_files = get_list_of_files(raw_dir)
    if not all_files:
        print(f"No files found in {raw_dir}")
        sys.exit(1)

    # Get comparison files for filtering
    compare_files = get_list_of_files(base_dir)
    compare_basenames = []

    for file in compare_files:
        basename = os.path.basename(file)[:-4]  # Remove extension
        compare_basenames.append(basename)

    print(f"Found {len(all_files)} files to process")
    print(f"Found {len(compare_basenames)} comparison files")

    # Process each file for each field
    for file in all_files:
        print(f"Processing: {os.path.basename(file)}")
        try:
            radar = pyart.io.read(file)

            for field in fields:
                field_output_dir = os.path.join(output_dir, field)
                make_dir(field_output_dir)

                im_list = dat_to_img(radar, field)
                save_vis_compare(im_list, file, field_output_dir, compare_basenames, field)

        except Exception as e:
            print(f"Error processing {file}: {e}")
            continue

    print("Processing complete!")
