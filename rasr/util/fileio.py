import os


def clearFiles(dirname):
    try:
        for file in os.listdir(dirname):
            os.remove(dirname + "/" + file)
            print("\nClearing directory {}".format(dirname))
    except FileNotFoundError:
        pass


def makeDir(dirname):
    try:
        os.mkdir(dirname)
        print("Making directory {}".format(dirname))
    except FileExistsError:
        pass


def getListOfFiles(dirname):
    listOfFile = os.listdir(dirname)
    allFiles = list()
    for entry in listOfFile:
        fullPath = os.path.join(dirname, entry)
        if os.path.isdir(fullPath):
            allFiles = allFiles + getListOfFiles(fullPath)
        else:
            allFiles.append(fullPath)
    # Reducing process size, will require mutliple iteration
    if len(allFiles) > 160:
        all_files = allFiles[:160]
    else:
        all_files = allFiles
    return all_files
