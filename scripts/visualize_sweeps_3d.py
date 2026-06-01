"""
3D visualization of all sweeps in a NEXRAD radar file.

Plots each sweep's gate positions in Cartesian (x, y, z) space,
colored by a radar field, with a marker at the radar location.
Uses plotly for GPU-accelerated WebGL rendering in the browser.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pyart
import plotly.graph_objects as go


def main():
    parser = argparse.ArgumentParser(
        description="Visualize all sweeps of a NEXRAD file in 3D Cartesian space"
    )
    parser.add_argument("file", type=str, help="Path to a NEXRAD Level II radar file")
    parser.add_argument(
        "--field",
        type=str,
        default="reflectivity",
        help="Radar field to color by (default: reflectivity)",
    )
    parser.add_argument(
        "--max-range-km",
        type=float,
        default=150.0,
        help="Maximum range in km to plot (default: 150)",
    )
    parser.add_argument(
        "--downsample",
        type=int,
        default=2,
        help="Plot every Nth gate to reduce point count (default: 2)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Save figure as HTML to this path instead of opening in browser",
    )
    args = parser.parse_args()

    radar_path = Path(args.file)
    if not radar_path.exists():
        print(f"Error: file not found: {radar_path}")
        sys.exit(1)

    print(f"Reading {radar_path.name} ...")
    radar = pyart.io.read(str(radar_path))

    # Resolve field name
    field_name = _resolve_field(args.field, radar)
    if field_name is None:
        available = list(radar.fields.keys())
        print(f"Error: field '{args.field}' not found. Available: {available}")
        sys.exit(1)

    print(
        f"Plotting {radar.nsweeps} sweeps, field={field_name}, "
        f"max_range={args.max_range_km} km, downsample={args.downsample}"
    )

    max_range_m = args.max_range_km * 1000.0
    ds = args.downsample

    fig = go.Figure()

    for sweep_idx in range(radar.nsweeps):
        sweep_slice = radar.get_slice(sweep_idx)
        elevation = radar.elevation["data"][sweep_slice]
        azimuth = radar.azimuth["data"][sweep_slice]
        ranges = radar.range["data"]

        # Limit range first, then downsample
        range_mask = ranges <= max_range_m
        r_cut = ranges[range_mask]

        if len(r_cut) == 0 or len(azimuth) == 0:
            continue

        field_data = radar.fields[field_name]["data"][sweep_slice]
        field_cut = field_data[:, range_mask]

        # Downsample both axes
        az_sub = azimuth[::ds]
        el_sub = elevation[::ds]
        r_sub = r_cut[::ds]
        field_sub = field_cut[::ds, ::ds]
        if hasattr(field_sub, "mask"):
            field_sub = np.ma.filled(field_sub, np.nan)

        # Broadcast to (rays, gates)
        az_rad = np.deg2rad(az_sub)[:, np.newaxis]
        el_rad = np.deg2rad(el_sub)[:, np.newaxis]
        r = r_sub[np.newaxis, :]

        # Spherical -> Cartesian (x=east, y=north, z=up)
        x = r * np.cos(el_rad) * np.sin(az_rad)
        y = r * np.cos(el_rad) * np.cos(az_rad)
        z = r * np.sin(el_rad)

        # Flatten and filter
        xf = (x.ravel() / 1000).astype(np.float32)
        yf = (y.ravel() / 1000).astype(np.float32)
        zf = (z.ravel() / 1000).astype(np.float32)
        cf = field_sub.ravel().astype(np.float32)
        valid = np.isfinite(cf) & (cf != 0)
        if not valid.any():
            continue

        elev_angle = radar.fixed_angle["data"][sweep_idx]
        fig.add_trace(
            go.Scatter3d(
                x=xf[valid],
                y=yf[valid],
                z=zf[valid],
                mode="markers",
                marker=dict(
                    size=1.5,
                    color=cf[valid],
                    colorscale="Viridis",
                    opacity=0.7,
                    colorbar=dict(title=field_name) if sweep_idx == 0 else None,
                    showscale=(sweep_idx == 0),
                ),
                name=f"{elev_angle:.1f}\u00b0",
                hovertemplate=(
                    f"Sweep {elev_angle:.1f}\u00b0<br>"
                    "E: %{x:.1f} km<br>N: %{y:.1f} km<br>"
                    "Alt: %{z:.1f} km<br>"
                    f"{field_name}: " + "%{marker.color:.1f}<extra></extra>"
                ),
            )
        )

    # Radar at origin
    fig.add_trace(
        go.Scatter3d(
            x=[0], y=[0], z=[0],
            mode="markers",
            marker=dict(size=8, color="red", symbol="diamond"),
            name="Radar",
            hovertemplate="Radar<extra></extra>",
        )
    )

    station = radar_path.parent.name or radar_path.stem
    fig.update_layout(
        title=f"{station} \u2014 {radar_path.name} ({field_name})",
        scene=dict(
            xaxis_title="East (km)",
            yaxis_title="North (km)",
            zaxis_title="Altitude (km)",
            aspectmode="data",
        ),
        legend=dict(itemsizing="constant"),
    )

    if args.output:
        fig.write_html(args.output)
        print(f"Saved to {args.output}")
    else:
        fig.show()


def _resolve_field(name, radar):
    """Map a common field name to whatever key exists in this radar file."""
    aliases = {
        "reflectivity": ["reflectivity", "REF", "DBZ", "reflectivity_horizontal"],
        "velocity": ["velocity", "VEL", "radial_velocity"],
        "spectrum_width": ["spectrum_width", "SW", "WIDTH"],
        "cross_correlation_ratio": [
            "cross_correlation_ratio", "RHOHV", "RHO", "correlation_coefficient",
        ],
        "differential_reflectivity": [
            "differential_reflectivity", "ZDR", "diff_reflectivity",
        ],
        "differential_phase": ["differential_phase", "PHIDP", "diff_phase"],
    }

    if name in radar.fields:
        return name

    for variants in aliases.get(name, []):
        if variants in radar.fields:
            return variants

    return None


if __name__ == "__main__":
    main()
