#!/usr/bin/env python3
"""
AFM-Lite 1M Parameter Scaling Experiment
==========================================

Scales AFM from 602K to ~1M parameters by increasing hidden_dim from 256 to 512.
Trains all 4 ablation configs at 1M scale on Fashion-MNIST and compares against
the existing 602K baseline results.

Configs at hidden_dim=256 (602K):
  - BaselineModel(input_dim=784, hidden_dim=256, latent_dim=128, num_classes=10)
  - AFMLiteModel(input_dim=784, hidden_dim=256, d=32, K=4, num_classes=10)

Configs at hidden_dim=512 (~1M):
  - BaselineModel(input_dim=784, hidden_dim=512, latent_dim=128, num_classes=10)
  - AFMLiteModel(input_dim=784, hidden_dim=512, d=32, K=4, num_classes=10)

Ablation variants:
  1. baseline:   BaselineModel + L_task only
  2. beta_vae:   BaselineModel + β-VAE KL regularisation
  3. afm_task:   AFMLiteModel + L_task only (no KL)
  4. afm_rib:    AFMLiteModel + L_RIB (Stiefel KL regularisation)

Output:
  - results_v02/scale_1m.json
  - /home/z/my-project/AFM_SCALE_REPORT_1M.md

Usage:
  python /home/z/my-project/afm-lite/run_scale_1m.py
"""

import sys
sys.path.insert(0, '/home/z/my-project/afm-lite')

import os
import json
import time
import pickle
import warnings
from collections import defaultdict

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

from models import BaselineModel, AFMLiteModel
from losses import l_rib, l_vae
from stiefel import stiefel_project_qr, thread_orthogonality, stiefel_kl_complexity

# ---------------------------------------------------------------------------
# Global configuration
# ---------------------------------------------------------------------------
DEVICE = 'cpu'
RESULTS_DIR = '/home/z/my-project/afm-lite/results_v02'
CACHE_DIR = '/home/z/my-project/afm-lite/.cache'
REPORT_PATH = '/home/z/my-project/AFM_SCALE_REPORT_1M.md'

# Architecture
D_STIEFEL = 32
K_THREADS = 4
LATENT_DIM = D_STIEFEL * K_THREADS  # 128

# Scaling configs
SCALE_CONFIGS = {
    '602k': {'hidden_dim': 256},
    '1m':   {'hidden_dim': 512},
}

# Training hyperparameters
BATCH_SIZE = 512
EPOCHS = 15
LR = 1e-3
BETA = 0.01
SEED = 42


# ===========================================================================
# Utility helpers
# ===========================================================================

def numpy_safe(obj):
    """Recursively convert numpy types for JSON serialization."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.float32, np.float64, np.floating)):
        return float(obj)
    if isinstance(obj, (np.int32, np.int64, np.integer)):
        return int(obj)
    if isinstance(obj, dict):
        return {k: numpy_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [numpy_safe(v) for v in obj]
    if isinstance(obj, torch.Tensor):
        return numpy_safe(obj.detach().cpu().numpy())
    return obj


def save_json(name, data):
    """Save results dict to JSON in results directory."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f'{name}.json')
    with open(path, 'w') as f:
        json.dump(numpy_safe(data), f, indent=2, default=str)
    print(f"  [SAVE] {path}")
    return path


def set_seed(seed):
    """Set random seed for reproducibility."""
    torch.manual_seed(seed)
    np.random.seed(seed)


# ===========================================================================
# Dataset loader
# ===========================================================================

def get_fashion_mnist(batch_size=512):
    """Load Fashion-MNIST with caching."""
    cache_path = os.path.join(CACHE_DIR, 'fashion_mnist.pkl')

    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            data = pickle.load(f)
        X_train, y_train = data['X_train'], data['y_train']
        X_test, y_test = data['X_test'], data['y_test']
    else:
        print("  Downloading Fashion-MNIST via fetch_openml...")
        from sklearn.datasets import fetch_openml
        fashion = fetch_openml('Fashion-MNIST', version=1, as_frame=False)
        X, y = fashion.data, fashion.target.astype(int)
        X_train, X_test = X[:60000], X[60000:]
        y_train, y_test = y[:60000], y[60000:]
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump({'X_train': X_train, 'y_train': y_train,
                         'X_test': X_test, 'y_test': y_test}, f)

    X_train = X_train.astype(np.float32) / 255.0
    X_test = X_test.astype(np.float32) / 255.0

    train_ds = TensorDataset(torch.FloatTensor(X_train), torch.LongTensor(y_train))
    test_ds = TensorDataset(torch.FloatTensor(X_test), torch.LongTensor(y_test))

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

    return train_loader, test_loader, 784, 10


