from detecto.core import Model, Dataset, DataLoader
from detecto.visualize import plot_prediction_grid
from detecto.utils import read_image
import matplotlib
from matplotlib import pyplot as plt
from matplotlib import patches
import os

########################################################
cint = 0.8
imdir = 'test/set/'
detdir = 'test/detections/'
model = Model.load('RASRmodl.pth', ['fall'])
i = 0;
for file in os.scandir(imdir):
    if (file.path.endswith('.jpg')):
        print('Evaluating: ' + file.path[len(imdir):])
        i += 1
        image = read_image(file.path)
        dpi = matplotlib.rcParams['figure.dpi']
        pred = model.predict(image)
        height, width, nbands = image.shape
        figsize = width / float(dpi), height / float(dpi)
        fig = plt.figure(figsize=figsize)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis('off')
        for n in range(len(pred[1])):
            if(pred[2][n] > cint):
                print('Detection!')
                ax.imshow(image)
                x,y,x1,y1 = float(pred[1][n][0]),float(pred[1][n][1]),float(pred[1][n][2]),float(pred[1][n][3])
                w,h = abs(x-x1),abs(y-y1)
                rect = patches.Rectangle((x,y),w,h,linewidth=1,edgecolor='r',facecolor='none')
                ax.add_patch(rect)
                detstr = pred[0][n] + ': ' + str(round(float(pred[2][n]),2))
                plt.text(x+w/2,y-5,detstr, fontsize = 8, color='red', ha='center')
                name = detdir + file.path[len(imdir):-4] + '_detected' + '.jpg'
                plt.savefig(name, bbox_inches='tight')
