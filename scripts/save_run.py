"""Save a training run's artifacts to a named snapshot folder."""

import shutil
import json
import argparse
from pathlib import Path
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description='Save training run artifacts')
    parser.add_argument('name', nargs='?', default=None,
                        help='Run name (default: auto-generated from config)')
    parser.add_argument('--config', default='configs/train_poc.json',
                        help='Training config used for this run')
    parser.add_argument('--runs_dir', default='runs', help='Base directory for saved runs')
    args = parser.parse_args()

    # Load config for auto-naming
    with open(args.config) as f:
        cfg = json.load(f)

    if args.name is None:
        fields = '-'.join(f[:3] for f in cfg.get('fields', ['ref']))
        args.name = (
            f"{cfg['image_size']}px_"
            f"s{cfg['spatial_latent_dim']}_t{cfg['temporal_hidden_dim']}_"
            f"sw{cfg['max_sweeps']}_{fields}_"
            f"{datetime.now():%Y%m%d_%H%M}"
        )

    run_dir = Path(args.runs_dir) / args.name
    run_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_dir = Path(cfg['checkpoint_dir'])
    vis_dir = checkpoint_dir / 'visualizations'
    eval_dir = Path('evaluation_results')

    copied = []

    # Config
    shutil.copy2(args.config, run_dir / 'config.json')
    copied.append(args.config)

    # Best model
    best_model = checkpoint_dir / 'best_model.pt'
    if best_model.exists():
        shutil.copy2(best_model, run_dir / 'best_model.pt')
        copied.append(str(best_model))

    # Training curves
    curves = vis_dir / 'training_curves.png'
    if curves.exists():
        shutil.copy2(curves, run_dir / 'training_curves.png')
        copied.append(str(curves))

    # Timelapse GIFs
    for gif in sorted(vis_dir.glob('reconstruction_timelapse_*.gif')):
        shutil.copy2(gif, run_dir / gif.name)
        copied.append(str(gif))

    # If no GIFs yet, try to build them
    if not list(vis_dir.glob('reconstruction_timelapse_*.gif')):
        print("No timelapse GIFs found, building from frames...")
        try:
            from PIL import Image
            import glob
            for sample_idx in range(4):
                pattern = str(vis_dir / f'reconstruction_sample_{sample_idx}_epoch*.png')
                frames_paths = sorted(glob.glob(pattern))
                if not frames_paths:
                    continue
                frames = [Image.open(p) for p in frames_paths]
                gif_name = f'reconstruction_timelapse_sample_{sample_idx}.gif'
                gif_path = run_dir / gif_name
                frames[0].save(gif_path, save_all=True, append_images=frames[1:],
                               duration=200, loop=0)
                copied.append(str(gif_path))
                print(f"  Built {gif_name} ({len(frames)} frames)")
        except ImportError:
            print("  Pillow not installed, skipping GIF generation")

    # Evaluation results
    if eval_dir.exists():
        eval_dest = run_dir / 'evaluation'
        eval_dest.mkdir(exist_ok=True)
        for f in eval_dir.iterdir():
            if f.is_dir():
                shutil.copytree(f, eval_dest / f.name, dirs_exist_ok=True)
            else:
                shutil.copy2(f, eval_dest / f.name)
            copied.append(str(f))

    print(f"\nRun saved to: {run_dir}")
    print(f"Copied {len(copied)} files:")
    for f in copied:
        print(f"  {f}")

    # Wipe checkpoints and eval results for next run
    for d in [checkpoint_dir, eval_dir]:
        if d.exists():
            shutil.rmtree(d)
            d.mkdir(parents=True)
            print(f"Wiped {d}/ for next run")


if __name__ == '__main__':
    main()
