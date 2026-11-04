"""Trusted configuration validation. No agent-supplied code or filesystem paths."""
import hashlib
import json
import math

FAMILIES = {
    'residual_cnn': ['resnet18', 'resnet34', 'resnet50'],
    'dense_cnn': ['densenet121', 'densenet169', 'densenet201'],
    'efficient_cnn': ['efficientnet_b0', 'efficientnet_b1', 'efficientnet_b2', 'efficientnet_b3', 'efficientnet_b4', 'efficientnet_b5', 'squeezenet1_0', 'squeezenet1_1'],
    'mobile_cnn': ['mobilenet_v2', 'mobilenet_v3_small', 'mobilenet_v3_large', 'mnasnet0_5', 'mnasnet0_75', 'mnasnet1_0', 'mnasnet1_3'],
    'convnext_cnn': ['convnext_tiny'],
    'regnet_cnn': ['regnet_x_400mf', 'regnet_x_800mf', 'regnet_y_400mf', 'regnet_y_800mf', 'regnet_y_1_6gf', 'regnet_y_3_2gf'],
    'shuffle_cnn': ['shufflenet_v2_x0_5', 'shufflenet_v2_x1_0', 'shufflenet_v2_x1_5', 'shufflenet_v2_x2_0'],
}
REGISTRY = {name: family for family, names in FAMILIES.items() for name in names}


def packed(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(obj):
    return hashlib.sha256(packed(obj).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def number(value, minimum, maximum, name, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(name + ' must be a finite number')
    if integer and not isinstance(value, int):
        raise ValueError(name + ' must be an integer')
    if not minimum <= value <= maximum:
        raise ValueError(name + ' outside allowed bounds')
    return value


def config(raw):
    if not isinstance(raw, dict):
        raise ValueError('config must be an object')
    allowed = {'architecture', 'custom', 'optimizer', 'lr', 'weight_decay', 'batch_size', 'seed', 'epochs', 'stage', 'timeout_seconds'}
    if set(raw) - allowed:
        raise ValueError('Unknown config fields: ' + ','.join(sorted(set(raw) - allowed)))
    c = dict(raw)
    c.setdefault('optimizer', 'AdamW'); c.setdefault('lr', .001)
    c.setdefault('weight_decay', .001); c.setdefault('batch_size', 32)
    c.setdefault('stage', 'screen'); c.setdefault('epochs', 5); c.setdefault('timeout_seconds', None)
    if c.get('architecture') not in REGISTRY and c.get('architecture') != 'custom':
        raise ValueError('Architecture is not in the trusted registry')
    if c['optimizer'] not in ('AdamW', 'SGD') or c['stage'] not in ('screen', 'promote', 'confirm'):
        raise ValueError('Unsupported optimizer or stage')
    number(c.get('seed'), 0, 2147483647, 'seed', True)
    number(c['epochs'], 1, 2147483647, 'epochs', True)
    number(c['batch_size'], 8, 128, 'batch_size', True)
    if c['timeout_seconds'] is not None:
        number(c['timeout_seconds'], .01, 28800, 'timeout_seconds')
    number(c['lr'], .00001, .1, 'lr')
    number(c['weight_decay'], 0, .1, 'weight_decay')
    if c['architecture'] == 'custom':
        spec = c.get('custom')
        if not isinstance(spec, dict) or set(spec) != {'channels', 'kernel', 'norm', 'residual', 'dropout'}:
            raise ValueError('custom needs exactly channels,kernel,norm,residual,dropout')
        channels = spec['channels']
        if not isinstance(channels, list) or not 2 <= len(channels) <= 6:
            raise ValueError('custom channels must define 2..6 blocks')
        for width in channels:
            number(width, 16, 256, 'channels', True)
        if spec['kernel'] not in (3, 5, 7) or isinstance(spec['kernel'], bool):
            raise ValueError('kernel must be 3,5,7')
        if spec['norm'] not in ('batch', 'group') or not isinstance(spec['residual'], bool):
            raise ValueError('Invalid norm or residual flag')
        number(spec['dropout'], 0, .3, 'dropout')
        c['family'] = 'custom_cnn'
        # Probability is a recipe variable; dropout presence changes the module graph.
        graph = {k: v for k, v in spec.items() if k != 'dropout'}
        graph['dropout_enabled'] = spec['dropout'] > 0
        c['architecture_id'] = 'custom-' + digest(graph)[:16]
    else:
        if 'custom' in c:
            raise ValueError('custom fields are only allowed for architecture=custom')
        c['family'] = REGISTRY[c['architecture']]
        c['architecture_id'] = c['architecture']
    return c


def scientific(c):
    return {k: v for k, v in c.items() if k not in ('timeout_seconds', 'stage')}


def raw_config(c):
    return {k: v for k, v in c.items() if k not in ('family', 'architecture_id', 'actual_parameters')}
