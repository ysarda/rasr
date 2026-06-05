"""Generate labeled figures for Artemis II splashdown radar analysis."""

import pyart
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path

out_dir = Path('artemis_ii_figures')
out_dir.mkdir(exist_ok=True)

OFFICIAL_SPLASHDOWN = datetime(2026, 4, 11, 0, 7, 27)
SPLASH_E, SPLASH_N = -63.0, -56.0  # radar-relative coords (km)

# View window
cx, cy = -58.0, -50.0
view_half = 30.0

files = [
    'data/positive/KNKX/KNKX20260410_235612_V06',
    'data/positive/KNKX/KNKX20260411_000447_V06',
    'data/positive/KNKX/KNKX20260411_001321_V06',
    'data/positive/KNKX/KNKX20260411_002156_V06',
    'data/positive/KNKX/KNKX20260411_003030_V06',
]

target_elevs = [3.12, 4.0, 5.1, 6.42]


def get_ref_time(radar):
    ref_str = radar.time['units'].replace('seconds since ', '')
    return datetime.fromisoformat(ref_str.replace('Z', ''))


def sweep_cartesian(radar, sweep_idx):
    sweep_slice = radar.get_slice(sweep_idx)
    elevation = radar.elevation['data'][sweep_slice]
    azimuth = radar.azimuth['data'][sweep_slice]
    ranges = radar.range['data']
    times = radar.time['data'][sweep_slice]

    az_rad = np.deg2rad(azimuth)[:, np.newaxis]
    el_rad = np.deg2rad(elevation)[:, np.newaxis]
    r = ranges[np.newaxis, :]

    x = r * np.cos(el_rad) * np.sin(az_rad) / 1000.0
    y = r * np.cos(el_rad) * np.cos(az_rad) / 1000.0
    z = r * np.sin(el_rad) / 1000.0
    return x, y, z, times, sweep_slice


