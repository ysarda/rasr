"""
Train a track classifier on the extracted feature vectors.

The signature + descent-coherence filter reduces a scan to ~60 candidate tracks;
this learns "fall/re-entry track vs clutter track" from those candidates. Because
positives are few (tens of tracks from a handful of events), we use a shallow
gradient-boosted model with balanced class weights and GROUP cross-validation
keyed on event, so every score is measured on a held-out event (no leakage from a
sibling track of the same event).
"""

import argparse

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.model_selection import GroupKFold
from sklearn.metrics import (average_precision_score, roc_auc_score,
                             precision_recall_fscore_support, confusion_matrix)
from sklearn.utils.class_weight import compute_sample_weight


def load(path, max_pos_dist=None):
    """Load the regions .npz. If max_pos_dist is set, positive regions farther
    than that from the event truth are dropped (cleaner positive labels)."""
    d = np.load(path, allow_pickle=True)
    X = d['X_feat'].astype(float)
    y = d['y'].astype(int)
    groups = d['groups']
    dist = d['dist'].astype(float)
    feat_names = list(d['feat_names'])
    if max_pos_dist is not None:
        keep = ~((y == 1) & (dist > max_pos_dist))
        X, y, groups, dist = X[keep], y[keep], groups[keep], dist[keep]
    return X, y, groups, feat_names


def make_model():
    return HistGradientBoostingClassifier(
        max_depth=3, learning_rate=0.08, max_iter=300,
        l2_regularization=1.0, min_samples_leaf=5, random_state=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default='data/regions.npz')
    ap.add_argument('--folds', type=int, default=5)
    ap.add_argument('--max_pos_dist', type=float, default=None,
                    help='Drop positive regions farther than this (km) from truth')
    args = ap.parse_args()

    X, y, groups, feats = load(args.data, args.max_pos_dist)
    n_pos = int(y.sum())
    pos_groups = sorted(set(groups[y == 1]))
    print(f"Loaded {len(y)} regions: {n_pos} positive ({len(pos_groups)} events), "
          f"{len(y) - n_pos} negative")
    print(f"Positive events: {', '.join(pos_groups)}\n")

    # grouped out-of-fold predictions: each event held out in turn
    n_splits = min(args.folds, len(pos_groups))
    gkf = GroupKFold(n_splits=n_splits)
    oof = np.full(len(y), np.nan)
    for tr, te in gkf.split(X, y, groups):
        m = make_model()
        sw = compute_sample_weight('balanced', y[tr])
        m.fit(X[tr], y[tr], sample_weight=sw)
        oof[te] = m.predict_proba(X[te])[:, 1]

    mask = ~np.isnan(oof)
    yt, pp = y[mask], oof[mask]
    ap_score = average_precision_score(yt, pp)
    roc = roc_auc_score(yt, pp)
    print("=" * 64)
    print(f"GROUPED CV ({n_splits}-fold, held-out events)")
    print(f"  PR-AUC (average precision): {ap_score:.3f}   "
          f"(baseline = prevalence {yt.mean():.3f})")
    print(f"  ROC-AUC:                    {roc:.3f}")
    print(f"\n  {'thresh':>7}{'precision':>11}{'recall':>9}{'TP':>5}{'FP':>6}{'FN':>5}")
    for T in [0.3, 0.5, 0.7, 0.9]:
        pred = (pp >= T).astype(int)
        if pred.sum() == 0:
            print(f"  {T:>7.1f}{'-':>11}{'0.00':>9}{0:>5}{0:>6}{int(yt.sum()):>5}")
            continue
        p, r, _, _ = precision_recall_fscore_support(yt, pred, average='binary', zero_division=0)
        tn, fp, fn, tp = confusion_matrix(yt, pred, labels=[0, 1]).ravel()
        print(f"  {T:>7.1f}{p:>11.3f}{r:>9.3f}{tp:>5}{fp:>6}{fn:>5}")

    # feature importances on a model fit to all data
    m = make_model()
    m.fit(X, y, sample_weight=compute_sample_weight('balanced', y))
    imp = permutation_importance(m, X, y, n_repeats=10, random_state=0,
                                 scoring='average_precision')
    order = np.argsort(imp.importances_mean)[::-1]
    print("\n" + "=" * 64)
    print("TOP FEATURES (permutation importance, avg-precision drop)")
    for i in order[:10]:
        print(f"  {feats[i]:<18}{imp.importances_mean[i]:+.4f}")
    print("=" * 64)


if __name__ == '__main__':
    main()
