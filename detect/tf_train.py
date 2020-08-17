import tensorflow as tf
from tensorflow.keras import datasets, layers, models

import matplotlib as mpl
import matplotlib.pyplot as plt
mpl.rcParams["backend"] = "TkAgg"

nd = 5
dim = 2500
h = int(dim/nd)

model = models.Sequential()
model.add(layers.Conv2D(h, (4, 4), activation='relu', input_shape=(h, h, 4)))
model.add(layers.MaxPooling2D((2, 2)))
model.add(layers.Conv2D(500, (4, 4), activation='relu'))
model.add(layers.MaxPooling2D((2, 2)))
model.add(layers.Conv2D(64, (3, 3), activation='relu'))
model.add(layers.Flatten())
model.add(layers.Dense(32, activation='relu'))
model.add(layers.Dense(1, activation = "sigmoid"))

model.compile(optimizer='adam', loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True), metrics=['accuracy'])

history = model.fit(trainim, trainlb, epochs=1, validation_data=(testim, testlb))

model.save_weights('rasrmodl')
