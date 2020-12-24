import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    warnings.simplefilter("ignore", category=RuntimeWarning)

    import sys
    import imp
    import gc
    import os
    os.environ["PYART_QUIET"] = "1"

    import numpy as np
    import cv2
    import pyart

############################################################################

def getListOfFiles(dirName):
    listOfFile = os.listdir(dirName)
    allFiles = list()
    for entry in listOfFile:
        fullPath = os.path.join(dirName, entry)
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



############################################################################
imdir = 'all/'
redir = 'res/'
size = (1536,1536)

for file in os.scandir(imdir):
    if (file.path.endswith('.jpg')):
        img = cv2.imread(file.path)
        print('Resizing image: ', file.path)
        print('Initial shape: ', img.shape)
        res = cv2.resize(img, dsize=size, interpolation=cv2.INTER_NEAREST)
        print('Resized shape: ', res.shape)
        imname = redir + file.path[4:]
        cv2.imwrite(imname, res)
        print()
