# Validation ? 2026-10-23

Local workstation: Windows, Unreal Engine 5.8.3, MSVC 14.44, RTX 4050 Laptop GPU.

| Check | Result |
| --- | --- |
| C++ editor build | Passed after final controller and camera changes |
| Asset dependency audit | 1,026 packages checked across source and World Partition maps; no legacy art dependencies |
| Python compilation | Passed for project scripts and startup script |
| Unit tests | 7 passed: georeference/scale, all 821 roof triangulation areas, road vegetation exclusion, source hashes, terrain and Well data validation |
| The Well export | 49 bounded samples from the pinned public shear-flow HDF5 file; checksum verified |
| CC0 downloads | 15 PBR texture maps plus 17 vegetation files, source MD5 and pinned SHA256 verified |
| Pandori generation | 821 mapped building shells, 265 mesh chunks, 146 PCG instances configured, 13 physics props; 306 base actors |
| Detail pass | 399 procedural roof-tank / shade actors added, exit 0 |
| World Partition conversion | Passed, exit 0, source map preserved; runtime streaming generation initialized |
| GPU runtime smoke | Player grounded at 90.15 cm; 13 finite simulating bodies, designated buoyancy check passed; 146 instanced vegetation items |
| Native Well playback | Engine confirmed 49 validated samples |

The live smoke test checks actual engine simulation after 35 seconds and
captures at 40 seconds. It verifies ground contact, body simulation, finite
positions, designated pond flotation, and generated instanced vegetation.
It does not prove every control, long-duration stability, or scientific
accuracy of the wind and plane-buoyancy approximations.

The map outline projection and roof triangulation preserve the downloaded
geographic footprints. This is not a validation of their real-world accuracy:
ML footprints can be wrong, OSM is incomplete, heights and facades are
procedural, and terrain uses a flat datum.

Run checks:

```powershell
python -m unittest discover -s Tests -v
.\Scripts\play.ps1 -EngineRoot 'E:\U.E\UE_5.8' -Smoke -Headless
.\Scripts\play.ps1 -EngineRoot 'E:\U.E\UE_5.8' -Smoke -Overview
```

Uncooked game runs still log editor-widget and unbaked HLOD-settings warnings.
The final material pass removes Nanite/instancing fallback warnings. Cached
lighting pre-exposure is set to EV8, whose documented usable range extends
through EV16, to avoid the daylight clipping warning.

The game launcher disables Python because the experimental MCP editor tools'
startup scripts expect editor-only classes. Authoring commandlets and the full
editor keep Python enabled. Automatic installation of optional training
packages is disabled in project settings.

Evidence: `Saved/VillageMeshGenerated/` and `Saved/Logs/VillageMesh*.log`.
Published previews are actual engine captures; the reference map is plotted
from the checked-in geographic data.

Not verified: shipping package, multiplayer, HLOD baking, sustained frame
rate, streaming traversal throughout the world, independent fresh-machine
bootstrap, or scientific validation against a fluid solver.
