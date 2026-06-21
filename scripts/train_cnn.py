"""
CV proof-of-concept: small CNN on multi-channel region patches.

Each candidate region is a 3-channel patch (reflectivity, velocity, rho_hv)
cropped around it. A small CNN learns "fall/re-entry region vs clutter region"
directly from the patch, instead of hand-crafted features. Radar patches have no
canonical orientation, so random 90-degree rotations + flips are valid, label-
preserving augmentation that multiplies the scarce positives.

Evaluation is grouped (by event / null scan) so every score is on a held-out
event. Reports OOF ROC-AUC and PR-AUC, comparable to the tabular GBT.
"""

import argparse

import numpy as np
import torch
import torch.nn as nn
from sklearn.model_selection import GroupKFold
from sklearn.metrics import average_precision_score, roc_auc_score


class PatchCNN(nn.Module):
    def __init__(self, in_ch=3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_ch, 16, 3, padding=1), nn.BatchNorm2d(16), nn.ReLU(),
            nn.MaxPool2d(2),                                            # 32->16
            nn.Conv2d(16, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.MaxPool2d(2),                                            # 16->8
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
        )
        self.head = nn.Sequential(nn.Flatten(), nn.Dropout(0.3), nn.Linear(64, 1))

    def forward(self, x):
        return self.head(self.net(x)).squeeze(1)


def augment(x):
    """Random k*90 rotation + flips on a batch (B,C,H,W)."""
    k = int(torch.randint(0, 4, (1,)))
    x = torch.rot90(x, k, dims=(2, 3))
    if torch.rand(1) < 0.5:
        x = torch.flip(x, dims=(2,))
    if torch.rand(1) < 0.5:
        x = torch.flip(x, dims=(3,))
    return x


def train_fold(Xtr, ytr, Xte, device, epochs, bs, pos_weight):
    model = PatchCNN(Xtr.shape[1]).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    lossf = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(pos_weight, device=device))
    Xtr_t = torch.from_numpy(Xtr).float()
    ytr_t = torch.from_numpy(ytr).float()
    n = len(Xtr)
    for ep in range(epochs):
        model.train()
        perm = torch.randperm(n)
        for i in range(0, n, bs):
            idx = perm[i:i + bs]
            xb = augment(Xtr_t[idx].to(device))
            yb = ytr_t[idx].to(device)
            opt.zero_grad()
            loss = lossf(model(xb), yb)
            loss.backward()
            opt.step()
    model.eval()
    probs = []
    with torch.no_grad():
        Xte_t = torch.from_numpy(Xte).float()
        for i in range(0, len(Xte), 512):
            xb = Xte_t[i:i + 512].to(device)
            probs.append(torch.sigmoid(model(xb)).cpu().numpy())
    return np.concatenate(probs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default='data/stacks.npz')
    ap.add_argument('--folds', type=int, default=5)
    ap.add_argument('--epochs', type=int, default=25)
    ap.add_argument('--batch_size', type=int, default=128)
    ap.add_argument('--max_pos_dist', type=float, default=10.0)
    args = ap.parse_args()

    d = np.load(args.data, allow_pickle=True)
    Xkey = 'X' if 'X' in d else 'X_patch'        # stacks.npz uses 'X', regions.npz 'X_patch'
    X, y, groups, dist = d[Xkey].astype(np.float32), d['y'].astype(int), d['groups'], d['dist']

    if args.max_pos_dist is not None:
        keep = ~((y == 1) & (dist > args.max_pos_dist))
        X, y, groups, dist = X[keep], y[keep], groups[keep], dist[keep]

    pos_groups = sorted(set(groups[y == 1]))
    print(f"Patches: {X.shape}  positives {int(y.sum())} ({len(pos_groups)} events)  "
          f"negatives {int((y==0).sum())}")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}  (max_pos_dist={args.max_pos_dist})\n")

    n_splits = min(args.folds, len(pos_groups))
    gkf = GroupKFold(n_splits=n_splits)
    oof = np.full(len(y), np.nan)
    pos_weight = (y == 0).sum() / max((y == 1).sum(), 1)
    for fold, (tr, te) in enumerate(gkf.split(X, y, groups), 1):
        oof[te] = train_fold(X[tr], y[tr], X[te], device, args.epochs,
                             args.batch_size, pos_weight)
        m = ~np.isnan(oof)
        print(f"  fold {fold}/{n_splits} done  "
              f"(running ROC {roc_auc_score(y[m], oof[m]):.3f})")

    m = ~np.isnan(oof)
    print("\n" + "=" * 60)
    print(f"GROUPED CV CNN ({n_splits}-fold, held-out events)")
    print(f"  PR-AUC: {average_precision_score(y[m], oof[m]):.3f}  "
          f"(baseline {y[m].mean():.3f})")
    print(f"  ROC-AUC: {roc_auc_score(y[m], oof[m]):.3f}")
    for T in [0.5, 0.7, 0.9]:
        pred = (oof[m] >= T)
        tp = int((pred & (y[m] == 1)).sum()); fp = int((pred & (y[m] == 0)).sum())
        fn = int((~pred & (y[m] == 1)).sum())
        prec = tp / (tp + fp) if tp + fp else 0
        rec = tp / (tp + fn) if tp + fn else 0
        print(f"  thr {T}: precision {prec:.3f} recall {rec:.3f} (TP{tp} FP{fp} FN{fn})")
    print("=" * 60)


if __name__ == '__main__':
    main()
