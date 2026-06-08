"""
Data Loading for AFM-Lite Experiments

Provides:
- MNIST (digit classification)
- Fashion-MNIST (clothing classification)
- Synthetic multi-task datasets
- Sequential task loaders for multi-task experiments
"""

import torch
import numpy as np
from torch.utils.data import DataLoader, TensorDataset, Subset
from sklearn.datasets import fetch_openml
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import os
import pickle


def get_mnist(batch_size: int = 128, flatten: bool = True):
    """
    Load MNIST dataset using sklearn/openml.

    Returns:
        train_loader, test_loader, input_dim, num_classes
    """
    cache_path = '/home/z/my-project/afm-lite/.cache/mnist.pkl'

    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            data = pickle.load(f)
        X_train, y_train = data['X_train'], data['y_train']
        X_test, y_test = data['X_test'], data['y_test']
    else:
        print("Downloading MNIST...")
        mnist = fetch_openml('mnist_784', version=1, as_frame=False)
        X, y = mnist.data, mnist.target.astype(int)

        # Split: 60k train, 10k test (standard MNIST split)
        X_train, X_test = X[:60000], X[60000:]
        y_train, y_test = y[:60000], y[60000:]

        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump({'X_train': X_train, 'y_train': y_train,
                         'X_test': X_test, 'y_test': y_test}, f)

    # Normalize to [0, 1]
    X_train = X_train.astype(np.float32) / 255.0
    X_test = X_test.astype(np.float32) / 255.0

    if flatten:
        # Already flat from fetch_openml
        pass

    # Create tensors
    X_train_t = torch.FloatTensor(X_train)
    y_train_t = torch.LongTensor(y_train)
    X_test_t = torch.FloatTensor(X_test)
    y_test_t = torch.LongTensor(y_test)

    train_dataset = TensorDataset(X_train_t, y_train_t)
    test_dataset = TensorDataset(X_test_t, y_test_t)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    return train_loader, test_loader, 784, 10


def get_fashion_mnist(batch_size: int = 128, flatten: bool = True):
    """
    Load Fashion-MNIST dataset.

    Returns:
        train_loader, test_loader, input_dim, num_classes
    """
    cache_path = '/home/z/my-project/afm-lite/.cache/fashion_mnist.pkl'

    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            data = pickle.load(f)
        X_train, y_train = data['X_train'], data['y_train']
        X_test, y_test = data['X_test'], data['y_test']
    else:
        print("Downloading Fashion-MNIST...")
        fashion = fetch_openml('Fashion-MNIST', version=1, as_frame=False)
        X, y = fashion.data, fashion.target.astype(int)

        X_train, X_test = X[:60000], X[60000:]
        y_train, y_test = y[:60000], y[60000:]

        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump({'X_train': X_train, 'y_train': y_train,
                         'X_test': X_test, 'y_test': y_test}, f)

    X_train = X_train.astype(np.float32) / 255.0
    X_test = X_test.astype(np.float32) / 255.0

    X_train_t = torch.FloatTensor(X_train)
    y_train_t = torch.LongTensor(y_train)
    X_test_t = torch.FloatTensor(X_test)
    y_test_t = torch.LongTensor(y_test)

    train_dataset = TensorDataset(X_train_t, y_train_t)
    test_dataset = TensorDataset(X_test_t, y_test_t)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    return train_loader, test_loader, 784, 10


