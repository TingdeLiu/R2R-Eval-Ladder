import argparse
import subprocess
from pathlib import Path
from .core import *

def main():
    parser = argparse.ArgumentParser(description='Frozen nested VLN-CE evaluation datasets and audits')
    sub = parser.add_subparsers(dest='command', required=True)
    gen = sub.add_parser('generate')
    for name in ('source', 'parent100', 'parent500', 'out'):
        gen.add_argument('--'+name, required=True)
    gen.add_argument('--seed', type=int, default=20261006)
    gen.add_argument('--holdout')
    audit = sub.add_parser('audit')
    audit.add_argument('--directory', required=True)
    audit.add_argument('--source', required=True)
    cache = sub.add_parser('cache')
    cache.add_argument('--records', required=True)
    rep = sub.add_parser('report')
    for name in ('directory', 'b0', 'candidate', 'b0-manifest', 'candidate-manifest', 'out'):
        rep.add_argument('--'+name, required=True)
    stage = sub.add_parser('stage')
    stage.add_argument('--manifest', required=True)
    stage.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.command == 'generate':
        generate(args.source, args.parent100, args.parent500, args.out, args.seed, holdout=args.holdout)
    elif args.command == 'audit':
        directory = Path(args.directory)
        source = index(read(args.source)['episodes'])
        for path in directory.glob('*.manifest.json'):
            m = read(path)
            if sha(args.source) != m['source_sha256'] or sha(directory / m['output_dataset']) != m['output_sha256']:
                raise ValueError('Manifest hash mismatch')
            rows = read(directory / m['output_dataset'])['episodes']
            validate_subset(source, rows, m['output_count'])
            if [list(key(r)) for r in rows] != m['selected_keys']:
                raise ValueError('Manifest selected keys mismatch')
            if [list(key(read(args.source)['episodes'][i])) for i in m['selected_source_indices']] != [list(key(r)) for r in read(args.source)['episodes'] if key(r) in index(rows)]:
                raise ValueError('Source indices mismatch')
        a,b,c = [set(index(read(directory / f'random{n}_v1.json.gz')['episodes'])) for n in (100,500,1000)]
        if not a < b < c or len(a)!=100 or len(b)!=500 or len(c)!=1000:
            raise ValueError('Invalid ladder')
        for n, expected in ((400,b-a),(500,c-b)):
            if set(index(read(directory / f'additional{n}_v1.json.gz')['episodes'])) != expected:
                raise ValueError('Invalid increment')
    elif args.command == 'cache':
        cache_audit(read(args.records))
    elif args.command == 'report':
        directory = Path(args.directory)
        datasets = [read(directory / f'random{n}_v1.json.gz')['episodes'] for n in (100,500,1000)]
        a,b,c = [set(index(r)) for r in datasets]
        manifest_path = directory / 'random1000_v1.manifest.json'
        bm, cm = read(args.b0_manifest), read(args.candidate_manifest)
        if bm.get('dataset_manifest_sha256') != sha(manifest_path):
            raise ValueError('Run manifest does not lock supplied dataset manifest')
        left,right = pairing(read(args.b0), read(args.candidate), datasets[2], bm, cm)
        write(args.out, report({'original100':a,'additional400':b-a,'additional500':c-b,'combined500':b,'combined1000':c},left,right))
    elif args.command == 'stage':
        m = read(args.manifest)
        for field in ('event_count', 'p50_prompt_tokens', 'p50_completion_tokens', 'retry_rate', 'failure_reserve', 'approved_token_budget'):
            value = m[field]
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not __import__('math').isfinite(value) or value < 0:
                raise ValueError(f'Invalid budget field: {field}')
        if not isinstance(m['command'], list) or not m['command'] or not all(isinstance(v, str) for v in m['command']):
            raise ValueError('Command must be a nonempty string argument array')
        if any(f not in m for f in LOCK_FIELDS):
            raise ValueError('Incomplete run manifest')
        if m['stage'] not in ('smoke','P1','P2','P3'):
            raise ValueError('Unknown stage')
        if m['stage'] != 'smoke' and not m.get('previous_stage_passed'):
            raise ValueError('Previous stage has not passed')
        if m['stage'] in ('P2','P3') and not m.get('protocol_frozen'):
            raise ValueError('Protocol is not frozen')
        estimate = m['event_count']*(m['p50_prompt_tokens']+m['p50_completion_tokens'])*(1+m['retry_rate']+m['failure_reserve'])
        if estimate > m['approved_token_budget']:
            raise ValueError('Insufficient approved token budget')
        for file, field in ((m['dataset_manifest'],'dataset_manifest_sha256'),(m['checkpoint'],'checkpoint_sha256'),(m['config'],'config_sha256'),(m['cache_policy'],'cache_policy_sha256')):
            if sha(file) != m[field]:
                raise ValueError(f'Run input hash mismatch: {field}')
        if subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip() != m['source_commit']:
            raise ValueError('Source commit mismatch')
        if subprocess.check_output(['git','status','--porcelain'],text=True).strip():
            raise ValueError('Source checkout is dirty')
        print(json.dumps({'estimated_reserved_tokens':estimate,'command':m['command'],'stage':m['stage']}))
        if args.execute:
            subprocess.run(m['command'], check=True, shell=False)
    print('Validation passed')

if __name__ == '__main__':
    main()
