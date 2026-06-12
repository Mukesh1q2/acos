"""
OLP-RSSM: Moving-MNIST Dataset

Generates sequences of digits moving in a 64x64 or 32x32 frame.
This is the first test environment for OLP in RSSM.

Optimized for CPU training with configurable limits.
"""

import torch
import torch.nn.functional as F
import numpy as np
from torch.utils.data import Dataset, DataLoader, Subset
from torchvision import datasets


class MovingMNIST(Dataset):
    """
    Moving-MNIST dataset for video prediction.
    
    Each sample is a sequence of frames showing digits bouncing
    inside a frame. Digits move with constant velocity and
    bounce off walls.
    """
    
    def __init__(self, root='./data', seq_len=10, num_digits=2, 
                 image_size=32, digit_size=14, train=True, seed=None,
                 max_samples=None):
        self.seq_len = seq_len
        self.num_digits = num_digits
        self.image_size = image_size
        self.digit_size = digit_size
        self.train = train
        self.max_samples = max_samples
        
        # Load MNIST digits
        mnist = datasets.MNIST(root=root, train=train, download=True)
        self.digits = mnist.data.float() / 255.0  # (N, 28, 28)
        self.labels = mnist.targets
        
        # Resize digits to digit_size
        self.digits_resized = F.interpolate(
            self.digits.unsqueeze(1),  # (N, 1, 28, 28)
            size=(digit_size, digit_size),
            mode='bilinear',
            align_corners=False
        ).squeeze(1)  # (N, digit_size, digit_size)
        
        # Pre-generate random state for reproducibility
        self.rng = np.random.RandomState(seed)
    
    def __len__(self):
        if self.max_samples:
            return min(self.max_samples, len(self.digits))
        return len(self.digits)
    
    def _get_random_digit(self):
        """Get a random MNIST digit (resized)."""
        idx = self.rng.randint(0, len(self.digits_resized))
        digit = self.digits_resized[idx]
        label = self.labels[idx].item()
        return digit, label
    
    def _generate_trajectory(self):
        """Generate digit positions and velocities for a sequence."""
        max_pos = self.image_size - self.digit_size
        
        digits = []
        positions = []
        velocities = []
        labels = []
        
        for _ in range(self.num_digits):
            digit, label = self._get_random_digit()
            digits.append(digit)
            labels.append(label)
            
            # Random starting position
            x = self.rng.randint(0, max_pos + 1)
            y = self.rng.randint(0, max_pos + 1)
            
            # Random velocity (1-2 pixels per frame)
            vx = self.rng.choice([-2, -1, 1, 2])
            vy = self.rng.choice([-2, -1, 1, 2])
            
            positions.append([float(x), float(y)])
            velocities.append([float(vx), float(vy)])
        
        # Generate full trajectory
        frames = []
        pos = [list(p) for p in positions]
        vel = [list(v) for v in velocities]
        
        for t in range(self.seq_len):
            frame = torch.zeros(self.image_size, self.image_size)
            
            for d in range(self.num_digits):
                # Place digit
                x, y = int(pos[d][0]), int(pos[d][1])
                x = max(0, min(x, self.image_size - self.digit_size))
                y = max(0, min(y, self.image_size - self.digit_size))
                
                frame[y:y+self.digit_size, x:x+self.digit_size] = torch.max(
                    frame[y:y+self.digit_size, x:x+self.digit_size],
                    digits[d]
                )
                
                # Update position
                pos[d][0] += vel[d][0]
                pos[d][1] += vel[d][1]
                
                # Bounce off walls
                if pos[d][0] <= 0 or pos[d][0] >= max_pos:
                    vel[d][0] *= -1
                    pos[d][0] = max(0, min(pos[d][0], max_pos))
                if pos[d][1] <= 0 or pos[d][1] >= max_pos:
                    vel[d][1] *= -1
                    pos[d][1] = max(0, min(pos[d][1], max_pos))
            
            frames.append(frame)
        
        # Stack: (seq_len, H, W) -> (seq_len, 1, H, W)
        frames = torch.stack(frames, dim=0).unsqueeze(1)
        return frames, labels
    
    def __getitem__(self, idx):
        return self._generate_trajectory()
    
    @staticmethod
    def collate_fn(batch):
        """Custom collate for variable-dimension batches."""
        frames_list = [item[0] for item in batch]
        labels_list = [item[1] for item in batch]
        frames = torch.stack(frames_list, dim=0)  # (B, T, 1, H, W)
        return frames, labels_list


