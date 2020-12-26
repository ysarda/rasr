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


############################################################################
imdir = '2500/'
redir = 'res/'
size = (640,640)

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
