"""Validate a downloaded GPU candidate without changing the deployed model."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort

from build_kaggle_policy_job import FILES, ROOT
from train_v25_policy import dataset


def evaluate(folder):
    folder = Path(folder)
    report = json.loads((folder / 'gpu_evaluation.json').read_text())
    source_hashes = json.loads((folder / 'source_hashes.json').read_text())
    expected = {name: hashlib.sha256((ROOT / 'Scripts' / name).read_text(encoding='utf-8').encode()).hexdigest() for name in FILES}
    if source_hashes != expected:
        raise ValueError('Downloaded job sources differ from the current reviewed source bundle')
    candidate = folder / 'candidate_npc_policy.onnx'
    digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
    if digest != report['candidate_sha256'] or not report['passed'] or not report['cuda_available']:
        raise ValueError('Remote GPU report or candidate digest failed verification')
    model = onnx.load(candidate, load_external_data=False)
    if any(t.external_data for t in model.graph.initializer):
        raise ValueError('Candidate must not depend on external weight files')
    if any(n.op_type not in {'Gemm', 'Relu'} or n.domain for n in model.graph.node):
        raise ValueError('Unexpected candidate operators')
    onnx.checker.check_model(model)
    physical = sum(int(np.prod(t.dims)) for t in model.graph.initializer)
    if physical != 121520:
        raise ValueError('Unexpected candidate parameter count')
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    current = ROOT / 'Assets/Models/npc_policy_v1.onnx'
    x, mask, labels = dataset(9002, 4000, True)
    x, mask, labels = x.numpy(), mask.numpy(), labels.numpy()
    scores = {}
    for name, path in [('candidate', candidate), ('existing_experimental_model', current)]:
        session = ort.InferenceSession(str(path), options, providers=['CPUExecutionProvider'])
        if session.get_inputs()[0].shape != [1, 64] or session.get_outputs()[0].shape != [1, 48]:
            raise ValueError('Unexpected ONNX runtime dimensions')
        logits = np.concatenate([session.run(None, {'state': row[None]})[0] for row in x])
        if not np.isfinite(logits).all():
            raise ValueError('Non-finite model output')
        prediction = np.where(mask, logits, -1e9).argmax(1)
        scores[name] = {'teacher_agreement': float(np.mean(prediction == labels)),
                        'invalid_after_mask': int(np.sum(~mask[np.arange(len(labels)), prediction])),
                        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    candidate_score = scores['candidate']
    result = {'passed': candidate_score['teacher_agreement'] >= .99 and candidate_score['invalid_after_mask'] == 0,
              'recorded_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'test_seed': 9002, 'rows': 4000, 'physical_initializer_values': physical,
              'source_hashes_verified': True, 'download_sha256_verified': True, 'scores': scores,
              'onnxruntime_version': ort.__version__, 'deployed_model_changed': False,
              'scope': 'Local CPU ONNX validation on synthetic states. No Unreal NNE parity, gameplay benefit or release claim.'}
    (folder / 'local_validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    if not result['passed']:
        raise RuntimeError('Candidate failed local evaluation')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', required=True)
    evaluate(parser.parse_args().results)
