import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    warnings.simplefilter("ignore", category=RuntimeWarning)

    import matplotlib
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvas
    from matplotlib import pyplot as plt
    from matplotlib import patches
    matplotlib.use("TKagg")

    import pyart

    import os

    import numpy as np

    from kinematics import org
    from jsonoutput import jsonsquare, jsonpoint, stringed
    from torchdet import detectvis
########################################################


def readpyart(file, outdir, detdir):
    #file = file[len(fdir):]
    radar = pyart.io.read(fdir + file)
    name, m, d, y, hh, mm, ss, date = stringed(file)
    print('Checking ' + name + ' at ' + date)
    r, dr, allr = [], [], []
    for x in range(radar.nsweeps):
        plotter = pyart.graph.RadarDisplay(radar)
        fig = plt.figure(figsize=(25, 25), frameon=False)
        ax = plt.Axes(fig, [0., 0., 1., 1.])
        fig.add_axes(ax)
        plotter.set_limits(xlim=(-250, 250), ylim=(-250, 250), ax=ax)
        data = plotter._get_data('velocity', x, mask_tuple=None, filter_transitions=True, gatefilter=None)
        if np.any(data) > 0:
            xDat, yDat = plotter._get_x_y(x, edges=True, filter_transitions=True)
            data = data * (70 / np.max(np.abs(data)))
            ax.pcolormesh(xDat, yDat, data)
            canvas = FigureCanvas(fig)
            fig.canvas.draw()
            img = np.array(canvas.renderer.buffer_rgba())
            img = np.delete(img, 3, 2)
            sweepangle = str(format(radar.fixed_angle['data'][x], ".2f"))
            print('Reading Velocity at sweep angle: ', sweepangle)
            t = radar.time['data'][x]
            locDat = [xDat, yDat, t]
            v = detectvis(radar, img, file, locDat, sweepangle, detdir)
            if v is not None:
                vc, vall = v
                vc.append(x)
                r.append(vc)
                allr.append(vall)
            plt.cla()
            plt.clf()
            plt.close('all')
    if(len(r) >= 2):
        rlsp = org(r)
        jsonsquare(file, radar, allr, outdir)
        #jsonpoint(file, radar, r, outdir)


##########################################################
fdir = 'test/raw/'
detdir = 'test/detections/'
outdir = 'test/out/'

try:
    for file in os.listdir(outdir):
        os.remove(outdir + file)
except FileNotFoundError:
    pass
for file in os.listdir(fdir):
    readpyart(file, outdir, detdir)
