"""
AFM-Lite Validation v0.2 — Unified Experiment Runner

Runs all 7 phases sequentially, saving results after each phase.
"""

import sys, os, json, time, warnings
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
    get_synthetic, get_emnist, get_split_mnist, get_permuted_mnist
)
from stiefel import thread_orthogonality

RESULTS_DIR = '/home/z/my-project/afm-lite/results_v2'
os.makedirs(RESULTS_DIR, exist_ok=True)

EPOCHS = 15
LR = 1e-3
BS = 512
N_SEEDS = 10


def save(name, data):
    """Save results to JSON."""
    def conv(obj):
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, (np.float32, np.float64)): return float(obj)
        if isinstance(obj, (np.int32, np.int64)): return int(obj)
        if isinstance(obj, dict): return {k: conv(v) for k, v in obj.items()}
        if isinstance(obj, list): return [conv(v) for v in obj]
        if isinstance(obj, torch.Tensor): return obj.detach().cpu().numpy().tolist()
        return obj
    with open(os.path.join(RESULTS_DIR, f'{name}.json'), 'w') as f:
        json.dump(conv(data), f, indent=2)


def train_eval(model, train_l, test_l, config, beta=0.0, epochs=EPOCHS, device='cpu'):
    """Train and evaluate a model. Returns best test accuracy and final test accuracy."""
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)
    best_acc = 0
    final_acc = 0
    
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
        acc = correct / total
        if acc > best_acc:
            best_acc = acc
        final_acc = acc
    
    return best_acc, final_acc


def ci_95(data):
    """Compute 95% confidence interval."""
    n = len(data)
    if n < 2:
        return 0.0
    return stats.t.ppf(0.975, n-1) * np.std(data, ddof=1) / np.sqrt(n)


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
        ('baseline_vae', 1e-3),
        ('afm_qr', 0.0),
        ('afm_rib', 1e-3),
    ]
    
    results = {}
    for config, beta in configs:
        print(f"\n  Config: {config} (beta={beta})")
        accs = []
        
        for seed_idx in range(N_SEEDS):
            seed = seed_idx * 42
            torch.manual_seed(seed)
            np.random.seed(seed)
            
            model = get_model(config)
            best_acc, final_acc = train_eval(model, train_l, test_l, config, beta)
            accs.append(best_acc)
            
            if (seed_idx + 1) % 5 == 0:
                print(f"    {seed_idx+1}/{N_SEEDS} seeds: mean={np.mean(accs):.4f}±{np.std(accs):.4f}")
        
        mean = np.mean(accs)
        std = np.std(accs, ddof=1)
        ci = ci_95(accs)
        
        results[config] = {
            'accs': accs,
            'mean': float(mean),
            'std': float(std),
            'ci_95': float(ci),
            'min': float(min(accs)),
            'max': float(max(accs)),
        }
        print(f"    Result: {mean:.4f} ± {std:.4f} (95% CI: [{mean-ci:.4f}, {mean+ci:.4f}])")
    
    # Paired t-tests
    bt = results['baseline_task']['accs']
    ar = results['afm_rib']['accs']
    t, p = stats.ttest_rel(ar, bt)
    d = np.mean(np.array(ar) - np.array(bt)) / np.sqrt((np.std(bt)**2 + np.std(ar)**2) / 2)
    
    results['paired_test'] = {
        'baseline_task_mean': results['baseline_task']['mean'],
        'afm_rib_mean': results['afm_rib']['mean'],
        'diff': float(np.mean(np.array(ar) - np.array(bt))),
        't_stat': float(t),
        'p_value': float(p),
        'cohens_d': float(d),
        'significant_005': p < 0.05,
    }
    print(f"\n  Paired t-test (AFM+RIB vs Baseline): t={t:.3f}, p={p:.4f}, d={d:.3f}")
    print(f"  Significant at α=0.05? {'YES' if p < 0.05 else 'NO'}")
    
    save('phase1', results)
    return results


