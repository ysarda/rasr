import torch
import torch.nn as nn
import matplotlib.pyplot as plt
from tqdm.notebook import tqdm
from torchvision.utils import make_grid
from torch.utils.data import DataLoader

if torch.cuda.is_available():
    device = torch.device('cuda:0')
    print('Running on the GPU')
else:
    device = torch.device('cpu')
    print('Running on the CPU')


class Encoder(nn.Module):
    def __init__(
        self, in_channels=3, out_channels=16, latent_dim=200, act_fn=nn.ReLU()
    ):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 9, padding=1, stride=2),
            act_fn,
            nn.Conv2d(out_channels, out_channels, 9, padding=1, stride=2),
            act_fn,
            nn.Conv2d(out_channels, 2 * out_channels, 9, padding=1, stride=2),
            act_fn,
            nn.Conv2d(2 * out_channels, 2 * out_channels, 9, padding=1, stride=2),
            act_fn,
            nn.Conv2d(2 * out_channels, 4 * out_channels, 7, padding=1, stride=3),
            act_fn,
            nn.Conv2d(4 * out_channels, 4 * out_channels, 5, padding=1, stride=3),
            act_fn,
            nn.Flatten(),
            nn.Linear(4 * out_channels * 16 * 16, latent_dim),
            act_fn,
        )

    def forward(self, x):
        x = x.view(-1, 3, 2500, 2500)
        output = self.net(x)
        return output


class Decoder(nn.Module):
    def __init__(
        self, in_channels=3, out_channels=16, latent_dim=200, act_fn=nn.ReLU()
    ):
        super().__init__()

        self.out_channels = out_channels

        self.linear = nn.Sequential(
            nn.Linear(latent_dim, 4 * out_channels * 16 * 16), act_fn
        )

        self.conv = nn.Sequential(
            nn.ConvTranspose2d(
                4 * out_channels,
                4 * out_channels,
                5,
                padding=1,
                stride=3,
                output_padding=1,
            ),
            act_fn,
            nn.ConvTranspose2d(
                4 * out_channels,
                2 * out_channels,
                7,
                padding=1,
                stride=3,
                output_padding=1,
            ),
            act_fn,
            nn.ConvTranspose2d(
                2 * out_channels,
                2 * out_channels,
                9,
                padding=1,
                stride=2,
                output_padding=1,
            ),
            act_fn,
            nn.ConvTranspose2d(2 * out_channels, out_channels, 9, stride=2),
            act_fn,
            nn.ConvTranspose2d(
                out_channels, out_channels, 9, stride=2, output_padding=1
            ),
            act_fn,
            nn.ConvTranspose2d(
                out_channels, in_channels, 9, stride=2, output_padding=1
            ),
            nn.Sigmoid(),
        )

    def forward(self, x):
        output = self.linear(x)
        output = output.view(-1, 4 * self.out_channels, 16, 16)
        output = self.conv(output)
        return output


class Autoencoder(nn.Module):
    def __init__(self, encoder, decoder):
        super().__init__()
        self.encoder = encoder
        self.decoder = decoder

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded


class ConvolutionalAutoencoder:
    def __init__(self, autoencoder):
        self.network = autoencoder
        self.optimizer = torch.optim.Adam(self.network.parameters(), lr=1e-3)

    def train(
        self, loss_function, epochs, batch_size, training_set, validation_set, test_set
    ):
        log_dict = {
            "training_loss_per_batch": [],
            "validation_loss_per_batch": [],
            "visualizations": [],
        }

        #  defining weight initialization function
        def init_weights(module):
            if isinstance(module, nn.Conv2d):
                torch.nn.init.xavier_uniform_(module.weight)
                module.bias.data.fill_(0.01)
            elif isinstance(module, nn.Linear):
                torch.nn.init.xavier_uniform_(module.weight)
                module.bias.data.fill_(0.01)

        #  initializing network weights
        self.network.apply(init_weights)

        #  creating dataloaders
        train_loader = DataLoader(training_set, batch_size)
        val_loader = DataLoader(validation_set, batch_size)
        test_loader = DataLoader(test_set, 10)

        #  setting convnet to training mode
        self.network.train()
        self.network.to(device)

        for epoch in range(epochs):
            print(f"Epoch {epoch+1}/{epochs}")

            # ------------
            #  TRAINING
            # ------------
            print("training...")
            for images in tqdm(train_loader):
                #  zeroing gradients
                self.optimizer.zero_grad()
                #  sending images to device
                images = images.to(device)
                #  reconstructing images
                output = self.network(images)
                #  computing loss
                loss = loss_function(output, images.view(-1, 3, 32, 32))
                #  calculating gradients
                loss.backward()
                #  optimizing weights
                self.optimizer.step()

                # --------------
                # LOGGING
                # --------------
                log_dict["training_loss_per_batch"].append(loss.item())

            # --------------
            # VALIDATION
            # --------------
            print("validating...")
            for val_images in tqdm(val_loader):
                with torch.no_grad():
                    #  sending validation images to device
                    val_images = val_images.to(device)
                    #  reconstructing images
                    output = self.network(val_images)
                    #  computing validation loss
                    val_loss = loss_function(output, val_images.view(-1, 3, 32, 32))

                # --------------
                # LOGGING
                # --------------
                log_dict["validation_loss_per_batch"].append(val_loss.item())

            # --------------
            # VISUALISATION
            # --------------
            print(
                f"training_loss: {round(loss.item(), 4)} validation_loss: {round(val_loss.item(), 4)}"
            )

            for test_images in test_loader:
                #  sending test images to device
                test_images = test_images.to(device)
                with torch.no_grad():
                    #  reconstructing test images
                    reconstructed_imgs = self.network(test_images)
                    #  sending reconstructed and images to cpu to allow for visualization
                    reconstructed_imgs = reconstructed_imgs.cpu()
                    test_images = test_images.cpu()

                #  visualisation
                imgs = torch.stack(
                    [test_images.view(-1, 3, 32, 32), reconstructed_imgs], dim=1
                ).flatten(0, 1)
                grid = make_grid(imgs, nrow=10, normalize=True, padding=1)
                grid = grid.permute(1, 2, 0)
                plt.figure(dpi=170)
                plt.title("Original/Reconstructed")
                plt.imshow(grid)
                log_dict["visualizations"].append(grid)
                plt.axis("off")
                plt.show()

        return log_dict

    def autoencode(self, x):
        return self.network(x)

    def encode(self, x):
        encoder = self.network.encoder
        return encoder(x)

    def decode(self, x):
        decoder = self.network.decoder
        return decoder(x)
