import tensorflow as tf
from tensorflow.keras import datasets, layers, models

import matplotlib as mpl
import matplotlib.pyplot as plt
mpl.rcParams["backend"] = "TkAgg"

(trainim, trainlb),(testim, testlb) = datasets.cifar10.load_data()
trainim, testim = trainim/255, testim/255

model = models.Sequential()
model.add(layers.Conv2D(32, (3, 3), activation='relu', input_shape=(32, 32, 3)))
model.add(layers.MaxPooling2D((2, 2)))
model.add(layers.Conv2D(64, (3, 3), activation='relu'))
model.add(layers.MaxPooling2D((2, 2)))
model.add(layers.Conv2D(64, (3, 3), activation='relu'))
model.add(layers.Flatten())
model.add(layers.Dense(64, activation='relu'))
model.add(layers.Dense(10))


model.compile(optimizer='adam', loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True), metrics=['accuracy'])

history = model.fit(trainim, trainlb, epochs=1, validation_data=(testim, testlb))

test_loss, test_acc = model.evaluate(testim,  testlb, verbose=2)

model.save_weights('meteormodel')