# ===========================================================================
# Ablation configurations
# ===========================================================================

ABLATION_CONFIGS = {
    'baseline': {
        'model_type': 'baseline',
        'loss_type': 'task',
        'beta': 0.0,
        'description': 'No regularization (cross-entropy only)',
    },
    'beta_vae': {
        'model_type': 'baseline',
        'loss_type': 'vae',
        'beta': BETA,
        'description': 'Standard beta-VAE KL regularization',
    },
    'afm_task': {
        'model_type': 'afm',
        'loss_type': 'task',
        'beta': 0.0,
        'description': 'AFM Stiefel projection + L_task only (no KL)',
    },
    'afm_rib': {
        'model_type': 'afm',
        'loss_type': 'rib',
        'beta': BETA,
        'description': 'AFM + L_RIB (Stiefel KL regularization)',
    },
}


def create_model(config_name, hidden_dim, input_dim=784, num_classes=10):
    """Instantiate model for the given ablation configuration at the given scale."""
    cfg = ABLATION_CONFIGS[config_name]
    if cfg['model_type'] == 'baseline':
        return BaselineModel(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            latent_dim=LATENT_DIM,
            num_classes=num_classes,
        )
    else:
        return AFMLiteModel(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            d=D_STIEFEL,
            K=K_THREADS,
            num_classes=num_classes,
        )


# ===========================================================================
# Training loop
# ===========================================================================

def train_one_epoch(model, loader, optimizer, config_name, beta=0.01, device='cpu'):
    """Train model for one epoch, recording all loss components."""
    cfg = ABLATION_CONFIGS[config_name]
    model.train()
    metrics = defaultdict(list)

    for X, y in loader:
        X, y = X.to(device), y.to(device)
        optimizer.zero_grad()

        if cfg['model_type'] == 'baseline':
            logits, recon, mu, log_var = model(X)
            kl_val = torch.tensor(0.0)

            if cfg['loss_type'] == 'vae' and beta > 0:
                ce = F.cross_entropy(logits, y)
                kl_val = -0.5 * torch.sum(1 + log_var - mu.pow(2) - log_var.exp())
                total_loss = ce + beta * kl_val
            else:
                ce = F.cross_entropy(logits, y)
                total_loss = ce

            latent_for_active = mu

        else:  # afm
            logits, recon, mu, log_var, kl_val = model(X)
            ce = F.cross_entropy(logits, y)
            total_loss = ce

            if cfg['loss_type'] in ('rib', 'vae') and beta > 0 and kl_val is not None:
                total_loss = total_loss + beta * kl_val

            latent_for_active = mu

        total_loss.backward()
        optimizer.step()

        with torch.no_grad():
            acc = (logits.argmax(1) == y).float().mean().item()
            latent_var = latent_for_active.var(dim=0)
            active_dims = (latent_var > 1e-4).sum().item()

        metrics['total_loss'].append(total_loss.item())
        metrics['ce_loss'].append(ce.item())
        metrics['kl_loss'].append(kl_val.item() if isinstance(kl_val, torch.Tensor) else float(kl_val))
        metrics['accuracy'].append(acc)
        metrics['active_dims'].append(active_dims)

    return {k: float(np.mean(v)) for k, v in metrics.items()}


def evaluate_model(model, loader, config_name, device='cpu'):
    """Fast evaluation: loss + accuracy only."""
    model.eval()
    total_loss = 0.0
    total_correct = 0
    total_samples = 0

    with torch.no_grad():
        for X, y in loader:
            X, y = X.to(device), y.to(device)
            if ABLATION_CONFIGS[config_name]['model_type'] == 'baseline':
                logits, _, _, _ = model(X)
            else:
                logits, _, _, _, _ = model(X)
            loss = F.cross_entropy(logits, y, reduction='sum')
            total_loss += loss.item()
            total_correct += (logits.argmax(1) == y).sum().item()
            total_samples += y.size(0)

    return {
        'loss': total_loss / total_samples,
        'accuracy': total_correct / total_samples,
    }


