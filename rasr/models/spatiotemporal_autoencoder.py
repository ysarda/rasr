"""
Spatio-Temporal Autoencoder for Meteorite Fall Anomaly Detection

Architecture:
1. Spatial Encoder: Multi-branch 2D-CNN for each radar field
2. Temporal Encoder: Bidirectional LSTM over sweep sequences
3. Temporal Decoder: LSTM decoder
4. Spatial Decoder: Per-field 2D-CNN decoders
5. Anomaly Scoring: Reconstruction error + temporal prediction error
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Dict


class SpatialEncoder(nn.Module):
    """
    Encodes a single radar sweep across multiple fields.

    Separate CNN branches for each field, with late fusion.

    Args:
        num_fields: Number of radar fields (e.g., 3 for velocity/reflectivity/spectrum_width)
        image_size: Input image size (H, W)
        latent_dim: Dimension of spatial latent representation
    """

    def __init__(self, num_fields: int = 3, image_size: Tuple[int, int] = (128, 128), latent_dim: int = 512):
        super().__init__()
        self.num_fields = num_fields
        self.latent_dim = latent_dim

        # Separate encoder branch for each field
        self.field_encoders = nn.ModuleList([
            self._build_encoder_branch() for _ in range(num_fields)
        ])

        # Fusion layer to combine field representations
        self.fusion = nn.Sequential(
            nn.Linear(latent_dim * num_fields, latent_dim * 2),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(latent_dim * 2, latent_dim)
        )

    def _build_encoder_branch(self):
        """Build a single encoder branch for one radar field."""
        return nn.Sequential(
            # Input: (1, H, W); for H=W=128: (1, 128, 128)
            nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3),   # (64, 64, 64)
            nn.BatchNorm2d(64),
            nn.ReLU(),

            nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1),  # (128, 32, 32)
            nn.BatchNorm2d(128),
            nn.ReLU(),

            nn.Conv2d(128, 256, kernel_size=3, stride=2, padding=1),  # (256, 16, 16)
            nn.BatchNorm2d(256),
            nn.ReLU(),

            nn.Conv2d(256, 512, kernel_size=3, stride=2, padding=1),  # (512, 8, 8)
            nn.BatchNorm2d(512),
            nn.ReLU(),

            nn.AdaptiveAvgPool2d((8, 8)),  # (512, 8, 8) — keep spatial structure
            nn.Flatten(),                  # (8192,)
            nn.Linear(512 * 8 * 8, self.latent_dim),  # learned spatial compression
            nn.ReLU()
        )

    def forward(self, x):
        """
        Encode a single sweep with multiple fields.

        Args:
            x: Tensor of shape (batch_size, num_fields, H, W)

        Returns:
            Spatial latent representation of shape (batch_size, latent_dim)
        """
        batch_size = x.size(0)

        # Process each field separately
        field_features = []
        for field_idx in range(self.num_fields):
            field_input = x[:, field_idx:field_idx+1, :, :]  # (B, 1, H, W)
            field_feat = self.field_encoders[field_idx](field_input)  # (B, latent_dim)
            field_features.append(field_feat)

        # Concatenate and fuse
        concatenated = torch.cat(field_features, dim=1)  # (B, latent_dim * num_fields)
        fused = self.fusion(concatenated)  # (B, latent_dim)

        return fused


class SpatialDecoder(nn.Module):
    """
    Decodes spatial latent representation back to multi-field sweep.

    Args:
        num_fields: Number of radar fields to reconstruct
        image_size: Target image size (H, W)
        latent_dim: Dimension of spatial latent representation
    """

    def __init__(self, num_fields: int = 3, image_size: Tuple[int, int] = (128, 128), latent_dim: int = 512):
        super().__init__()
        self.num_fields = num_fields
        self.image_size = image_size
        self.latent_dim = latent_dim

        # Project latent to each field's spatial feature map
        self.initial_size = 8  # spatial bottleneck resolution (8x8)
        self.projection = nn.Sequential(
            nn.Linear(latent_dim, latent_dim * 2),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(latent_dim * 2, latent_dim * self.initial_size * self.initial_size * num_fields)
        )

        # Separate decoder branch for each field
        self.field_decoders = nn.ModuleList([
            self._build_decoder_branch() for _ in range(num_fields)
        ])

    def _build_decoder_branch(self):
        """Build a single decoder branch for one radar field.

        Number of upsampling layers is determined by image_size and initial_size so
        this works for any supported image resolution (64, 128, 256, …).
        """
        import math
        c = self.latent_dim
        num_layers = int(math.log2(self.image_size[0] // self.initial_size))

        # Channel schedule: halve each layer, minimum 8
        ch = [c]
        for _ in range(num_layers - 1):
            ch.append(max(ch[-1] // 2, 8))
        ch.append(1)  # final output

        layers = []
        for i in range(num_layers):
            in_ch, out_ch = ch[i], ch[i + 1]
            is_last = (i == num_layers - 1)
            layers.append(nn.ConvTranspose2d(
                in_ch, out_ch,
                kernel_size=7 if is_last else 3,
                stride=2,
                padding=3 if is_last else 1,
                output_padding=1
            ))
            layers.append(nn.Tanh() if is_last else nn.Sequential(nn.BatchNorm2d(out_ch), nn.ReLU()))

        return nn.Sequential(*layers)

    def forward(self, z):
        """
        Decode spatial latent representation to multi-field sweep.

        Args:
            z: Latent tensor of shape (batch_size, latent_dim)

        Returns:
            Reconstructed sweep of shape (batch_size, num_fields, H, W)
        """
        batch_size = z.size(0)

        # Project and split for each field
        projected = self.projection(z)  # (B, latent_dim * initial_size * initial_size * num_fields)
        field_size = self.latent_dim * self.initial_size * self.initial_size
        field_latents = projected.split(field_size, dim=1)  # List of (B, field_size)

        # Decode each field
        field_outputs = []
        for field_idx in range(self.num_fields):
            # Reshape to spatial feature map — different values at each position
            field_z = field_latents[field_idx].view(batch_size, self.latent_dim, self.initial_size, self.initial_size)

            # Decode
            field_out = self.field_decoders[field_idx](field_z)  # (B, 1, H, W)
            field_outputs.append(field_out)

        # Stack fields
        output = torch.cat(field_outputs, dim=1)  # (B, num_fields, H, W)

        return output


class SpatioTemporalAutoencoder(nn.Module):
    """
    Full spatio-temporal autoencoder for radar sequence anomaly detection.

    Args:
        num_fields: Number of radar fields (default: 3)
        image_size: Image size (H, W) (default: 512x512)
        spatial_latent_dim: Spatial encoding dimension (default: 512)
        temporal_hidden_dim: LSTM hidden dimension (default: 256)
        max_sweeps: Maximum sequence length (default: 12)
    """

    def __init__(
        self,
        num_fields: int = 3,
        image_size: Tuple[int, int] = (128, 128),
        spatial_latent_dim: int = 512,
        temporal_hidden_dim: int = 256,
        max_sweeps: int = 12
    ):
        super().__init__()

        self.num_fields = num_fields
        self.spatial_latent_dim = spatial_latent_dim
        self.temporal_hidden_dim = temporal_hidden_dim
        self.max_sweeps = max_sweeps

        # Spatial encoder/decoder
        self.spatial_encoder = SpatialEncoder(num_fields, image_size, spatial_latent_dim)
        self.spatial_decoder = SpatialDecoder(num_fields, image_size, spatial_latent_dim)

        # Temporal encoder (bidirectional LSTM)
        self.temporal_encoder = nn.LSTM(
            input_size=spatial_latent_dim,
            hidden_size=temporal_hidden_dim,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
            dropout=0.3
        )

        # Temporal decoder (unidirectional LSTM)
        self.temporal_decoder = nn.LSTM(
            input_size=temporal_hidden_dim * 2,  # Bidirectional encoder output
            hidden_size=spatial_latent_dim,
            num_layers=2,
            batch_first=True,
            dropout=0.3
        )

    def forward(self, x, mask=None):
        """
        Forward pass through the autoencoder.

        Args:
            x: Input tensor of shape (batch_size, max_sweeps, num_fields, H, W)
            mask: Boolean mask of shape (batch_size, max_sweeps) for valid sweeps

        Returns:
            reconstruction: Reconstructed input of same shape as x
            latent: Temporal latent representation
        """
        batch_size, max_sweeps, num_fields, H, W = x.shape

        # Encode all sweeps in one batched CNN call instead of a Python loop
        x_flat = x.view(batch_size * max_sweeps, num_fields, H, W)       # (B*T, F, H, W)
        feats_flat = self.spatial_encoder(x_flat)                          # (B*T, latent_dim)
        spatial_features = feats_flat.view(batch_size, max_sweeps, -1)    # (B, T, latent_dim)

        # Temporal encoding
        if mask is not None:
            lengths = mask.sum(dim=1).cpu()
            packed = nn.utils.rnn.pack_padded_sequence(
                spatial_features, lengths, batch_first=True, enforce_sorted=False
            )
            temporal_encoded, _ = self.temporal_encoder(packed)
            temporal_encoded, _ = nn.utils.rnn.pad_packed_sequence(
                temporal_encoded, batch_first=True, total_length=max_sweeps
            )
        else:
            temporal_encoded, _ = self.temporal_encoder(spatial_features)

        # Temporal decoding
        temporal_decoded, _ = self.temporal_decoder(temporal_encoded)  # (B, T, latent_dim)

        # Decode all sweeps in one batched CNN call
        td_flat = temporal_decoded.reshape(batch_size * max_sweeps, -1)   # (B*T, latent_dim)
        recon_flat = self.spatial_decoder(td_flat)                         # (B*T, F, H, W)
        reconstruction = recon_flat.view(batch_size, max_sweeps, num_fields, H, W)

        return reconstruction, temporal_encoded

    def compute_anomaly_score(self, x, reconstruction, mask=None):
        """
        Compute per-sweep anomaly scores based on reconstruction error.

        Returns per-sweep scores so that individual anomalous sweeps aren't
        diluted by averaging with normal ones. Downstream consumers can
        aggregate (max, mean, threshold count) as needed.

        Args:
            x: Original input (B, max_sweeps, num_fields, H, W)
            reconstruction: Reconstructed input (same shape)
            mask: Valid sweep mask (B, max_sweeps)

        Returns:
            per_sweep_scores: Tensor of shape (B, max_sweeps) with per-sweep anomaly scores
                              (invalid sweeps are set to 0)
            sample_scores: Tensor of shape (B,) with max per-sweep score per sample
        """
        # Compute per-pixel MSE, masked to non-zero signal pixels only
        mse = (x - reconstruction) ** 2  # (B, max_sweeps, num_fields, H, W)
        signal_mask = (x != 0).float()

        # Per-sweep masked MSE: average only over non-zero pixels
        masked_mse = (mse * signal_mask).sum(dim=[2, 3, 4])  # (B, max_sweeps)
        pixel_counts = signal_mask.sum(dim=[2, 3, 4]).clamp(min=1)  # (B, max_sweeps)
        per_sweep_scores = masked_mse / pixel_counts  # (B, max_sweeps)

        # Zero out invalid sweeps
        if mask is not None:
            per_sweep_scores = per_sweep_scores * mask.float()

        # Sample-level score: max across sweeps (catches single anomalous sweep)
        if mask is not None:
            # Use -inf for invalid sweeps so they don't affect max
            masked_scores = per_sweep_scores.masked_fill(~mask, float('-inf'))
            sample_scores = masked_scores.max(dim=1).values
            # Handle fully-masked samples
            sample_scores = sample_scores.clamp(min=0)
        else:
            sample_scores = per_sweep_scores.max(dim=1).values

        return per_sweep_scores, sample_scores


# Testing
if __name__ == "__main__":
    # Create model
    model = SpatioTemporalAutoencoder(
        num_fields=3,
        image_size=(128, 128),
        spatial_latent_dim=512,
        temporal_hidden_dim=256,
        max_sweeps=12
    )

    print(f"Model created with {sum(p.numel() for p in model.parameters()):,} parameters")

    # Test forward pass
    batch_size = 2
    dummy_input = torch.randn(batch_size, 12, 3, 128, 128)
    dummy_mask = torch.ones(batch_size, 12, dtype=torch.bool)
    dummy_mask[:, 10:] = False  # Last 2 sweeps are padding

    reconstruction, latent = model(dummy_input, dummy_mask)

    print(f"\nInput shape: {dummy_input.shape}")
    print(f"Reconstruction shape: {reconstruction.shape}")
    print(f"Latent shape: {latent.shape}")

    # Compute anomaly scores
    per_sweep_scores, sample_scores = model.compute_anomaly_score(dummy_input, reconstruction, dummy_mask)
    print(f"Per-sweep scores shape: {per_sweep_scores.shape}")
    print(f"Sample scores shape: {sample_scores.shape}")
    print(f"Sample scores: {sample_scores}")
