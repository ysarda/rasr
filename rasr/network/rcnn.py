"""
RCNN ver 1.0
as of Apr. 24, 2022

Recurrent Convolutional Neural Network Architecture

@authors: Yash Sarda, Carson Lansdowne
"""

import os
import torch.optim as optim
import torch.nn as nn
import torch
from torchvision.datasets import ImageFolder
from torch.utils.data import DataLoader, Dataset, ConcatDataset
from torchvision.transforms import ToTensor
from torchvision import transforms
import sys
from pathlib import Path
from rasr.util.video_dataset import VideoFrameDataset, ImglistToTensor
# path_root = Path(__file__).parents[2]
# sys.path.append(str(path_root))
# print(sys.path)


# print(sys.path)
# sys.path.append(os.path.join(os.path.dirname(video_dataset.py), '../../'))


class RCNN2D(nn.Module):
    def __init__(self, ic):
        super(RCNN2D, self).__init__()

        # iw, ih, ic = input_size
        ow, oh, oc = (16, 16, 128)

        self.group1 = nn.Sequential(
            nn.Conv3d(ic, 64, kernel_size=3, padding=0),
            nn.BatchNorm3d(64),
            nn.ReLU(),
            nn.MaxPool3d(kernel_size=8, stride=3, padding=4),
        )
        self.group2 = nn.Sequential(
            nn.Conv3d(64, 128, kernel_size=6, padding=6),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool3d(kernel_size=8, stride=3, padding=4),
        )
        self.group3 = nn.Sequential(
            nn.Conv3d(128, oc, kernel_size=4, padding=0),
            nn.BatchNorm3d(oc),
            nn.ReLU(),
            nn.Conv3d(oc, oc, kernel_size=4, padding=0),
            nn.BatchNorm3d(oc),
            nn.ReLU(),
            nn.MaxPool3d(kernel_size=8, stride=3, padding=4),
        )
        self.group4 = nn.Sequential(
            nn.Conv3d(oc, oc, kernel_size=4, padding=0),
            nn.BatchNorm3d(oc),
            nn.ReLU(),
            nn.Conv3d(oc, oc, kernel_size=4, padding=0),
            nn.BatchNorm3d(oc),
            nn.ReLU(),
            nn.MaxPool3d(kernel_size=8, stride=3, padding=4),
        )
        self.group5 = nn.Sequential(
            nn.Conv3d(oc, oc, kernel_size=4, padding=0),
            nn.BatchNorm3d(oc),
            nn.ReLU(),
            nn.Conv3d(oc, oc, kernel_size=4, padding=0),
            nn.BatchNorm3d(oc),
            nn.ReLU(),
            nn.MaxPool3d(kernel_size=4, stride=2, padding=4),
        )
        self.fc1 = nn.Sequential(
            nn.Linear(ow * oh * oc, oh * oc), nn.Sigmoid())
        self.cell = torch.zeros(1, oh * oc)
        self.hidden = torch.zeros(1, oh * oc)
        self.lstm = nn.LSTMCell(oh * oc, oh * oc)
        self.fc2 = nn.Sequential(nn.Linear(oh * oc, oc), nn.Sigmoid())

    def forward(self, x):
        # x = (
        #     torch.tensor(x).permute((2, 0, 1)).unsqueeze(0).float()
        # )  # .to(device="cuda")
        print(x.shape, "input")
        x = self.group1(x)
        print(x.shape, "conv group 1")
        x = self.group2(x)
        print(x.shape, "conv group 2")
        x = self.group3(x)
        print(x.shape, "conv group 3")
        x = self.group4(x)
        print(x.shape, "conv group 4")
        x = self.group5(x)
        print(x.shape, "conv group 5")
        x = torch.flatten(x).unsqueeze(0)
        x = self.fc1(x)
        print(x.shape, "fully connected 1")
        self.hidden, self.cell = self.lstm(x, (self.hidden, self.cell))
        x = self.hidden
        print(x.shape, "lstm cell")
        x = self.fc2(x)
        print(x.shape, "fully connected 2")
        return x

    def prepare_data(train_path, test_path):
        # def collate_batch(batch):
        #     data = [item[0] for item in batch]
        #     data = pad_sequence(data, batch_first=True)
        #     targets = [item[1] for item in batch]
        #     targets = pad_sequence(torch.tensor(
        #         targets).unsqueeze(0), batch_first=True)
        #     print(data, targets[:])
        #     return data, targets

        train_annotation_file = os.path.join(train_path, 'annotations.txt')
        test_annotation_file = os.path.join(test_path, 'annotations.txt')

        train_dataset = VideoFrameDataset(
            root_path=train_path,
            annotationfile_path=train_annotation_file,
            num_segments=1,
            frames_per_segment=12,
            imagefile_template='img_{:03d}.jpg',
            transform=ImglistToTensor(),
            main_mode=True
        )

        test_dataset = VideoFrameDataset(
            root_path=test_path,
            annotationfile_path=test_annotation_file,
            num_segments=1,
            frames_per_segment=12,
            imagefile_template='img_{:03d}.jpg',
            transform=ImglistToTensor(),
            main_mode=True
        )

        sample = train_dataset[0]
        frames = sample[0]  # list of PIL images
        label = sample[1]   # integer label

        # for file in os.listdir(train_path):
        #     # load dataset
        #     print(file)
        #     d = os.path.join(train_path, file)
        #     train.append(ImageFolder((d),
        #                              transform=ToTensor()))

        # # for i in range(len(dataset_list) - 1):
        # train_dataset = ConcatDataset((train[0], train[1]))

        # test = ImageFolder(test_path, transform=ToTensor())

        # prepare data loaders
        train_dl = DataLoader(train_dataset, batch_size=1,
                              shuffle=False)
        test_dl = DataLoader(test_dataset, batch_size=2,
                             shuffle=False)

        return train_dl, test_dl

    def train_model(model, train_dl, epochs, lr):
        # define the optimization
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=lr)
        # enumerate epochs
        for epoch in range(epochs):
            # enumerate mini batches
            for inputs, targets in train_dl:
                # clear the gradients
                print(targets)
                print(inputs.shape)
                optimizer.zero_grad()
                # compute the model output
                yhat = model(inputs)
                # calculate loss
                loss = criterion(yhat, targets)
                # credit assignment
                loss.backward()
                # update model weights
                optimizer.step()
                print("target")
            print('epoch')
