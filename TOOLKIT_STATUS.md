# Toolkit application and remaining work

The supplied [ue5-open-world-toolkit.md](ue5-open-world-toolkit.md) is the
reference catalogue. Its version, maturity, price and licensing claims are
not treated as verified facts. Installed UE 5.8.3 plugin descriptors and
official documentation take precedence for this build.

## Working in the generated world

| Toolkit component | Concrete use |
| --- | --- |
| OSM / Overture | Pandori Nijjaran road centerlines and 821 building outlines inside a 1.28 km play area; source extracts and hashes are checked in |
| Poly Haven | Checksummed 2K soil/brick/plaster and tree textures, tree geometry, 1K shrub geometry/textures; CC0 |
| PCG | Two seeded point-source/spawner layers generate instanced vegetation; road and building exclusion rules use GIS geometry |
| Nanite | Imported vegetation uses Nanite with area preservation; terrain collision keeps its full fallback geometry |
| Lumen / Substrate / virtual shadows | Existing UE rendering pipeline, weather-driven surface shading, dynamic sky and fog |
| Chaos | Interactive rigid bodies, CCD, substepping, grab/throw and a bounded plane-buoyancy demonstration |
| The Well | Pinned source submodule; a real shear-flow velocity trace drives foliage/prop wind; no neural solver is claimed |
| World Partition | Converter produces `Lvl_PandoriNijjaran_WP`, preserving the source map; HLOD baking and long-distance streaming profiling remain unverified |
| Reproducible generation | Python source creates the assets and map, source licenses remain separated, no unverified imported art is published |

## Native authoring tools

`Scripts/configure_toolkit.py --engine-root <UE-root> --profile authoring --apply`
enables installed PCG, PVE, Mesh Terrain, USD import, Water, Landmass,
Niagara Fluids, NNE ORT, Learning Agents, MassAI, StateTree, SmartObjects,
PoseSearch and the MCP/editor/PCG toolsets. This checkout has the authoring profile enabled. The smaller `core` profile contains
PCG and editor MCP toolsets. Neither profile downloads plugins.

Enabling a plugin makes its authoring tools available; it does not create
a water body, trained agent, ONNX model, animation database, or smoke simulation.
Automatic Python dependency installation is disabled; optional training tools
need their own dependencies before use. MCP's server is not automatically started by this setup. Its local engine
settings default to manual start. No external AI account configuration is stored.

PVE, Mesh Terrain, Water, Learning Agents, MassAI and the MCP toolsets are
marked experimental in this installed engine. Nanite area preservation is
used for the imported foliage; PVE-generated voxel foliage is a separate task.

## External tools and datasets from the catalogue

| Catalogue group | Status and concrete requirement |
| --- | --- |
| Cesium / QGIS / GDAL / BlenderGIS / OSM2World | Real coordinates are already converted locally; Cesium is not installed, QGIS/GDAL are not on PATH. No globe or satellite imagery is embedded |
| Copernicus DEM / Bhuvan / CartoDEM / OpenTopography | No elevation raster has been acquired. The level explicitly uses a flat datum; it is not surveyed terrain |
| ESA WorldCover / Sentinel / NASA / Natural Earth | No land-cover classification yet; vegetation positions are designed, constrained by mapped roads/buildings |
| Blender / Send to Unreal / USD / Infinigen | USD import can be enabled with the authoring profile; Blender is not on PATH. No Blender/Infinigen scene was generated |
| Gaea / Houdini / Material Maker / ArmorPaint / Krita / WFC | Alternative authoring pipelines, not dependencies of this source build; no licensed software or projects installed |
| Genesis / MuJoCo / Warp / Taichi / PhysX | Offline simulation alternatives; not substituted for UE Chaos. No cross-solver validation performed |
| The Well 3D VDB / SVT / 2D Niagara flipbooks | Wind playback is implemented. Volume conversion, SVT import, flipbooks and neural surrogates remain separate integrations; no multi-terabyte download |
| PDEBench / APEBench / JHU / Multimodal Universe / ERA5 / WeatherBench | Research datasets, not game content. No model training or weather assimilation performed |
| Fab / Megascans / ambientCG / Quaternius / Kenney / Smithsonian / OpenGameArt / Objaverse | Poly Haven is the chosen verified asset source for this pass. Other assets must retain their individual licenses and provenance |
| Freesound / Sonniss / CMU / Mixamo | No audio or animation pack acquired; first-person exploration has no proprietary character dependency |
| TRELLIS / Pixal / Hunyuan / Roblox Cube / HY-World / Matrix Game / LingBot / Cosmos / FLUX | No model weights, hosted inference, generated props or world-model rollout. These alternatives are not interchangeable production engines |
| COLMAP / Meshroom / RealityScan / gsplat / Nerfstudio / FreeMoCap | Need suitable site captures; no scan of this village exists in the project |
| MetaHuman / MPFB / MakeHuman / Motion Matching | No new human rig or animation database; original character source is retained separately |
| Llama-Unreal / whisper.cpp / Kokoro | No local dialogue, speech recognition or speech synthesis service connected |
| Iris / EOS / Nakama / Perforce | No multiplayer backend or replication validation. Git source publication is used; generated binary content is rebuilt locally |
| MegaLights / hardware ray tracing | Not required by the laptop profile; no performance claims for these paths |

The next fidelity bottleneck is site evidence: street-facing photos, measured
heights, elevation and landmark dimensions. The public village-tour title and
transcript confirm a school, entrance gate and a Nishan Sahib, but do not supply
reliable coordinates or facade measurements. None is positioned as a verified
landmark based on that transcript alone.

Sources: [Epic World Partition](https://dev.epicgames.com/documentation/en-us/unreal-engine/world-partition-in-unreal-engine),
[Overture retrieval](https://docs.overturemaps.org/getting-data/),
[Overture attribution](https://docs.overturemaps.org/attribution/#buildings),
[Poly Haven license](https://polyhaven.com/license),
[Pandori Nijjran post office](https://jalandhar.nic.in/public-utility/pandori-nijjran-b-o/),
[public village tour](https://www.youtube.com/watch?v=tFzYOovj_EI).