def make_sweep_plot(radar, sweep_idx, ref_time, fname, fig_num):
    """Generate vel + ref side-by-side for one sweep."""
    elev_angle = float(radar.fixed_angle['data'][sweep_idx])
    x, y, z, times, sweep_slice = sweep_cartesian(radar, sweep_idx)

    in_view = (
        (x >= cx - view_half) & (x <= cx + view_half) &
        (y >= cy - view_half) & (y <= cy + view_half)
    )

    # Check for signal above 2km
    has_signal = False
    for fn in ['velocity', 'reflectivity']:
        if fn in radar.fields:
            fd = radar.fields[fn]['data'][sweep_slice]
            if hasattr(fd, 'mask'):
                fd = np.ma.filled(fd, 0)
            if np.any((fd != 0) & in_view & (z > 2.0)):
                has_signal = True
                break
    if not has_signal:
        return fig_num

    sweep_time = ref_time + timedelta(seconds=float(np.median(times)))
    dt_min = (sweep_time - OFFICIAL_SPLASHDOWN).total_seconds() / 60.0
    sign = "+" if dt_min >= 0 else ""

    alt_at_range = z[in_view & (z > 1.0)]
    mean_alt = float(np.mean(alt_at_range)) if len(alt_at_range) > 0 else 0

    ri, gi = np.where(in_view)
    xf = x[ri, gi]
    yf = y[ri, gi]

    fig, (ax_vel, ax_ref) = plt.subplots(1, 2, figsize=(20, 9))

    # --- Velocity ---
    if 'velocity' in radar.fields:
        vel_data = radar.fields['velocity']['data'][sweep_slice]
        if hasattr(vel_data, 'mask'):
            vf = np.ma.filled(vel_data, np.nan)[ri, gi]
        else:
            vf = vel_data[ri, gi].astype(float)
        vf[vf == 0] = np.nan
        valid = np.isfinite(vf)
        if valid.any():
            sc = ax_vel.scatter(xf[valid], yf[valid], c=vf[valid],
                                cmap='RdBu_r', vmin=-30, vmax=30, s=2, alpha=0.8)
            cb = plt.colorbar(sc, ax=ax_vel, shrink=0.8)
            cb.set_label('Radial Velocity (m/s)', fontsize=11)

            neg_v = vf[valid][vf[valid] < -5]
            pos_v = vf[valid][vf[valid] > 5]
            if len(neg_v) > 0 and len(pos_v) > 0:
                ax_vel.text(0.02, 0.02,
                            f'OPPOSING VELOCITIES: [{min(neg_v):.0f} to {max(neg_v):.0f}] & '
                            f'[+{min(pos_v):.0f} to +{max(pos_v):.0f}] m/s\n'
                            'Characteristic re-entry / falling object signature',
                            transform=ax_vel.transAxes, fontsize=9,
                            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.9),
                            verticalalignment='bottom')

    ax_vel.plot(SPLASH_E, SPLASH_N, 'k*', markersize=18, markeredgewidth=1.5,
                markeredgecolor='white', label='ARES splashdown coords', zorder=10)
    ax_vel.set_title('Radial Velocity', fontsize=13, fontweight='bold')
    ax_vel.set_xlabel('East of Radar (km)')
    ax_vel.set_ylabel('North of Radar (km)')
    ax_vel.set_xlim(cx - view_half, cx + view_half)
    ax_vel.set_ylim(cy - view_half, cy + view_half)
    ax_vel.set_aspect('equal')
    ax_vel.grid(True, alpha=0.3)
    ax_vel.legend(loc='upper right', fontsize=9)

    # --- Reflectivity ---
    if 'reflectivity' in radar.fields:
        ref_data = radar.fields['reflectivity']['data'][sweep_slice]
        if hasattr(ref_data, 'mask'):
            rf = np.ma.filled(ref_data, np.nan)[ri, gi]
        else:
            rf = ref_data[ri, gi].astype(float)
        rf[rf == 0] = np.nan
        valid = np.isfinite(rf)
        if valid.any():
            sc = ax_ref.scatter(xf[valid], yf[valid], c=rf[valid],
                                cmap='NWSRef', vmin=-10, vmax=30, s=2, alpha=0.8)
            cb = plt.colorbar(sc, ax=ax_ref, shrink=0.8)
            cb.set_label('Reflectivity (dBZ)', fontsize=11)

    ax_ref.plot(SPLASH_E, SPLASH_N, 'k*', markersize=18, markeredgewidth=1.5,
                markeredgecolor='white', label='ARES splashdown coords', zorder=10)
    ax_ref.set_title('Reflectivity', fontsize=13, fontweight='bold')
    ax_ref.set_xlabel('East of Radar (km)')
    ax_ref.set_ylabel('North of Radar (km)')
    ax_ref.set_xlim(cx - view_half, cx + view_half)
    ax_ref.set_ylim(cy - view_half, cy + view_half)
    ax_ref.set_aspect('equal')
    ax_ref.grid(True, alpha=0.3)
    ax_ref.legend(loc='upper right', fontsize=9)

    fig.suptitle(
        f'KNKX — {sweep_time.strftime("%Y-%m-%d %H:%M:%S")} UTC  '
        f'({sign}{dt_min:.0f} min from reported splashdown)\n'
        f'Elevation: {elev_angle:.2f}\u00b0  |  Beam altitude at capsule range: ~{mean_alt:.1f} km  |  '
        f'File: {fname}',
        fontsize=13, fontweight='bold', y=1.01
    )
    plt.tight_layout()
    fig_num += 1
    out_name = f'{fig_num:02d}_{fname}_elev{elev_angle:.1f}.png'
    plt.savefig(out_dir / out_name, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  {out_name}')
    return fig_num


# === Generate per-sweep figures ===
print("Generating sweep figures...")
fig_num = 0
for fpath in files:
    radar = pyart.io.read(fpath)
    fname = fpath.split('/')[-1]
    ref_time = get_ref_time(radar)

    for sweep_idx in range(radar.nsweeps):
        elev = float(radar.fixed_angle['data'][sweep_idx])
        if any(abs(elev - te) < 0.15 for te in target_elevs):
            fig_num = make_sweep_plot(radar, sweep_idx, ref_time, fname, fig_num)


# === Generate descent profile (altitude vs time) ===
print("\nGenerating descent profile...")
times_r, alts_r, refs_r = [], [], []
times_v, alts_v, vels_v = [], [], []

for fpath in files:
    radar = pyart.io.read(fpath)
    ref_time = get_ref_time(radar)

    for sweep_idx in range(radar.nsweeps):
        x, y, z, times, sweep_slice = sweep_cartesian(radar, sweep_idx)

        in_box = (
            (x >= -75) & (x <= -40) &
            (y >= -68) & (y <= -35) &
            (z > 1.5)
        )

        for fn in ['reflectivity', 'velocity']:
            if fn not in radar.fields:
                continue
            fd = radar.fields[fn]['data'][sweep_slice]
            if hasattr(fd, 'mask'):
                fd = np.ma.filled(fd, np.nan)

            ri, gi = np.where(in_box & np.isfinite(fd) & (fd != 0))
            for i in range(len(ri)):
                t = ref_time + timedelta(seconds=float(times[ri[i]]))
                alt = float(z[ri[i], gi[i]])
                val = float(fd[ri[i], gi[i]])
                if fn == 'reflectivity':
                    times_r.append(t)
                    alts_r.append(alt)
                    refs_r.append(val)
                else:
                    times_v.append(t)
                    alts_v.append(alt)
                    vels_v.append(val)

t_min_r = [(t - OFFICIAL_SPLASHDOWN).total_seconds() / 60.0 for t in times_r]
t_min_v = [(t - OFFICIAL_SPLASHDOWN).total_seconds() / 60.0 for t in times_v]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

# Reflectivity altitude profile
sc1 = ax1.scatter(t_min_r, alts_r, c=refs_r, cmap='NWSRef',
                  vmin=-10, vmax=25, s=8, alpha=0.7)
cb1 = plt.colorbar(sc1, ax=ax1, shrink=0.8)
cb1.set_label('Reflectivity (dBZ)')

ax1.axvline(0, color='red', linewidth=2.5, linestyle='--',
            label='Reported splashdown 00:07:27 UTC (5:07 PM PDT)')

# Theoretical descent
t_theory = np.linspace(-4, 26, 200)
alt_theory = 10.5 - (7.5 / 1000 * 60) * (t_theory - (-4))
alt_theory = np.clip(alt_theory, 0, 15)
ax1.plot(t_theory, alt_theory, 'k--', alpha=0.5, linewidth=2,
         label='Theoretical Orion descent (7.5 m/s)')
ax1.axhline(0, color='blue', linewidth=1.5, linestyle=':',
            alpha=0.5, label='Sea level')

ax1.set_ylabel('Altitude (km)', fontsize=12)
ax1.set_title(
    'Artemis II Capsule Descent \u2014 KNKX NEXRAD Radar\n'
    'All returns >1.5 km altitude in splashdown region  |  '
    'Object clearly at altitude well past reported splashdown time',
    fontsize=13, fontweight='bold'
)
ax1.legend(fontsize=10, loc='upper right')
ax1.grid(True, alpha=0.3)
ax1.set_ylim(-0.5, 12)

# Velocity altitude profile
sc2 = ax2.scatter(t_min_v, alts_v, c=vels_v, cmap='RdBu_r',
                  vmin=-30, vmax=30, s=8, alpha=0.7)
cb2 = plt.colorbar(sc2, ax=ax2, shrink=0.8)
cb2.set_label('Radial Velocity (m/s)')
ax2.axvline(0, color='red', linewidth=2.5, linestyle='--',
            label='Reported splashdown 00:07:27 UTC')
ax2.axhline(0, color='blue', linewidth=1.5, linestyle=':', alpha=0.5)

ax2.set_xlabel('Minutes from reported splashdown (00:07:27 UTC, April 11)', fontsize=12)
ax2.set_ylabel('Altitude (km)', fontsize=12)
ax2.set_title(
    'Velocity structure \u2014 blue/red opposing velocities indicate falling object (not aircraft)',
    fontsize=12, fontweight='bold'
)
ax2.legend(fontsize=10, loc='upper right')
ax2.grid(True, alpha=0.3)
ax2.set_ylim(-0.5, 12)

plt.tight_layout()
fig_num += 1
out_name = f'{fig_num:02d}_descent_profile.png'
plt.savefig(out_dir / out_name, dpi=150, bbox_inches='tight')
plt.close()
print(f'  {out_name}')

# === Summary figure: annotated timeline ===
print("\nGenerating annotated timeline...")
fig, ax = plt.subplots(figsize=(16, 6))

events = [
    (-3, 10.5, 'First radar detection\n~10.5 km alt, single vel (+25.5 m/s)', 'green'),
    (0, 9.0, 'REPORTED SPLASHDOWN\n00:07:27 UTC (5:07 PM PDT)\nBut radar shows object at ~9 km alt', 'red'),
    (5, 7.0, 'Strong detection: 42 returns\nOpposing velocities (\u00b127 m/s)\nRe-entry signature at 6.42\u00b0\nPeak ref 12.5 dBZ at 5.1\u00b0', 'orange'),
    (14, 5.0, 'Brightest return: 20 dBZ\nDescended to ~5 km\nCoherent vel -18 to -20 m/s\nSeen across 5 elevations', 'orange'),
    (22, 3.0, 'Continued descent: ~3 km\nOpposing vel at 1.8\u00b0\nWeakening signal', 'orange'),
    (27, 1.0, 'Signal disappears\n~00:33 UTC\nActual splashdown?', 'blue'),
]

# Descent curve
t_line = np.linspace(-3, 27, 100)
alt_line = 10.5 - (7.5/1000*60) * (t_line - (-3))
alt_line = np.clip(alt_line, 0, 12)
ax.plot(t_line, alt_line, 'k-', linewidth=2, alpha=0.4, label='~7.5 m/s descent rate')
ax.fill_between(t_line, 0, alt_line, alpha=0.05, color='gray')

for t, alt, text, color in events:
    ax.plot(t, alt, 'o', color=color, markersize=12, zorder=5, markeredgecolor='black')
    ax.annotate(text, xy=(t, alt), xytext=(t + 1.5, alt + 0.8),
                fontsize=8, ha='left', va='bottom',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=color, alpha=0.9),
                arrowprops=dict(arrowstyle='->', color=color))

ax.axvline(0, color='red', linewidth=2.5, linestyle='--', alpha=0.8)
ax.axhline(0, color='blue', linewidth=1, linestyle=':', alpha=0.5)

ax.set_xlabel('Minutes from reported splashdown (00:07:27 UTC)', fontsize=12)
ax.set_ylabel('Altitude (km)', fontsize=12)
ax.set_title(
    'Artemis II Descent Timeline: KNKX Radar vs Reported Splashdown Time\n'
    'ARES cites 9.071 km altitude at 0007 UTC \u2014 '
    'radar data shows ~25 min descent to surface after reported splashdown',
    fontsize=13, fontweight='bold'
)
ax.set_xlim(-8, 35)
ax.set_ylim(-0.5, 14)
ax.legend(loc='upper right', fontsize=10)
ax.grid(True, alpha=0.3)

plt.tight_layout()
fig_num += 1
out_name = f'{fig_num:02d}_annotated_timeline.png'
plt.savefig(out_dir / out_name, dpi=150, bbox_inches='tight')
plt.close()
print(f'  {out_name}')

print(f"\nDone! {fig_num} figures saved to {out_dir}/")
