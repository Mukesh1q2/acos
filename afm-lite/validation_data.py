"""
AFM-Lite Validation Data Loader — Multi-dataset support for v0.2

Supports: MNIST, EMNIST, Fashion-MNIST, KMNIST, CIFAR-10, Synthetic
"""

import torch
import numpy as np
from torch.utils.data import DataLoader, TensorDataset, Subset
from sklearn.datasets import fetch_openml
from sklearn.model_selection import train_test_split
import os
import pickle
import warnings
warnings.filterwarnings('ignore')

CACHE_DIR = '/home/z/my-project/afm-lite/.cache'


def _cache_or_fetch(name, openml_name, batch_size=512, max_samples=None):
    """Generic cache/fetch for OpenML datasets."""
    cache_path = os.path.join(CACHE_DIR, f'{name}.pkl')
    
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            data = pickle.load(f)
        X_train, y_train = data['X_train'], data['y_train']
        X_test, y_test = data['X_test'], data['y_test']
    else:
        print(f"  Downloading {name}...")
        ds = fetch_openml(openml_name, version=1, as_frame=False, parser='auto')
        X, y = ds.data, ds.target.astype(int)
        
        # Standard split: 80/20
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump({'X_train': X_train, 'y_train': y_train,
                         'X_test': X_test, 'y_test': y_test}, f)
    
    X_train = X_train.astype(np.float32) / 255.0 if X_train.max() > 1 else X_train.astype(np.float32)
    X_test = X_test.astype(np.float32) / 255.0 if X_test.max() > 1 else X_test.astype(np.float32)
    
    # Flatten if needed (for CIFAR-10)
    if X_train.ndim > 2:
        X_train = X_train.reshape(X_train.shape[0], -1)
        X_test = X_test.reshape(X_test.shape[0], -1)
    
    input_dim = X_train.shape[1]
    num_classes = len(np.unique(y_train))
    
    # Subsample if needed
    if max_samples and len(X_train) > max_samples:
        idx = np.random.choice(len(X_train), max_samples, replace=False)
        X_train, y_train = X_train[idx], y_train[idx]
    
    train_dataset = TensorDataset(
        torch.FloatTensor(X_train), torch.LongTensor(y_train)
    )
    test_dataset = TensorDataset(
        torch.FloatTensor(X_test), torch.LongTensor(y_test)
    )
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    return train_loader, test_loader, input_dim, num_classes


