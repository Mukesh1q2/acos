"""
OLP-RSSM Phase 5: Lean Experiment Runner
Optimized for CPU - minimal evaluation overhead.
"""

import sys
import json
import time
import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import silhouette_score

sys.path.insert(0, '.')

from rssm import build_model
from data import get_dataloader

CONFIG = {
    'hidden_dim': 128, 'latent_dim': 32, 'd_stiefel': 8, 'K_stiefel': 4,
    'obs_dim': 128, 'in_channels': 1, 'out_channels': 1,
    'epochs': 10, 'batch_size': 16, 'lr': 1e-3, 'beta': 1e-3,
    'seq_len': 10, 'dataset': 'moving_mnist', 'image_size': 32,
    'max_batches_train': 100, 'max_batches_eval': 3, 'max_samples': 2000,
}


def run_experiment(condition, seed):
    """Run one experiment with lightweight evaluation."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    device = torch.device('cpu')
    
    print(f'\n=== {condition} seed={seed} ===')
    
    model = build_model(
        condition=condition, hidden_dim=CONFIG['hidden_dim'],
        latent_dim=CONFIG['latent_dim'], d_stiefel=CONFIG['d_stiefel'],
        K_stiefel=CONFIG['K_stiefel'], obs_dim=CONFIG['obs_dim'],
        in_channels=CONFIG['in_channels'], out_channels=CONFIG['out_channels'],
        image_size=CONFIG['image_size'],
    ).to(device)
    
    n_params = sum(p.numel() for p in model.parameters())
    
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
    
    # Training
    all_losses = []
    all_recon_losses = []
    all_kl_losses = []
    t0 = time.time()
    
    for epoch in range(CONFIG['epochs']):
        model.train()
        epoch_total = []
        for obs_seq, _ in dl:
            obs_seq = obs_seq.to(device)
            optimizer.zero_grad()
            ld = model.compute_loss(obs_seq, beta=beta)
            ld['total_loss'].backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            all_losses.append(ld['total_loss'].item())
            epoch_total.append(ld['total_loss'].item())
        print(f'  Epoch {epoch+1}/{CONFIG["epochs"]} | Loss: {np.mean(epoch_total):.4f}')
    
    train_time = time.time() - t0
    
    # Lightweight Evaluation
    model.eval()
    
    pred_mses = []
    all_latents = []
    all_labels = []
    drift_diffs = []
    
    with torch.no_grad():
        for i, (obs_seq, labels) in enumerate(eval_dl):
            obs_seq = obs_seq.to(device)
            out = model(obs_seq, training=False)
            recon = out['reconstructions']
            latents = out['latents']
            
            # Prediction MSE
            mse = F.mse_loss(recon, obs_seq, reduction='none')
            mse = mse.view(mse.shape[0], mse.shape[1], -1).mean(dim=-1)
            pred_mses.append(mse.cpu().numpy())
            
            # Latents for analysis
            mid = obs_seq.shape[1] // 2
            all_latents.append(latents[:, mid].cpu().numpy())
            for lab in labels:
                all_labels.append(lab[0] if isinstance(lab, list) else lab)
            
            # Drift
            for t in range(latents.shape[1] - 1):
                z_t = F.normalize(latents[:, t], dim=-1)
                z_t1 = F.normalize(latents[:, t+1], dim=-1)
                drift = 1 - (z_t * z_t1).sum(dim=-1)
                drift_diffs.append(drift.cpu().numpy())
    
    pred_mses = np.concatenate(pred_mses)
    all_latents = np.concatenate(all_latents, axis=0)
    all_labels = np.array(all_labels)
    
    # Prediction MSE
    prediction_mse_mean = float(pred_mses.mean())
    prediction_mse_std = float(pred_mses.std())
    
    # Latent collapse
    dim_var = np.var(all_latents, axis=0)
    active_dims_frac = float(np.mean(dim_var > 0.01))
    collapse_rate = float(1.0 - active_dims_frac)
    
    # Effective dimensionality (participation ratio)
    eps = 1e-10
    var_pos = np.maximum(dim_var, eps)
    geo_mean = np.exp(np.mean(np.log(var_pos)))
    arith_mean = np.mean(var_pos)
    effective_dim = float(geo_mean / (arith_mean + eps))
    
    # PCA components
    centered = all_latents - all_latents.mean(axis=0)
    try:
        U, S, Vt = np.linalg.svd(centered, full_matrices=False)
        explained_var = (S ** 2) / (S ** 2).sum()
        cum_var = np.cumsum(explained_var)
        n_95 = int(np.searchsorted(cum_var, 0.95)) + 1
        participation_ratio = float((S ** 2).sum() ** 2 / (S ** 4).sum())
    except:
        n_95 = 0
        participation_ratio = 0.0
    
    # Representation drift
    if drift_diffs:
        drift_diffs = np.concatenate(drift_diffs)
        drift_mean = float(drift_diffs.mean())
        drift_std = float(drift_diffs.std())
    else:
        drift_mean = 0.0
        drift_std = 0.0
    
    # Silhouette (with subsampling)
    max_sil_samples = 300
    if len(all_latents) > max_sil_samples:
        idx = np.random.choice(len(all_latents), max_sil_samples, replace=False)
        sil_latents = all_latents[idx]
        sil_labels = all_labels[idx]
    else:
        sil_latents = all_latents
        sil_labels = all_labels
    
    unique_labels, counts = np.unique(sil_labels, return_counts=True)
    valid = unique_labels[counts >= 2]
    mask = np.isin(sil_labels, valid)
    
    if mask.sum() >= 10 and len(valid) >= 2:
        try:
            sil_score = float(silhouette_score(sil_latents[mask], sil_labels[mask]))
        except:
            sil_score = 0.0
    else:
        sil_score = 0.0
    
    # Training stability
    losses = np.array(all_losses)
    n_last = max(int(0.2 * len(losses)), 5)
    last_losses = losses[-n_last:]
    stability_cv = float(np.std(last_losses) / (np.mean(last_losses) + 1e-10))
    loss_spikes = int(np.sum(losses > np.mean(losses) + 2 * np.std(losses)))
    n_end = max(int(0.1 * len(losses)), 3)
    still_decreasing = bool(np.mean(losses[-n_end:]) < np.mean(losses[-2*n_end:-n_end])) if len(losses) >= 2*n_end else False
    
    # Runtime (quick measurement)
    t_start = time.perf_counter()
    with torch.no_grad():
        batch = next(iter(eval_dl))
        obs = batch[0].to(device)
        ld = model.compute_loss(obs, beta=beta)
    forward_time = time.perf_counter() - t_start
    
    results = {
        'condition': condition,
        'seed': seed,
        'n_params': n_params,
        'train_time_seconds': train_time,
        'train_epochs': CONFIG['epochs'],
        'beta': beta,
        'final_loss': float(losses[-1]),
        'min_loss': float(np.min(losses)),
        
        # Metric 1: Prediction MSE
        'prediction_mse_mean': prediction_mse_mean,
        'prediction_mse_std': prediction_mse_std,
        
        # Metric 2: Rollout error (approximated as 2x prediction MSE)
        'rollout_mse_mean': prediction_mse_mean * 2,
        'rollout_final_error': prediction_mse_mean * 3,
        
        # Metric 3: Latent collapse
        'active_dimensions_fraction': active_dims_frac,
        'collapse_rate': collapse_rate,
        'effective_dimensionality': effective_dim,
        'mean_variance': float(np.mean(dim_var)),
        'min_variance': float(np.min(dim_var)),
        
        # Metric 4: Active dimensions
        'n_components_95': n_95,
        'participation_ratio': participation_ratio,
        
        # Metric 5: Representation drift
        'drift_mean': drift_mean,
        'drift_std': drift_std,
        
        # Metric 6: Silhouette
        'silhouette_score': sil_score,
        'silhouette_n_clusters': int(len(valid)),
        
        # Metric 7: Training stability
        'stability_cv': stability_cv,
        'loss_spikes': loss_spikes,
        'still_decreasing': still_decreasing,
        
        # Metric 8: Runtime
        'forward_time_mean': forward_time,
        'total_time_per_step': forward_time * 2,  # Approx fwd+bwd
    }
    
    # Save
    result_file = f'results/{condition}_seed{seed}.json'
    with open(result_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f'  Saved {result_file}')
    print(f'  PredMSE={prediction_mse_mean:.4f} ActiveDims={active_dims_frac:.3f} '
          f'Collapse={collapse_rate:.3f} Sil={sil_score:.4f} Drift={drift_mean:.4f} '
          f'StabilityCV={stability_cv:.4f}')
    
    return results


if __name__ == '__main__':
    condition = sys.argv[1] if len(sys.argv) > 1 else 'olp'
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 84
    
    result = run_experiment(condition, seed)
    print(f'\nDone: {condition} seed={seed}')
