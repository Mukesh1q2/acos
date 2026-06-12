"""
OLP-RSSM Phase 5: Main Experiment Runner

Runs all 4 conditions across multiple seeds:
1. Vanilla RSSM
2. RSSM + β-VAE
3. RSSM + OLP (QR only)
4. RSSM + OLP + KL

Datasets: Moving-MNIST (primary)

Strict failure policy:
- If RSSM+OLP ≈ RSSM: mark OLP as FAILED
- If OLP hurts: document it, do not rescue
"""

import sys
import os
import json
import time
import numpy as np
import torch
import torch.nn.functional as F
from torch.optim import Adam
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from rssm import build_model
from data import get_dataloader
from metrics import evaluate_all_metrics


# ── Configuration ──────────────────────────────────────────────────────────

CONFIG = {
    # Model (optimized for CPU)
    'hidden_dim': 128,
    'latent_dim': 32,
    'd_stiefel': 8,
    'K_stiefel': 4,  # 8*4 = 32 = latent_dim
    'obs_dim': 128,
    'in_channels': 1,
    'out_channels': 1,
    
    # Training
    'epochs': 10,
    'batch_size': 16,
    'lr': 1e-3,
    'beta': 1e-3,  # For β-VAE and OLP+KL
    'seq_len': 10,  # Total sequence length
    
    # Data
    'dataset': 'moving_mnist',
    'image_size': 32,  # Smaller for CPU speed
    'max_batches_train': 100,  # Limit batches per epoch for CPU
    'max_batches_eval': 20,
    'max_samples': 2000,
    
    # Experiment
    'seeds': [0, 42, 84],
    'conditions': ['vanilla', 'beta_vae', 'olp', 'olp_kl'],
    
    # Evaluation
    'rollout_steps': 5,
    
    # Output
    'results_dir': 'results',
}

RESULTS_DIR = Path(__file__).parent / CONFIG['results_dir']
RESULTS_DIR.mkdir(exist_ok=True)