class PendulumDataset(Dataset):
    """
    Simple pendulum environment for sequential prediction.
    
    Generates sequences of pendulum images.
    State: angle θ, angular velocity ω
    Dynamics: θ_{t+1} = θ_t + ω_t, ω_{t+1} = ω_t - g/L * sin(θ_t)
    """
    
    def __init__(self, seq_len=10, image_size=32, n_samples=5000,
                 g=9.81, L=1.0, dt=0.05, train=True, seed=None):
        self.seq_len = seq_len
        self.image_size = image_size
        self.n_samples = n_samples
        self.g = g
        self.L = L
        self.dt = dt
        self.rng = np.random.RandomState(seed)
    
    def __len__(self):
        return self.n_samples
    
    def _render_pendulum(self, theta):
        """Render a pendulum image given angle."""
        img = torch.zeros(self.image_size, self.image_size)
        cx, cy = self.image_size // 2, self.image_size // 4  # pivot
        
        # Pendulum tip position
        rod_len = self.image_size // 3
        tx = cx + int(rod_len * np.sin(theta))
        ty = cy + int(rod_len * np.cos(theta))
        
        # Draw rod (line from pivot to tip)
        n_steps = max(abs(tx - cx), abs(ty - cy), 1)
        for i in range(n_steps + 1):
            frac = i / max(n_steps, 1)
            px = int(cx + frac * (tx - cx))
            py = int(cy + frac * (ty - cy))
            if 0 <= px < self.image_size and 0 <= py < self.image_size:
                img[py, px] = 1.0
        
        # Draw pivot
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                px, py = cx + dx, cy + dy
                if 0 <= px < self.image_size and 0 <= py < self.image_size:
                    img[py, px] = 1.0
        
        # Draw bob
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx*dx + dy*dy <= 9:
                    px, py = tx + dx, ty + dy
                    if 0 <= px < self.image_size and 0 <= py < self.image_size:
                        img[py, px] = 1.0
        
        return img
    
    def __getitem__(self, idx):
        # Random initial state
        theta = self.rng.uniform(-np.pi, np.pi)
        omega = self.rng.uniform(-2, 2)
        
        frames = []
        for t in range(self.seq_len):
            frames.append(self._render_pendulum(theta))
            # Euler integration
            omega = omega - (self.g / self.L) * np.sin(theta) * self.dt
            theta = theta + omega * self.dt
        
        frames = torch.stack(frames, dim=0).unsqueeze(1)  # (T, 1, H, W)
        return frames, [0]
    
    @staticmethod
    def collate_fn(batch):
        frames_list = [item[0] for item in batch]
        labels_list = [item[1] for item in batch]
        frames = torch.stack(frames_list, dim=0)
        return frames, labels_list


class LimitedDataLoader:
    """Wrapper that limits the number of batches per epoch."""
    
    def __init__(self, dataloader, max_batches=None):
        self.dataloader = dataloader
        self.max_batches = max_batches
    
    def __iter__(self):
        for i, batch in enumerate(self.dataloader):
            if self.max_batches and i >= self.max_batches:
                break
            yield batch
    
    def __len__(self):
        if self.max_batches:
            return min(self.max_batches, len(self.dataloader))
        return len(self.dataloader)


def get_dataloader(dataset_name='moving_mnist', batch_size=16, seq_len=10,
                   image_size=32, train=True, seed=None, 
                   max_batches=None, max_samples=None, **kwargs):
    """Create dataloader for specified dataset."""
    
    if dataset_name == 'moving_mnist':
        dataset = MovingMNIST(
            seq_len=seq_len, image_size=image_size,
            train=train, seed=seed, max_samples=max_samples,
            **kwargs
        )
        dl = DataLoader(dataset, batch_size=batch_size, shuffle=train,
                        collate_fn=MovingMNIST.collate_fn,
                        num_workers=0, drop_last=True)
    
    elif dataset_name == 'pendulum':
        dataset = PendulumDataset(
            seq_len=seq_len, image_size=image_size,
            train=train, seed=seed, **kwargs
        )
        dl = DataLoader(dataset, batch_size=batch_size, shuffle=train,
                        collate_fn=PendulumDataset.collate_fn,
                        num_workers=0, drop_last=True)
    
    else:
        raise ValueError(f"Unknown dataset: {dataset_name}")
    
    if max_batches:
        return LimitedDataLoader(dl, max_batches=max_batches)
    return dl