def train_full(model, train_loader, test_loader, config_name,
               epochs=15, lr=1e-3, beta=0.01, device='cpu', verbose=True):
    """Full training loop with per-epoch metric recording."""
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=15, gamma=0.5)

    history = []
    best_test_acc = 0.0
    t0 = time.time()

    for epoch in range(epochs):
        ep_start = time.time()

        # Train
        train_m = train_one_epoch(model, train_loader, optimizer, config_name,
                                  beta=beta, device=device)

        # Evaluate
        eval_m = evaluate_model(model, test_loader, config_name, device)

        scheduler.step()
        ep_time = time.time() - ep_start

        test_acc = eval_m['accuracy']
        if test_acc > best_test_acc:
            best_test_acc = test_acc

        ep_record = {
            'epoch': epoch,
            'train_total_loss': train_m['total_loss'],
            'train_ce_loss': train_m['ce_loss'],
            'train_kl_loss': train_m['kl_loss'],
            'train_accuracy': train_m['accuracy'],
            'train_active_dims': train_m['active_dims'],
            'test_accuracy': test_acc,
            'test_loss': eval_m['loss'],
            'epoch_time': ep_time,
        }
        history.append(ep_record)

        if verbose and (epoch + 1) % 5 == 0:
            print(f"    Epoch {epoch+1}/{epochs}: "
                  f"loss={train_m['total_loss']:.4f} "
                  f"ce={train_m['ce_loss']:.4f} "
                  f"kl={train_m['kl_loss']:.4f} "
                  f"train_acc={train_m['accuracy']:.4f} "
                  f"test_acc={test_acc:.4f} "
                  f"active={train_m['active_dims']:.0f} "
                  f"t={ep_time:.1f}s")

    total_time = time.time() - t0

    return {
        'history': history,
        'best_test_acc': best_test_acc,
        'final_test_acc': history[-1]['test_accuracy'] if history else 0,
        'final_test_loss': history[-1]['test_loss'] if history else 0,
        'total_time': total_time,
    }


# ===========================================================================
# Main experiment
# ===========================================================================

