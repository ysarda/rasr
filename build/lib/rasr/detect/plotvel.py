"""
PLOTVEL ver 1.0
as of Jan 09, 2021

Script for visualizing the distribution of fall velocities

@author: Yash Sarda
"""

import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    warnings.simplefilter("ignore", category=RuntimeWarning)

    import os

    import numpy as np

    import matplotlib.pyplot as plt
    from mpl_toolkits import mplot3d

####################################################################
fname = 'detect/fallvel.txt'
vel = np.loadtxt(fname)
plt.hist(vel)
plt.show()
