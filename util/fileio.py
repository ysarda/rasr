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


def get_list_of_files(dirname):
    list_of_files = os.listdir(dirname)
    all_files = list()
    for entry in list_of_files:
        full_path = os.path.join(dirname, entry)
        if os.path.isdir(full_path):
            all_files = all_files + get_list_of_files(full_path)
        else:
            all_files.append(full_path)
    # Reducing process size, will require mutliple iteration
    if len(all_files) > 160:
        all_files = all_files[:160]
    else:
        all_files = all_files
    return all_files
