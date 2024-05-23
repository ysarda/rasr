"""
CNN Test ver 1.0
as of Jan 21, 2022

Model Testing Script

@authors: Yash Sarda
"""

from torchvision import transforms
import matplotlib.pyplot as plt
from PIL import Image


from rasr.network.cae import ConvolutionalAutoencoder, Autoencoder, Encoder, Decoder
from rasr.util.fileio import get_list_of_files

if __name__ == "__main__":
    im_dir = "test/images/"
    convert_tensor = transforms.ToTensor()

    model = ConvolutionalAutoencoder(Autoencoder(Encoder(), Decoder()))

    all_files = get_list_of_files(im_dir)
    for file in all_files:
        input = convert_tensor(Image.open(file))
        output = model.autoencode(input)
        print(input)
        plt.imshow(input.permute(1, 2, 0))
        plt.show()
        print(output)
        plt.imshow(output.squeeze().permute(1, 2, 0).detach().numpy())
        plt.show()
        break
