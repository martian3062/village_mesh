# V2 pilot implementation

The [V2 plan](../../Village_Mesh_V2_Hyperrealism_Plan_20261023.txt) is being implemented as a separate, reproducible pilot. The user selected the mapped street near the original starting area. The pilot follows approximately **240 m**, with **16 mapped frontages**, **three representative enterable spaces**, and **eight fixed camera viewpoints**.

This is a Punjab-inspired architectural pass on sourced footprints. Local facade photographs, measurements, elevation control, and resident review have not been supplied. No private interior or distinctive landmark is represented as a surveyed reconstruction. The full M0–M6 plan remains subject to the [acceptance register](../V2_ACCEPTANCE.txt).

![Selected street, frontages, entrances and fixed cameras](pilot_map.png)

## Run the pilot

Run from the repository root, with Unreal Engine 5.8.3 installed. Close the editor before generation, HLOD building, or packaging.

```powershell
# Build C++, verify CC0 assets, generate V2, and convert its World Partition copy.
.\Scripts\v2.ps1 -EngineRoot 'E:\U.E\UE_5.8' -Action Build

# Launch the V2 map in a separate game window.
.\Scripts\v2.ps1 -EngineRoot 'E:\U.E\UE_5.8' -Action Play

# Audit dependencies and build HLOD proxies.
.\Scripts\v2.ps1 -EngineRoot 'E:\U.E\UE_5.8' -Action Audit
.\Scripts\v2.ps1 -EngineRoot 'E:\U.E\UE_5.8' -Action HLOD
```

The generated source is `/Game/VillageMeshV2/Lvl_PandoriV2`; the playable map is `/Game/VillageMeshV2/Lvl_PandoriV2_WP`. V1 remains under `/Game/VillageMesh`. `Content/VillageMeshAuthored` is reserved and is never overwritten by either generator.

Use the existing WASD/mouse/Shift/Space controls. **F10** cycles through the three room entrances; aim at a door and press **E** to open it. Other pilot doors remain closed decorative entrances. **F6** changes weather, **F7** advances local time, **F8** visits the physics yard, and **F9** toggles the overview. Door state survives actor recreation within the current world through a stable-ID store; this is not a disk save or multiplayer persistence system.

## Inputs and regeneration

| Input | Purpose |
| --- | --- |
| `Assets/Reference/manifest.json` | One reference/confidence record per selected frontage; local photographs and measurements are explicitly absent |
| `Assets/Routes/pilot_street.json` | User-approved pilot selection, stable building IDs, facade edges, and eight cameras |
| `Assets/Routes/validation_route.json` | Walking route, units, warmup, and proposed frame-time target |
| `Assets/Geodata/overrides.geojson` | Corrections keyed by stable building ID; two explicitly inferred design overrides choose single-storey representative rooms |
| `Assets/Geodata/terrain_manifest.json` | Coordinate convention and explicit inferred street/threshold heights |
| `Assets/Architecture/archetypes.json` | Original procedural kit dimensions, palettes, and component names |
| `Assets/Architecture/authored_content.json` | Exact authored package allowlist and future distribution requirements; initially empty |

Precedence is pinned source data, normalized attributes, explicit reviewed overrides, then seeded defaults for missing values. A source refresh that orphans an override raises an error. Array position no longer controls V2 facade variation or fallback height. `prepare_v2.py` preserves existing selections and reference registers.

The audit found **zero populated height/floor attributes in all 824 source features**. The selected 821 footprints therefore retain inferred heights, with separate confidence and reason fields. A future height override requires a `building_id`, `height_m`, `confidence`, and `reason`; measured values must come from actual evidence.

The current kit is recovered from tracked recipes, engine basic shapes, and pinned CC0 files, so it needs no private binary bundle. Before adding authored binary art, provide its license, bundle/checksum or LFS distribution path, and exact approved package names. The dependency audit continues rejecting unapproved legacy art.

## Appearance and environment

Pilot buildings use 25 component types and 932 detail boxes: separate thick walls, roof and ceiling surfaces, window openings/reveals, grills, coping, porches, pipes, tanks, and selected benches/furniture. Three spaces have actual doorway collision openings. Their layouts are representative rather than observed private interiors. The street verges add 128 small CC0 shrub instances, placed outside roads and building footprints.

Pilot road meshes use continuous shared cross-sections with inferred 6 cm crowns and 2.5 cm edges. The base terrain remains an arbitrary flat datum; no DEM or measured drainage model is introduced.

The existing directional light is driven by Epic's installed SunPosition library using latitude 31.4610594, longitude 75.7240654, 2026-10-23, and UTC+05:30. X remains east and Y north; no second sun is added. Weather exposes a common wind vector in m/s, a designed rainfall-rate parameter, cloudiness, wetness, and sun elevation. Wetness accumulates and dries gradually. Overhead traces suppress the player's rain effects under roofs; this is a local shelter approximation. Roof runoff, spatial puddles, rain audio, and Niagara splash/collision layers remain pending.

The Well trace and its original source pin are unchanged. This work adds no atmospheric model training or local meteorological validation.

