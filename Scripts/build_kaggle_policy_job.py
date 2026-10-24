"""Bundle an explicit source allowlist into one private Kaggle script."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FILES = ('v25_contracts.py', 'train_v25_policy.py', 'train_v25_gpu.py')


def build(owner):
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', owner):
        raise ValueError('Invalid Kaggle owner')
    folder = ROOT / 'Saved/Kaggle/job'
    folder.mkdir(parents=True, exist_ok=True)
    sources = {name: (ROOT / 'Scripts' / name).read_text(encoding='utf-8') for name in FILES}
    hashes = {name: hashlib.sha256(value.encode()).hexdigest() for name, value in sources.items()}
    bootstrap = '''import importlib.util
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
requirements = [('onnx', 'onnx==1.18.0'), ('onnxruntime', 'onnxruntime==1.20.1')]
for module, requirement in requirements:
    if importlib.util.find_spec(module) is None:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', requirement], check=True)
root = Path('/kaggle/working/village_mesh_source')
root.mkdir(parents=True, exist_ok=True)
'''
    bootstrap += 'sources = ' + repr(sources) + '\nsource_hashes = ' + repr(hashes) + '\n'
    bootstrap += '''for name, source in sources.items():
    (root / name).write_text(source)
output = Path('/kaggle/working/village_mesh_results')
output.mkdir(parents=True, exist_ok=True)
(output / 'source_hashes.json').write_text(json.dumps(source_hashes, indent=2))
sys.path.insert(0, str(root))
runpy.run_path(str(root / 'train_v25_gpu.py'), run_name='__main__')
'''
    compile(bootstrap, 'village_mesh_gpu.py', 'exec')
    (folder / 'village_mesh_gpu.py').write_text(bootstrap, encoding='utf-8')
    metadata = {'id': owner + '/village-mesh-tinyai-gpu-pilot',
                'title': 'Village Mesh TinyAI GPU Pilot', 'code_file': 'village_mesh_gpu.py',
                'language': 'python', 'kernel_type': 'script', 'is_private': True,
                'enable_gpu': True, 'enable_internet': True,
                'dataset_sources': [], 'competition_sources': [], 'kernel_sources': []}
    (folder / 'kernel-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    (folder / 'source_hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(json.dumps({'kernel': metadata['id'], 'private': True, 'source_files': list(FILES), 'sha256': hashes}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--owner', required=True)
    build(parser.parse_args().owner)