def get_synthetic_task(n_samples: int = 10000, input_dim: int = 784,
                       num_classes: int = 10, task_type: str = 'cluster',
                       seed: int = 42):
    """
    Generate a synthetic classification task.

    Task types:
    - 'cluster': Gaussian clusters in high-D space
    - 'parity': Parity of sum of input features
    - 'nonlinear': Nonlinear decision boundary

    Returns:
        train_loader, test_loader, input_dim, num_classes
    """
    np.random.seed(seed)

    if task_type == 'cluster':
        # Gaussian clusters
        centers = np.random.randn(num_classes, input_dim) * 2
        X = np.zeros((n_samples, input_dim), dtype=np.float32)
        y = np.zeros(n_samples, dtype=np.int64)
        samples_per_class = n_samples // num_classes

        for c in range(num_classes):
            start = c * samples_per_class
            end = start + samples_per_class
            X[start:end] = centers[c] + np.random.randn(samples_per_class, input_dim) * 0.5
            y[start:end] = c

        # Normalize
        X = (X - X.mean()) / (X.std() + 1e-8)

    elif task_type == 'parity':
        # Binary features, parity of first 10 features
        X = np.random.randint(0, 2, size=(n_samples, input_dim)).astype(np.float32)
        y = (X[:, :10].sum(axis=1) % 2).astype(np.int64)
        num_classes = 2

    elif task_type == 'nonlinear':
        # Spiral/nonlinear decision boundary
        X = np.random.randn(n_samples, input_dim).astype(np.float32) * 0.5
        # Class based on angle in first 2 dimensions
        angles = np.arctan2(X[:, 1], X[:, 0])
        y = ((angles + np.pi) / (2 * np.pi) * num_classes).astype(np.int64) % num_classes

    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed
    )

    train_dataset = TensorDataset(
        torch.FloatTensor(X_train), torch.LongTensor(y_train)
    )
    test_dataset = TensorDataset(
        torch.FloatTensor(X_test), torch.LongTensor(y_test)
    )

    train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False)

    return train_loader, test_loader, input_dim, num_classes


def get_multi_task_data(tasks: list = None, batch_size: int = 128, max_samples: int = 20000):
    """
    Load multiple tasks for multi-task experiments.

    Returns:
        list of (train_loader, test_loader, input_dim, num_classes) tuples
    """
    if tasks is None:
        tasks = ['mnist', 'fashion', 'synthetic_cluster']

    task_data = []
    for task in tasks:
        if task == 'mnist':
            train_l, test_l, in_dim, nc = get_mnist(batch_size=batch_size)
            # Subsample for faster multi-task training
            if len(train_l.dataset) > max_samples:
                indices = list(range(max_samples))
                train_l = DataLoader(Subset(train_l.dataset, indices),
                                     batch_size=batch_size, shuffle=True)
        elif task == 'fashion':
            train_l, test_l, in_dim, nc = get_fashion_mnist(batch_size=batch_size)
            if len(train_l.dataset) > max_samples:
                indices = list(range(max_samples))
                train_l = DataLoader(Subset(train_l.dataset, indices),
                                     batch_size=batch_size, shuffle=True)
        elif task == 'synthetic_cluster':
            train_l, test_l, in_dim, nc = get_synthetic_task(
                n_samples=max_samples, input_dim=784, num_classes=10, task_type='cluster'
            )
        elif task == 'synthetic_parity':
            train_l, test_l, in_dim, nc = get_synthetic_task(
                n_samples=max_samples, input_dim=784, num_classes=2, task_type='parity'
            )
        elif task == 'synthetic_nonlinear':
            train_l, test_l, in_dim, nc = get_synthetic_task(
                n_samples=max_samples, input_dim=784, num_classes=5, task_type='nonlinear'
            )
        else:
            raise ValueError(f"Unknown task: {task}")

        task_data.append((train_l, test_l, in_dim, nc))
        print(f"  Task '{task}': {len(train_l.dataset)} train, {len(test_l.dataset)} test, "
              f"{in_dim} input dim, {nc} classes")

    return task_data


if __name__ == "__main__":
    print("Testing data loading...")

    print("\n1. MNIST:")
    train_l, test_l, in_dim, nc = get_mnist(batch_size=64)
    for X, y in train_l:
        print(f"   Batch: X={X.shape}, y={y.shape}, X range=[{X.min():.3f}, {X.max():.3f}]")
        break

    print("\n2. Fashion-MNIST:")
    train_l, test_l, in_dim, nc = get_fashion_mnist(batch_size=64)
    for X, y in train_l:
        print(f"   Batch: X={X.shape}, y={y.shape}")
        break

    print("\n3. Synthetic cluster:")
    train_l, test_l, in_dim, nc = get_synthetic_task(n_samples=5000, task_type='cluster')
    for X, y in train_l:
        print(f"   Batch: X={X.shape}, y={y.shape}")
        break

    print("\n4. Multi-task:")
    task_data = get_multi_task_data(max_samples=5000)
    for i, (train_l, test_l, in_dim, nc) in enumerate(task_data):
        print(f"   Task {i}: {nc} classes, {len(train_l.dataset)} samples")
