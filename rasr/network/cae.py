import torch.nn as nn


class Encoder(nn.Module):
    def __init__(
        self, in_channels=3, out_channels=16, latent_dim=200, act_fn=nn.ReLU()
    ):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1),  # (32, 32)
            act_fn,
            nn.Conv2d(out_channels, out_channels, 3, padding=1),
            act_fn,
            nn.Conv2d(
                out_channels, 2 * out_channels, 3, padding=1, stride=2
            ),  # (16, 16)
            act_fn,
            nn.Conv2d(2 * out_channels, 2 * out_channels, 3, padding=1),
            act_fn,
            nn.Conv2d(
                2 * out_channels, 4 * out_channels, 3, padding=1, stride=2
            ),  # (8, 8)
            act_fn,
            nn.Conv2d(4 * out_channels, 4 * out_channels, 3, padding=1),
            act_fn,
            nn.Flatten(),
            nn.Linear(4 * out_channels * 8 * 8, latent_dim),
            act_fn,
        )

    def forward(self, x):
        x = x.view(-1, 3, 32, 32)
        output = self.net(x)
        return output


class Decoder(nn.Module):
    def __init__(
        self, in_channels=3, out_channels=16, latent_dim=200, act_fn=nn.ReLU()
    ):
        super().__init__()

        self.out_channels = out_channels

        self.linear = nn.Sequential(
            nn.Linear(latent_dim, 4 * out_channels * 8 * 8), act_fn
        )

        self.conv = nn.Sequential(
            nn.ConvTranspose2d(
                4 * out_channels, 4 * out_channels, 3, padding=1
            ),  # (8, 8)
            act_fn,
            nn.ConvTranspose2d(
                4 * out_channels,
                2 * out_channels,
                3,
                padding=1,
                stride=2,
                output_padding=1,
            ),  # (16, 16)
            act_fn,
            nn.ConvTranspose2d(2 * out_channels, 2 * out_channels, 3, padding=1),
            act_fn,
            nn.ConvTranspose2d(
                2 * out_channels, out_channels, 3, padding=1, stride=2, output_padding=1
            ),  # (32, 32)
            act_fn,
            nn.ConvTranspose2d(out_channels, out_channels, 3, padding=1),
            act_fn,
            nn.ConvTranspose2d(out_channels, in_channels, 3, padding=1),
        )

    def forward(self, x):
        output = self.linear(x)
        output = output.view(-1, 4 * self.out_channels, 8, 8)
        output = self.conv(output)
        return output


#  defining autoencoder
class Autoencoder(nn.Module):
    def __init__(self, encoder, decoder):
        super().__init__()
        self.encoder = encoder
        self.decoder = decoder

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded
