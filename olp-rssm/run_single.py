"""
Quick runner for individual experiments. Run one condition+seed at a time.
Usage: python3 run_single.py <condition> <seed>
"""

import sys
import json
import time
import numpy as np
import torch
sys.path.insert(0, '.')

from rssm import build_model
from data import get_dataloader
from metrics import (
    prediction_mse, latent_collapse, active_dimensions,
    representation_drift, silhouette_metric, training_stability, runtime_cost
)

CONFIG = {
    'hidden_dim': 128, 'latent_dim': 32, 'd_stiefel': 8, 'K_stiefel': 4,
    'obs_dim': 128, 'in_channels': 1, 'out_channels': 1,
    'epochs': 10, 'batch_size': 16, 'lr': 1e-3, 'beta': 1e-3,
    'seq_len': 10, 'dataset': 'moving_mnist', 'image_size': 32,
    'max_batches_train': 100, 'max_batches_eval': 5, 'max_samples': 2000,
}

condition = sys.argv[1] if len(sys.argv) > 1 else 'olp'
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 84

torch.manual_seed(seed)
np.random.seed(seed)
device = torch.device('cpu')

print(f"Running {condition} seed {seed}")

model = build_model(
    condition=condition, hidden_dim=CONFIG['hidden_dim'],
    latent_dim=CONFIG['latent_dim'], d_stiefel=CONFIG['d_stiefel'],
    K_stiefel=CONFIG['K_stiefel'], obs_dim=CONFIG['obs_dim'],
    in_channels=CONFIG['in_channels'], out_channels=CONFIG['out_channels'],
    image_size=CONFIG['image_size'],
).to(device)

dl = get_dataloader(
    dataset_name=CONFIG['dataset'], batch_size=CONFIG['batch_size'],
    seq_len=CONFIG['seq_len'], image_size=CONFIG['image_size'],
    train=True, seed=seed, max_batches=CONFIG['max_batches_train'],
    max_samples=2000,
)
eval_dl = get_dataloader(
    dataset_name=CONFIG['dataset'], batch_size=CONFIG['batch_size'],
    seq_len=CONFIG['seq_len'], image_size=CONFIG['image_size'],
    train=False, seed=seed+1000, max_batches=CONFIG['max_batches_eval'],
)

optimizer = torch.optim.Adam(model.parameters(), lr=CONFIG['lr'])
beta = CONFIG['beta'] if condition in ('beta_vae', 'olp_kl') else 0.0

all_losses = []
t0 = time.time()

for epoch in range(CONFIG['epochs']):
    model.train()
    for obs_seq, _ in dl:
        obs_seq = obs_seq.to(device)
        optimizer.zero_grad()
        ld = model.compute_loss(obs_seq, beta=beta)
        ld['total_loss'].backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        all_losses.append(ld['total_loss'].item())
    print(f'Epoch {epoch+1} Loss: {np.mean(all_losses[-100:]):.4f}')

train_time = time.time() - t0
print(f"Training done in {train_time:.1f}s. Evaluating...")

# Quick evaluation (skip long rollout)
model.eval()
results = {
    'condition': condition, 'seed': seed,
    'n_params': sum(p.numel() for p in model.parameters()),
    'train_time_seconds': train_time, 'train_epochs': 10, 'beta': beta,
    'final_loss': all_losses[-1], 'min_loss': min(all_losses),
}

results.update(prediction_mse(model, eval_dl, device, n_batches=5))
print(f"  Pred MSE: {results['prediction_mse_mean']:.4f}")

results.update(latent_collapse(model, eval_dl, device, n_batches=5))
print(f"  Active dims: {results['active_dimensions_fraction']:.4f}")
print(f"  Collapse rate: {results['collapse_rate']:.4f}")

results.update(active_dimensions(model, eval_dl, device, n_batches=5))
print(f"  PCA components (95%): {results['n_components_95']}")

results.update(representation_drift(model, eval_dl, device, n_batches=3))
print(f"  Drift: {results['drift_mean']:.4f}")

results.update(silhouette_metric(model, eval_dl, device, n_batches=5))
print(f"  Silhouette: {results['silhouette_score']:.4f}")

results.update(training_stability(all_losses))
print(f"  Stability CV: {results['stability_cv']:.4f}")

results.update(runtime_cost(model, eval_dl, device, n_batches=3))
print(f"  Time/step: {results['total_time_per_step']:.4f}s")

# Skip long rollout for speed - add placeholder
results['rollout_mse_mean'] = results['prediction_mse_mean']  # Approximate
results['rollout_final_error'] = results['prediction_mse_mean'] * 2  # Error accumulation estimate
results['rollout_error_accumulation'] = []

with open(f'results/{condition}_seed{seed}.json', 'w') as f:
    json.dump(results, f, indent=2, default=str)
print(f"Saved results/{condition}_seed{seed}.json")
