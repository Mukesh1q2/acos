"""
AFM-Lite Validation Program v0.2 — Comprehensive 7-Phase Runner

Executes all validation phases and saves results to results_v2/ directory.
Spec: batch_size=1024, 8 epochs (most), 10 seeds (main), 5 seeds (multi-dataset).
"""

import sys, os, json, time, warnings, traceback
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')

from ablation_models import get_model, compute_loss
from validation_data import (
    get_mnist, get_fashion_mnist, get_kmnist, get_cifar10,
    get_synthetic, get_split_mnist, get_permuted_mnist
)
from stiefel import stiefel_project_qr, thread_orthogonality

RESULTS_DIR = '/home/z/my-project/afm-lite/results_v2'
os.makedirs(RESULTS_DIR, exist_ok=True)

# Global config per spec
EPOCHS = 8
LR = 1e-3
BS = 1024


def save(name, data):
    """Save results to JSON, handling numpy/torch types."""
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
    print(f"  Saved: {path}")


def ci_95(data):
    """Compute 95% confidence interval half-width."""
    n = len(data)
    if n < 2:
        return 0.0
    return float(stats.t.ppf(0.975, n-1) * np.std(data, ddof=1) / np.sqrt(n))


def train_eval(model, train_l, test_l, config, beta=0.0, epochs=EPOCHS, device='cpu'):
    """Train model for given epochs and return best test accuracy."""
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)
    best_acc = 0.0
    final_acc = 0.0

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

        # Evaluate
        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for X, y in test_l:
                if config in ['afm_qr', 'afm_rib']:
                    logits, _, _, _, _ = model(X)
                else:
                    logits, _, _, _ = model(X)
                correct += (logits.argmax(1) == y).sum().item()
                total += y.size(0)
        acc = correct / total if total > 0 else 0
        if acc > best_acc:
            best_acc = acc
        final_acc = acc

    return best_acc, final_acc


# ============================================================
# PHASE 1: Independent Replication (10 seeds)
# ============================================================
def phase1():
    print("\n" + "="*70)
    print("PHASE 1: Independent Replication (10 seeds)")
    print("="*70)

    train_l, test_l, _, _ = get_mnist(batch_size=BS)

    configs = [
        ('baseline_task', 0.0),
        ('afm_qr', 0.0),
        ('afm_rib', 1e-3),
    ]

    results = {}
    for config, beta in configs:
        print(f"\n  Config: {config} (beta={beta})")
        accs = []

        for seed_idx in range(10):
            seed = seed_idx * 42
            torch.manual_seed(seed)
            np.random.seed(seed)

            model = get_model(config)
            best_acc, _ = train_eval(model, train_l, test_l, config, beta)
            accs.append(best_acc)

            if (seed_idx + 1) % 5 == 0:
                print(f"    {seed_idx+1}/10 seeds: mean={np.mean(accs):.4f} +/- {np.std(accs):.4f}")

        mean = float(np.mean(accs))
        std = float(np.std(accs, ddof=1))
        ci = ci_95(accs)

        results[config] = {
            'accs': accs,
            'mean': mean,
            'std': std,
            'ci_95': ci,
            'ci_range': [mean - ci, mean + ci],
            'min': float(min(accs)),
            'max': float(max(accs)),
        }
        print(f"    Result: {mean:.4f} +/- {std:.4f} (95% CI: [{mean-ci:.4f}, {mean+ci:.4f}])")

    # Paired t-test: afm_rib vs baseline_task
    bt = results['baseline_task']['accs']
    ar = results['afm_rib']['accs']
    t_stat, p_val = stats.ttest_rel(ar, bt)
    pooled_std = np.sqrt((np.std(bt, ddof=1)**2 + np.std(ar, ddof=1)**2) / 2)
    cohens_d = float(np.mean(np.array(ar) - np.array(bt)) / pooled_std) if pooled_std > 0 else 0

    results['paired_test'] = {
        'baseline_task_mean': results['baseline_task']['mean'],
        'afm_rib_mean': results['afm_rib']['mean'],
        'diff': float(np.mean(np.array(ar) - np.array(bt))),
        't_stat': float(t_stat),
        'p_value': float(p_val),
        'cohens_d': cohens_d,
        'significant_005': bool(p_val < 0.05),
    }
    print(f"\n  Paired t-test (AFM+RIB vs Baseline): t={t_stat:.3f}, p={p_val:.4f}, d={cohens_d:.3f}")
    print(f"  Significant at alpha=0.05? {'YES' if p_val < 0.05 else 'NO'}")

    save('phase1', results)
    return results


# ============================================================
# PHASE 2: Multi-Dataset (5 seeds per dataset)
# ============================================================
def phase2():
    print("\n" + "="*70)
    print("PHASE 2: Multi-Dataset (5 seeds per dataset)")
    print("="*70)

    datasets = {
        'fashion': lambda: get_fashion_mnist(batch_size=BS),
        'kmnist': lambda: get_kmnist(batch_size=BS),
        'cifar10': lambda: get_cifar10(batch_size=BS),
        'synthetic': lambda: get_synthetic(n_samples=20000, batch_size=BS),
    }

    configs = [
        ('baseline_task', 0.0),
        ('afm_qr', 0.0),
        ('afm_rib', 1e-3),
    ]

    results = {}

    for ds_name, ds_loader in datasets.items():
        print(f"\n  Dataset: {ds_name}")
        try:
            train_l, test_l, in_dim, nc = ds_loader()
            print(f"    Loaded: {in_dim} dims, {nc} classes")
        except Exception as e:
            print(f"    FAILED to load: {e}")
            traceback.print_exc()
            results[ds_name] = {'error': str(e)}
            continue

        results[ds_name] = {'input_dim': in_dim, 'num_classes': nc}

        for config, beta in configs:
            accs = []
            for seed_idx in range(5):
                seed = seed_idx * 42
                torch.manual_seed(seed)
                np.random.seed(seed)

                # For CIFAR-10, adjust hidden_dim and latent_dim proportionally
                if in_dim > 784:
                    model = get_model(config, input_dim=in_dim, hidden_dim=512,
                                      latent_dim=128, d=32, K=4, num_classes=nc)
                else:
                    model = get_model(config, input_dim=in_dim, num_classes=nc)

                best_acc, _ = train_eval(model, train_l, test_l, config, beta)
                accs.append(best_acc)

            results[ds_name][config] = {
                'accs': accs,
                'mean': float(np.mean(accs)),
                'std': float(np.std(accs, ddof=1)) if len(accs) > 1 else 0.0,
            }
            print(f"    {config}: {np.mean(accs):.4f} +/- {np.std(accs):.4f}")

    save('phase2', results)
    return results


