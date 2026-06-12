"""
OLP-RSSM Phase 5: Metrics

Eight metrics as specified:
1. Prediction MSE
2. Long rollout error
3. Latent collapse
4. Active dimensions
5. Representation drift
6. Silhouette score
7. Training stability
8. Runtime cost
"""

import torch
import torch.nn.functional as F
import numpy as np
from sklearn.metrics import silhouette_score
import time
from typing import Dict, List, Optional


def prediction_mse(model, dataloader, device, n_batches=10):
    """
    Metric 1: Prediction MSE
    
    One-step-ahead prediction error.
    Given frames [0..t], predict frame t+1.
    Average MSE over all timesteps.
    """
    model.eval()
    mses = []
    
    with torch.no_grad():
        for i, (obs_seq, _) in enumerate(dataloader):
            if i >= n_batches:
                break
            obs_seq = obs_seq.to(device)
            
            # Use first t-1 frames as input, predict last frame
            out = model(obs_seq, training=False)
            recon = out['reconstructions']
            
            # MSE per timestep
            mse = F.mse_loss(recon, obs_seq, reduction='none')
            mse = mse.view(mse.shape[0], mse.shape[1], -1).mean(dim=-1)
            mses.append(mse.cpu().numpy())
    
    mses = np.concatenate(mses, axis=0)
    return {
        'prediction_mse_mean': float(mses.mean()),
        'prediction_mse_std': float(mses.std()),
        'prediction_mse_per_step': mses.mean(axis=0).tolist(),
    }


def long_rollout_error(model, dataloader, device, rollout_steps=50, n_batches=5):
    """
    Metric 2: Long Rollout Error
    
    Open-loop rollout: given first 5 frames, predict all subsequent frames
    using only prior (no posterior correction).
    Measure how error accumulates over time.
    """
    model.eval()
    errors = []
    
    warmup = 5
    
    with torch.no_grad():
        for i, (obs_seq, _) in enumerate(dataloader):
            if i >= n_batches:
                break
            obs_seq = obs_seq.to(device)
            batch_size = obs_seq.shape[0]
            seq_len = obs_seq.shape[1]
            
            # Only possible if sequence is long enough
            actual_rollout = min(rollout_steps, seq_len - warmup)
            if actual_rollout <= 0:
                continue
            
            # Warmup: process first `warmup` frames with posterior
            out = model(obs_seq[:, :warmup], training=True)
            h = out['hiddens'][:, -1]  # Last hidden state
            z = out['latents'][:, -1]  # Last latent
            
            # Open-loop rollout
            rollout_errors = []
            for t in range(warmup, warmup + actual_rollout):
                # Use prior
                if hasattr(model, 'stoch_path') and hasattr(model.stoch_path, 'prior'):
                    mu_prior, logvar_prior = model.stoch_path.prior(h)
                    z = model.stoch_path.sample(mu_prior, logvar_prior)
                
                # Decode
                recon = model.decoder(z, h)
                target = obs_seq[:, t]
                
                mse = F.mse_loss(recon, target, reduction='none')
                mse = mse.view(mse.shape[0], -1).mean(dim=-1)
                rollout_errors.append(mse.cpu().numpy())
                
                # Update deterministic state
                h = model.det_path(h, z)
            
            errors.append(np.stack(rollout_errors, axis=1))
    
    if not errors:
        return {
            'rollout_mse_mean': float('inf'),
            'rollout_mse_std': 0.0,
            'rollout_error_accumulation': [],
        }
    
    errors = np.concatenate(errors, axis=0)
    return {
        'rollout_mse_mean': float(errors.mean()),
        'rollout_mse_std': float(errors.std()),
        'rollout_error_accumulation': errors.mean(axis=0).tolist(),
        'rollout_final_error': float(errors[:, -1].mean()),
    }


def latent_collapse(model, dataloader, device, threshold=0.01, n_batches=10):
    """
    Metric 3: Latent Collapse
    
    Measure what fraction of latent dimensions are "dead" (variance < threshold).
    A collapsed model uses very few dimensions effectively.
    """
    model.eval()
    all_latents = []
    
    with torch.no_grad():
        for i, (obs_seq, _) in enumerate(dataloader):
            if i >= n_batches:
                break
            obs_seq = obs_seq.to(device)
            out = model(obs_seq, training=False)
            # Use last timestep latents
            all_latents.append(out['latents'][:, -1].cpu().numpy())
    
    all_latents = np.concatenate(all_latents, axis=0)  # (N, latent_dim)
    
    # Per-dimension variance
    dim_variance = np.var(all_latents, axis=0)
    
    # Fraction of "active" dimensions (above threshold)
    active_dims = np.mean(dim_variance > threshold)
    
    # Effective dimensionality (ratio of geometric mean to arithmetic mean of variance)
    eps = 1e-10
    var_positive = np.maximum(dim_variance, eps)
    geo_mean = np.exp(np.mean(np.log(var_positive)))
    arith_mean = np.mean(var_positive)
    effective_dim = geo_mean / (arith_mean + eps)
    
    return {
        'active_dimensions_fraction': float(active_dims),
        'collapse_rate': float(1.0 - active_dims),
        'dim_variance': dim_variance.tolist(),
        'effective_dimensionality': float(effective_dim),
        'mean_variance': float(np.mean(dim_variance)),
        'min_variance': float(np.min(dim_variance)),
    }