def get_mnist(batch_size=512, max_samples=None):
    """Standard MNIST with 60k/10k split."""
    cache_path = os.path.join(CACHE_DIR, 'mnist.pkl')
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            data = pickle.load(f)
        X_train, y_train = data['X_train'], data['y_train']
        X_test, y_test = data['X_test'], data['y_test']
    else:
        ds = fetch_openml('mnist_784', version=1, as_frame=False, parser='auto')
        X, y = ds.data, ds.target.astype(int)
        X_train, X_test = X[:60000], X[60000:]
        y_train, y_test = y[:60000], y[60000:]
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump({'X_train': X_train, 'y_train': y_train,
                         'X_test': X_test, 'y_test': y_test}, f)
    
    X_train = X_train.astype(np.float32) / 255.0
    X_test = X_test.astype(np.float32) / 255.0
    if max_samples and len(X_train) > max_samples:
        idx = np.random.choice(len(X_train), max_samples, replace=False)
        X_train, y_train = X_train[idx], y_train[idx]
    
    train_loader = DataLoader(TensorDataset(torch.FloatTensor(X_train), torch.LongTensor(y_train)),
                              batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(TensorDataset(torch.FloatTensor(X_test), torch.LongTensor(y_test)),
                             batch_size=batch_size, shuffle=False)
    return train_loader, test_loader, 784, 10


def get_emnist(batch_size=512, max_samples=None):
    """EMNIST (ByClass) - 62 classes, 28x28 images."""
    return _cache_or_fetch('emnist_byclass', 'EMNIST_ByClass', batch_size, max_samples)


def get_fashion_mnist(batch_size=512, max_samples=None):
    """Fashion-MNIST - 10 classes, 28x28 images."""
    return _cache_or_fetch('fashion_mnist', 'Fashion-MNIST', batch_size, max_samples)


def get_kmnist(batch_size=512, max_samples=None):
    """KMNIST (Kuzushiji) - 10 classes, 28x28 images."""
    return _cache_or_fetch('kmnist', 'KMNIST', batch_size, max_samples)


def get_cifar10(batch_size=512, max_samples=None):
    """CIFAR-10 - 10 classes, 32x32x3 images (flattened to 3072)."""
    cache_path = os.path.join(CACHE_DIR, 'cifar10.pkl')
    
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            data = pickle.load(f)
        X_train, y_train = data['X_train'], data['y_train']
        X_test, y_test = data['X_test'], data['y_test']
    else:
        ds = fetch_openml('CIFAR_10', version=1, as_frame=False, parser='auto')
        X, y = ds.data.astype(np.float32), ds.target.astype(int)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        # Normalize to [0,1]
        X_train = X_train / 255.0
        X_test = X_test / 255.0
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump({'X_train': X_train, 'y_train': y_train,
                         'X_test': X_test, 'y_test': y_test}, f)
    
    if max_samples and len(X_train) > max_samples:
        idx = np.random.choice(len(X_train), max_samples, replace=False)
        X_train, y_train = X_train[idx], y_train[idx]
    
    input_dim = X_train.shape[1]  # 3072 for CIFAR-10
    num_classes = 10
    
    train_loader = DataLoader(TensorDataset(torch.FloatTensor(X_train), torch.LongTensor(y_train)),
                              batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(TensorDataset(torch.FloatTensor(X_test), torch.LongTensor(y_test)),
                             batch_size=batch_size, shuffle=False)
    return train_loader, test_loader, input_dim, num_classes


def get_synthetic(n_samples=20000, input_dim=784, num_classes=10, seed=42, batch_size=512):
    """Synthetic Gaussian cluster dataset."""
    np.random.seed(seed)
    centers = np.random.randn(num_classes, input_dim) * 2
    X = np.zeros((n_samples, input_dim), dtype=np.float32)
    y = np.zeros(n_samples, dtype=np.int64)
    spc = n_samples // num_classes
    for c in range(num_classes):
        s, e = c * spc, (c + 1) * spc
        X[s:e] = centers[c] + np.random.randn(spc, input_dim) * 0.5
        y[s:e] = c
    X = (X - X.mean()) / (X.std() + 1e-8)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=seed)
    train_loader = DataLoader(TensorDataset(torch.FloatTensor(X_train), torch.LongTensor(y_train)),
                              batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(TensorDataset(torch.FloatTensor(X_test), torch.LongTensor(y_test)),
                             batch_size=batch_size, shuffle=False)
    return train_loader, test_loader, input_dim, num_classes


# ============ Continual Learning Datasets ============

def get_split_mnist(batch_size=512):
    """Split-MNIST: 5 binary tasks, each on 2 digit classes."""
    train_l, test_l, _, _ = get_mnist(batch_size=batch_size)
    
    # Extract all data
    all_X_train, all_y_train = [], []
    for X, y in train_l:
        all_X_train.append(X)
        all_y_train.append(y)
    all_X_train = torch.cat(all_X_train)
    all_y_train = torch.cat(all_y_train)
    
    all_X_test, all_y_test = [], []
    for X, y in test_l:
        all_X_test.append(X)
        all_y_test.append(y)
    all_X_test = torch.cat(all_X_test)
    all_y_test = torch.cat(all_y_test)
    
    tasks = []
    for i in range(5):
        c1, c2 = i * 2, i * 2 + 1
        # Train: filter to c1, c2, relabel to 0, 1
        mask_tr = (all_y_train == c1) | (all_y_train == c2)
        X_tr = all_X_train[mask_tr]
        y_tr = (all_y_train[mask_tr] == c2).long()
        # Test
        mask_te = (all_y_test == c1) | (all_y_test == c2)
        X_te = all_X_test[mask_te]
        y_te = (all_y_test[mask_te] == c2).long()
        
        train_ds = TensorDataset(X_tr, y_tr)
        test_ds = TensorDataset(X_te, y_te)
        tasks.append((
            DataLoader(train_ds, batch_size=batch_size, shuffle=True),
            DataLoader(test_ds, batch_size=batch_size, shuffle=False),
            784, 2  # binary classification
        ))
    
    return tasks


def get_permuted_mnist(n_tasks=5, batch_size=512):
    """Permuted-MNIST: each task applies a random permutation to pixels."""
    train_l, test_l, _, _ = get_mnist(batch_size=batch_size)
    
    all_X_train, all_y_train = [], []
    for X, y in train_l:
        all_X_train.append(X)
        all_y_train.append(y)
    all_X_train = torch.cat(all_X_train)
    all_y_train = torch.cat(all_y_train)
    
    all_X_test, all_y_test = [], []
    for X, y in test_l:
        all_X_test.append(X)
        all_y_test.append(y)
    all_X_test = torch.cat(all_X_test)
    all_y_test = torch.cat(all_y_test)
    
    tasks = []
    rng = np.random.RandomState(42)
    
    for t in range(n_tasks):
        perm = rng.permutation(784)
        X_tr = all_X_train[:, perm]
        X_te = all_X_test[:, perm]
        
        train_ds = TensorDataset(X_tr, all_y_train)
        test_ds = TensorDataset(X_te, all_y_test)
        tasks.append((
            DataLoader(train_ds, batch_size=batch_size, shuffle=True),
            DataLoader(test_ds, batch_size=batch_size, shuffle=False),
            784, 10
        ))
    
    return tasks


def get_sequential_fashion(batch_size=512, max_samples=15000):
    """Sequential Fashion-MNIST: train on the full dataset, evaluate forgetting."""
    train_l, test_l, _, _ = get_fashion_mnist(batch_size=batch_size, max_samples=max_samples)
    return [(train_l, test_l, 784, 10)]


DATASET_LOADERS = {
    'mnist': get_mnist,
    'fashion': get_fashion_mnist,
    'kmnist': get_kmnist,
    'cifar10': get_cifar10,
    'synthetic': lambda **kw: get_synthetic(**kw),
    'emnist': get_emnist,
}
