"""
TORCHTRAIN ver 1.0
as of Jan 09, 2021

Training script for Py-Torch based Convolutional Neural Network Object Detection of radar data

@author: Yash Sarda
"""

from detecto.core import Model, Dataset
import matplotlib
import matplotlib.pyplot as plt

########################################################

tdataset = Dataset('training/2500/train/')    # Training dataset
vdataset = Dataset('training/2500/test/')     # Evaluation dataseet

model = Model(['fall'])

# Keep the learning rate low, otherwise the loss will be too high
loss = model.fit(tdataset, vdataset, epochs=15, learning_rate=0.001,
                   gamma=0.2, lr_step_size=5, verbose=True)

plt.plot(loss)
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.show()
model.save('RASRmodl.pth')