def active_dimensions(model, dataloader, device, n_batches=10):
    """
    Metric 4: Active Dimensions
    
    PCA-based effective dimensionality.
    How many PCA components explain 95% of variance?
    """
    model.eval()
    all_latents = []
    
    with torch.no_grad():
        for i, (obs_seq, _) in enumerate(dataloader):
            if i >= n_batches:
                break
            obs_seq = obs_seq.to(device)
            out = model(obs_seq, training=False)
            all_latents.append(out['latents'].reshape(-1, out['latents'].shape[-1]).cpu().numpy())
    
    all_latents = np.concatenate(all_latents, axis=0)
    
    # PCA via SVD
    centered = all_latents - all_latents.mean(axis=0)
    U, S, Vt = np.linalg.svd(centered, full_matrices=False)
    
    # Explained variance ratio
    explained_var = (S ** 2) / (S ** 2).sum()
    cumulative_var = np.cumsum(explained_var)
    
    # Number of components for 95% variance
    n_95 = int(np.searchsorted(cumulative_var, 0.95)) + 1
    
    # Participation ratio
    participation_ratio = (S ** 2).sum() ** 2 / (S ** 4).sum()
    
    return {
        'n_components_95': n_95,
        'participation_ratio': float(participation_ratio),
        'explained_variance_ratio': explained_var.tolist()[:20],  # Top 20
        'cumulative_variance': cumulative_var.tolist()[:20],
    }


def representation_drift(model, dataloader, device, n_batches=5):
    """
    Metric 5: Representation Drift
    
    How much do latent representations change across timesteps?
    Low drift = stable representations.
    High drift = representations are chaotic.
    """
    model.eval()
    drifts = []
    
    with torch.no_grad():
        for i, (obs_seq, _) in enumerate(dataloader):
            if i >= n_batches:
                break
            obs_seq = obs_seq.to(device)
            out = model(obs_seq, training=False)
            latents = out['latents']  # (B, T, D)
            
            # Cosine distance between consecutive timesteps
            for t in range(latents.shape[1] - 1):
                z_t = latents[:, t]
                z_t1 = latents[:, t + 1]
                
                # Normalize
                z_t_norm = F.normalize(z_t, dim=-1)
                z_t1_norm = F.normalize(z_t1, dim=-1)
                
                # Cosine similarity -> drift = 1 - similarity
                cos_sim = (z_t_norm * z_t1_norm).sum(dim=-1)
                drift = 1 - cos_sim
                drifts.append(drift.cpu().numpy())
    
    if not drifts:
        return {'drift_mean': 0.0, 'drift_std': 0.0}
    
    drifts = np.concatenate(drifts)
    return {
        'drift_mean': float(drifts.mean()),
        'drift_std': float(drifts.std()),
        'drift_median': float(np.median(drifts)),
    }


def silhouette_metric(model, dataloader, device, n_batches=10):
    """
    Metric 6: Silhouette Score
    
    How well-separated are the latent representations?
    Use k-means clustering with k=10, then compute silhouette.
    """
    model.eval()
    all_latents = []
    all_labels = []
    
    with torch.no_grad():
        for i, (obs_seq, labels) in enumerate(dataloader):
            if i >= n_batches:
                break
            obs_seq = obs_seq.to(device)
            out = model(obs_seq, training=False)
            
            # Use middle timestep latent
            mid = obs_seq.shape[1] // 2
            all_latents.append(out['latents'][:, mid].cpu().numpy())
            
            # Use first label as cluster assignment
            for lab in labels:
                all_labels.append(lab[0] if isinstance(lab, list) else lab)
    
    all_latents = np.concatenate(all_latents, axis=0)
    all_labels = np.array(all_labels)
    
    # Subsample if too many points (silhouette is O(n²))
    max_samples = 500
    if len(all_latents) > max_samples:
        idx = np.random.choice(len(all_latents), max_samples, replace=False)
        all_latents = all_latents[idx]
        all_labels = all_labels[idx]
    
    # Filter to labels with at least 2 samples
    unique_labels, counts = np.unique(all_labels, return_counts=True)
    valid_labels = unique_labels[counts >= 2]
    mask = np.isin(all_labels, valid_labels)
    
    if mask.sum() < 10 or len(valid_labels) < 2:
        return {'silhouette_score': 0.0, 'silhouette_n_clusters': 0}
    
    try:
        sil = silhouette_score(all_latents[mask], all_labels[mask])
    except Exception:
        sil = 0.0
    
    return {
        'silhouette_score': float(sil),
        'silhouette_n_clusters': int(len(valid_labels)),
    }


