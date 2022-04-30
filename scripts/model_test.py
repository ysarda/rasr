"""
CNN Test ver 1.0
as of Jan 21, 2022

Model Testing Script

@authors: Yash Sarda
"""

import pyart

from rasr.util.fileio import get_list_of_files
from rasr.util.unpack import dat_to_img
from rasr.network.rcnn import RCNN2D
import torch

if __name__ == "__main__":

    raw_dir = "data/"
    # model = RCNN2D(3)  # .to("cuda")

    # set radar field
    field = 'reflectivity'

    # all_files = get_list_of_files(raw_dir)
    # for file in all_files[0:1]:
    #     radar = pyart.io.read(file)
    #     im_list = dat_to_img(radar, field)
    #     for img, _, _ in im_list[0:1]:
    #         img2 = model.forward(img)

    # prepare the data
    train_path = 'training/Time_Series/Train'
    test_path = 'training/Time_Series/Test'
    train_dl, test_dl = RCNN2D.prepare_data(train_path, test_path)
    print(len(train_dl.dataset), len(test_dl.dataset))
    # define the network
    model = RCNN2D(6)
    # define hyperparameters
    epoch = 2
    lr = .001
    # # train the model
    RCNN2D.train_model(model, train_dl, epoch, lr)
    torch.save(model.state_dict(), 'lstm_model.pth')
    # evaluate the model
    # acc = evaluate_model(test_dl, model)
    # print('Accuracy: %.3f' % acc)