def set_seed(seed):
    """Set random seed for reproducibility."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def train_one_epoch(model, dataloader, optimizer, beta, device):
    """Train for one epoch. Returns list of batch losses."""
    model.train()
    epoch_losses = []
    
    for batch_idx, (obs_seq, _) in enumerate(dataloader):
        obs_seq = obs_seq.to(device)
        
        optimizer.zero_grad()
        loss_dict = model.compute_loss(obs_seq, beta=beta)
        loss = loss_dict['total_loss']
        
        loss.backward()
        # Gradient clipping for stability
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        
        epoch_losses.append({
            'total': loss_dict['total_loss'].item(),
            'recon': loss_dict['recon_loss'].item(),
            'kl': loss_dict['kl_loss'].item() if isinstance(loss_dict['kl_loss'], torch.Tensor) else loss_dict['kl_loss'],
        })
    
    return epoch_losses


def run_single_experiment(condition, seed, config=None):
    """
    Run one experiment: condition x seed.
    Returns full results dict.
    """
    if config is None:
        config = CONFIG
    
    set_seed(seed)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    print(f"\n{'='*60}")
    print(f"Condition: {condition} | Seed: {seed} | Device: {device}")
    print(f"{'='*60}")
    
    # Build model
    model = build_model(
        condition=condition,
        hidden_dim=config['hidden_dim'],
        latent_dim=config['latent_dim'],
        d_stiefel=config['d_stiefel'],
        K_stiefel=config['K_stiefel'],
        obs_dim=config['obs_dim'],
        in_channels=config['in_channels'],
        out_channels=config['out_channels'],
        image_size=config['image_size'],
    ).to(device)
    
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Model: {condition} | Parameters: {n_params:,}")
    
    # Data
    dataloader = get_dataloader(
        dataset_name=config['dataset'],
        batch_size=config['batch_size'],
        seq_len=config['seq_len'],
        image_size=config['image_size'],
        train=True,
        seed=seed,
        max_batches=config['max_batches_train'],
        max_samples=config.get('max_samples'),
    )
    
    eval_loader = get_dataloader(
        dataset_name=config['dataset'],
        batch_size=config['batch_size'],
        seq_len=config['seq_len'],
        image_size=config['image_size'],
        train=False,
        seed=seed + 1000,
        max_batches=config['max_batches_eval'],
    )
    
    # Optimizer
    optimizer = Adam(model.parameters(), lr=config['lr'])
    
    # Beta value
    beta = 0.0
    if condition == 'beta_vae':
        beta = config['beta']
    elif condition == 'olp_kl':
        beta = config['beta']
    
    # Training loop
    all_losses = []
    start_time = time.time()
    
    for epoch in range(config['epochs']):
        epoch_losses = train_one_epoch(model, dataloader, optimizer, beta, device)
        
        avg_total = np.mean([l['total'] for l in epoch_losses])
        avg_recon = np.mean([l['recon'] for l in epoch_losses])
        avg_kl = np.mean([l['kl'] for l in epoch_losses])
        
        all_losses.extend([l['total'] for l in epoch_losses])
        
        print(f"  Epoch {epoch+1}/{config['epochs']} | "
              f"Loss: {avg_total:.4f} | Recon: {avg_recon:.4f} | KL: {avg_kl:.4f}")
    
    train_time = time.time() - start_time
    
    # Evaluation
    print("\n  Evaluating metrics...")
    eval_results = evaluate_all_metrics(
        model, eval_loader, device,
        loss_history=all_losses,
        rollout_steps=config['rollout_steps'],
        n_batches=config['max_batches_eval'],
    )
    
    # Compile results
    results = {
        'condition': condition,
        'seed': seed,
        'n_params': n_params,
        'train_time_seconds': train_time,
        'train_epochs': config['epochs'],
        'beta': beta,
        'final_loss': all_losses[-1] if all_losses else None,
        'min_loss': min(all_losses) if all_losses else None,
        **eval_results,
    }
    
    # Save individual result
    result_file = RESULTS_DIR / f"{condition}_seed{seed}.json"
    with open(result_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  Saved: {result_file}")
    
    return results


def run_all_experiments(config=None):
    """Run all conditions x seeds."""
    if config is None:
        config = CONFIG
    
    all_results = {}
    
    for condition in config['conditions']:
        all_results[condition] = []
        
        for seed in config['seeds']:
            result = run_single_experiment(condition, seed, config)
            all_results[condition].append(result)
    
    # Save combined results
    combined_file = RESULTS_DIR / 'all_results.json'
    with open(combined_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nSaved combined results to {combined_file}")
    
    return all_results


def compute_summary(all_results):
    """Compute mean/std across seeds for each condition."""
    summary = {}
    
    for condition, seed_results in all_results.items():
        if not seed_results:
            continue
        
        # Numeric keys to aggregate
        numeric_keys = [
            'prediction_mse_mean', 'prediction_mse_std',
            'rollout_mse_mean', 'rollout_mse_std', 'rollout_final_error',
            'active_dimensions_fraction', 'collapse_rate',
            'effective_dimensionality', 'mean_variance', 'min_variance',
            'n_components_95', 'participation_ratio',
            'drift_mean', 'drift_std', 'drift_median',
            'silhouette_score',
            'stability_cv', 'loss_spikes', 'final_loss', 'min_loss',
            'forward_time_mean', 'backward_time_mean', 'total_time_per_step',
            'n_params', 'train_time_seconds',
        ]
        
        summary[condition] = {}
        for key in numeric_keys:
            values = [r.get(key) for r in seed_results if key in r and r[key] is not None]
            if values:
                values = [float(v) for v in values]
                summary[condition][key] = {
                    'mean': float(np.mean(values)),
                    'std': float(np.std(values)),
                    'min': float(np.min(values)),
                    'max': float(np.max(values)),
                    'values': values,
                }
    
    return summary


if __name__ == '__main__':
    print("OLP Phase 5: Orthogonal Latent Projection in RSSM")
    print("=" * 60)
    print(f"Conditions: {CONFIG['conditions']}")
    print(f"Seeds: {CONFIG['seeds']}")
    print(f"Dataset: {CONFIG['dataset']}")
    print(f"Epochs: {CONFIG['epochs']}")
    print(f"Batches/epoch: {CONFIG['max_batches_train']}")
    print(f"Device: {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    print("=" * 60)
    
    results = run_all_experiments()
    
    # Compute summary
    summary = compute_summary(results)
    
    summary_file = RESULTS_DIR / 'summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nSaved summary to {summary_file}")
    
    # Print comparison table
    print("\n" + "=" * 60)
    print("RESULTS COMPARISON")
    print("=" * 60)
    
    metrics_to_show = [
        ('prediction_mse_mean', 'Pred MSE'),
        ('rollout_final_error', 'Rollout Err'),
        ('active_dimensions_fraction', 'Active Dims'),
        ('collapse_rate', 'Collapse Rate'),
        ('drift_mean', 'Rep Drift'),
        ('silhouette_score', 'Silhouette'),
        ('stability_cv', 'Train Stability'),
        ('total_time_per_step', 'Time/Step'),
    ]
    
    # Header
    header = f"{'Metric':<16}"
    for cond in CONFIG['conditions']:
        header += f" {cond:>14}"
    print(header)
    print("-" * (16 + 15 * len(CONFIG['conditions'])))
    
    for key, label in metrics_to_show:
        row = f"{label:<16}"
        for cond in CONFIG['conditions']:
            if cond in summary and key in summary[cond]:
                val = summary[cond][key]['mean']
                std = summary[cond][key]['std']
                row += f" {val:>10.4f}±{std:.3f}"
            else:
                row += f" {'N/A':>14}"
        print(row)
    
    print("\nPhase 5 experiments complete.")
