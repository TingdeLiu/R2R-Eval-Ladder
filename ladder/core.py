import gzip
import hashlib
import json
import random
from pathlib import Path

SOURCE_SHA = '0e4fddca056d2e012ecc52f43a259ebddb1128503a7767b5da3b5af8ea8cf653'
PARENT_SHA = {100: '3b80bf55c1c070e92f796a04f26f848a500acb41365d4fdb2fe6e502a4036fea', 500: '19ea4ac4dd0bc513c5bcbc1f69326f556193e95b8b122ed0db8faf52db506d9f'}

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    data = Path(path).read_bytes()
    return json.loads(gzip.decompress(data) if str(path).endswith('.gz') else data)

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical(value)
    if str(path).endswith('.gz'):
        data = gzip.compress(data, compresslevel=9, mtime=0)
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f'Refusing to overwrite frozen artifact: {path}')
    path.write_bytes(data)

def key(row):
    return (str(row['scene_id']), str(row['episode_id']))

def index(rows):
    result = {key(r): r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate (scene_id, episode_id)')
    return result

def validate_subset(source, rows, count=None):
    subset = index(rows)
    if count is not None and len(subset) != count:
        raise ValueError(f'Expected {count} episodes, got {len(subset)}')
    for k, row in subset.items():
        if k not in source or canonical(row) != canonical(source[k]):
            raise ValueError(f'Episode differs from source: {k}')
    return subset

def logical_label(value, fallback):
    """Return a single relative label suitable for a published manifest."""
    label = str(value) if value else Path(fallback).name
    if not label or label in ('.', '..') or '/' in label or '\\' in label or Path(label).name != label:
        raise ValueError('Dataset labels must be single relative names')
    return label

def generate(source_path, parent100, parent500, out, seed=20261006, expected_sha=SOURCE_SHA, counts=(100, 500, 1000), check_parent_hash=True, holdout=None, source_label=None, parent_labels=None, holdout_label=None):
    if sha(source_path) != expected_sha:
        raise ValueError('Source SHA-256 mismatch')
    source = read(source_path)
    source_index = index(source['episodes'])
    paths = [parent100, parent500]
    parents = [read(p) for p in paths]
    maps = [validate_subset(source_index, p['episodes'], n) for p, n in zip(parents, counts[:2])]
    if not maps[0].keys() < maps[1].keys():
        raise ValueError('S100 must be a strict subset of S500')
    if check_parent_hash:
        for p, n in zip(paths, counts[:2]):
            if sha(p) != PARENT_SHA[n]:
                raise ValueError('Frozen parent SHA-256 mismatch')
    excluded = set()
    if holdout:
        excluded = set(validate_subset(source_index, read(holdout)['episodes']))
        if excluded & maps[1].keys():
            raise ValueError('Holdout overlaps parent')
    remaining = [i for i, r in enumerate(source['episodes']) if key(r) not in maps[1] and key(r) not in excluded]
    selected = random.Random(seed).sample(remaining, counts[2] - counts[1])
    additional = [source['episodes'][i] for i in selected]
    combined = parents[1]['episodes'] + additional
    validate_subset(source_index, combined, counts[2])
    out = Path(out)
    # Record seed and inputs before producing outputs.
    source_label = logical_label(source_label, source_path)
    raw_labels = parent_labels if parent_labels is not None else [Path(p).name for p in paths]
    labels = [logical_label(label, path) for label, path in zip(raw_labels, paths)]
    if len(labels) != 2:
        raise ValueError('parent_labels must contain exactly two labels')
    plan = {'version': 'nested_random_episode_subset_v1', 'seed': seed,
            'source_dataset': source_label, 'source_sha256': expected_sha,
            'parent_datasets': [{'path': label, 'count': n, 'sha256': sha(p)} for p, n, label in zip(paths, counts[:2], labels)],
            'holdout_sha256': sha(holdout) if holdout else None,
            'holdout_dataset': logical_label(holdout_label, holdout) if holdout else None}
    write(out / 'generation_plan.json', plan)
    groups = {f'random{counts[0]}_v1': parents[0]['episodes'], f'random{counts[1]}_v1': parents[1]['episodes'],
              f'additional{counts[1]-counts[0]}_v1': [r for r in parents[1]['episodes'] if key(r) not in maps[0]],
              f'additional{counts[2]-counts[1]}_v1': additional, f'random{counts[2]}_v1': combined}
    for name, rows in groups.items():
        rows = sorted(rows, key=key)
        payload = {**source, 'episodes': rows}
        output = out / (name + '.json.gz')
        write(output, payload)
        validate_subset(source_index, read(output)['episodes'], len(rows))
        manifest = {**plan, 'output_dataset': output.name, 'output_count': len(rows), 'parent_count': counts[1],
                    'additional_count': counts[2]-counts[1], 'selected_source_indices': [i for i, r in enumerate(source['episodes']) if key(r) in index(rows)],
                    'selected_keys': [list(key(r)) for r in rows], 'output_sha256': sha(output)}
        write(out / (name + '.manifest.json'), manifest)
    return groups

LOCK_FIELDS = ('protocol_version', 'dataset_manifest_sha256', 'source_commit', 'checkpoint_sha256', 'model', 'model_version', 'config_sha256', 'episode_seed', 'max_steps', 'cache_policy_sha256')

def pairing(b0, candidate, dataset, b0_manifest, candidate_manifest):
    for field in LOCK_FIELDS:
        if field not in b0_manifest or b0_manifest[field] != candidate_manifest.get(field):
            raise ValueError(f'Pairing lock mismatch: {field}')
    left, right, expected = index(b0), index(candidate), index(dataset)
    if left.keys() != expected.keys() or right.keys() != expected.keys():
        raise ValueError('Results must exactly cover dataset')
    for k in expected:
        for metric in ('sr', 'spl', 'os', 'ne', 'steps'):
            for row in (left[k], right[k]):
                v = row[metric]
                if not isinstance(v, (int, float)) or isinstance(v, bool) or not __import__('math').isfinite(v) or v < 0:
                    raise ValueError(f'Invalid metric {metric}: {k}')
                if metric in ('sr', 'os') and v not in (0, 1) or metric == 'spl' and v > 1:
                    raise ValueError(f'Invalid metric range: {metric}')
    return left, right

def cache_audit(records):
    required = ('protocol_version', 'dataset_manifest_sha256', 'source_commit', 'model', 'model_version', 'schema', 'system_prompt', 'user_prompt', 'media_sha256', 'event_id', 'scene_id', 'episode_id', 'control_epoch', 'frame_sequence')
    for row in records:
        request = row['request']
        if any(f not in request for f in required):
            raise ValueError('Incomplete cache input identity')
        if digest(request) != row['input_sha256']:
            raise ValueError('Cache input hash mismatch')
        if any(f not in row for f in ('response', 'technical_error', 'fallback', 'cache_hit')):
            raise ValueError('Cache must preserve response, errors, fallback and hits')
        if row['cache_hit'] and row.get('reused_input_sha256') != row['input_sha256']:
            raise ValueError('Reused cache identity mismatch')

def report(groups, left, right, samples=2000, seed=20261006):
    output = {}
    for name, keys in groups.items():
        keys = sorted(keys)
        if not keys:
            raise ValueError('Empty report group')
        rng = random.Random(seed)
        metrics = {}
        for metric in ('sr', 'spl', 'os', 'ne', 'steps'):
            values = [right[k][metric]-left[k][metric] for k in keys]
            boot = sorted(sum(rng.choices(values, k=len(values)))/len(values) for _ in range(samples))
            metrics[metric] = {'b0': sum(left[k][metric] for k in keys)/len(keys), 'candidate': sum(right[k][metric] for k in keys)/len(keys),
                               'delta': sum(values)/len(values), 'paired_bootstrap_95_ci': [boot[int(.025*samples)], boot[min(samples-1, int(.975*samples))]]}
        gain = sum(left[k]['sr'] == 0 and right[k]['sr'] == 1 for k in keys)
        loss = sum(left[k]['sr'] == 1 and right[k]['sr'] == 0 for k in keys)
        successes = sum(left[k]['sr'] for k in keys)
        output[name] = {'count': len(keys), 'gain': gain, 'loss': loss, 'net_gain': gain-loss, 'success_retention': (successes-loss)/successes if successes else None, 'metrics': metrics}
    return output
