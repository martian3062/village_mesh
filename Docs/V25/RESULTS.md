# V2.5 local validation

These results belong to this workstation and Development build. Rendered checks use D3D12 at 1440 x 900, 67% render scale and a 60 FPS cap. The workstation also ran other applications; these are not isolated hardware benchmarks. Automated scene time/weather changes are labelled test behaviour; crop growth remains disabled.

| Run | Rendering / build | Outcome | Frame p95 / max ms | CPU batch p95 ms | Director tick p95 ms |
| --- | --- | --- | --- | --- | --- |
| packaged_rendered | rendered standalone | pass | 16.81 / 198.32 | 0.343 | 0.057 |
| packaged_missing_model | NullRHI standalone | pass | not rendering evidence | 0.000 | 0.081 |
| packaged_rules | rendered standalone | pass | 16.85 / 184.97 | 0.492 | 0.073 |
| packaged_soak | rendered standalone | pass | 28.69 / 58.36 | 0.403 | 0.099 |

| Fictional resident | Rules / 180 s | Learned / 180 s | Learned soak / 1800 s |
| --- | ---: | ---: | ---: |
| Harjit | 0 | 0 | 5 |
| Simran | 3 | 3 | 20 |
| Aman | 0 | 0 | 10 |
| Gurleen | 0 | 0 | 4 |
| Navdeep | 4 | 4 | 14 |
| Mehar | 0 | 0 | 0 |
| Kiran | 3 | 3 | 18 |
| Jas | 0 | 0 | 0 |

Activity-completion coverage remains open for **Mehar, Jas**: neither completed an activity in this accelerated weather/schedule run. The bounded stability pass does not accept every resident routine.

Counts represent completed generic prototype activities, not reviewed human work animations. The two short runs use matched time/weather/capture scripts; the camera follows a moving resident, so the resulting views can differ. These individual runs do not establish a statistical behaviour or frame-rate advantage. The longer run uses a different weather period and is not a direct speed comparison.

A CPU batch is up to eight serialized policy calls on one worker-owned instance. The director tick excludes worker inference. Frame distributions exclude the first 20 simulation seconds; later streaming, font and capture hitches remain included. Queue delay, stale rejections, per-person activity and save/restore results are retained in [evidence.json](evidence.json). A successful bounded check does not certify every daily routine or an animation/vehicle swept path.

Six collision-enabled pedestrian traversals (three daylight, three rain) ran in the V2.5 standalone scene with residents and the CPU policy loaded in shadow mode. Exact paths, durations and frame measurements are retained in the traversal records in evidence.json. These checks are not vehicle clearance certification. The separate 30-minute simulation soak keeps the player at the start and exercises accelerated schedules/weather; it is not the earlier V2 moving-camera soak.

The original synthetic policy achieved 99.65% agreement with its rule teacher on the held-out scenario dataset; no advantage over that teacher is established. Rules remain the default. [Training evaluation](policy_evaluation.json).

## Open acceptance

Local wardrobe/voice/language review, complete cloth/contact/vehicle animation, measured roads/farms, separate GPU profiling, and independent fresh-machine release testing remain open. See the [acceptance register](../V25_ACCEPTANCE.txt).

Continuous run `packaged_soak`: 30.00 minutes, 4 completed tractor legs, peak process physical memory 1563.0 MiB. These bounded observations are not a memory-leak proof.