# ============================================================
# PHASE 2: Stronger Datasets
# ============================================================
def phase2():
    print("\n" + "="*70)
    print("PHASE 2: Stronger Datasets")
    print("="*70)
    
    datasets = {
        'mnist': lambda: get_mnist(batch_size=BS),
        'fashion': lambda: get_fashion_mnist(batch_size=BS),
        'kmnist': lambda: get_kmnist(batch_size=BS, max_samples=30000),
        'cifar10': lambda: get_cifar10(batch_size=BS, max_samples=30000),
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
            results[ds_name] = {'error': str(e)}
            continue
        
        results[ds_name] = {'input_dim': in_dim, 'num_classes': nc}
        
        for config, beta in configs:
            accs = []
            for seed_idx in range(5):  # 5 seeds per dataset
                seed = seed_idx * 42
                torch.manual_seed(seed)
                np.random.seed(seed)
                
                model = get_model(config, input_dim=in_dim, num_classes=nc)
                best_acc, _ = train_eval(model, train_l, test_l, config, beta)
                accs.append(best_acc)
            
            results[ds_name][config] = {
                'accs': accs,
                'mean': float(np.mean(accs)),
                'std': float(np.std(accs, ddof=1)) if len(accs) > 1 else 0.0,
            }
            print(f"    {config}: {np.mean(accs):.4f} ± {np.std(accs):.4f}")
    
    save('phase2', results)
    return results


# ============================================================
# PHASE 3: Ablation Study
# ============================================================
def phase3():
    print("\n" + "="*70)
    print("PHASE 3: Ablation Study")
    print("="*70)
    
    train_l, test_l, _, _ = get_mnist(batch_size=BS)
    
    # 5 ablation configs with varying beta
    ablation_configs = [
        ('baseline_task', 0.0),       # 1. Baseline + L_task
        ('baseline_vae', 1e-3),       # 2. Baseline + β-VAE
        ('afm_no_qr', 0.0),          # 3. AFM without QR
        ('afm_no_qr', 1e-3),         # 3b. AFM without QR + KL
        ('afm_qr', 0.0),             # 4. AFM with QR, no KL
        ('afm_rib', 1e-3),           # 5. AFM + L_RIB
    ]
    
    results = {}
    
    for config, beta in ablation_configs:
        key = f"{config}_b{beta}" if beta > 0 else config
        print(f"\n  Config: {key}")
        accs = []
        
        for seed_idx in range(N_SEEDS):
            seed = seed_idx * 42
            torch.manual_seed(seed)
            np.random.seed(seed)
            
            model = get_model(config)
            best_acc, _ = train_eval(model, train_l, test_l, config, beta)
            accs.append(best_acc)
        
        results[key] = {
            'config': config,
            'beta': beta,
            'accs': accs,
            'mean': float(np.mean(accs)),
            'std': float(np.std(accs, ddof=1)),
            'ci_95': float(ci_95(accs)),
        }
        print(f"    Result: {np.mean(accs):.4f} ± {np.std(accs):.4f}")
    
    # Analysis: which component matters?
    print("\n  === ABLATION ANALYSIS ===")
    base_acc = results['baseline_task']['mean']
    
    for key in results:
        diff = results[key]['mean'] - base_acc
        print(f"    {key}: Δ = {diff:+.4f} vs baseline")
    
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
    
    # Test 1: Wide beta sweep for both models
    print("\n  Test 1: Beta sweep (collapse threshold)")
    beta_values = [1e-5, 1e-4, 5e-4, 1e-3, 5e-3, 1e-2, 5e-2, 1e-1, 5e-1, 1.0]
    
    collapse_results = {}
    for beta in beta_values:
        for config in ['baseline_vae', 'afm_rib']:
            torch.manual_seed(42)
            model = get_model(config if config != 'baseline_vae' else 'baseline_task')
            best_acc, _ = train_eval(model, train_l, test_l, config, beta, epochs=15)
            key = f"{config}_b{beta}"
            collapse_results[key] = {'config': config, 'beta': beta, 'acc': best_acc}
            status = "COLLAPSED" if best_acc < 0.5 else "OK"
            print(f"    {key}: acc={best_acc:.4f} [{status}]")
    
    # Test 2: What happens to the latent space during collapse?
    print("\n  Test 2: Latent space analysis during collapse")
    latent_analysis = {}
    
    for config in ['baseline_task', 'afm_rib']:
        for beta in [0.0, 1e-3, 1e-2, 1e-1]:
            torch.manual_seed(42)
            model = get_model(config if config != 'baseline_task' else config)
            optimizer = torch.optim.Adam(model.parameters(), lr=LR)
            
            latent_norms = []
            for epoch in range(10):
                model.train()
                for X, y in train_l:
                    optimizer.zero_grad()
                    if config == 'afm_rib':
                        logits, recon, mu, lv, kl = model(X)
                    else:
                        logits, recon, mu, lv = model(X)
                        kl = None
                    loss = compute_loss(model, config, logits, y, mu, lv, kl, beta)
                    loss.backward()
                    optimizer.step()
                
                # Measure latent norm
                model.eval()
                with torch.no_grad():
                    X_s, y_s = next(iter(test_l))
                    if config == 'afm_rib':
                        logits, recon, mu, lv, kl = model(X_s)
                        S, _ = model.stiefel(mu, lv)
                        norm = S.norm().item()
                    else:
                        logits, recon, mu, lv = model(X_s)
                        norm = mu.norm().item()
                    latent_norms.append(norm)
            
            key = f"{config}_b{beta}"
            latent_analysis[key] = {
                'config': config, 'beta': beta,
                'final_latent_norm': latent_norms[-1],
                'latent_norm_history': latent_norms,
            }
            print(f"    {key}: final_norm={latent_norms[-1]:.4f}")
    
    # Test 3: Decoder dependence on latent (can decoder work with small latents?)
    print("\n  Test 3: Decoder sensitivity to latent scale")
    decoder_analysis = {}
    
    for config in ['baseline_task', 'afm_rib']:
        torch.manual_seed(42)
        model = get_model(config if config != 'baseline_task' else config)
        # Train normally first
        train_eval(model, train_l, test_l, config if config != 'baseline_task' else 'baseline_task', 0.0, epochs=10)
        
        model.eval()
        with torch.no_grad():
            X_s, y_s = next(iter(test_l))
            if config == 'afm_rib':
                logits_orig, _, mu, lv, _ = model(X_s)
                S, _ = model.stiefel(mu, lv)
                # Scale S down
                for scale in [1.0, 0.5, 0.1, 0.01, 0.001]:
                    S_scaled = S * scale
                    S_flat = S_scaled.reshape(S_scaled.shape[0], -1)
                    logits_scaled = model.classifier(S_flat)
                    acc = (logits_scaled.argmax(1) == y_s).float().mean().item()
                    print(f"    {config} scale={scale}: acc={acc:.4f}")
            else:
                logits_orig, _, mu, lv = model(X_s)
                for scale in [1.0, 0.5, 0.1, 0.01, 0.001]:
                    z_scaled = mu * scale
                    logits_scaled = model.classifier(z_scaled)
                    acc = (logits_scaled.argmax(1) == y_s).float().mean().item()
                    print(f"    {config} scale={scale}: acc={acc:.4f}")
    
    # Test 4: Does QR projection prevent zero-latent?
    print("\n  Test 4: QR projection prevents zero output?")
    qr_test = {}
    for d_val in [16, 32, 64]:
        for K_val in [2, 4, 8]:
            from stiefel import stiefel_project_qr
            # Test: can we get a zero output from QR?
            near_zero = torch.randn(1, d_val, K_val) * 1e-10
            Q = stiefel_project_qr(near_zero)
            norm = Q.norm().item()
            key = f"d{d_val}_K{K_val}"
            qr_test[key] = {'norm': norm, 'd': d_val, 'K': K_val}
            print(f"    d={d_val}, K={K_val}: ||QR(ε)|| = {norm:.4f} (must be sqrt({d_val}*{K_val})={np.sqrt(d_val*K_val):.4f})")
    
    save('phase4', {
        'collapse_sweep': collapse_results,
        'latent_analysis': latent_analysis,
        'qr_test': qr_test,
    })
    return {**collapse_results, **latent_analysis, 'qr_test': qr_test}


# ============================================================
# PHASE 5: Continual Learning Benchmarks
# ============================================================
def phase5():
    print("\n" + "="*70)
    print("PHASE 5: Continual Learning Benchmarks")
    print("="*70)
    
    results = {}
    
    # --- Split-MNIST ---
    print("\n  Split-MNIST (5 binary tasks)")
    try:
        split_tasks = get_split_mnist(batch_size=BS)
        task_classes = [nc for _, _, _, nc in split_tasks]
        
        for config_name in ['baseline_task', 'afm_qr', 'afm_rib']:
            print(f"    Config: {config_name}")
            torch.manual_seed(42)
            
            # Use multi-task heads
            from ablation_models import AFMWithQR, AFMWithRIB, BaselineLTask
            import torch.nn as nn
            
            class MTLBaseline(BaselineLTask):
                def __init__(self, input_dim, hidden_dim, latent_dim, task_classes):
                    super().__init__(input_dim, hidden_dim, latent_dim, task_classes[0])
                    self.heads = nn.ModuleList([
                        nn.Sequential(nn.Linear(latent_dim, hidden_dim//2), nn.ReLU(),
                                      nn.Linear(hidden_dim//2, nc))
                        for nc in task_classes
                    ])
                    self.classifier = self.heads[0]  # dummy
                
                def forward(self, x, task_id=0):
                    h = self.encoder(x)
                    mu, lv = self.fc_mu(h), self.fc_logvar(h)
                    if self.training:
                        z = mu + torch.exp(0.5 * lv) * torch.randn_like(mu)
                    else:
                        z = mu
                    logits = self.heads[task_id](z)
                    return logits, mu, lv
            
            class MTLAFM(AFMWithRIB):
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
            
            if config_name == 'baseline_task':
                model = MTLBaseline(784, 256, 128, task_classes)
                mtype = 'baseline'
            elif config_name == 'afm_qr':
                model = MTLAFM(784, 256, 32, 4, task_classes)
                mtype = 'afm'
            else:
                model = MTLAFM(784, 256, 32, 4, task_classes)
                mtype = 'afm'
            
            beta = 1e-3 if config_name == 'afm_rib' else 0.0
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
                
                # Evaluate all tasks
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
                    acc_matrix[task_id, eval_id] = correct / total
            
            # Compute forgetting
            forgetting = []
            for tid in range(num_tasks - 1):
                acc_after = acc_matrix[tid, tid]
                acc_final = acc_matrix[num_tasks - 1, tid]
                forgetting.append(acc_after - acc_final)
            
            avg_forgetting = np.mean(forgetting) if forgetting else 0
            
            # Backward transfer
            bwt = np.mean([acc_matrix[-1, i] - acc_matrix[i, i] for i in range(num_tasks - 1)])
            # Forward transfer (not applicable for first task)
            # Average accuracy
            avg_acc = np.mean([acc_matrix[-1, i] for i in range(num_tasks)])
            
            results[f'split_mnist_{config_name}'] = {
                'acc_matrix': acc_matrix.tolist(),
                'forgetting': forgetting,
                'avg_forgetting': float(avg_forgetting),
                'backward_transfer': float(bwt),
                'avg_accuracy': float(avg_acc),
            }
            print(f"      Forgetting: {avg_forgetting:.4f}, BWT: {bwt:.4f}, Avg Acc: {avg_acc:.4f}")
    
    except Exception as e:
        print(f"    Split-MNIST FAILED: {e}")
        import traceback; traceback.print_exc()
        results['split_mnist_error'] = str(e)
    
    # --- Permuted-MNIST ---
    print("\n  Permuted-MNIST (5 tasks)")
    try:
        perm_tasks = get_permuted_mnist(n_tasks=5, batch_size=BS)
        task_classes_p = [10] * 5
        
        for config_name in ['baseline_task', 'afm_qr', 'afm_rib']:
            print(f"    Config: {config_name}")
            torch.manual_seed(42)
            
            class MTLBaseline10(BaselineLTask):
                def __init__(self, input_dim, hidden_dim, latent_dim):
                    super().__init__(input_dim, hidden_dim, latent_dim, 10)
                    # Single head for Permuted-MNIST (same classes)
                
            if config_name == 'baseline_task':
                model = MTLBaseline10(784, 256, 128)
                mtype = 'baseline'
            else:
                from ablation_models import AFMWithQR
                class MTLAFM10(AFMWithQR):
                    def __init__(self, input_dim, hidden_dim, d, K):
                        super().__init__(input_dim, hidden_dim, d, K, 10)
                model = MTLAFM10(784, 256, 32, 4)
                mtype = 'afm'
            
            beta = 1e-3 if config_name == 'afm_rib' else 0.0
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
                            logits, mu, lv = model(X)
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
                                logits, _, _ = model(X)
                            else:
                                logits, _, _, _, _ = model(X)
                            correct += (logits.argmax(1) == y).sum().item()
                            total += y.size(0)
                    acc_matrix[task_id, eval_id] = correct / total
            
            forgetting = []
            for tid in range(num_tasks - 1):
                acc_after = acc_matrix[tid, tid]
                acc_final = acc_matrix[num_tasks - 1, tid]
                forgetting.append(acc_after - acc_final)
            
            avg_forgetting = np.mean(forgetting) if forgetting else 0
            bwt = np.mean([acc_matrix[-1, i] - acc_matrix[i, i] for i in range(num_tasks - 1)])
            avg_acc = np.mean([acc_matrix[-1, i] for i in range(num_tasks)])
            
            results[f'permuted_mnist_{config_name}'] = {
                'acc_matrix': acc_matrix.tolist(),
                'forgetting': forgetting,
                'avg_forgetting': float(avg_forgetting),
                'backward_transfer': float(bwt),
                'avg_accuracy': float(avg_acc),
            }
            print(f"      Forgetting: {avg_forgetting:.4f}, BWT: {bwt:.4f}, Avg Acc: {avg_acc:.4f}")
    
    except Exception as e:
        print(f"    Permuted-MNIST FAILED: {e}")
        import traceback; traceback.print_exc()
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
    from sklearn.manifold import TSNE
    
    train_l, test_l, _, _ = get_mnist(batch_size=BS)
    
    configs = ['baseline_task', 'afm_qr', 'afm_rib']
    results = {}
    
    for config in configs:
        print(f"\n  Training {config}...")
        torch.manual_seed(42)
        model = get_model(config)
        beta = 1e-3 if config == 'afm_rib' else 0.0
        train_eval(model, train_l, test_l, config, beta, epochs=15)
        
        # Extract representations
        model.eval()
        latents, labels_list = [], []
        
        with torch.no_grad():
            for i, (X, y) in enumerate(test_l):
                if i >= 10:
                    break
                if config in ['afm_qr', 'afm_rib']:
                    logits, recon, mu, lv, kl = model(X)
                    S, _ = model.stiefel(mu, lv)
                    latent = S.reshape(S.shape[0], -1)
                else:
                    logits, recon, mu, lv = model(X)
                    latent = mu
                latents.append(latent.numpy())
                labels_list.append(y.numpy())
        
        lat = np.concatenate(latents)
        lab = np.concatenate(labels_list)
        
        # PCA
        pca = PCA(n_components=min(10, lat.shape[1]))
        pca.fit(lat)
        ev = pca.explained_variance_ratio_
        
        # Silhouette
        sil = silhouette_score(lat, lab, sample_size=min(5000, len(lab)))
        
        # t-SNE (on PCA-reduced data for speed)
        tsne = TSNE(n_components=2, random_state=42, perplexity=30)
        lat_pca = PCA(n_components=20).fit_transform(lat[:2000])
        tsne_coords = tsne.fit_transform(lat_pca)
        
        # Thread analysis (AFM only)
        thread_info = {}
        if config in ['afm_qr', 'afm_rib']:
            with torch.no_grad():
                for i, (X, y) in enumerate(test_l):
                    if i >= 10:
                        break
                    mu, lv = model.fc_mu(model.encoder(X)), model.fc_logvar(model.encoder(X))
                    S, _ = model.stiefel(mu, lv)
                    if 'stiefel' not in thread_info:
                        thread_info['stiefel'] = []
                    thread_info['stiefel'].append(S.numpy())
            
            stiefel = np.concatenate(thread_info['stiefel'])
            K = stiefel.shape[2]
            
            # Thread-class correlation
            tc_corr = []
            for k in range(K):
                proj = stiefel[:, 0, k]
                c = np.corrcoef(proj, lab[:len(proj)])[0, 1]
                tc_corr.append(float(abs(c)) if not np.isnan(c) else 0)
            
            # Inter-thread dot products
            dots = []
            for k1 in range(K):
                for k2 in range(k1+1, K):
                    d = np.mean(np.sum(stiefel[:, :, k1] * stiefel[:, :, k2], axis=1))
                    dots.append(float(d))
            
            thread_info = {
                'thread_class_correlation': tc_corr,
                'inter_thread_dots': dots,
                'thread_norms': [float(np.mean(np.linalg.norm(stiefel[:, :, k], axis=1))) for k in range(K)],
            }
        
        results[config] = {
            'pca_explained_variance': ev.tolist(),
            'pca_cumulative_10': float(ev.sum()),
            'silhouette_score': float(sil),
            'thread_info': thread_info,
        }
        
        print(f"    Silhouette: {sil:.4f}, PCA cumul: {ev.sum():.4f}")
        if thread_info:
            print(f"    Thread-class |corr|: {thread_info.get('thread_class_correlation', [])}")
    
    save('phase6', results)
    return results


# ============================================================
# PHASE 7: Failure Analysis
# ============================================================
def phase7(phase1_results, phase2_results, phase3_results, phase4_results, phase5_results):
    print("\n" + "="*70)
    print("PHASE 7: Failure Analysis")
    print("="*70)
    
    failures = []
    
    # Check Phase 1: Is the accuracy improvement real?
    if 'paired_test' in phase1_results:
        pt = phase1_results['paired_test']
        if not pt.get('significant_005', False):
            failures.append("Phase 1: AFM+RIB vs Baseline NOT significant at α=0.05")
        else:
            print("  ✓ Phase 1: Accuracy improvement IS significant (p={:.4f})".format(pt['p_value']))
    
    # Check Phase 2: Does AFM help on harder datasets?
    if isinstance(phase2_results, dict):
        for ds_name in phase2_results:
            if isinstance(phase2_results[ds_name], dict) and 'error' in phase2_results[ds_name]:
                failures.append(f"Phase 2: Dataset {ds_name} failed: {phase2_results[ds_name]['error']}")
            elif isinstance(phase2_results[ds_name], dict):
                bt = phase2_results[ds_name].get('baseline_task', {}).get('mean', 0)
                ar = phase2_results[ds_name].get('afm_rib', {}).get('mean', 0)
                if ar < bt:
                    failures.append(f"Phase 2: AFM+RIB WORSE on {ds_name} ({ar:.4f} vs {bt:.4f})")
                    print(f"  ✗ {ds_name}: AFM+RIB ({ar:.4f}) < Baseline ({bt:.4f})")
                else:
                    print(f"  ✓ {ds_name}: AFM+RIB ({ar:.4f}) >= Baseline ({bt:.4f})")
    
    # Check Phase 3: Ablation - what causes the improvement?
    if isinstance(phase3_results, dict):
        base = phase3_results.get('baseline_task', {}).get('mean', 0)
        for key, val in phase3_results.items():
            if isinstance(val, dict) and 'mean' in val:
                diff = val['mean'] - base
                if diff < 0:
                    failures.append(f"Phase 3: {key} WORSE than baseline by {abs(diff):.4f}")
    
    # Check Phase 4: Beta instability
    if isinstance(phase4_results, dict):
        for key, val in phase4_results.items():
            if isinstance(val, dict) and 'acc' in val and val['acc'] < 0.5:
                failures.append(f"Phase 4: {key} COLLAPSED (acc={val['acc']:.4f})")
    
    # Check Phase 5: Continual learning
    if isinstance(phase5_results, dict):
        for key, val in phase5_results.items():
            if isinstance(val, dict) and 'avg_forgetting' in val:
                if val['avg_forgetting'] < 0:
                    failures.append(f"Phase 5: {key} has NEGATIVE forgetting (anomaly)")
    
    # Print failure summary
    print("\n  === FAILURE SUMMARY ===")
    if not failures:
        print("  No failures detected.")
    else:
        for f in failures:
            print(f"  ✗ {f}")
    
    save('phase7', {'failures': failures, 'count': len(failures)})
    return failures


# ============================================================
# MAIN
# ============================================================
def main():
    print("\n" + "#"*70)
    print("# AFM-Lite Validation Program v0.2")
    print("# Objective: Determine if previous improvements are genuine or artifacts")
    print(f"# Seeds: {N_SEEDS}, Epochs: {EPOCHS}, Batch: {BS}")
    print("#"*70)
    
    t0 = time.time()
    
    # Run phases
    try:
        p1 = phase1()
    except Exception as e:
        print(f"Phase 1 FAILED: {e}")
        import traceback; traceback.print_exc()
        p1 = {}
    
    try:
        p2 = phase2()
    except Exception as e:
        print(f"Phase 2 FAILED: {e}")
        import traceback; traceback.print_exc()
        p2 = {}
    
    try:
        p3 = phase3()
    except Exception as e:
        print(f"Phase 3 FAILED: {e}")
        import traceback; traceback.print_exc()
        p3 = {}
    
    try:
        p4 = phase4()
    except Exception as e:
        print(f"Phase 4 FAILED: {e}")
        import traceback; traceback.print_exc()
        p4 = {}
    
    try:
        p5 = phase5()
    except Exception as e:
        print(f"Phase 5 FAILED: {e}")
        import traceback; traceback.print_exc()
        p5 = {}
    
    try:
        p6 = phase6()
    except Exception as e:
        print(f"Phase 6 FAILED: {e}")
        import traceback; traceback.print_exc()
        p6 = {}
    
    try:
        p7 = phase7(p1, p2, p3, p4, p5)
    except Exception as e:
        print(f"Phase 7 FAILED: {e}")
        p7 = []
    
    total_time = time.time() - t0
    print(f"\n\nTotal validation time: {total_time:.1f}s ({total_time/60:.1f}min)")
    
    # Generate report
    generate_report(p1, p2, p3, p4, p5, p6, p7)


def generate_report(p1, p2, p3, p4, p5, p6, p7):
    """Generate AFM_VALIDATION_REPORT_v0.2.md"""
    # This will be a comprehensive report
    # For now, save a summary
    save('validation_summary', {
        'phase1': 'completed' if p1 else 'failed',
        'phase2': 'completed' if p2 else 'failed',
        'phase3': 'completed' if p3 else 'failed',
        'phase4': 'completed' if p4 else 'failed',
        'phase5': 'completed' if p5 else 'failed',
        'phase6': 'completed' if p6 else 'failed',
        'phase7_failures': p7,
    })
    print("Validation summary saved.")


if __name__ == "__main__":
    main()