def run_scaling_experiment():
    """Run the 1M scaling experiment and compare against 602K baseline."""

    print("=" * 70)
    print("AFM-Lite 1M Parameter Scaling Experiment")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Step 1: Print parameter counts for both scales
    # ------------------------------------------------------------------
    print("\n[1] Parameter Count Comparison")
    print("-" * 50)

    param_counts = {}
    for scale_name, scale_cfg in SCALE_CONFIGS.items():
        hd = scale_cfg['hidden_dim']
        b = BaselineModel(input_dim=784, hidden_dim=hd, latent_dim=LATENT_DIM, num_classes=10)
        a = AFMLiteModel(input_dim=784, hidden_dim=hd, d=D_STIEFEL, K=K_THREADS, num_classes=10)
        b_count = b.count_parameters()
        a_count = a.count_parameters()
        param_counts[scale_name] = {
            'hidden_dim': hd,
            'baseline_params': b_count,
            'afm_params': a_count,
        }
        print(f"  {scale_name.upper()} (hidden_dim={hd}):")
        print(f"    BaselineModel: {b_count:,} params")
        print(f"    AFMLiteModel:  {a_count:,} params")
        print(f"    Matched: {'YES' if abs(b_count - a_count) < 100 else 'NO'}")

    # ------------------------------------------------------------------
    # Step 2: Load Fashion-MNIST
    # ------------------------------------------------------------------
    print("\n[2] Loading Fashion-MNIST dataset...")
    train_loader, test_loader, input_dim, num_classes = get_fashion_mnist(batch_size=BATCH_SIZE)
    print(f"  input_dim={input_dim}, num_classes={num_classes}")
    print(f"  train={len(train_loader.dataset)}, test={len(test_loader.dataset)}")
    print(f"  batch_size={BATCH_SIZE}")

    # ------------------------------------------------------------------
    # Step 3: Train all 4 ablation configs at 1M scale
    # ------------------------------------------------------------------
    print(f"\n[3] Training 4 ablation configs at 1M scale ({EPOCHS} epochs, seed={SEED})")
    print("-" * 50)

    results_1m = {}

    for cfg_name, cfg in ABLATION_CONFIGS.items():
        print(f"\n  Config: {cfg_name} - {cfg['description']}")

        set_seed(SEED)
        model = create_model(cfg_name, hidden_dim=512, input_dim=input_dim, num_classes=num_classes)
        n_params = model.count_parameters()
        print(f"    Parameters: {n_params:,}")

        result = train_full(
            model, train_loader, test_loader, cfg_name,
            epochs=EPOCHS, lr=LR, beta=cfg['beta'],
            device=DEVICE, verbose=True,
        )

        results_1m[cfg_name] = {
            'seed': SEED,
            'hidden_dim': 512,
            'param_count': n_params,
            'best_test_acc': result['best_test_acc'],
            'final_test_acc': result['final_test_acc'],
            'final_test_loss': result['final_test_loss'],
            'total_time': result['total_time'],
            'history': result['history'],
            'final_kl': result['history'][-1]['train_kl_loss'] if result['history'] else 0,
            'final_active_dims': result['history'][-1]['train_active_dims'] if result['history'] else 0,
        }

        print(f"    => best_test_acc={result['best_test_acc']:.4f}, "
              f"time={result['total_time']:.1f}s")

    # ------------------------------------------------------------------
    # Step 4: Load 602K baseline results for comparison
    # ------------------------------------------------------------------
    print(f"\n[4] Loading 602K baseline results for comparison...")
    baseline_path = os.path.join(RESULTS_DIR, 'ablation_fashion_mnist.json')
    results_602k = {}
    if os.path.exists(baseline_path):
        with open(baseline_path, 'r') as f:
            results_602k = json.load(f)
        print(f"  Loaded: {baseline_path}")
    else:
        print(f"  WARNING: {baseline_path} not found. Training 602K configs now...")
        # Train 602K configs as fallback
        for cfg_name, cfg in ABLATION_CONFIGS.items():
            print(f"\n  Config: {cfg_name} (602K)")
            set_seed(SEED)
            model = create_model(cfg_name, hidden_dim=256, input_dim=input_dim, num_classes=num_classes)
            n_params = model.count_parameters()
            print(f"    Parameters: {n_params:,}")

            result = train_full(
                model, train_loader, test_loader, cfg_name,
                epochs=EPOCHS, lr=LR, beta=cfg['beta'],
                device=DEVICE, verbose=True,
            )

            results_602k[cfg_name] = {
                'runs': [{
                    'seed': SEED,
                    'param_count': n_params,
                    'best_test_acc': result['best_test_acc'],
                    'final_test_acc': result['final_test_acc'],
                    'final_test_loss': result['final_test_loss'],
                    'total_time': result['total_time'],
                    'history': result['history'],
                }],
                'summary': {
                    'test_acc_mean': result['best_test_acc'],
                    'final_kl_mean': result['history'][-1]['train_kl_loss'] if result['history'] else 0,
                    'final_active_dims_mean': result['history'][-1]['train_active_dims'] if result['history'] else 0,
                    'time_mean': result['total_time'],
                },
            }

    # ------------------------------------------------------------------
    # Step 5: Compare results
    # ------------------------------------------------------------------
    print(f"\n[5] Comparison: 602K vs 1M")
    print("=" * 70)

    comparison = {}
    for cfg_name in ABLATION_CONFIGS:
        # Get 602K metrics
        if cfg_name in results_602k:
            r602 = results_602k[cfg_name]
            if 'summary' in r602:
                acc_602 = r602['summary']['test_acc_mean']
                kl_602 = r602['summary'].get('final_kl_mean', 0)
                active_602 = r602['summary'].get('final_active_dims_mean', 0)
                time_602 = r602['summary'].get('time_mean', 0)
            elif 'runs' in r602 and len(r602['runs']) > 0:
                run = r602['runs'][0]
                acc_602 = run['best_test_acc']
                kl_602 = run['history'][-1].get('train_kl_loss', 0) if run.get('history') else 0
                active_602 = run['history'][-1].get('train_active_dims', 0) if run.get('history') else 0
                time_602 = run['total_time']
            else:
                acc_602 = kl_602 = active_602 = time_602 = 0
        else:
            acc_602 = kl_602 = active_602 = time_602 = 0

        # Get 1M metrics
        r1m = results_1m[cfg_name]
        acc_1m = r1m['best_test_acc']
        kl_1m = r1m['final_kl']
        active_1m = r1m['final_active_dims']
        time_1m = r1m['total_time']

        acc_delta = acc_1m - acc_602
        time_ratio = time_1m / time_602 if time_602 > 0 else float('inf')

        comparison[cfg_name] = {
            'acc_602k': acc_602,
            'acc_1m': acc_1m,
            'acc_delta': acc_delta,
            'acc_delta_pct': acc_delta * 100,
            'kl_602k': kl_602,
            'kl_1m': kl_1m,
            'active_dims_602k': active_602,
            'active_dims_1m': active_1m,
            'time_602k': time_602,
            'time_1m': time_1m,
            'time_ratio': time_ratio,
            'params_602k': param_counts['602k']['baseline_params'] if ABLATION_CONFIGS[cfg_name]['model_type'] == 'baseline' else param_counts['602k']['afm_params'],
            'params_1m': r1m['param_count'],
        }

        print(f"\n  {cfg_name}:")
        print(f"    Accuracy: {acc_602:.4f} -> {acc_1m:.4f}  (delta={acc_delta:+.4f}, {acc_delta*100:+.2f}%)")
        print(f"    KL Loss:  {kl_602:.4f} -> {kl_1m:.4f}")
        print(f"    Active Dims: {active_602:.0f} -> {active_1m:.0f}")
        print(f"    Time:     {time_602:.1f}s -> {time_1m:.1f}s  (ratio={time_ratio:.2f}x)")
        print(f"    Params:   {comparison[cfg_name]['params_602k']:,} -> {r1m['param_count']:,}")

    # ------------------------------------------------------------------
    # Step 6: Save all results to JSON
    # ------------------------------------------------------------------
    print(f"\n[6] Saving results...")

    all_results = {
        'experiment': 'scale_1m',
        'description': 'AFM-Lite scaling from 602K to ~1M parameters',
        'config': {
            'batch_size': BATCH_SIZE,
            'epochs': EPOCHS,
            'lr': LR,
            'beta': BETA,
            'seed': SEED,
            'device': DEVICE,
            'd_stiefel': D_STIEFEL,
            'k_threads': K_THREADS,
            'latent_dim': LATENT_DIM,
        },
        'param_counts': param_counts,
        'results_1m': results_1m,
        'comparison': comparison,
    }

    save_json('scale_1m', all_results)

    # ------------------------------------------------------------------
    # Step 7: Generate report
    # ------------------------------------------------------------------
    print(f"\n[7] Generating report: {REPORT_PATH}")
    report = generate_report(param_counts, results_1m, results_602k, comparison)
    with open(REPORT_PATH, 'w') as f:
        f.write(report)
    print(f"  [SAVE] {REPORT_PATH}")

    print("\n" + "=" * 70)
    print("EXPERIMENT COMPLETE")
    print("=" * 70)

    return all_results


