# UE5 Open-World Toolkit — Tools, Data, AI (Oct 2026)

**Engine:** Unreal Engine 5.8 (released 17 Jun 2026, last planned big UE5 release). Ships an official **Unreal MCP plugin** so Claude Code can drive the editor. Stay on 5.8 until UE6 early access (~late 2027).

**The Well** ([PolymathicAI](https://github.com/PolymathicAI/the_well)) = 15 TB, 16 datasets of raw PDE simulation grids (fluids, MHD, supernovae, active matter, acoustics). Not game assets. Use it for baked VFX (VDB volumes, flipbooks) or to train neural fluid surrogates run in-engine via NNE.

---

## Contents

1. [Pipeline](#1-pipeline)
2. [UE-Native Features](#2-ue-native-features)
3. [External Tools That Plug Into UE](#3-external-tools-that-plug-into-ue)
4. [Physics & Simulation](#4-physics--simulation)
5. [The Well → UE](#5-the-well--ue)
6. [More Realism Datasets](#6-more-realism-datasets)
7. [Real-Earth Data](#7-real-earth-data)
8. [Asset Libraries](#8-asset-libraries)
9. [AI Generation](#9-ai-generation)
10. [Capture](#10-capture)
11. [Start Here](#11-start-here)
12. [Citation](#12-citation)
13. [Sources](#13-sources)

---

## 1. Pipeline

```
DEM / OSM / WorldCover --QGIS--> 16-bit heightmap --> Landscape / Mesh Terrain
        |
        +--------------------> Cesium for Unreal (real globe, georeferenced)

Infinigen / Blender --(USD / Send to Unreal)--> Nanite meshes
TRELLIS.2 / Pixal3D --> .glb --> Nanite props
Megascans / Poly Haven --> materials + scanned props
PCG + PVE --> Nanite Foliage (biomes from WorldCover masks)

THE WELL --> OpenVDB --> Sparse Volume Texture   (3D volumes)
         --> PNG seq --> Niagara flipbook         (2D effects)
         --> FNO --> ONNX --> NNE                 (live ML fluid)

World Partition + HLOD + Large World Coords --> seamless open world
Claude Code --> Unreal MCP (5.8) --> agentic level building
```

---

## 2. UE-Native Features

| Feature | Status | Use |
|---|---|---|
| PCG framework + PCG Editor Mode | Production-ready (5.7+) | Rule-based roads, rocks, villages, biomes |
| Procedural Vegetation Editor (PVE) | Experimental | In-engine trees/plants → Nanite assemblies |
| Nanite Foliage | Experimental | Dense animated forests, no LOD pop; USD tree import |
| Substrate | Production-ready | Layered materials: wet rock, snow on moss, mud |
| Lumen Lite (5.8) | New | ~2× faster GI, near-same quality |
| Mesh Terrain (5.8) | Experimental | Overhangs, cliffs, caves |
| MegaLights | Production-ready (5.8) | Many dynamic lights |
| Iris | Production-ready (5.8) | Scalable multiplayer replication |
| World Partition + HLOD + Large World Coordinates | Stable | Streaming, distant LOD, double-precision coords |
| Chaos (destruction, vehicles, cloth, flesh) | Stable | Physics realism |
| Niagara Fluids + Heterogeneous Volumes / SVT | Plugin | Smoke, fire, water; OpenVDB import |
| NNE (Neural Network Engine) | Built-in | Run ONNX models in-game |
| Learning Agents | Plugin | RL / imitation-trained NPCs, drivers |
| Mass Entity, StateTree, Smart Objects | Stable | Crowds, traffic, NPC schedules |
| Water + Landmass | Plugin | Rivers, lakes, ocean, terrain carving |
| MetaHuman Creator (in-engine) | Free | Realistic humans |
| Motion Matching (Game Animation Sample) | Free sample | Realistic locomotion |
| Unreal MCP plugin | Ships in 5.8 | Claude Code drives editor, builds levels, spawns PCG |

**Free samples to study:** City Sample (updated with PCG + Unreal MCP), Electric Dreams (PCG), Game Animation Sample, Paragon assets — all on [Fab](https://www.fab.com).

---

## 3. External Tools That Plug Into UE

| Tool | Route into UE |
|---|---|
| [Cesium for Unreal](https://cesium.com/platform/cesium-for-unreal/) | Real-Earth terrain, 3D Tiles, georeferencing |
| [QGIS](https://qgis.org) + [GDAL](https://gdal.org) | DEM → 16-bit heightmap; WorldCover → PCG masks |
| [BlenderGIS](https://github.com/domlysz/BlenderGIS) | GIS data → meshes in Blender |
| [OSM2World](https://osm2world.org) | OSM → 3D city meshes |
| [Blender](https://www.blender.org) + [Send to Unreal](https://github.com/EpicGamesExt/BlenderTools) | One-click export to UE |
| [Infinigen](https://github.com/princeton-vl/infinigen) | Procedural terrain/plants/creatures → USD/FBX → Nanite |
| [Gaea](https://quadspinner.com) | Erosion-realistic terrain heightmaps |
| [Houdini Engine](https://www.sidefx.com) | Procedural HDAs inside UE |
| [Material Maker](https://github.com/RodZill4/material-maker) | Procedural PBR textures → Substrate |
| [ArmorPaint](https://armorpaint.org) | Texture painting |
| [Krita](https://krita.org) | Painting, decals, UI |
| [WaveFunctionCollapse](https://github.com/mxgmn/WaveFunctionCollapse) | Town/dungeon layouts → PCG input |
| [MakeHuman / MPFB2](https://www.makehumancommunity.org) | Background humans |
| [Llama-Unreal](https://github.com/getnamo/Llama-Unreal) | Local LLM NPC dialogue (llama.cpp) |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | Player speech → text |
| [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) | NPC text-to-speech |
| [Perforce](https://www.perforce.com) / [Git LFS](https://git-lfs.com) | Version control for large binaries |
| [Epic Online Services](https://dev.epicgames.com/en-US/services) / [Nakama](https://heroiclabs.com) | Lobbies, matchmaking, accounts |

---

## 4. Physics & Simulation

| Tool | Use |
|---|---|
| [Genesis](https://github.com/Genesis-Embodied-AI/genesis-world) | Unified rigid / MPM / SPH / FEM / PBD, differentiable; offline realism bakes |
| [MuJoCo](https://github.com/google-deepmind/mujoco) | Physics-based creature/character locomotion |
| [NVIDIA Warp](https://github.com/NVIDIA/warp) | GPU sims in Python (snow, sand, fluids) → bake to VDB |
| [Taichi](https://github.com/taichi-dev/taichi) | GPU MPM/fluid sims → bake |
| [PhysX 5](https://github.com/NVIDIA-Omniverse/PhysX) | Reference / standalone physics tools |

---

## 5. The Well → UE

```bash
pip install the_well
the-well-download --base-path ./well --dataset supernova_explosion_64 --split train
```

Docs: [polymathic-ai.org/the_well](https://polymathic-ai.org/the_well/) · Data also streams from Hugging Face.

| Well dataset | UE path | Result |
|---|---|---|
| `supernova_explosion`, `MHD`, `post_neutron_star_merger`, `convective_envelope_rsg` (3D) | h5py → OpenVDB → import as SVT → Heterogeneous Volume | Nebulae, star surfaces, blast waves |
| `turbulent_radiative_layer_3D`, `rayleigh_taylor_instability` | VDB → SVT | Volumetric smoke, mixing plumes |
| `rayleigh_benard`, `shear_flow`, `turbulent_radiative_layer_2D` | PNG sequence → SubUV flipbook (Niagara / material) | Lava convection, clouds, smoke cards |
| `gray_scott_reaction_diffusion` | PNG frames → textures | Organic patterns: coral, skin, lichen |
| `euler_multi_quadrants` | Flipbook | Explosion / shock fronts |
| `planetswe` | Equirectangular flipbook on sky sphere / planet | Planet-scale weather flow |
| `acoustic_scattering` | Train small model → ONNX → NNE | ML sound occlusion |
| `active_matter` | Reference for Mass Entity behaviours | Swarm / flocking |
| FNO checkpoints (HF) | `FNO.from_pretrained` → `torch.onnx.export` → NNE | Live low-res fluid driving Niagara |

---

## 6. More Realism Datasets

| Dataset | What |
|---|---|
| [PDEBench](https://github.com/pdebench/PDEBench) | Fluid / PDE benchmark data |
| [APEBench](https://github.com/tum-pbs/apebench) | Autoregressive PDE sims |
| [JHU Turbulence DB](https://turbulence.pha.jhu.edu) | Real DNS turbulence |
| [Multimodal Universe](https://github.com/MultimodalUniverse/MultimodalUniverse) | Astronomy data (Polymathic) |
| [ERA5](https://cds.climate.copernicus.eu) | Real global hourly weather |
| [WeatherBench 2](https://github.com/google-research/weatherbench2) | ML weather data + baselines |

---

## 7. Real-Earth Data

| Data | Use |
|---|---|
| [Copernicus DEM GLO-30](https://dataspace.copernicus.eu) | 30 m global elevation → Landscape |
| [ISRO Bhuvan / CartoDEM](https://bhuvan.nrsc.gov.in) | Indian terrain + imagery |
| [OpenTopography](https://opentopography.org) | Lidar / high-res DEMs |
| [OpenStreetMap (Geofabrik)](https://download.geofabrik.de) | Roads, buildings, rivers |
| [Overture Maps](https://overturemaps.org) | Clean buildings / places layers |
| [MS Building Footprints](https://github.com/microsoft/GlobalMLBuildingFootprints) | Global building outlines |
| [ESA WorldCover](https://esa-worldcover.org) | 10 m land cover → PCG biome masks |
| [Sentinel-2](https://dataspace.copernicus.eu) | Satellite colour → terrain albedo |
| [NASA Visible Earth](https://visibleearth.nasa.gov) / [Natural Earth](https://www.naturalearthdata.com) | Planet textures, vector borders |

---

## 8. Asset Libraries

| Source | Content |
|---|---|
| [Fab (Megascans + free monthly)](https://www.fab.com) | Scanned surfaces, props, UE packs |
| [Poly Haven](https://polyhaven.com) | HDRIs, scanned textures, models |
| [ambientCG](https://ambientcg.com) | PBR materials |
| [Quaternius](https://quaternius.com) | Animated characters, nature |
| [Kenney](https://kenney.nl) | Low-poly kits |
| [Smithsonian 3D](https://3d.si.edu) | Real scanned artifacts |
| [OpenGameArt](https://opengameart.org) | Everything |
| [Objaverse-XL](https://objaverse.allenai.org) | 10M+ 3D models |
| [Freesound](https://freesound.org) / [Sonniss GDC bundle](https://sonniss.com/gameaudiogdc) | Sound effects |
| [CMU MoCap](https://mocap.cs.cmu.edu) / [Mixamo](https://www.mixamo.com) | Animation (retarget via IK Retargeter) |

---

## 9. AI Generation

| Model | Output → UE |
|---|---|
| [TRELLIS.2](https://github.com/microsoft/TRELLIS.2) | Best downloadable image-to-3D; .glb → Nanite |
| [Pixal3D](https://huggingface.co/models?search=Pixal3D) | Pixel-aligned image-to-3D + PBR (May 2026) |
| [Hunyuan3D 2.1](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1) | Textured meshes from image/text |
| [Roblox Cube](https://github.com/Roblox/cube) | Text-to-3D objects |
| [HY-World 2.0](https://github.com/Tencent-Hunyuan/HY-World-2.0) | Text/image → 3DGS + mesh + point cloud; use mesh, or a UE Gaussian-splat plugin |
| [Matrix-Game 4.0](https://github.com/SkyworkAI/Matrix-Game) | Engine owns logic/physics, model neurally re-renders low-poly frames (Oct 2026) |
| [LingBot-World](https://github.com/robbyant/lingbot-world) | Real-time interactive world model, 16 fps |
| [NVIDIA Cosmos 3](https://huggingface.co/nvidia/Cosmos3-Super) | Physics-grounded world generation, synthetic data |
| [FLUX.1 schnell](https://huggingface.co/black-forest-labs/FLUX.1-schnell) | Concept art, texture bases |
| [Awesome Interactive World Model](https://github.com/EasonTuT/Awesome-Interactive-World-Model) | Tracker for new world-model releases |

---

## 10. Capture

| Tool | Use |
|---|---|
| [COLMAP](https://colmap.github.io) | Photogrammetry / camera solve |
| [Meshroom](https://alicevision.org) | Photos → mesh |
| [RealityScan](https://www.realityscan.com) | Phone scans → UE-ready meshes |
| [gsplat](https://github.com/nerfstudio-project/gsplat) / [Nerfstudio](https://nerf.studio) | Gaussian splats from video |
| [FreeMoCap](https://freemocap.org) | Webcam motion capture → FBX |

---

## 11. Start Here

1. Install UE 5.8; enable PCG, PVE, Nanite Foliage, Cesium, NNE, MCP plugin.
2. Clip a Copernicus DEM tile in QGIS → 16-bit heightmap → Landscape import with World Partition on.
3. WorldCover → masks → PCG biome graph + PVE foliage.
4. Props from Megascans / Poly Haven / Quaternius; fill gaps with TRELLIS.2.
5. One Well supernova field → VDB → SVT volume test.
6. Hook Claude Code to the Unreal MCP plugin for agentic level building.

---

## 12. Citation

```bibtex
@article{ohana2024well,
  title   = {The Well: a large-scale collection of diverse physics simulations for machine learning},
  author  = {Ohana, Ruben and McCabe, Michael and Meyer, Lucas and Morel, Rudy and others},
  journal = {Advances in Neural Information Processing Systems},
  volume  = {37},
  pages   = {44989--45037},
  year    = {2024}
}
```

---

## 13. Sources

- [The Well — GitHub](https://github.com/PolymathicAI/the_well)
- [Unreal Engine 5.7 is now available](https://www.unrealengine.com/news/unreal-engine-5-7-is-now-available)
- [UE 5.8 + UE6 announcement (godisageek)](https://godisageek.com/2026/06/epic-ue6-uefn-payouts/)
- [UE 5.8 features (wnhub)](https://wnhub.io/news/engines/item-51157)
- [State of Unreal 2026 takeaways (Edge)](https://knowledge.edge-online.com/p/ai-goes-native-in-unreal-engine-the-five-main-takeaways-from-state-of-unreal-2026)
- [UE 5.7 Preview: PCG + Nanite Foliage (Digital Production)](https://digitalproduction.com/2025/10/17/unreal-5-7-preview-pcg-grows-up-foliage-gets-fancy/)
- [AI 3D model generation timeline 2026 (Cinevva)](https://app.cinevva.com/guides/ai-3d-model-generation-timeline-2026)
- [HY-World 2.0 — GitHub](https://github.com/Tencent-Hunyuan/HY-World-2.0)
- [Matrix-Game 4.0 open source (ToolNavs)](https://toolnavs.com/article/2588-matrix-game-40-goes-open-source-the-engine-owns-the-logic-the-model-only-paints)
- [LingBot-World paper (arXiv 2601.20540)](https://arxiv.org/pdf/2601.20540)
- [NVIDIA Cosmos 3 launch (DataNorth)](https://datanorth.ai/news/nvidia-launches-cosmos-3)
- [Infinigen (CG Channel)](https://www.cgchannel.com/2023/07/infinigen-a-free-generator-for-procedural-3d-environments)
- [Genesis World — GitHub](https://github.com/Genesis-Embodied-AI/genesis-world)
