"""
TORCHTRAIN ver 1.0
as of Jan 09, 2021

Training script for Py-Torch based Convolutional Neural Network Object Detection of radar data

@author: Yash Sarda
"""

from detecto.core import Model, Dataset, DataLoader
import matplotlib.pyplot as plt
import torch


########################################################

if __name__ == "__main__":

    tdataset = Dataset("training/2500/train/")  # Training dataset
    loader = DataLoader(tdataset, batch_size=2)
    vdataset = Dataset("training/2500/test/")  # Evaluation dataseet

    device = torch.device("cpu")

    model = Model(["fall"], device)

    # Keep the learning rate low, otherwise the loss will be too high
    loss = model.fit(
        loader,
        vdataset,
        epochs=15,
        learning_rate=0.001,
        gamma=0.2,
        lr_step_size=1,
        verbose=True,
    )

    plt.plot(loss)
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.show()
    model.save("RASRmodl.pth")