# ===========================================================================
# Report generation
# ===========================================================================

def generate_report(param_counts, results_1m, results_602k, comparison):
    """Generate markdown report for the scaling experiment."""

    lines = []
    lines.append("# AFM-Lite 1M Parameter Scaling Report")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append("This report examines whether AFM's Stiefel manifold constraint provides")
    lines.append("differential benefits when model capacity is scaled from ~602K to ~1M parameters.")
    lines.append("")
    lines.append(f"- **Dataset**: Fashion-MNIST (784-dim, 10 classes)")
    lines.append(f"- **Batch size**: {BATCH_SIZE}")
    lines.append(f"- **Epochs**: {EPOCHS}")
    lines.append(f"- **Seed**: {SEED}")
    lines.append(f"- **Device**: {DEVICE}")
    lines.append("")

    # Parameter counts
    lines.append("## 1. Parameter Counts")
    lines.append("")
    lines.append("| Scale | hidden_dim | BaselineModel | AFMLiteModel | Matched? |")
    lines.append("|-------|-----------|---------------|-------------|----------|")
    for scale_name, pc in param_counts.items():
        matched = "YES" if abs(pc['baseline_params'] - pc['afm_params']) < 100 else "NO"
        lines.append(f"| {scale_name.upper()} | {pc['hidden_dim']} | {pc['baseline_params']:,} | "
                     f"{pc['afm_params']:,} | {matched} |")
    lines.append("")

    # Accuracy comparison
    lines.append("## 2. Accuracy Comparison (602K vs 1M)")
    lines.append("")
    lines.append("| Config | 602K Acc | 1M Acc | Delta | Delta % |")
    lines.append("|--------|---------|--------|-------|---------|")
    for cfg_name in ABLATION_CONFIGS:
        c = comparison[cfg_name]
        lines.append(f"| {cfg_name} | {c['acc_602k']:.4f} | {c['acc_1m']:.4f} | "
                     f"{c['acc_delta']:+.4f} | {c['acc_delta_pct']:+.2f}% |")
    lines.append("")

    # KL and active dimensions
    lines.append("## 3. KL Loss and Active Dimensions")
    lines.append("")
    lines.append("| Config | 602K KL | 1M KL | 602K Active | 1M Active |")
    lines.append("|--------|--------|-------|-------------|-----------|")
    for cfg_name in ABLATION_CONFIGS:
        c = comparison[cfg_name]
        lines.append(f"| {cfg_name} | {c['kl_602k']:.4f} | {c['kl_1m']:.4f} | "
                     f"{c['active_dims_602k']:.0f} | {c['active_dims_1m']:.0f} |")
    lines.append("")

    # Training time
    lines.append("## 4. Training Time")
    lines.append("")
    lines.append("| Config | 602K Time | 1M Time | Slowdown |")
    lines.append("|--------|----------|---------|----------|")
    for cfg_name in ABLATION_CONFIGS:
        c = comparison[cfg_name]
        lines.append(f"| {cfg_name} | {c['time_602k']:.1f}s | {c['time_1m']:.1f}s | "
                     f"{c['time_ratio']:.2f}x |")
    lines.append("")

    # Scaling efficiency
    lines.append("## 5. Scaling Efficiency Analysis")
    lines.append("")
    lines.append("How much accuracy gain per extra parameter?")
    lines.append("")
    lines.append("| Config | Extra Params | Acc Gain | Acc/1K Params |")
    lines.append("|--------|-------------|---------|---------------|")
    for cfg_name in ABLATION_CONFIGS:
        c = comparison[cfg_name]
        extra = c['params_1m'] - c['params_602k']
        gain = c['acc_delta']
        eff = (gain / extra * 1000) if extra > 0 else 0
        lines.append(f"| {cfg_name} | {extra:,} | {gain:+.4f} | {eff:+.6f} |")
    lines.append("")

    # Per-epoch training curves
    lines.append("## 6. Per-Epoch Training Curves (1M)")
    lines.append("")
    for cfg_name, r in results_1m.items():
        lines.append(f"### {cfg_name}")
        lines.append("")
        lines.append("| Epoch | Train Loss | Train Acc | Test Acc | KL Loss | Active Dims | Time |")
        lines.append("|-------|-----------|-----------|----------|---------|-------------|------|")
        for ep in r['history']:
            lines.append(f"| {ep['epoch']+1} | {ep['train_total_loss']:.4f} | "
                        f"{ep['train_accuracy']:.4f} | {ep['test_accuracy']:.4f} | "
                        f"{ep['train_kl_loss']:.4f} | {ep['train_active_dims']:.0f} | "
                        f"{ep['epoch_time']:.1f}s |")
        lines.append("")

    # Key findings
    lines.append("## 7. Key Findings")
    lines.append("")

    # Compute key deltas
    baseline_delta = comparison['baseline']['acc_delta']
    afm_rib_delta = comparison['afm_rib']['acc_delta']
    afm_task_delta = comparison['afm_task']['acc_delta']

    lines.append("### Does AFM benefit more from scaling?")
    lines.append("")
    lines.append(f"- Baseline accuracy gain from scaling: {baseline_delta:+.4f} ({baseline_delta*100:+.2f}%)")
    lines.append(f"- AFM+L_task accuracy gain from scaling: {afm_task_delta:+.4f} ({afm_task_delta*100:+.2f}%)")
    lines.append(f"- AFM+L_RIB accuracy gain from scaling: {afm_rib_delta:+.4f} ({afm_rib_delta*100:+.2f}%)")
    lines.append("")

    if afm_rib_delta > baseline_delta:
        lines.append("**AFM+L_RIB benefits MORE from scaling than the baseline.**")
        lines.append("This is consistent with the hypothesis that the Stiefel constraint")
        lines.append("becomes more valuable at higher capacity, where the unconstrained")
        lines.append("baseline is more prone to overfitting.")
    elif afm_rib_delta < baseline_delta - 0.005:
        lines.append("**AFM+L_RIB benefits LESS from scaling than the baseline.**")
        lines.append("This suggests the Stiefel constraint may be overly restrictive at")
        lines.append("higher capacity, limiting the model's ability to use additional parameters.")
    else:
        lines.append("**AFM+L_RIB scales similarly to the baseline.**")
        lines.append("The Stiefel constraint neither helps nor hurts as capacity increases.")
    lines.append("")

    # Gap analysis
    gap_602k = comparison['afm_rib']['acc_602k'] - comparison['baseline']['acc_602k']
    gap_1m = comparison['afm_rib']['acc_1m'] - comparison['baseline']['acc_1m']
    lines.append("### AFM vs Baseline gap at different scales")
    lines.append("")
    lines.append(f"- At 602K: AFM+L_RIB - Baseline = {gap_602k:+.4f}")
    lines.append(f"- At 1M:   AFM+L_RIB - Baseline = {gap_1m:+.4f}")
    lines.append("")
    if gap_1m > gap_602k:
        lines.append("The AFM advantage **widens** at 1M scale.")
    elif gap_1m < gap_602k - 0.005:
        lines.append("The AFM advantage **narrows** at 1M scale.")
    else:
        lines.append("The AFM advantage remains **stable** across scales.")
    lines.append("")

    # Active dimensions
    lines.append("### Active Dimensions")
    lines.append("")
    for cfg_name in ABLATION_CONFIGS:
        c = comparison[cfg_name]
        lines.append(f"- **{cfg_name}**: {c['active_dims_602k']:.0f} -> {c['active_dims_1m']:.0f} "
                     f"(latent_dim={LATENT_DIM})")
    lines.append("")
    lines.append("If AFM maintains full active dimensions while baseline collapses,")
    lines.append("this supports the Stiefel constraint preventing posterior collapse.")
    lines.append("")

    # Honest assessment
    lines.append("## 8. Honest Assessment")
    lines.append("")
    lines.append("### What this experiment CAN tell us:")
    lines.append("- Whether scaling hidden_dim from 256 to 512 changes the AFM vs baseline gap")
    lines.append("- Whether active dimensions change with scale")
    lines.append("- Whether training time scales linearly with parameter count")
    lines.append("")
    lines.append("### What this experiment CANNOT tell us:")
    lines.append("- Whether the results generalize to other scaling strategies (e.g., more layers)")
    lines.append("- Whether results hold at much larger scales (10M+)")
    lines.append("- Whether the hidden_dim scaling is fair (it may favor one architecture)")
    lines.append("- Causal claims about WHY any differences exist")
    lines.append("")
    lines.append("### Caveats:")
    lines.append("- Single seed only (SEED=42). Multi-seed runs needed for statistical rigor.")
    lines.append("- Only 15 epochs — longer training may change relative rankings.")
    lines.append("- Fashion-MNIST only — results may differ on other datasets.")
    lines.append("- The beta-VAE baseline collapsed at 602K; we need to check if this")
    lines.append("  improves at 1M or continues to fail.")
    lines.append("")

    lines.append("## 9. Raw Data")
    lines.append("")
    lines.append("Full results saved to: `results_v02/scale_1m.json`")
    lines.append("")

    return "\n".join(lines)


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == '__main__':
    results = run_scaling_experiment()
