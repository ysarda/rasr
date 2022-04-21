"""
RCNN ver 1.0
as of Jan 31, 2022

Recurrent Convolutional Neural Network Architecture

@authors: Yash Sarda
"""

import torch
import torch.nn as nn
import torch.optim as optim


class RCNN2D(nn.Module):
    def __init__(self, input_size=(2500, 2500, 3), output_size=(16, 16, 128)):
        super(RCNN2D, self).__init__()

        iw, ih, ic = input_size
        ow, oh, oc = output_size

        self.group1 = nn.Sequential(
            nn.Conv2d(ic, 64, kernel_size=6, padding=0),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=(8, 8), stride=(3, 3)),
        )
        self.group2 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=6, padding=0),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=(8, 8), stride=(3, 3)),
        )
        self.group3 = nn.Sequential(
            nn.Conv2d(128, 128, kernel_size=4, padding=0),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.Conv2d(128, 128, kernel_size=4, padding=0),
            nn.BatchNorm2d(128),
            nn.Conv2d(128, oc, kernel_size=4, padding=0),
            nn.BatchNorm2d(oc),
            nn.ReLU(),
            nn.Conv2d(oc, oc, kernel_size=4, padding=0),
            nn.BatchNorm2d(oc),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=(6, 6), stride=(3, 3)),
        )
        self.group4 = nn.Sequential(
            nn.Conv2d(128, 128, kernel_size=4, padding=0),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.Conv2d(128, 128, kernel_size=4, padding=0),
            nn.BatchNorm2d(128),
            nn.Conv2d(oc, oc, kernel_size=4, padding=0),
            nn.BatchNorm2d(oc),
            nn.ReLU(),
            nn.Conv2d(oc, oc, kernel_size=4, padding=0),
            nn.BatchNorm2d(oc),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=(4, 4), stride=(2, 2)),
        )
        self.group5 = nn.Sequential(
            nn.Conv2d(oc, oc, kernel_size=4, padding=0),
            nn.BatchNorm2d(oc),
            nn.ReLU(),
            nn.Conv2d(oc, oc, kernel_size=4, padding=0),
            nn.BatchNorm2d(oc),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=(4, 4), stride=(2, 2)),
        )
        self.fc1 = nn.Sequential(
            nn.Linear(ow * oh * oc, oh * oc), nn.Sigmoid())
        self.cell = torch.zeros(1, oh * oc)
        self.hidden = torch.zeros(1, oh * oc)
        self.lstm = nn.LSTMCell(oh * oc, oh * oc)
        self.fc2 = nn.Sequential(nn.Linear(oh * oc, oc), nn.Sigmoid())

    def forward(self, x):
        x = (
            torch.tensor(x).permute((2, 0, 1)).unsqueeze(0).float()
        )  # .to(device="cuda")
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
        # load dataset
        train = ImageFolder(train_path, transform=ToTensor())
        test = ImageFolder(test_path, transform=ToTensor())
        # prepare data loaders
        train_dl = DataLoader(train, batch_size=2, shuffle=True)
        test_dl = DataLoader(test, batch_size=2, shuffle=False)
        return train_dl, test_dl

    def train_model(train_dl, model, epochs, lr):
        # define the optimization
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=lr)
        # enumerate epochs
        for epoch in range(epochs):
            # enumerate mini batches
            for i, (inputs, targets) in enumerate(train_dl):
                # clear the gradients
                print(len(targets))
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
