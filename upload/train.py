"""
Training Utilities for AFM-Lite Experiments

Provides training loops, evaluation functions, and metric tracking.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import time
from collections import defaultdict


def train_epoch_baseline(model, loader, optimizer, loss_type='task',
                         beta=0.01, recon_weight=0.0, device='cpu'):
    """Train baseline model for one epoch."""
    model.train()
    metrics = defaultdict(list)

    for batch_idx, (X, y) in enumerate(loader):
        X, y = X.to(device), y.to(device)

        optimizer.zero_grad()
        logits, recon, mu, log_var = model(X)

        if loss_type == 'task':
            result = {'total_loss': F.cross_entropy(logits, y)}
        elif loss_type == 'vae':
            result = l_vae_loss(logits, y, mu, log_var, beta, recon, X, recon_weight)
        else:
            result = {'total_loss': F.cross_entropy(logits, y)}

        loss = result['total_loss']
        loss.backward()
        optimizer.step()

        # Track metrics
        metrics['loss'].append(loss.item())
        with torch.no_grad():
            acc = (logits.argmax(1) == y).float().mean().item()
            metrics['accuracy'].append(acc)

    return {k: np.mean(v) for k, v in metrics.items()}


def train_epoch_afm(model, loader, optimizer, loss_type='rib',
                    beta=0.01, recon_weight=0.0, device='cpu'):
    """Train AFM-Lite model for one epoch."""
    model.train()
    metrics = defaultdict(list)

    for batch_idx, (X, y) in enumerate(loader):
        X, y = X.to(device), y.to(device)

        optimizer.zero_grad()
        logits, recon, mu, log_var, kl = model(X)

        if loss_type == 'task':
            # L_task only (no KL regularization)
            loss = F.cross_entropy(logits, y)
        elif loss_type == 'rib':
            # L_RIB = L_task + beta * KL
            ce_loss = F.cross_entropy(logits, y)
            loss = ce_loss + beta * kl if kl is not None else ce_loss
        elif loss_type == 'vae_stiefel':
            # Use standard KL approximation (same as rib for consistency)
            ce_loss = F.cross_entropy(logits, y)
            loss = ce_loss + beta * kl if kl is not None else ce_loss
        else:
            loss = F.cross_entropy(logits, y)

        if recon_weight > 0:
            recon_loss = F.mse_loss(recon, X)
            loss = loss + recon_weight * recon_loss

        loss.backward()
        optimizer.step()

        # Track metrics
        metrics['loss'].append(loss.item())
        with torch.no_grad():
            acc = (logits.argmax(1) == y).float().mean().item()
            metrics['accuracy'].append(acc)
            if kl is not None:
                metrics['kl'].append(kl.item())

    return {k: np.mean(v) for k, v in metrics.items()}


def l_vae_loss(logits, y, mu, log_var, beta=1.0, recon=None, X=None, recon_weight=0.0):
    """Standard β-VAE loss for baseline."""
    ce = F.cross_entropy(logits, y)
    kl = -0.5 * torch.sum(1 + log_var - mu.pow(2) - log_var.exp())
    loss = ce + beta * kl
    if recon_weight > 0 and recon is not None and X is not None:
        loss = loss + recon_weight * F.mse_loss(recon, X)
    return {'total_loss': loss}


def evaluate(model, loader, model_type='baseline', device='cpu'):
    """Evaluate model on a dataset."""
    model.eval()
    total_loss = 0
    total_correct = 0
    total_samples = 0
    all_latents = []
    all_labels = []

    with torch.no_grad():
        for X, y in loader:
            X, y = X.to(device), y.to(device)

            if model_type == 'baseline':
                logits, recon, mu, log_var = model(X, return_latent=False)
                latent = mu
            else:  # afm
                logits, recon, mu, log_var, kl = model(X, return_latent=False)
                # For AFM, the "latent" is the Stiefel state
                # Re-encode to get Stiefel state
                S, _ = model.stiefel(mu, log_var)
                latent = S.reshape(S.shape[0], -1)

            loss = F.cross_entropy(logits, y, reduction='sum')
            total_loss += loss.item()
            total_correct += (logits.argmax(1) == y).sum().item()
            total_samples += y.size(0)

            all_latents.append(latent.cpu().numpy())
            all_labels.append(y.cpu().numpy())

    avg_loss = total_loss / total_samples
    accuracy = total_correct / total_samples

    return {
        'loss': avg_loss,
        'accuracy': accuracy,
        'latents': np.concatenate(all_latents, axis=0) if all_latents else None,
        'labels': np.concatenate(all_labels, axis=0) if all_labels else None,
    }


def train_model(model, train_loader, test_loader, model_type='baseline',
                loss_type='task', beta=0.01, epochs=30, lr=1e-3,
                recon_weight=0.0, device='cpu', verbose=True):
    """
    Full training loop with metric tracking.

    Returns:
        Dictionary with training history and final metrics
    """
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=15, gamma=0.5)

    history = {
        'train_loss': [], 'train_acc': [],
        'test_loss': [], 'test_acc': [],
        'epoch_time': [],
    }

    best_test_acc = 0
    start_time = time.time()

    for epoch in range(epochs):
        epoch_start = time.time()

        # Train
        if model_type == 'baseline':
            train_metrics = train_epoch_baseline(
                model, train_loader, optimizer, loss_type, beta, recon_weight, device
            )
        else:
            train_metrics = train_epoch_afm(
                model, train_loader, optimizer, loss_type, beta, recon_weight, device
            )

        # Evaluate
        test_metrics = evaluate(model, test_loader, model_type, device)

        scheduler.step()

        epoch_time = time.time() - epoch_start
        history['train_loss'].append(train_metrics['loss'])
        history['train_acc'].append(train_metrics['accuracy'])
        history['test_loss'].append(test_metrics['loss'])
        history['test_acc'].append(test_metrics['accuracy'])
        history['epoch_time'].append(epoch_time)

        if test_metrics['accuracy'] > best_test_acc:
            best_test_acc = test_metrics['accuracy']

        if verbose and (epoch + 1) % 5 == 0:
            print(f"  Epoch {epoch+1}/{epochs}: "
                  f"train_loss={train_metrics['loss']:.4f}, "
                  f"train_acc={train_metrics['accuracy']:.4f}, "
                  f"test_loss={test_metrics['loss']:.4f}, "
                  f"test_acc={test_metrics['accuracy']:.4f}, "
                  f"time={epoch_time:.1f}s")

    total_time = time.time() - start_time

    return {
        'history': history,
        'best_test_acc': best_test_acc,
        'final_test_acc': history['test_acc'][-1],
        'final_test_loss': history['test_loss'][-1],
        'total_time': total_time,
    }


def train_sequential(model, task_data, model_type='afm', loss_type='rib',
                     beta=0.01, epochs_per_task=20, lr=1e-3, device='cpu',
                     verbose=True):
    """
    Sequential multi-task training (for measuring catastrophic forgetting).

    Train on tasks one at a time, evaluate on all tasks after each.

    Returns:
        Dictionary with accuracy matrix and forgetting metrics
    """
    num_tasks = len(task_data)
    # Accuracy matrix: [task_trained_on][task_evaluated_on]
    acc_matrix = np.zeros((num_tasks, num_tasks))
    orth_history = []  # Thread orthogonality over training

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)

    for task_id in range(num_tasks):
        train_loader, test_loader, in_dim, nc = task_data[task_id]

        if verbose:
            print(f"\n  Training Task {task_id} ({epochs_per_task} epochs)...")

        for epoch in range(epochs_per_task):
            model.train()
            for X, y in train_loader:
                X, y = X.to(device), y.to(device)
                optimizer.zero_grad()

                if model_type == 'baseline':
                    logits, mu, log_var = model(X, task_id=task_id)
                    ce = F.cross_entropy(logits, y)
                    if loss_type == 'vae' and beta > 0:
                        kl = -0.5 * torch.sum(1 + log_var - mu.pow(2) - log_var.exp())
                        loss = ce + beta * kl
                    else:
                        loss = ce
                else:  # afm
                    logits, mu, log_var, kl = model(X, task_id=task_id)
                    ce = F.cross_entropy(logits, y)
                    loss = ce + (beta * kl if kl is not None and loss_type == 'rib' else 0)

                loss.backward()
                optimizer.step()

            scheduler.step()

            # Track orthogonality for AFM models
            if model_type == 'afm' and hasattr(model, 'get_thread_interference'):
                with torch.no_grad():
                    sample_X = next(iter(train_loader))[0][:32].to(device)
                    interf = model.get_thread_interference(sample_X)
                    orth_history.append(interf)

        # Evaluate on ALL tasks after training on this task
        for eval_id in range(num_tasks):
            _, eval_loader, _, _ = task_data[eval_id]
            model.eval()
            correct = 0
            total = 0
            with torch.no_grad():
                for X, y in eval_loader:
                    X, y = X.to(device), y.to(device)
                    if model_type == 'baseline':
                        logits, _, _ = model(X, task_id=eval_id)
                    else:
                        logits, _, _, _ = model(X, task_id=eval_id)
                    correct += (logits.argmax(1) == y).sum().item()
                    total += y.size(0)
            acc_matrix[task_id, eval_id] = correct / total

            if verbose:
                marker = " ←" if eval_id <= task_id else ""
                print(f"    Task {eval_id} accuracy: {acc_matrix[task_id, eval_id]:.4f}{marker}")

    # Compute catastrophic forgetting
    forgetting = []
    for task_id in range(num_tasks - 1):
        # Accuracy on task_id after training on task_id vs after training on last task
        acc_after = acc_matrix[task_id, task_id]
        acc_final = acc_matrix[num_tasks - 1, task_id]
        forgetting.append(acc_after - acc_final)

    return {
        'acc_matrix': acc_matrix,
        'forgetting': forgetting,
        'avg_forgetting': np.mean(forgetting) if forgetting else 0,
        'orth_history': orth_history,
    }
