from detecto.core import Model, Dataset
import matplotlib
import matplotlib.pyplot as plt

########################################################

tdataset = Dataset('../images/2500/train/')
vdataset = Dataset('../images/2500/test/')

model = Model(['fall'])

loss = model.fit(tdataset, vdataset, epochs=20, learning_rate=0.001,
                   gamma=0.2, lr_step_size=5, verbose=True)

plt.plot(loss)
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.show()
model.save('../RASRmodl.pth')
