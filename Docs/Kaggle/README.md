# Kaggle GPU training for Village Mesh

The project account is connected. On 24 October 2026, private kernel version 1 completed three CUDA training trials on a **Tesla T4**. The session exposed two T4 devices; this small model used `cuda:0`. Server metadata readback confirmed `is_private: true`, `enable_gpu: true`, and `machine_shape: NvidiaTeslaT4`.

This provides remote compute for the numeric TinyAI experiment. Unreal Editor, rendering, character assembly and interactive play still run on the local machine.

## Verified result

| Check | Result |
| --- | --- |
| Architecture | 64-256-256-128-48 MLP, 121,520 learned values |
| Training | Three seeds, 16,000 synthetic states and 36 epochs per trial |
| Validation | Separate seed 9001, 4,000 states; selects a candidate |
| Final evaluation | Seed 9002, 4,000 states, evaluated after selection |
| Candidate agreement with the authored controller | 99.8% on the final set |
| Existing experimental model on the same final set | 99.675% |
| Invalid actions after the mandatory action mask | 0 for both |
| Candidate ONNX size | 486,961 bytes |
| Local validation | Download/source hashes, ONNX structure, parameter count and CPU inference passed |

The [GPU report](gpu_evaluation.json), [local validation](local_validation.json), and [source digests](source_hashes.json) record the evidence. This is synthetic controller imitation, not proof of better gameplay, Punjabi language ability or improvement over the deterministic rules. The rules remain the default, and the existing experimental runtime model has not been replaced. Promotion requires Unreal NNE parity and behavior checks.

The candidate is local at `Saved/Kaggle/results/v1/village_mesh_results/candidate_npc_policy.onnx`. Weights, downloaded logs, the Python environment and account metadata stay under ignored `Saved/Kaggle`.

## Run again

The installed CLI is isolated from the project Python environment:

```powershell
python -m venv Saved/Kaggle/venv
.\Saved\Kaggle\venv\Scripts\python.exe -m pip install kaggle==2.2.5
```

On this machine the project token is already in `%LOCALAPPDATA%\VillageMesh\Kaggle\access_token`, outside Git, with access restricted to the current Windows user. For another machine, create this local file with that machine's own token. Never add the token or a credential screenshot to the repository. The runner supplies the token through a child-process environment and restores the caller's environment afterward.

```powershell
.\Scripts\kaggle_policy.ps1 -Action Prepare
.\Scripts\kaggle_policy.ps1 -Action Run
.\Scripts\kaggle_policy.ps1 -Action Status
.\Scripts\kaggle_policy.ps1 -Action Logs
.\Scripts\kaggle_policy.ps1 -Action Readback
.\Scripts\kaggle_policy.ps1 -Action Download
python Scripts/evaluate_kaggle_candidate.py --results Saved/Kaggle/results/v1/village_mesh_results
```

Use the version recorded in `Saved/Kaggle/run.json` in the last command. `Prepare` authenticates and builds an explicit source bundle. `Run` creates a private kernel version, requests T4 compute, and caps execution at 1,800 seconds. The remaining commands address that exact version. A job fails if CUDA is unavailable; it does not silently claim CPU execution as a GPU run.

Only `v25_contracts.py`, `train_v25_policy.py` and `train_v25_gpu.py` enter the upload. The job generates synthetic states remotely. It contains no credentials, resident records, geographic assets, MetaHuman art, DNA, animations or rendered images. The candidate workflow does not train on Epic content.

The [official Kaggle authentication documentation](https://github.com/Kaggle/kaggle-cli/blob/main/docs/README.md#authentication) describes token authentication. The [kernel CLI documentation](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md) documents private-job metadata, versioned results and accelerator requests. Actual GPU availability and quota are determined by Kaggle for the account at run time.