# ============================================================
# PHASE 3: Ablation Study (10 seeds)
# ============================================================
def phase3():
    print("\n" + "="*70)
    print("PHASE 3: Ablation Study (10 seeds)")
    print("="*70)

    train_l, test_l, _, _ = get_mnist(batch_size=BS)

    ablation_configs = [
        ('baseline_task', 0.0),       # 1. Baseline + L_task (beta=0)
        ('baseline_vae', 1e-3),       # 2. Baseline + beta-VAE
        ('afm_no_qr', 0.0),          # 3. AFM without QR (beta=0)
        ('afm_no_qr', 1e-3),         # 4. AFM without QR + KL (beta=1e-3)
        ('afm_qr', 0.0),             # 5. AFM with QR, no KL
        ('afm_rib', 1e-3),           # 6. AFM + L_RIB (Stiefel + KL)
    ]

    results = {}

    for config, beta in ablation_configs:
        key = f"{config}_b{beta}" if beta > 0 else config
        print(f"\n  Config: {key}")
        accs = []

        for seed_idx in range(10):
            seed = seed_idx * 42
            torch.manual_seed(seed)
            np.random.seed(seed)

            model = get_model(config)
            best_acc, _ = train_eval(model, train_l, test_l, config, beta)
            accs.append(best_acc)

        mean = float(np.mean(accs))
        std = float(np.std(accs, ddof=1))
        ci = ci_95(accs)

        results[key] = {
            'config': config,
            'beta': beta,
            'accs': accs,
            'mean': mean,
            'std': std,
            'ci_95': ci,
        }
        print(f"    Result: {mean:.4f} +/- {std:.4f}")

    # Ablation analysis
    print("\n  === ABLATION ANALYSIS ===")
    base_acc = results['baseline_task']['mean']

    for key in results:
        diff = results[key]['mean'] - base_acc
        direction = "BETTER" if diff > 0 else ("WORSE" if diff < 0 else "SAME")
        print(f"    {key}: delta = {diff:+.4f} vs baseline [{direction}]")

    save('phase3', results)
    return results


# ============================================================
# PHASE 4: KL Collapse Investigation
# ============================================================
def phase4():
    print("\n" + "="*70)
    print("PHASE 4: KL Collapse Investigation")
    print("="*70)

    train_l, test_l, _, _ = get_mnist(batch_size=BS)
    beta_values = [1e-5, 1e-4, 5e-4, 1e-3, 5e-3, 1e-2, 5e-2, 1e-1, 5e-1, 1.0]

    # Test 1: Beta sweep for both baseline_vae and afm_rib
    print("\n  Test 1: Beta sweep (collapse threshold)")
    collapse_results = {}
    for beta in beta_values:
        for config in ['baseline_vae', 'afm_rib']:
            torch.manual_seed(42)
            np.random.seed(42)
            model = get_model('baseline_task' if config == 'baseline_vae' else config)
            best_acc, _ = train_eval(model, train_l, test_l, config, beta)
            key = f"{config}_b{beta}"
            collapse_results[key] = {
                'config': config,
                'beta': beta,
                'acc': best_acc,
                'collapsed': bool(best_acc < 0.5),
            }
            status = "COLLAPSED" if best_acc < 0.5 else "OK"
            print(f"    {key}: acc={best_acc:.4f} [{status}]")

    # Test 2: Track ||mu|| and ||S|| over 8 epochs at high beta
    print("\n  Test 2: Latent norm tracking at beta=1e-2")
    norm_tracking = {}

    for config in ['baseline_task', 'afm_rib']:
        torch.manual_seed(42)
        np.random.seed(42)
        model = get_model(config)
        optimizer = torch.optim.Adam(model.parameters(), lr=LR)

        mu_norms = []
        s_norms = []

        for epoch in range(8):
            model.train()
            for X, y in train_l:
                optimizer.zero_grad()
                if config == 'afm_rib':
                    logits, recon, mu, lv, kl = model(X)
                    loss = compute_loss(model, config, logits, y, mu, lv, kl, beta=1e-2)
                else:
                    logits, recon, mu, lv = model(X)
                    # For baseline with VAE KL at beta=1e-2
                    loss = compute_loss(model, 'baseline_vae', logits, y, mu, lv, None, beta=1e-2)
                loss.backward()
                optimizer.step()

            # Measure norms after each epoch
            model.eval()
            with torch.no_grad():
                X_s = next(iter(test_l))[0]
                if config == 'afm_rib':
                    _, _, mu, lv, kl = model(X_s)
                    S, _ = model.stiefel(mu, lv)
                    mu_norms.append(float(mu.norm(dim=-1).mean().item()))
                    s_norms.append(float(S.norm(dim=(1,2)).mean().item()))
                else:
                    _, _, mu, lv = model(X_s)
                    mu_norms.append(float(mu.norm(dim=-1).mean().item()))

        norm_tracking[config] = {
            'beta': 1e-2,
            'mu_norm_per_epoch': mu_norms,
        }
        if config == 'afm_rib':
            norm_tracking[config]['s_norm_per_epoch'] = s_norms

        print(f"    {config} at beta=1e-2: mu_norm final={mu_norms[-1]:.4f}")
        if s_norms:
            print(f"    {config} at beta=1e-2: s_norm final={s_norms[-1]:.4f}")

    # Test 3: QR(near_zero_input) still produces ||Q|| ≈ sqrt(d*K)
    print("\n  Test 3: QR projection stability (near-zero input)")
    qr_results = {}
    for d_val in [16, 32, 64]:
        for K_val in [2, 4, 8]:
            near_zero = torch.randn(100, d_val, K_val) * 1e-10
            Q = stiefel_project_qr(near_zero)
            norms = Q.norm(dim=(1,2))
            expected_norm = np.sqrt(d_val * K_val)
            key = f"d{d_val}_K{K_val}"
            qr_results[key] = {
                'd': d_val,
                'K': K_val,
                'expected_norm': expected_norm,
                'mean_norm': float(norms.mean().item()),
                'std_norm': float(norms.std().item()),
                'ratio': float(norms.mean().item() / expected_norm),
            }
            print(f"    d={d_val}, K={K_val}: ||QR(eps)||={norms.mean().item():.4f}, "
                  f"expected sqrt({d_val}*{K_val})={expected_norm:.4f}, ratio={norms.mean().item()/expected_norm:.4f}")

    # Identify collapse thresholds
    print("\n  Collapse threshold analysis:")
    for config in ['baseline_vae', 'afm_rib']:
        collapse_betas = []
        for beta in beta_values:
            key = f"{config}_b{beta}"
            if key in collapse_results and collapse_results[key]['collapsed']:
                collapse_betas.append(beta)
        if collapse_betas:
            threshold = min(collapse_betas)
            print(f"    {config}: collapse at beta >= {threshold}")
        else:
            print(f"    {config}: NO collapse in tested range")

    save('phase4', {
        'collapse_sweep': collapse_results,
        'norm_tracking': norm_tracking,
        'qr_test': qr_results,
    })
    return collapse_results, norm_tracking, qr_results


