import pyart

import os

import numpy as np

####################################################################

def org(vec):
    rlsp = []
    tmp = []
    index = vec[0][4]
    for dat in vec:
        x, y, z, t, n = dat
        if(n <= index):
            tmp.append([x, y, z, t])
        elif(n > index):
            index = n
            rlsp.append(tmp)
            tmp = [[x, y, z, t]]
    rlsp.append(tmp)
    return rlsp
