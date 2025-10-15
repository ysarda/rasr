import os


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