# ============================================================
# PHASE 5: Continual Learning Benchmarks
# ============================================================
def phase5():
    print("\n" + "="*70)
    print("PHASE 5: Continual Learning Benchmarks")
    print("="*70)

    results = {}

    # ---- Multi-task model definitions ----
    from ablation_models import BaselineLTask, AFMWithQR, AFMWithRIB

    class MTLBaseline(BaselineLTask):
        """Multi-task baseline with separate heads per task."""
        def __init__(self, input_dim, hidden_dim, latent_dim, task_classes):
            super().__init__(input_dim, hidden_dim, latent_dim, task_classes[0])
            self.heads = nn.ModuleList([
                nn.Sequential(nn.Linear(latent_dim, hidden_dim//2), nn.ReLU(),
                              nn.Linear(hidden_dim//2, nc))
                for nc in task_classes
            ])
            self.classifier = self.heads[0]

        def forward(self, x, task_id=0):
            h = self.encoder(x)
            mu, lv = self.fc_mu(h), self.fc_logvar(h)
            if self.training:
                z = mu + torch.exp(0.5 * lv) * torch.randn_like(mu)
            else:
                z = mu
            logits = self.heads[task_id](z)
            return logits, mu, lv

    class MTLAFMQR(AFMWithQR):
        """Multi-task AFM+QR with separate heads per task."""
        def __init__(self, input_dim, hidden_dim, d, K, task_classes):
            super().__init__(input_dim, hidden_dim, d, K, task_classes[0])
            self.heads = nn.ModuleList([
                nn.Sequential(nn.Linear(d*K, hidden_dim//2), nn.ReLU(),
                              nn.Linear(hidden_dim//2, nc))
                for nc in task_classes
            ])
            self.classifier = self.heads[0]

        def forward(self, x, task_id=0):
            h = self.encoder(x)
            mu, lv = self.fc_mu(h), self.fc_logvar(h)
            S, kl = self.stiefel(mu, lv)
            S_flat = S.reshape(S.shape[0], -1)
            logits = self.heads[task_id](S_flat)
            return logits, mu, lv, kl

    class MTLAFMRIB(AFMWithRIB):
        """Multi-task AFM+RIB with separate heads per task."""
        def __init__(self, input_dim, hidden_dim, d, K, task_classes):
            super().__init__(input_dim, hidden_dim, d, K, task_classes[0])
            self.heads = nn.ModuleList([
                nn.Sequential(nn.Linear(d*K, hidden_dim//2), nn.ReLU(),
                              nn.Linear(hidden_dim//2, nc))
                for nc in task_classes
            ])
            self.classifier = self.heads[0]

        def forward(self, x, task_id=0):
            h = self.encoder(x)
            mu, lv = self.fc_mu(h), self.fc_logvar(h)
            S, kl = self.stiefel(mu, lv)
            S_flat = S.reshape(S.shape[0], -1)
            logits = self.heads[task_id](S_flat)
            return logits, mu, lv, kl

    # --- Split-MNIST ---
    print("\n  Split-MNIST (5 binary tasks)")
    try:
        split_tasks = get_split_mnist(batch_size=BS)
        task_classes = [nc for _, _, _, nc in split_tasks]

        for config_name in ['baseline_task', 'afm_qr', 'afm_rib']:
            print(f"    Config: {config_name}")
            torch.manual_seed(42)
            np.random.seed(42)

            if config_name == 'baseline_task':
                model = MTLBaseline(784, 256, 128, task_classes)
                mtype = 'baseline'
                beta = 0.0
            elif config_name == 'afm_qr':
                model = MTLAFMQR(784, 256, 32, 4, task_classes)
                mtype = 'afm_qr'
                beta = 0.0
            else:  # afm_rib
                model = MTLAFMRIB(784, 256, 32, 4, task_classes)
                mtype = 'afm_rib'
                beta = 1e-3

            num_tasks = len(split_tasks)
            acc_matrix = np.zeros((num_tasks, num_tasks))

            for task_id in range(num_tasks):
                train_l, test_l, in_dim, nc = split_tasks[task_id]
                optimizer = torch.optim.Adam(model.parameters(), lr=LR)

                for epoch in range(10):
                    model.train()
                    for X, y in train_l:
                        optimizer.zero_grad()
                        if mtype == 'baseline':
                            logits, mu, lv = model(X, task_id)
                            ce = F.cross_entropy(logits, y)
                            loss = ce
                        else:
                            logits, mu, lv, kl = model(X, task_id)
                            ce = F.cross_entropy(logits, y)
                            loss = ce + (beta * kl if kl is not None else 0)
                        loss.backward()
                        optimizer.step()

                # Evaluate all tasks after training on this one
                model.eval()
                for eval_id in range(num_tasks):
                    _, eval_l, _, _ = split_tasks[eval_id]
                    correct, total = 0, 0
                    with torch.no_grad():
                        for X, y in eval_l:
                            if mtype == 'baseline':
                                logits, _, _ = model(X, eval_id)
                            else:
                                logits, _, _, _ = model(X, eval_id)
                            correct += (logits.argmax(1) == y).sum().item()
                            total += y.size(0)
                    acc_matrix[task_id, eval_id] = correct / total if total > 0 else 0

            # Compute forgetting
            forgetting = []
            for tid in range(num_tasks - 1):
                acc_after = acc_matrix[tid, tid]
                acc_final = acc_matrix[num_tasks - 1, tid]
                forgetting.append(float(acc_after - acc_final))

            avg_forgetting = float(np.mean(forgetting)) if forgetting else 0.0
            bwt = float(np.mean([acc_matrix[-1, i] - acc_matrix[i, i] for i in range(num_tasks - 1)]))
            avg_acc = float(np.mean([acc_matrix[-1, i] for i in range(num_tasks)]))

            results[f'split_mnist_{config_name}'] = {
                'acc_matrix': acc_matrix.tolist(),
                'forgetting': forgetting,
                'avg_forgetting': avg_forgetting,
                'backward_transfer': bwt,
                'avg_accuracy': avg_acc,
            }
            print(f"      Forgetting: {avg_forgetting:.4f}, BWT: {bwt:.4f}, Avg Acc: {avg_acc:.4f}")

    except Exception as e:
        print(f"    Split-MNIST FAILED: {e}")
        traceback.print_exc()
        results['split_mnist_error'] = str(e)

    # --- Permuted-MNIST ---
    print("\n  Permuted-MNIST (5 tasks)")
    try:
        perm_tasks = get_permuted_mnist(n_tasks=5, batch_size=BS)

        for config_name in ['baseline_task', 'afm_qr', 'afm_rib']:
            print(f"    Config: {config_name}")
            torch.manual_seed(42)
            np.random.seed(42)

            # Permuted-MNIST uses single 10-class head
            if config_name == 'baseline_task':
                model = BaselineLTask(784, 256, 128, 10)
                mtype = 'baseline'
                beta = 0.0
            elif config_name == 'afm_qr':
                model = AFMWithQR(784, 256, 32, 4, 10)
                mtype = 'afm_qr'
                beta = 0.0
            else:
                model = AFMWithRIB(784, 256, 32, 4, 10)
                mtype = 'afm_rib'
                beta = 1e-3

            num_tasks = len(perm_tasks)
            acc_matrix = np.zeros((num_tasks, num_tasks))

            for task_id in range(num_tasks):
                train_l, test_l, in_dim, nc = perm_tasks[task_id]
                optimizer = torch.optim.Adam(model.parameters(), lr=LR)

                for epoch in range(10):
                    model.train()
                    for X, y in train_l:
                        optimizer.zero_grad()
                        if mtype == 'baseline':
                            logits, recon, mu, lv = model(X)
                            ce = F.cross_entropy(logits, y)
                            loss = ce
                        else:
                            logits, recon, mu, lv, kl = model(X)
                            ce = F.cross_entropy(logits, y)
                            loss = ce + (beta * kl if kl is not None else 0)
                        loss.backward()
                        optimizer.step()

                # Evaluate all tasks
                model.eval()
                for eval_id in range(num_tasks):
                    _, eval_l, _, _ = perm_tasks[eval_id]
                    correct, total = 0, 0
                    with torch.no_grad():
                        for X, y in eval_l:
                            if mtype == 'baseline':
                                logits, _, _, _ = model(X)
                            else:
                                logits, _, _, _, _ = model(X)
                            correct += (logits.argmax(1) == y).sum().item()
                            total += y.size(0)
                    acc_matrix[task_id, eval_id] = correct / total if total > 0 else 0

            forgetting = []
            for tid in range(num_tasks - 1):
                acc_after = acc_matrix[tid, tid]
                acc_final = acc_matrix[num_tasks - 1, tid]
                forgetting.append(float(acc_after - acc_final))

            avg_forgetting = float(np.mean(forgetting)) if forgetting else 0.0
            bwt = float(np.mean([acc_matrix[-1, i] - acc_matrix[i, i] for i in range(num_tasks - 1)]))
            avg_acc = float(np.mean([acc_matrix[-1, i] for i in range(num_tasks)]))

            results[f'permuted_mnist_{config_name}'] = {
                'acc_matrix': acc_matrix.tolist(),
                'forgetting': forgetting,
                'avg_forgetting': avg_forgetting,
                'backward_transfer': bwt,
                'avg_accuracy': avg_acc,
            }
            print(f"      Forgetting: {avg_forgetting:.4f}, BWT: {bwt:.4f}, Avg Acc: {avg_acc:.4f}")

    except Exception as e:
        print(f"    Permuted-MNIST FAILED: {e}")
        traceback.print_exc()
        results['permuted_mnist_error'] = str(e)

    save('phase5', results)
    return results


# ============================================================
# PHASE 6: Representation Analysis
# ============================================================
def phase6():
    print("\n" + "="*70)
    print("PHASE 6: Representation Analysis")
    print("="*70)

    from sklearn.decomposition import PCA
    from sklearn.metrics import silhouette_score

    train_l, test_l, _, _ = get_mnist(batch_size=BS)

    configs = ['baseline_task', 'afm_qr', 'afm_rib']
    results = {}

    for config in configs:
        print(f"\n  Training {config}...")
        torch.manual_seed(42)
        np.random.seed(42)
        model = get_model(config)
        beta = 1e-3 if config == 'afm_rib' else 0.0
        train_eval(model, train_l, test_l, config, beta)

        # Extract representations from first 10 batches
        model.eval()
        latents_list, labels_list = [], []
        stiefel_list = []

        with torch.no_grad():
            for i, (X, y) in enumerate(test_l):
                if i >= 10:
                    break
                if config in ['afm_qr', 'afm_rib']:
                    logits, recon, mu, lv, kl = model(X)
                    S, _ = model.stiefel(mu, lv)
                    latent = S.reshape(S.shape[0], -1)
                    stiefel_list.append(S.numpy())
                else:
                    logits, recon, mu, lv = model(X)
                    latent = mu
                latents_list.append(latent.numpy())
                labels_list.append(y.numpy())

        lat = np.concatenate(latents_list)
        lab = np.concatenate(labels_list)

        # PCA explained variance (top 10)
        pca = PCA(n_components=min(10, lat.shape[1]))
        pca.fit(lat)
        ev = pca.explained_variance_ratio_

        # Silhouette score
        sil = silhouette_score(lat, lab, sample_size=min(5000, len(lab)))

        # Thread analysis (AFM models only)
        thread_info = {}
        if config in ['afm_qr', 'afm_rib'] and stiefel_list:
            stiefel = np.concatenate(stiefel_list)
            K = stiefel.shape[2]

            # Thread-class correlation
            tc_corr = []
            for k in range(K):
                # Use mean of thread as scalar projection
                proj = stiefel[:, :, k].mean(axis=1)
                c = np.corrcoef(proj, lab[:len(proj)])[0, 1]
                tc_corr.append(float(abs(c)) if not np.isnan(c) else 0.0)

            # Inter-thread dot products
            dots = []
            for k1 in range(K):
                for k2 in range(k1+1, K):
                    d = float(np.mean(np.sum(stiefel[:, :, k1] * stiefel[:, :, k2], axis=1)))
                    dots.append(d)

            # Thread norms
            t_norms = [float(np.mean(np.linalg.norm(stiefel[:, :, k], axis=1))) for k in range(K)]

            thread_info = {
                'thread_class_correlation': tc_corr,
                'inter_thread_dots': dots,
                'thread_norms': t_norms,
            }

        results[config] = {
            'pca_explained_variance': ev.tolist(),
            'pca_cumulative_10': float(ev.sum()),
            'silhouette_score': float(sil),
            'thread_info': thread_info,
        }

        print(f"    Silhouette: {sil:.4f}, PCA cumulative (10): {ev.sum():.4f}")
        if thread_info:
            print(f"    Thread-class |corr|: {[f'{c:.4f}' for c in tc_corr]}")
            print(f"    Inter-thread dots: {[f'{d:.6f}' for d in dots]}")

    save('phase6', results)
    return results


# ============================================================
# PHASE 7: Failure Analysis
# ============================================================
def phase7(p1, p2, p3, p4, p5, p6):
    print("\n" + "="*70)
    print("PHASE 7: Failure Analysis")
    print("="*70)

    analysis = {
        'where_afm_performs_worse': [],
        'unstable_beta_values': [],
        'optimization_failures': [],
        'datasets_where_afm_doesnt_help': [],
        'overall_assessment': {},
    }

    # --- Phase 1 Analysis ---
    if isinstance(p1, dict) and 'paired_test' in p1:
        pt = p1['paired_test']
        diff = pt.get('diff', 0)
        if diff < 0:
            analysis['where_afm_performs_worse'].append(
                f"Phase 1: AFM+RIB is {abs(diff):.4f} WORSE than baseline on MNIST"
            )
        if not pt.get('significant_005', False):
            analysis['optimization_failures'].append(
                f"Phase 1: Accuracy difference NOT statistically significant (p={pt.get('p_value', 'N/A'):.4f})"
            )

    # --- Phase 2 Analysis ---
    if isinstance(p2, dict):
        for ds_name in p2:
            if isinstance(p2[ds_name], dict) and 'error' in p2[ds_name]:
                analysis['optimization_failures'].append(
                    f"Phase 2: {ds_name} dataset failed to load: {p2[ds_name]['error']}"
                )
            elif isinstance(p2[ds_name], dict):
                bt = p2[ds_name].get('baseline_task', {}).get('mean', 0)
                ar = p2[ds_name].get('afm_rib', {}).get('mean', 0)
                aq = p2[ds_name].get('afm_qr', {}).get('mean', 0)
                if ar < bt:
                    analysis['datasets_where_afm_doesnt_help'].append(
                        f"{ds_name}: AFM+RIB ({ar:.4f}) < Baseline ({bt:.4f})"
                    )
                if aq < bt:
                    analysis['datasets_where_afm_doesnt_help'].append(
                        f"{ds_name}: AFM+QR ({aq:.4f}) < Baseline ({bt:.4f})"
                    )

    # --- Phase 3 Analysis ---
    if isinstance(p3, dict):
        base = p3.get('baseline_task', {}).get('mean', 0)
        for key, val in p3.items():
            if isinstance(val, dict) and 'mean' in val:
                diff = val['mean'] - base
                if diff < -0.005:
                    analysis['where_afm_performs_worse'].append(
                        f"Phase 3: {key} is {abs(diff):.4f} worse than baseline"
                    )

    # --- Phase 4 Analysis ---
    if isinstance(p4, tuple) and len(p4) == 3:
        collapse_sweep, norm_tracking, qr_results = p4
        for key, val in collapse_sweep.items():
            if isinstance(val, dict) and val.get('collapsed', False):
                analysis['unstable_beta_values'].append(
                    f"{key}: acc={val['acc']:.4f} (COLLAPSED)"
                )
        for config, ntrack in norm_tracking.items():
            mu_norms = ntrack.get('mu_norm_per_epoch', [])
            if mu_norms and mu_norms[-1] < 1.0:
                analysis['optimization_failures'].append(
                    f"Phase 4: {config} at beta=1e-2, mu_norm collapsed to {mu_norms[-1]:.4f}"
                )
    elif isinstance(p4, dict):
        # Handle if p4 was saved directly
        collapse_sweep = p4.get('collapse_sweep', {})
        for key, val in collapse_sweep.items():
            if isinstance(val, dict) and val.get('collapsed', False):
                analysis['unstable_beta_values'].append(
                    f"{key}: acc={val['acc']:.4f} (COLLAPSED)"
                )

    # --- Phase 5 Analysis ---
    if isinstance(p5, dict):
        for key, val in p5.items():
            if isinstance(val, dict) and 'avg_forgetting' in val:
                af = val['avg_forgetting']
                avg_acc = val.get('avg_accuracy', 0)
                if af < 0:
                    analysis['optimization_failures'].append(
                        f"Phase 5: {key} has NEGATIVE forgetting (improvement, anomaly?)"
                    )
                if 'baseline_task' in key and 'split' in key:
                    pass  # Expected baseline forgetting
                if 'afm' in key:
                    if avg_acc < 0.8 and 'split' in key:
                        analysis['where_afm_performs_worse'].append(
                            f"Phase 5: {key} avg_accuracy={avg_acc:.4f} is low"
                        )

    # --- Phase 6 Analysis ---
    if isinstance(p6, dict):
        bt_sil = p6.get('baseline_task', {}).get('silhouette_score', 0)
        ar_sil = p6.get('afm_rib', {}).get('silhouette_score', 0)
        if ar_sil < bt_sil:
            analysis['where_afm_performs_worse'].append(
                f"Phase 6: AFM+RIB silhouette ({ar_sil:.4f}) < Baseline ({bt_sil:.4f})"
            )
        # Thread analysis
        for config in ['afm_qr', 'afm_rib']:
            ti = p6.get(config, {}).get('thread_info', {})
            if ti:
                dots = ti.get('inter_thread_dots', [])
                if dots and max(abs(d) for d in dots) > 0.1:
                    analysis['optimization_failures'].append(
                        f"Phase 6: {config} has high inter-thread dot products (max={max(abs(d) for d in dots):.4f})"
                    )

    # --- Overall assessment ---
    total_failures = (len(analysis['where_afm_performs_worse']) +
                     len(analysis['unstable_beta_values']) +
                     len(analysis['optimization_failures']) +
                     len(analysis['datasets_where_afm_doesnt_help']))

    analysis['overall_assessment'] = {
        'total_issues': total_failures,
        'worse_count': len(analysis['where_afm_performs_worse']),
        'unstable_count': len(analysis['unstable_beta_values']),
        'failure_count': len(analysis['optimization_failures']),
        'no_help_count': len(analysis['datasets_where_afm_doesnt_help']),
    }

    print("\n  === FAILURE ANALYSIS SUMMARY ===")
    print(f"  Total issues found: {total_failures}")
    for category, items in analysis.items():
        if isinstance(items, list) and items:
            print(f"\n  {category}:")
            for item in items:
                print(f"    - {item}")

    save('phase7', analysis)
    return analysis


# ============================================================
# MAIN
# ============================================================
def main():
    print("\n" + "#"*70)
    print("# AFM-Lite Validation Program v0.2")
    print("# All 7 phases: Replication, Multi-Dataset, Ablation, Collapse,")
    print("# Continual Learning, Representation Analysis, Failure Analysis")
    print(f"# Config: epochs={EPOCHS}, batch_size={BS}, lr={LR}")
    print("#"*70)

    t0 = time.time()
    all_results = {}

    # Phase 1
    try:
        p1 = phase1()
        all_results['phase1'] = p1
    except Exception as e:
        print(f"Phase 1 FAILED: {e}")
        traceback.print_exc()
        p1 = {}
        all_results['phase1'] = {'error': str(e)}

    # Phase 2
    try:
        p2 = phase2()
        all_results['phase2'] = p2
    except Exception as e:
        print(f"Phase 2 FAILED: {e}")
        traceback.print_exc()
        p2 = {}
        all_results['phase2'] = {'error': str(e)}

    # Phase 3
    try:
        p3 = phase3()
        all_results['phase3'] = p3
    except Exception as e:
        print(f"Phase 3 FAILED: {e}")
        traceback.print_exc()
        p3 = {}
        all_results['phase3'] = {'error': str(e)}

    # Phase 4
    try:
        p4 = phase4()
        all_results['phase4_raw'] = p4
    except Exception as e:
        print(f"Phase 4 FAILED: {e}")
        traceback.print_exc()
        p4 = ({}, {}, {})

    # Phase 5
    try:
        p5 = phase5()
        all_results['phase5'] = p5
    except Exception as e:
        print(f"Phase 5 FAILED: {e}")
        traceback.print_exc()
        p5 = {}
        all_results['phase5'] = {'error': str(e)}

    # Phase 6
    try:
        p6 = phase6()
        all_results['phase6'] = p6
    except Exception as e:
        print(f"Phase 6 FAILED: {e}")
        traceback.print_exc()
        p6 = {}
        all_results['phase6'] = {'error': str(e)}

    # Phase 7
    try:
        p7 = phase7(p1, p2, p3, p4, p5, p6)
        all_results['phase7'] = p7
    except Exception as e:
        print(f"Phase 7 FAILED: {e}")
        traceback.print_exc()
        p7 = {}

    total_time = time.time() - t0
    print(f"\n\nTotal validation time: {total_time:.1f}s ({total_time/60:.1f}min)")

    # Save combined results
    save('all_phases_summary', {
        'phase1_status': 'completed' if p1 else 'failed',
        'phase2_status': 'completed' if p2 else 'failed',
        'phase3_status': 'completed' if p3 else 'failed',
        'phase4_status': 'completed' if p4 else 'failed',
        'phase5_status': 'completed' if p5 else 'failed',
        'phase6_status': 'completed' if p6 else 'failed',
        'phase7_status': 'completed' if p7 else 'failed',
        'total_time_seconds': total_time,
    })

    # Generate final report
    generate_final_report(p1, p2, p3, p4, p5, p6, p7)

    return all_results


def generate_final_report(p1, p2, p3, p4, p5, p6, p7):
    """Generate AFM_VALIDATION_REPORT_v0.2.md"""
    report = []

    report.append("# AFM-Lite Validation Report v0.2")
    report.append("")
    report.append("## Executive Summary")
    report.append("")
    report.append("This report presents the results of a comprehensive 7-phase validation")
    report.append("of the AFM-Lite (Avadhana Field Model) framework, testing the core claims")
    report.append("about Stiefel manifold constraints and Riemannian Information Bottleneck (RIB).")
    report.append("")

    # Phase 1
    report.append("## Phase 1: Independent Replication (10 seeds)")
    report.append("")
    if isinstance(p1, dict) and 'paired_test' in p1:
        for config in ['baseline_task', 'afm_qr', 'afm_rib']:
            if config in p1:
                r = p1[config]
                report.append(f"- **{config}**: {r['mean']:.4f} +/- {r['std']:.4f} (95% CI: [{r['ci_range'][0]:.4f}, {r['ci_range'][1]:.4f}])")
        pt = p1['paired_test']
        report.append(f"- **Paired t-test** (AFM+RIB vs Baseline): t={pt['t_stat']:.3f}, p={pt['p_value']:.4f}, Cohen's d={pt['cohens_d']:.3f}")
        sig = "CONFIRMED" if pt['significant_005'] else "UNRESOLVED"
        report.append(f"- **Statistical significance**: {sig}")
    else:
        report.append("- Phase 1 data not available")
    report.append("")

    # Phase 2
    report.append("## Phase 2: Multi-Dataset Generalization")
    report.append("")
    if isinstance(p2, dict):
        for ds_name in ['fashion', 'kmnist', 'cifar10', 'synthetic']:
            if ds_name in p2 and isinstance(p2[ds_name], dict):
                ds = p2[ds_name]
                if 'error' in ds:
                    report.append(f"- **{ds_name}**: FAILED - {ds['error']}")
                else:
                    bt = ds.get('baseline_task', {}).get('mean', 'N/A')
                    aq = ds.get('afm_qr', {}).get('mean', 'N/A')
                    ar = ds.get('afm_rib', {}).get('mean', 'N/A')
                    report.append(f"- **{ds_name}** ({ds.get('input_dim', '?')} dims): Baseline={bt}, AFM+QR={aq}, AFM+RIB={ar}")
    else:
        report.append("- Phase 2 data not available")
    report.append("")

    # Phase 3
    report.append("## Phase 3: Ablation Study")
    report.append("")
    if isinstance(p3, dict):
        report.append("| Config | Beta | Mean Acc | Std | Delta vs Baseline |")
        report.append("|--------|------|----------|-----|--------------------|")
        base = p3.get('baseline_task', {}).get('mean', 0)
        for key in ['baseline_task', 'baseline_vae_b0.001', 'afm_no_qr', 'afm_no_qr_b0.001', 'afm_qr', 'afm_rib_b0.001']:
            if key in p3:
                v = p3[key]
                delta = v['mean'] - base
                report.append(f"| {key} | {v.get('beta', 0)} | {v['mean']:.4f} | {v['std']:.4f} | {delta:+.4f} |")
    report.append("")

    # Phase 4
    report.append("## Phase 4: KL Collapse Investigation")
    report.append("")
    if isinstance(p4, tuple) and len(p4) == 3:
        collapse_sweep, norm_tracking, qr_results = p4
        report.append("### Beta Sweep")
        report.append("| Config | Beta | Accuracy | Collapsed? |")
        report.append("|--------|------|----------|-----------|")
        for key, val in sorted(collapse_sweep.items()):
            report.append(f"| {val['config']} | {val['beta']} | {val['acc']:.4f} | {'YES' if val['collapsed'] else 'No'} |")
        report.append("")
        report.append("### QR Projection Stability")
        for key, val in qr_results.items():
            report.append(f"- {key}: ||QR(eps)||={val['mean_norm']:.4f}, expected={val['expected_norm']:.4f}, ratio={val['ratio']:.4f}")
    report.append("")

    # Phase 5
    report.append("## Phase 5: Continual Learning")
    report.append("")
    if isinstance(p5, dict):
        for bench in ['split_mnist', 'permuted_mnist']:
            report.append(f"### {bench}")
            for config in ['baseline_task', 'afm_qr', 'afm_rib']:
                key = f"{bench}_{config}"
                if key in p5:
                    v = p5[key]
                    report.append(f"- **{config}**: Avg Acc={v['avg_accuracy']:.4f}, Forgetting={v['avg_forgetting']:.4f}, BWT={v['backward_transfer']:.4f}")
    report.append("")

    # Phase 6
    report.append("## Phase 6: Representation Analysis")
    report.append("")
    if isinstance(p6, dict):
        report.append("| Model | Silhouette | PCA Cumulative (10) |")
        report.append("|-------|-----------|---------------------|")
        for config in ['baseline_task', 'afm_qr', 'afm_rib']:
            if config in p6:
                v = p6[config]
                report.append(f"| {config} | {v['silhouette_score']:.4f} | {v['pca_cumulative_10']:.4f} |")
        for config in ['afm_qr', 'afm_rib']:
            ti = p6.get(config, {}).get('thread_info', {})
            if ti:
                report.append(f"\n**Thread Analysis ({config})**:")
                report.append(f"- Thread-class |corr|: {ti.get('thread_class_correlation', [])}")
                report.append(f"- Inter-thread dots: {ti.get('inter_thread_dots', [])}")
    report.append("")

    # Phase 7
    report.append("## Phase 7: Failure Analysis")
    report.append("")
    if isinstance(p7, dict):
        for category in ['where_afm_performs_worse', 'unstable_beta_values',
                         'optimization_failures', 'datasets_where_afm_doesnt_help']:
            items = p7.get(category, [])
            report.append(f"### {category}")
            if items:
                for item in items:
                    report.append(f"- {item}")
            else:
                report.append("- None found")
            report.append("")

    # Classification of effects
    report.append("## Effect Classification")
    report.append("")
    report.append("### 1. Stiefel QR Projection Effect")
    # Determine classification based on data
    if isinstance(p3, dict):
        qr_no_kl = p3.get('afm_qr', {}).get('mean', 0)
        baseline = p3.get('baseline_task', {}).get('mean', 0)
        no_qr = p3.get('afm_no_qr', {}).get('mean', 0)
        if qr_no_kl > baseline + 0.005:
            report.append("- **CONFIRMED**: QR projection improves accuracy over baseline without KL")
        elif qr_no_kl > baseline:
            report.append("- **PARTIALLY CONFIRMED**: QR projection provides marginal improvement")
        else:
            report.append("- **ARTIFACT**: QR projection does not improve accuracy alone")
    report.append("")

    report.append("### 2. RIB (KL Regularization) Effect")
    if isinstance(p3, dict):
        rib = p3.get('afm_rib_b0.001', {}).get('mean', 0)
        baseline = p3.get('baseline_task', {}).get('mean', 0)
        vae = p3.get('baseline_vae_b0.001', {}).get('mean', 0)
        if rib > baseline + 0.005:
            report.append("- **CONFIRMED**: AFM+RIB improves over baseline")
        elif rib > baseline:
            report.append("- **PARTIALLY CONFIRMED**: AFM+RIB provides marginal improvement")
        else:
            report.append("- **FAILED**: AFM+RIB does not improve over baseline")
        if isinstance(vae, (int, float)) and rib > vae + 0.003:
            report.append("- **CONFIRMED**: Stiefel+KL > Gaussian+KL (AFM+RIB beats baseline+VAE)")
        elif isinstance(vae, (int, float)) and rib > vae:
            report.append("- **PARTIALLY CONFIRMED**: AFM+RIB marginally better than baseline+VAE")
        elif isinstance(vae, (int, float)):
            report.append("- **ARTIFACT**: No advantage of Stiefel+KL over Gaussian+KL")
    report.append("")

    report.append("### 3. KL Collapse Resistance")
    if isinstance(p4, tuple) and len(p4) == 3:
        collapse_sweep = p4[0]
        # Find collapse thresholds
        vae_collapse = None
        rib_collapse = None
        beta_values = [1e-5, 1e-4, 5e-4, 1e-3, 5e-3, 1e-2, 5e-2, 1e-1, 5e-1, 1.0]
        for beta in beta_values:
            vae_key = f"baseline_vae_b{beta}"
            rib_key = f"afm_rib_b{beta}"
            if vae_key in collapse_sweep and collapse_sweep[vae_key].get('collapsed') and vae_collapse is None:
                vae_collapse = beta
            if rib_key in collapse_sweep and collapse_sweep[rib_key].get('collapsed') and rib_collapse is None:
                rib_collapse = beta
        if vae_collapse and rib_collapse and rib_collapse > vae_collapse:
            report.append("- **CONFIRMED**: AFM+RIB resists KL collapse better than baseline+VAE")
        elif vae_collapse and not rib_collapse:
            report.append("- **CONFIRMED**: AFM+RIB resists collapse; baseline+VAE collapses")
        elif not vae_collapse and not rib_collapse:
            report.append("- **UNRESOLVED**: Neither collapsed in tested range")
        else:
            report.append("- **ARTIFACT**: No clear collapse resistance advantage")
    report.append("")

    report.append("### 4. Catastrophic Forgetting Reduction")
    if isinstance(p5, dict):
        split_base = p5.get('split_mnist_baseline_task', {}).get('avg_forgetting', 0)
        split_rib = p5.get('split_mnist_afm_rib', {}).get('avg_forgetting', 0)
        perm_base = p5.get('permuted_mnist_baseline_task', {}).get('avg_forgetting', 0)
        perm_rib = p5.get('permuted_mnist_afm_rib', {}).get('avg_forgetting', 0)
        if split_rib < split_base - 0.02:
            report.append(f"- **CONFIRMED**: Split-MNIST forgetting reduced ({split_rib:.4f} vs {split_base:.4f})")
        elif split_rib < split_base:
            report.append(f"- **PARTIALLY CONFIRMED**: Split-MNIST forgetting slightly reduced ({split_rib:.4f} vs {split_base:.4f})")
        else:
            report.append(f"- **FAILED**: Split-MNIST forgetting NOT reduced ({split_rib:.4f} vs {split_base:.4f})")
        if perm_rib < perm_base - 0.02:
            report.append(f"- **CONFIRMED**: Permuted-MNIST forgetting reduced ({perm_rib:.4f} vs {perm_base:.4f})")
        elif perm_rib < perm_base:
            report.append(f"- **PARTIALLY CONFIRMED**: Permuted-MNIST forgetting slightly reduced ({perm_rib:.4f} vs {perm_base:.4f})")
        else:
            report.append(f"- **FAILED**: Permuted-MNIST forgetting NOT reduced ({perm_rib:.4f} vs {perm_base:.4f})")
    report.append("")

    report.append("### 5. Representation Quality")
    if isinstance(p6, dict):
        bt_sil = p6.get('baseline_task', {}).get('silhouette_score', 0)
        ar_sil = p6.get('afm_rib', {}).get('silhouette_score', 0)
        if ar_sil > bt_sil + 0.02:
            report.append(f"- **CONFIRMED**: AFM+RIB has better cluster separation (silhouette={ar_sil:.4f} vs {bt_sil:.4f})")
        elif ar_sil > bt_sil:
            report.append(f"- **PARTIALLY CONFIRMED**: AFM+RIB slightly better cluster separation (silhouette={ar_sil:.4f} vs {bt_sil:.4f})")
        else:
            report.append(f"- **FAILED**: AFM+RIB has worse cluster separation (silhouette={ar_sil:.4f} vs {bt_sil:.4f})")
    report.append("")

    # Final assessment
    report.append("## Final Assessment")
    report.append("")
    report.append("### Which ideas survived stronger experiments?")
    report.append("")
    report.append("(See effect classifications above for detailed per-effect assessment.)")
    report.append("")

    report.append("### Which ideas should be abandoned?")
    report.append("")
    report.append("(Determined from failure analysis above.)")
    report.append("")

    report.append("### Is AFM currently a representation-learning technique or something more?")
    report.append("")
    report.append("Based on the evidence across all phases:")
    report.append("- If AFM+RIB improves accuracy significantly: representation-learning + regularization")
    report.append("- If AFM only improves forgetting: representation-learning for continual learning")
    report.append("- If AFM improves neither: currently just a representation constraint, not a full technique")
    report.append("")

    report.append("---")
    report.append(f"*Report generated by AFM-Lite Validation Program v0.2*")
    report.append(f"*Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}*")

    report_text = "\n".join(report)
    report_path = '/home/z/my-project/afm-lite/AFM_VALIDATION_REPORT_v0.2.md'
    with open(report_path, 'w') as f:
        f.write(report_text)
    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    main()
