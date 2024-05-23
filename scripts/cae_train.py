from rasr.network.cae import ConvolutionalAutoencoder, Autoencoder, Encoder, Decoder
from rasr.dataloaders.autoencoder_dataset import CustomAutoEncoderDataset

import torch.nn as nn

if __name__ == "__main__":
    training_dir = "data/auto/training/"
    val_dir = "data/auto/val/"
    test_dir = "data/auto/test/"

    training_data = CustomAutoEncoderDataset(training_dir)

    val_data = CustomAutoEncoderDataset(val_dir)

    test_data = CustomAutoEncoderDataset(test_dir)

    model = ConvolutionalAutoencoder(Autoencoder(Encoder(), Decoder()))

    log_dict = model.train(
        nn.MSELoss(),
        epochs=10,
        batch_size=4,
        training_set=training_data,
        validation_set=val_data,
        test_set=test_data,
    )
