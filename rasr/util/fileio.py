import os

def clearFiles(dirname):
    print('\nClearing directory {}'.format(dirname))
    try:
        for file in os.listdir(dirname):
            os.remove(dirname + file)
    except FileNotFoundError:
        pass

def makeDir(dirname):
    print('\nMaking directory {}'.format(dirname))
    try:
        os.mkdir(dirname)
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