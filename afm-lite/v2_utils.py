"""Shared utilities for AFM-Lite v0.2 validation phases."""

import sys, os, json, time, warnings
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from scipy import stats

sys.path.insert(0, '/home/z/my-project/afm-lite')
warnings.filterwarnings('ignore')

from ablation_models import get_model, compute_loss

RESULTS_DIR = '/home/z/my-project/afm-lite/results_v2'
os.makedirs(RESULTS_DIR, exist_ok=True)

EPOCHS = 8
LR = 1e-3
BS = 1024
MAX_SAMPLES = 10000  # Keep training fast


def save(name, data):
    def conv(obj):
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, (np.float32, np.float64)): return float(obj)
        if isinstance(obj, (np.int32, np.int64)): return int(obj)
        if isinstance(obj, dict): return {k: conv(v) for k, v in obj.items()}
        if isinstance(obj, list): return [conv(v) for v in obj]
        if isinstance(obj, torch.Tensor): return obj.detach().cpu().numpy().tolist()
        if isinstance(obj, bool): return obj
        return obj
    path = os.path.join(RESULTS_DIR, f'{name}.json')
    with open(path, 'w') as f:
        json.dump(conv(data), f, indent=2)
    print(f'  Saved: {path}')


def load(name):
    path = os.path.join(RESULTS_DIR, f'{name}.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def ci_95(data):
    n = len(data)
    if n < 2: return 0.0
    return float(stats.t.ppf(0.975, n-1) * np.std(data, ddof=1) / np.sqrt(n))


def train_eval(model, train_l, test_l, config, beta=0.0, epochs=EPOCHS,
               track_norms=False):
    """Train and evaluate. Returns dict with results."""
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)
    best_acc = 0.0
    final_acc = 0.0
    mu_norm_history = []
    s_norm_history = []

    for epoch in range(epochs):
        model.train()
        for X, y in train_l:
            optimizer.zero_grad()
            if config in ['afm_qr', 'afm_rib']:
                logits, recon, mu, lv, kl = model(X)
            else:
                logits, recon, mu, lv = model(X)
                kl = None
            loss = compute_loss(model, config, logits, y, mu, lv, kl, beta, recon, X)
            loss.backward()
            optimizer.step()
        scheduler.step()

        # Evaluate + optional norm tracking
        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for X, y in test_l:
                if config in ['afm_qr', 'afm_rib']:
                    logits, _, mu, lv, kl = model(X)
                else:
                    logits, _, mu, lv = model(X)
                correct += (logits.argmax(1) == y).sum().item()
                total += y.size(0)

        if track_norms and total > 0:
            with torch.no_grad():
                X_s = next(iter(test_l))[0]
                if config in ['afm_qr', 'afm_rib']:
                    _, _, mu, lv, kl = model(X_s)
                    mu_norm_history.append(float(mu.norm(dim=-1).mean().item()))
                    S, _ = model.stiefel(mu, lv)
                    s_norm_history.append(float(S.norm(dim=(1,2)).mean().item()))
                else:
                    _, _, mu, lv = model(X_s)
                    mu_norm_history.append(float(mu.norm(dim=-1).mean().item()))

        acc = correct / total if total > 0 else 0
        if acc > best_acc: best_acc = acc
        final_acc = acc

    result = {'best_acc': best_acc, 'final_acc': final_acc}
    if track_norms:
        result['mu_norm_history'] = mu_norm_history
        if s_norm_history:
            result['s_norm_history'] = s_norm_history
    return result
