"""
Classifier Experiment ver 1.0
as of April 4, 2022

Testing ground for binary meteor fall detection

@author: Carson Lansdowne
"""

from numpy import vstack
from numpy import argmax
from pandas import read_csv
from sklearn.metrics import accuracy_score, precision_score, confusion_matrix
from torchvision.datasets import ImageFolder
import torchvision.transforms as transforms
from torchvision.transforms import Resize
from torchvision.transforms import Compose
from torchvision.transforms import ToTensor
from torchvision.transforms import Normalize
from torch.utils.data import DataLoader, Dataset
from torch.nn import Conv2d
from torch.nn import MaxPool2d
from torch.nn import Linear
from torch.nn import ReLU
from torch.nn import Softmax
from torch.nn import Module
from torch.optim import SGD
from torch.nn import CrossEntropyLoss
from torch import save
from torch import load
from torch.nn.init import kaiming_uniform_
from torch.nn.init import xavier_uniform_

# model definition


class CNN(Module):
    # define model elements
    def __init__(self, n_channels):
        super(CNN, self).__init__()
        # input to first hidden layer
        self.hidden1 = Conv2d(n_channels, 64, (6, 6))
        kaiming_uniform_(self.hidden1.weight, nonlinearity="relu")
        self.act1 = ReLU()
        # first pooling layer
        self.pool1 = MaxPool2d((8, 8), stride=(3, 3))

        # second hidden layer
        self.hidden2 = Conv2d(64, 128, (6, 6))
        kaiming_uniform_(self.hidden2.weight, nonlinearity="relu")
        self.act2 = ReLU()
        # second pooling layer
        self.pool2 = MaxPool2d((8, 8), stride=(3, 3))

        # third hidden layer
        self.hidden3 = Conv2d(128, 128, (4, 4))
        kaiming_uniform_(self.hidden2.weight, nonlinearity="relu")
        self.act3 = ReLU()
        # third pooling layer
        self.pool3 = MaxPool2d((6, 6), stride=(2, 2))

        # # fourth hidden layer
        # self.hidden4 = Conv2d(128, 128, (6, 6))
        # kaiming_uniform_(self.hidden2.weight, nonlinearity='relu')
        # self.act4 = ReLU()
        # # fourth pooling layer
        # self.pool4 = MaxPool2d((8, 8), stride=(2, 2))

        # fully connected layer
        self.hidden5 = Linear(128 * (133**2), 100)
        kaiming_uniform_(self.hidden3.weight, nonlinearity="relu")
        self.act5 = ReLU()
        # output layer
        self.hidden6 = Linear(100, 10)
        xavier_uniform_(self.hidden5.weight)
        self.act6 = Softmax(dim=1)

    # forward propagate input
    def forward(self, X):
        # print(X)
        # print('forward', X.shape)
        # input to first hidden layer
        X = self.hidden1(X)
        X = self.act1(X)
        X = self.pool1(X)
        # second hidden layer
        X = self.hidden2(X)
        X = self.act2(X)
        X = self.pool2(X)
        # third hidden layer
        X = self.hidden3(X)
        X = self.act3(X)
        X = self.pool3(X)
        # fourth hidden layer
        # X = self.hidden4(X)
        # X = self.act4(X)
        # X = self.pool4(X)
        # flatten
        # print(X.shape)
        X = X.view(-1, 128 * (133**2))
        # print(X.shape)
        # fifth hidden layer
        X = self.hidden5(X)
        # print("yay")
        X = self.act5(X)
        # output layer
        X = self.hidden6(X)
        X = self.act6(X)
        return X


# prepare the dataset


def prepare_data(train_path, test_path):
    # simple_transform = transforms.compose(
    #     [transforms.Resize()]
    # )

    # load dataset
    train = ImageFolder(train_path, transform=ToTensor())
    test = ImageFolder(test_path, transform=ToTensor())
    # prepare data loaders
    train_dl = DataLoader(train, batch_size=4, shuffle=True)
    test_dl = DataLoader(test, batch_size=4, shuffle=False)
    return train_dl, test_dl


# train the model


def train_model(train_dl, model):
    # define the optimization
    criterion = CrossEntropyLoss()
    optimizer = SGD(model.parameters(), lr=0.001, momentum=0.9)
    # enumerate epochs
    for epoch in range(3):
        # enumerate mini batches
        print(epoch)
        for i, (inputs, targets) in enumerate(train_dl):
            # clear the gradients
            # print(len(targets))
            optimizer.zero_grad()
            # compute the model output
            yhat = model(inputs)
            # calculate loss
            loss = criterion(yhat, targets)
            # credit assignment
            loss.backward()
            # update model weights
            optimizer.step()
        print("epoch")


# evaluate the model


def evaluate_model(test_dl, model):
    predictions, actuals = list(), list()
    for i, (inputs, targets) in enumerate(test_dl):
        # evaluate the model on the test set
        yhat = model(inputs)
        # retrieve numpy array
        yhat = yhat.detach().numpy()
        actual = targets.numpy()
        # convert to class labels
        yhat = argmax(yhat, axis=1)
        # reshape for stacking
        actual = actual.reshape((len(actual), 1))
        yhat = yhat.reshape((len(yhat), 1))
        # store
        predictions.append(yhat)
        actuals.append(actual)
    predictions, actuals = vstack(predictions), vstack(actuals)
    # calculate accuracy
    acc = accuracy_score(actuals, predictions)
    pre = precision_score(actuals, predictions)
    tn, fp, fn, tp = confusion_matrix(actuals, predictions).ravel()
    return acc, pre, tn, fp, fn, tp


# prepare the data
train_path = "../../Data Repo/train/"
test_path = "../../Data Repo/validation/"
train_dl, test_dl = prepare_data(train_path, test_path)
print(len(train_dl.dataset), len(test_dl.dataset))
# define the network
model = CNN(3)
model.load_state_dict(load("network/classifier_model.pth"))
# # train the model
train_model(train_dl, model)
save(model.state_dict(), "/network/classifier_model.pth")
# evaluate the model
acc, pre, tn, fp, fn, tp = evaluate_model(test_dl, model)
print("Accuracy: %.3f" % acc)
print("Precision: %.3f" % pre)
print(tn, fp, fn, tp)
