"""GPU candidate experiment using only original synthetic numeric NPC states."""
import copy
import datetime
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import onnx
import onnxruntime as ort
import torch

from train_v25_policy import Policy, dataset
from v25_contracts import SCHEMA


def main():
    output = Path('/kaggle/working/village_mesh_results')
    output.mkdir(parents=True, exist_ok=True)
    report = {
        'passed': False, 'recorded_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'feature_schema': SCHEMA, 'cuda_available': torch.cuda.is_available(),
        'torch_version': torch.__version__, 'cuda_version': torch.version.cuda,
        'scope': 'Synthetic controller imitation candidate; no Unreal or MetaHuman data; no runtime model replacement.',
        'baseline_benefit_proven': False, 'trials': [],
    }
    report_path = output / 'gpu_evaluation.json'

    def save():
        report_path.write_text(json.dumps(report, indent=2) + '\n')

    save()
    if not report['cuda_available']:
        raise RuntimeError('A CUDA GPU is required; CPU fallback would not verify GPU access')
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    report.update(gpu_name=torch.cuda.get_device_name(0), gpu_count=torch.cuda.device_count(), used_device='cuda:0')
    validation = tuple(t.to('cuda') for t in dataset(9001, 4000, True))
    best_score, best_state = -1., None
    for seed in (3062, 104729, 24010):
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        np.random.seed(seed)
        model = Policy().to('cuda')
        parameters = sum(p.numel() for p in model.parameters())
        if parameters != 121520:
            raise RuntimeError('Policy architecture changed')
        train = tuple(t.to('cuda') for t in dataset(seed, 16000))
        optimizer = torch.optim.AdamW(model.parameters(), lr=.002, weight_decay=.001)
        torch.cuda.synchronize()
        started = time.perf_counter()
        model.train()
        for _epoch in range(36):
            for ids in torch.randperm(len(train[0]), device='cuda').split(256):
                x, mask, labels = (t[ids] for t in train)
                loss = torch.nn.functional.cross_entropy(model(x).masked_fill(~mask, -1e9), labels)
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - started
        model.eval()
        x, mask, labels = validation
        with torch.no_grad():
            prediction = model(x).masked_fill(~mask, -1e9).argmax(1)
        agreement = float((prediction == labels).float().mean())
        trial = {'seed': seed, 'epochs': 36, 'train_rows': 16000, 'validation_seed': 9001,
                 'validation_rows': 4000, 'validation_teacher_agreement': agreement,
                 'train_seconds': elapsed, 'unique_parameters': parameters}
        report['trials'].append(trial)
        if agreement > best_score:
            best_score, best_state = agreement, copy.deepcopy(model.cpu().state_dict())
            report['selected_seed'] = seed
        save()
        print(json.dumps(trial), flush=True)

    # Selection uses seed 9001 only. Seed 9002 is evaluated once after selection.
    model = Policy().to('cuda')
    model.load_state_dict(best_state)
    model.eval()
    x, mask, labels = dataset(9002, 4000, True)
    with torch.no_grad():
        gpu_logits = model(x.to('cuda')).cpu()
    predictions = gpu_logits.masked_fill(~mask, -1e9).argmax(1)
    agreement = float((predictions == labels).float().mean())
    invalid = int((~mask[torch.arange(len(labels)), predictions]).sum())
    model = model.cpu()
    with torch.no_grad():
        cpu_logits = model(x)
    gpu_cpu_error = float((gpu_logits - cpu_logits).abs().max())
    candidate = output / 'candidate_npc_policy.onnx'
    torch.onnx.export(model, torch.zeros(1, 64), str(candidate), input_names=['state'],
                      output_names=['logits'], opset_version=17, dynamo=False)
    exported = onnx.load(candidate)
    onnx.checker.check_model(exported)
    physical = sum(int(np.prod(t.dims)) for t in exported.graph.initializer)
    session = ort.InferenceSession(str(candidate), providers=['CPUExecutionProvider'])
    errors = [float(np.max(np.abs(session.run(None, {'state': x[i:i+1].numpy()})[0] - cpu_logits[i:i+1].numpy()))) for i in range(64)]
    report.update(final_test_seed=9002, final_test_rows=4000, final_teacher_agreement=agreement,
                  invalid_after_mask=invalid, gpu_cpu_max_abs_error=gpu_cpu_error,
                  onnx_max_abs_error=max(errors), physical_initializer_values=physical,
                  candidate_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
                  candidate_bytes=candidate.stat().st_size, ort_version=ort.__version__, onnx_version=onnx.__version__,
                  candidate_status='requires_local_Unreal_parity_and_behavior_review')
    report['passed'] = agreement >= .99 and invalid == 0 and physical == 121520 and gpu_cpu_error < .0001 and max(errors) < .0001
    save()
    print(json.dumps(report), flush=True)
    if not report['passed']:
        raise RuntimeError('GPU candidate failed evaluation gates; keep the existing runtime model')


if __name__ == '__main__':
    main()
