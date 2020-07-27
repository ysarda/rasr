import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore",category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    warnings.simplefilter("ignore",category=RuntimeWarning)
    import os
    os.environ["PYART_QUIET"] = "1"

    import numpy as np

    import pyart

    import matplotlib
    import matplotlib.pyplot as plt
    matplotlib.use("TKagg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvas

    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import datasets, layers, models

#########################################################################

thresh = 0.8
nd = 5;
dimx,dimy = 2500,2500
xh,yh = int(dimx/nd),int(dimy/nd)

if xh == yh:
    h = xh
else:
    h = xh+yh/2

model = models.Sequential()
model.add(layers.Conv2D(h, (4, 4), activation='relu', input_shape=(xh, yh, 4)))
model.add(layers.MaxPooling2D((2, 2)))
model.add(layers.Conv2D(500, (4, 4), activation='relu'))
model.add(layers.MaxPooling2D((2, 2)))
model.add(layers.Conv2D(64, (3, 3), activation='relu'))
model.add(layers.Flatten())
model.add(layers.Dense(32, activation='relu'))
model.add(layers.Dense(1, activation = "sigmoid"))
model.summary()
#model.load_weights('meteormodel')


#def evaluate(img,radar,nd, xh, yh):
    #img = np.reshape(img, [-1, xh, yh, 4])
    #print(img.shape)
    #predict = model.predict(img)
    #print(predict)


def fracteval(img,radar,sweep):
    global thresh, xh, yh, nd
    subX = []
    for i in range(nd):
        for j in range(nd):
            subX = img[i*xh:(i+1)*xh,j*yh:(j+1)*yh]
            subX = np.reshape(subX, [-1, xh, yh, 4])
            predict = model.predict(subX)
            alt = radar.altitude['data']
            lon = radar.longitude['data']
            lat = radar.latitude['data']
            if predict > thresh:
                print('Object detected:')
                print('Longitude: ' + str(lon) + ', Latitude: ' + str(lat))
                print('Altitude: ' + str(alt[0]) + ' meters, Sweep: ' + str(sweep))



def detect():
    global thresh, xh, yh, nd
    for file in os.listdir('../testdata'):
        radar = pyart.io.read('../testdata/' + file)
        name = file[0:4]
        date = file[4:8] + '/' + file[8:10] + '/' + file[10:12] + ' ' + file[13:15] + ':' + file[15:17] + ':' + file[17:19]
        print('Checking ' + name + ' at ' + date)
        for x in range(radar.nsweeps):
            plotter = pyart.graph.RadarDisplay(radar)
            fig = plt.figure(figsize=(25,25), frameon=False)
            ax = plt.Axes(fig, [0.,0.,1.,1.])
            ax.set_axis_off()
            fig.add_axes(ax)
            plotter.set_limits(xlim=(-150, 150), ylim=(-150, 150), ax=ax)
            vmin, vmax = pyart.graph.common.parse_vmin_vmax(radar, 'velocity', None, None)
            data = plotter._get_data('velocity', x, mask_tuple=None, filter_transitions=True, gatefilter=None)

            if np.any(data)>0:
                xDat, yDat = plotter._get_x_y(x, edges=True, filter_transitions=True)
                data = data*(70/np.max(np.abs(data)))
                ax.pcolormesh(xDat, yDat, data, vmin=-70, vmax=70)
                canvas = FigureCanvas(fig)
                fig.canvas.draw()
                img = np.array(canvas.renderer.buffer_rgba())



                fracteval(img, radar, x)


            plt.cla()
            plt.clf()
            plt.close()

        input('hit enter for next site')

detect()
