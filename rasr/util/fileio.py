import os


def is_valid_nexrad_file(filename):
    """
    Check if filename is a valid NEXRAD Level II file.

    Filters out non-standard formats like _MDM (Meteorological Data Manager)
    and _SLC files that are not compatible with PyART.

    Args:
        filename: NEXRAD filename (can be full path or just filename)

    Returns:
        True if valid, False otherwise
    """
    # Extract just the filename if a full path was provided
    if os.path.sep in filename or '/' in filename:
        filename = os.path.basename(filename)

    # Must contain V06 (NEXRAD Level II format)
    if 'V06' not in filename:
        return False

    # Exclude non-standard formats
    if '_MDM' in filename:
        return False
    if '_SLC' in filename:
        return False

    return True


def clear_files(dirname):
    try:
        for file in os.listdir(dirname):
            os.remove(dirname + "/" + file)
            print("\nClearing directory: {}".format(dirname))
    except FileNotFoundError:
        pass


def make_dir(dirname):
    try:
        os.makedirs(dirname)
        print("Making directory: {}".format(dirname))
    except FileExistsError:
        pass


def get_list_of_files(dirname, limit=None):
    """
    Get list of all files in directory recursively.

    Args:
        dirname: Directory to search
        limit: Optional limit on number of files (None = no limit)

    Returns:
        List of file paths
    """
    list_of_files = os.listdir(dirname)
    all_files = list()
    for entry in list_of_files:
        full_path = os.path.join(dirname, entry)
        if os.path.isdir(full_path):
            all_files = all_files + get_list_of_files(full_path, limit=None)
        else:
            all_files.append(full_path)

    # Apply limit if specified
    if limit is not None and len(all_files) > limit:
        all_files = all_files[:limit]

    return all_files
