"""Trusted fixed trainer. Invoked only by controller; no arbitrary model code."""
import argparse
import copy
import csv
import json
import os
from pathlib import Path
import random
import time

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['CUDA_CACHE_DISABLE'] = '1'
import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from common import config, REGISTRY, file_hash


class Block(nn.Module):
    def __init__(self, inc, out, kernel, norm, residual, dropout):
        super().__init__()
        def normalization():
            groups = max(g for g in range(1, min(32, out) + 1) if out % g == 0)
            return nn.BatchNorm2d(out) if norm == 'batch' else nn.GroupNorm(groups, out)
        self.main = nn.Sequential(nn.Conv2d(inc, out, kernel, padding=kernel//2, bias=False),
                                  normalization(), nn.ReLU(),
                                  nn.Conv2d(out, out, kernel, padding=kernel//2, bias=False), normalization())
        self.residual = residual
        self.shortcut = (nn.Identity() if inc == out else nn.Conv2d(inc, out, 1, bias=False)) if residual else None
        self.tail = nn.Sequential(nn.ReLU(), nn.Dropout2d(dropout) if dropout else nn.Identity(), nn.MaxPool2d(2))

    def forward(self, x):
        value = self.main(x)
        if self.residual:
            value = value + self.shortcut(x)
        return self.tail(value)


def build(c):
    if c['architecture'] == 'custom':
        spec = c['custom']; layers = []; inc = 3
        for out in spec['channels']:
            layers.append(Block(inc, out, spec['kernel'], spec['norm'], spec['residual'], spec['dropout']))
            inc = out
        return nn.Sequential(*layers, nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Linear(inc, 3))
    model = getattr(models, c['architecture'])(weights=None)
    if hasattr(model, 'fc') and isinstance(model.fc, nn.Linear):
        model.fc = nn.Linear(model.fc.in_features, 3)
    elif isinstance(model.classifier, nn.Linear):
        model.classifier = nn.Linear(model.classifier.in_features, 3)
    else:
        indices = [i for i, layer in enumerate(model.classifier) if isinstance(layer, nn.Linear)]
        if indices:
            i = indices[-1]
            model.classifier[i] = nn.Linear(model.classifier[i].in_features, 3)
        elif c['architecture'].startswith('squeezenet'):
            model.classifier[1] = nn.Conv2d(512, 3, 1)
            model.num_classes = 3
        else:
            raise ValueError('No supported classification head')
    return model


def probe(c):
    model = build(c)
    params = sum(p.numel() for p in model.parameters())
    if not 1000 <= params <= 30000000:
        raise ValueError('Actual parameter count outside [1000,30000000]: ' + str(params))
    model.eval()
    with torch.inference_mode():
        output = model(torch.zeros(2, 3, 160, 160))
    if output.shape != (2, 3) or not torch.isfinite(output).all():
        raise ValueError('Model forward did not produce finite [2,3] output')
    return {'parameters': params, 'forward_shape': list(output.shape)}


def score(y, p):
    cm = np.bincount(np.asarray(y)*3 + np.asarray(p), minlength=9).reshape(3, 3)
    denominator = cm.sum(axis=0) + cm.sum(axis=1)
    f = np.divide(2*np.diag(cm), denominator, out=np.zeros(3), where=denominator != 0)
    return {'validation_macro_f1': float(f.mean()), 'validation_accuracy': float(np.trace(cm)/cm.sum()),
            'confusion_matrix': cm.tolist(), 'per_class_f1': f.tolist()}


class Images(Dataset):
    def __init__(self, images, records, split):
        self.images = images
        self.records = [r for r in records if r['split'] == split]
        self.augment = transforms.Compose([transforms.RandomHorizontalFlip(.5), transforms.RandomRotation(10)]) if split == 'train' else None

    def __len__(self):
        return len(self.records)

    def __getitem__(self, index):
        r = self.records[index]
        x = torch.from_numpy(np.array(self.images[r['index']], dtype=np.float32)).unsqueeze(0).repeat(3, 1, 1)
        if self.augment:
            x = self.augment(x)
        return (x-.5)/.5, int(r['label'])


@torch.inference_mode()
def predict(model, loader, device):
    model.eval(); probs = []; labels = []
    for x, y in loader:
        with torch.autocast('cuda', dtype=torch.float16, enabled=device.type == 'cuda'):
            logits = model(x.to(device))
        probs.append(logits.float().softmax(1).cpu().numpy()); labels.extend(y.tolist())
    return np.concatenate(probs), np.asarray(labels)


def train(c, data, output):
    started = time.monotonic()
    random.seed(c['seed']); np.random.seed(c['seed']); torch.manual_seed(c['seed'])
    torch.backends.cudnn.benchmark = False; torch.backends.cudnn.deterministic = True
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    if device.type != 'cuda':
        raise ValueError('Research execution requires the configured CUDA GPU')
    images = np.load(data/'images_fp16.npy', mmap_mode='r')
    records = json.loads((data/'records.json').read_text())
    if any(r['split'] not in ('train', 'val') for r in records):
        raise ValueError('Forbidden split in trainer inputs')
    trainset = Images(images, records, 'train'); valset = Images(images, records, 'val')
    loader = DataLoader(trainset, batch_size=c['batch_size'], shuffle=True, num_workers=0)
    validation = DataLoader(valset, batch_size=32, shuffle=False, num_workers=0)
    model = build(c).to(device)
    params = sum(p.numel() for p in model.parameters())
    if not 1000 <= params <= 30000000:
        raise ValueError('Actual parameter limit violation')
    if c['optimizer'] == 'AdamW':
        optimizer = torch.optim.AdamW(model.parameters(), lr=c['lr'], weight_decay=c['weight_decay'])
    else:
        optimizer = torch.optim.SGD(model.parameters(), lr=c['lr'], weight_decay=c['weight_decay'], momentum=.9)
    scaler = torch.amp.GradScaler('cuda'); criterion = nn.CrossEntropyLoss()
    best = -1.; best_epoch = None; history = []
    for epoch in range(1, c['epochs']+1):
        model.train(); total_loss = 0.
        for x, y in loader:
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast('cuda', dtype=torch.float16):
                loss = criterion(model(x.to(device)), y.to(device))
            if not torch.isfinite(loss):
                raise ValueError('Nonfinite loss')
            scaler.scale(loss).backward(); scaler.step(optimizer); scaler.update()
            total_loss += float(loss.detach())*len(y)
        probabilities, labels = predict(model, validation, device)
        metrics = score(labels, probabilities.argmax(1))
        history.append({'epoch': epoch, 'train_loss': total_loss/len(trainset), **metrics})
        if metrics['validation_macro_f1'] > best:
            best = metrics['validation_macro_f1']; best_epoch = epoch
            # Preserve metadata (MNASNet) and clone tensors for CPU/GPU alike.
            weights = copy.deepcopy(model.state_dict())
            for key, value in weights.items():
                weights[key] = value.detach().cpu().clone()
            torch.save(weights, output/'best_model.pt')
        (output/'history.json').write_text(json.dumps(history, indent=2))
    model.load_state_dict(torch.load(output/'best_model.pt', map_location=device, weights_only=True))
    eval_started = time.monotonic()
    probabilities, labels = predict(model, validation, device)
    eval_seconds = time.monotonic()-eval_started
    metrics = score(labels, probabilities.argmax(1))
    if abs(metrics['validation_macro_f1']-best) > 1e-12:
        raise ValueError('Checkpoint does not reproduce its selected score')
    with (output/'validation.csv').open('w', newline='') as f:
        writer = csv.writer(f); writer.writerow(['index', 'p0', 'p1', 'p2'])
        for r, prob in zip(valset.records, probabilities):
            writer.writerow([r['index'], *map(float, prob)])
    result = {**metrics, 'epochs_completed': c['epochs'], 'best_epoch': best_epoch, 'parameters': params,
              'seed': c['seed'], 'architecture_id': c['architecture_id'], 'device': str(device),
              'precision': 'AMP float16', 'validation_seconds': eval_seconds,
              'trainer_elapsed_seconds': time.monotonic()-started,
              'checkpoint_sha256': file_hash(output/'best_model.pt')}
    (output/'metrics.json').write_text(json.dumps(result, indent=2))
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', type=Path)
    p.add_argument('--data', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--probe', action='store_true')
    p.add_argument('--catalogue', action='store_true')
    a = p.parse_args()
    torch.set_num_threads(4)
    if a.catalogue:
        results = {}
        for arch, family in REGISTRY.items():
            c = config({'architecture': arch, 'seed': 0})
            results[arch] = {'family': family, **probe(c)}
        print(json.dumps(results)); return
    c = config(json.loads(a.config.read_text()))
    if a.probe:
        print(json.dumps(probe(c))); return
    if not a.output.is_dir() or not a.data.is_dir():
        raise ValueError('Controller must create output and provide trusted inputs')
    print(json.dumps(train(c, a.data, a.output)))


if __name__ == '__main__':
    main()