def training_stability(loss_history: List[float]):
    """
    Metric 7: Training Stability
    
    Measure smoothness of training loss curve.
    - Coefficient of variation of last 20% of losses
    - Number of loss spikes (>2σ above local mean)
    - Is the loss still decreasing at the end?
    """
    if len(loss_history) < 10:
        return {'stability_cv': float('inf'), 'loss_spikes': 0, 'still_decreasing': False}
    
    losses = np.array(loss_history)
    
    # Last 20% of training
    n_last = max(int(0.2 * len(losses)), 5)
    last_losses = losses[-n_last:]
    
    # Coefficient of variation
    cv = float(np.std(last_losses) / (np.mean(last_losses) + 1e-10))
    
    # Loss spikes
    mean_loss = np.mean(losses)
    std_loss = np.std(losses)
    spikes = int(np.sum(losses > mean_loss + 2 * std_loss))
    
    # Still decreasing? (compare last 10% to second-to-last 10%)
    n_end = max(int(0.1 * len(losses)), 3)
    end_mean = np.mean(losses[-n_end:])
    prev_mean = np.mean(losses[-2*n_end:-n_end]) if len(losses) >= 2*n_end else end_mean
    still_decreasing = bool(end_mean < prev_mean)
    
    return {
        'stability_cv': cv,
        'loss_spikes': spikes,
        'still_decreasing': still_decreasing,
        'final_loss': float(losses[-1]),
        'min_loss': float(np.min(losses)),
    }


def runtime_cost(model, dataloader, device, n_batches=10):
    """
    Metric 8: Runtime Cost
    
    Wall-clock time for forward + backward pass.
    Memory usage (if CUDA available).
    Parameter count.
    """
    # Parameter count
    n_params = sum(p.numel() for p in model.parameters())
    
    # Forward pass timing
    model.train()
    times_forward = []
    times_backward = []
    
    for i, (obs_seq, _) in enumerate(dataloader):
        if i >= n_batches:
            break
        obs_seq = obs_seq.to(device)
        
        # Forward
        start = time.perf_counter()
        loss_dict = model.compute_loss(obs_seq, beta=0.001)
        t_forward = time.perf_counter() - start
        
        # Backward
        start = time.perf_counter()
        loss_dict['total_loss'].backward()
        t_backward = time.perf_counter() - start
        
        model.zero_grad()
        
        times_forward.append(t_forward)
        times_backward.append(t_backward)
    
    return {
        'n_params': n_params,
        'forward_time_mean': float(np.mean(times_forward)),
        'forward_time_std': float(np.std(times_forward)),
        'backward_time_mean': float(np.mean(times_backward)),
        'backward_time_std': float(np.std(times_backward)),
        'total_time_per_step': float(np.mean(times_forward) + np.mean(times_backward)),
        'cuda_available': torch.cuda.is_available(),
        'cuda_memory_mb': torch.cuda.max_memory_allocated() / 1e6 if torch.cuda.is_available() else 0,
    }


def evaluate_all_metrics(model, dataloader, device, loss_history=None,
                         rollout_steps=30, n_batches=10):
    """
    Run all 8 metrics and return combined results.
    """
    results = {}
    
    print("  Computing prediction MSE...")
    results.update(prediction_mse(model, dataloader, device, n_batches))
    
    print("  Computing long rollout error...")
    results.update(long_rollout_error(model, dataloader, device, rollout_steps, 
                                       min(n_batches, 5)))
    
    print("  Computing latent collapse...")
    results.update(latent_collapse(model, dataloader, device, n_batches=n_batches))
    
    print("  Computing active dimensions...")
    results.update(active_dimensions(model, dataloader, device, n_batches=n_batches))
    
    print("  Computing representation drift...")
    results.update(representation_drift(model, dataloader, device, n_batches=n_batches))
    
    print("  Computing silhouette score...")
    results.update(silhouette_metric(model, dataloader, device, n_batches=n_batches))
    
    if loss_history is not None:
        print("  Computing training stability...")
        results.update(training_stability(loss_history))
    
    print("  Computing runtime cost...")
    results.update(runtime_cost(model, dataloader, device, n_batches=min(n_batches, 5)))
    
    return results
