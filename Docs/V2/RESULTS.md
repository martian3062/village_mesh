# Local V2 results

Unreal 5.8.3 on the [recorded workstation](hardware_snapshot.json). Rendered diagnostics use offscreen D3D12, Epic scalability, 1440 x 900 output, 67% render scale for traversal and 100% for captures. Timings are observed frame wall time after warmup, not a separate CPU/GPU profile.

| Run | Build | Outcome | p95 / max frame ms | Peak process MiB |
| --- | --- | --- | --- | --- |
| capture_daylight_local.json | editor game | pass | not a route benchmark | 2401.7 |
| capture_evening_local.json | editor game | pass | not a route benchmark | 3257.7 |
| capture_overcast_local.json | editor game | pass | not a route benchmark | 3262.9 |
| capture_rain_local.json | editor game | pass | not a route benchmark | 2320.0 |
| interactions_rain_local.json | editor game (NullRHI) | pass | not a route benchmark | 1919.5 |
| interactions_rain_packaged_final.json | standalone package | pass | not a route benchmark | 1499.6 |
| route_daylight_packaged_trial1.json | standalone package | pass | 10.98 / 15.82 | 1575.8 |
| route_daylight_packaged_trial2.json | standalone package | pass | 13.13 / 31.43 | 1507.1 |
| route_daylight_packaged_trial3.json | standalone package | pass | 12.25 / 29.23 | 1474.7 |
| route_daylight_trial1.json | editor game | pass | 12.06 / 93.72 | 2233.2 |
| route_daylight_trial2.json | editor game | pass | 10.94 / 29.77 | 3239.0 |
| route_daylight_trial3.json | editor game | pass | 12.40 / 87.04 | 3237.6 |
| soak_daylight_packaged_soak.json | standalone package | pass | not a route benchmark | 1546.1 |

The proposed route target is p95 <=33.3 ms. Passing that percentile does not mean every frame stayed below the target. Capture and interaction timings are deliberately excluded from this comparison.

## Captures

32 fixed-camera PNGs indexed with SHA256 checksums in [evidence.json](evidence.json). Four representative views appear in the [pilot README](README.md); the complete set remains in `Saved/VillageMeshV2`.

## Continuous soak

soak_daylight_packaged_soak.json: **pass**, 30.0 wall-clock minutes, 31 completed route legs. Weather cycled between daylight, overcast, rain and evening. Per-minute process memory samples are retained in the evidence index.

Mixed-weather frame p95 12.71 ms; largest frame 62.10 ms. This is not an additional comparable daylight trial.

Whole-adapter monitoring for this run peaked at 4,297 MiB and 89 C, including other applications.

Interactive launchers cap at 60 FPS; automated measurements remain uncapped. Process-memory samples do not prove absence of all leaks.

## Acceptance limits

Local facade photographs, measured ground/facade dimensions, local architectural review, dedicated Lumen diagnostic views, complete people/animal/traffic/audio work, separate CPU/GPU frame profiling, and independent fresh-machine testing remain outstanding. This is a reproducible procedural pilot, not an accepted hyperrealistic reconstruction. See the [milestone register](../V2_ACCEPTANCE.txt).

The offscreen Lumen visualization attempts produced lit images despite accepting the console settings. They are excluded from the beauty evidence and do not establish surface-cache coverage. See the [attempt record](lumen_diagnostic_attempt.json).