## Repeatable checks

```powershell
python -m unittest discover -s Tests -v

# Collision-aware walk; returns nonzero on a blocked route or fall-through.
.\Scripts\v2.ps1 -EngineRoot 'E:\U.E\UE_5.8' -Action Route -RunId trial1

# Three door/entrance/shelter checks.
.\Scripts\v2.ps1 -EngineRoot 'E:\U.E\UE_5.8' -Action Interactions -Condition rain

# Physics/grounding smoke plus HLOD overview (preserves V1's saved evidence).
.\Scripts\smoke_v2.ps1 -EngineRoot 'E:\U.E\UE_5.8'

# Eight fixed views; repeat for evening, overcast, and rain.
.\Scripts\v2.ps1 -EngineRoot 'E:\U.E\UE_5.8' -Action Capture -Condition daylight -Quality capture

# Cook and stage a local Development package.
.\Scripts\v2.ps1 -EngineRoot 'E:\U.E\UE_5.8' -Action Package

# Validate the standalone executable, then run a continuous 30-minute soak.
.\Scripts\check_v2_package.ps1 -Action Route -RunId packaged_trial1
.\Scripts\check_v2_package.ps1 -Action Interactions -Condition rain
.\Scripts\check_v2_package.ps1 -Action Soak -RunId packaged_soak
```

Reports/captures are written to `Saved/VillageMeshV2`. Logs are under `Saved/Logs`. `-Headless` is available for simulation-only diagnostic runs and does not establish rendering performance. The `playable` preset uses 1440×900 output at 67% screen percentage; `capture` uses 100%. Both use Epic scalability, with dynamic resolution and VSync disabled. Automated diagnostics are uncapped; interactive `Play` and the packaged launcher cap at 60 FPS. The settings are explicit in [v2_quality.json](../../Config/v2_quality.json).

Route summaries report observed frame wall-time median/p95/p99/max after warmup and peak process physical memory. The automated rendered runs use D3D12 with `-RenderOffscreen`; they are local development measurements, not a promise of interactive FPS on other machines. They do not contain separate game/render/GPU timing or VRAM peaks. The p95 <=33.3 ms threshold is a proposed target; a successful route and a passing performance target are separate fields. Capture/interaction timing is not a traversal benchmark.

Packaging applies the explicit [runtime plugin profile](../../Config/v2_runtime_plugins.json) and selects V2 as the packaged default map, then restores both the authoring project descriptor and `DefaultEngine.ini` byte-for-byte in a `finally` block. The output is under `Saved/Packages/V2/Windows`; run `Play_V2.cmd` there for the tested graphics preset. The package includes its own README, attribution, map extracts, and source manifests. Packaging requires a closed project so its configuration cannot change under an editor session. A successful local package is still separate from a fresh-machine or shipping release acceptance.

The soak walks the same route continuously in both directions, changes between daylight/overcast/rain/evening after each leg, and requires 30 wall-clock minutes after warmup. It checks blocked movement and fall-through and samples process memory each minute. The package checker also records whole-adapter NVIDIA memory, temperature, power and utilization where available; these include other applications and are not process-specific VRAM figures. A soak pass is a bounded local stability observation, not a memory-leak proof.

## Evidence and remaining gates

- [Frozen V1 inputs](baseline_inputs.json)
- [Building attribute audit](building_attribute_audit.json)
- [Hardware and power snapshot](hardware_snapshot.json)
- [Recorded run results](RESULTS.md)
- [Final source and package fingerprint](build_manifest.json)
- [Engine checks and corrections](engine_checks.json)
- [Unaccepted Lumen diagnostic attempt](lumen_diagnostic_attempt.json)
- [Milestone acceptance register](../V2_ACCEPTANCE.txt)

The [evidence index](evidence.json) records all local diagnostic outcomes and SHA256 hashes of the 32 captures. The following are actual engine screenshots from fixed camera 4, not concept renders:

| Daylight | Evening |
| --- | --- |
| ![Daylight](daylight.png) | ![Evening](evening.png) |
| **Overcast** | **Rain** |
| ![Overcast](overcast.png) | ![Rain](rain.png) |

The [overview](overview.png) shows the wider mapped village with HLOD proxies. The 16 pilot buildings receive the detailed kit; surrounding buildings remain simpler generated shells.

Generation, World Partition conversion, 119 HLOD proxies, 32 camera captures, six rendered route trials, three standalone room checks, and the Windows Development package have passed their recorded local checks. The 2,230-package dependency audit found no unapproved legacy-art references. Local architectural review, calibrated reference comparisons, dedicated Lumen diagnostic views, people/animals/traffic/audio, and fresh-machine release testing remain open. The continuous-soak outcome is tracked separately in [RESULTS.md](RESULTS.md).

HLOD command usage follows [Epic's UE 5.8 documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/world-partition---hierarchical-level-of-detail-in-unreal-engine?application_version=5.8). Building-layer choices and measured outcomes belong in this project's evidence, not in assumptions based on the engine's capabilities.
