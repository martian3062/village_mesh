# Manpreet MetaHuman pilot

This is the first milestone of the character proposal: one fictional adult named Manpreet, authored locally with MetaHuman Creator in UE 5.8.4. He is a separate pilot. The existing roster is Harjit, Simran, Aman, Gurleen, Navdeep, Mehar, Kiran and Jas; none has been renamed or replaced.

The pilot uses Epic's white T-shirt and shorts, with bare feet. These are the installed default garments for checking the character pipeline. They are not the planned Punjabi wardrobe. The design profile is a frozen assembly input; current review outcomes are recorded in `setup_status.json`.

## Current verified state

On 24 October 2026 the project's Creator, SDK, HairStrands, RigLogic, Chaos Cloth Asset and Chaos Outfit Asset plugins were enabled. The Launcher update installed UE 5.8.4 and MetaHuman Creator Core Data. The native `rural_pardeepEditor Win64 Development` rebuild succeeded on the updated engine.

The filesystem and Unreal asset registry both report **96 wardrobe items**. The staged driver loaded `/Game/MetaHumanPilot/Characters/MH_Manpreet`, applied the 176 cm height target and skin design, and saved six selections: pulled-back hair, full beard, full mustache, natural eyebrows, fine eyelashes and Epic's default garment. `Style` and `Wardrobe` finished with **zero errors and zero warnings**. A separate `Inspect` process reopened the saved asset and confirmed all six selections. This is an authoring milestone, not a finished villager.

The user completed Epic's browser authentication. Cloud rigging finished and its facial blendshape flag was verified, followed by a successful high-resolution texture request. Both stages saved the character. Optimized Medium assembly produced **318 assets**, and all **10 generated Blueprints** compiled. Two missing Control Rig connections were repaired and verified after a fresh reload. The rendered full-body, walking and close-up views were reviewed. The isolated standalone checks, short performance comparison and a separate **Play-in-Editor run all passed**. No MetaHuman has replaced a resident or the player, and no custom Punjabi garment has been completed.

The full Python suite passes **38 tests**, including the private Kaggle upload boundary. Python and PowerShell syntax checks pass. [The recorded setup evidence](setup_status.json) includes the saved asset digest and the remaining gates. Local detailed stage reports are in `Saved/MetaHumanPilot`; raw engine/authentication logs stay local.

## Rendered pilot and local measurement

These are captures from the actual V3 village runtime, using the temporary Epic garment.

![Manpreet on the mapped Residential Lane](character_idle.png)

![Manpreet close-up in the village](character_portrait.png)

[Walking capture](character_walk.png).

| Standalone check | Result |
| --- | --- |
| Resolution / screen percentage / frame cap | 1440 x 900 / 67% / 60 FPS |
| Measured frames, without / with Manpreet | 1,821 / 1,813 |
| Mean frame time, without / with Manpreet | 21.76 / 21.82 ms |
| 95th percentile, without / with Manpreet | 29.72 / 29.77 ms |
| Shader work during measured frames | None in either run |
| Ground contact, idle clip, walk clip | Passed |
| Swept actor travel during walking | 8.42 m |
| Blocking collision / initial penetration | None on this short lane path |

The observed p95 difference is approximately 0.04 ms. These two capped runs, with other applications open, cannot isolate the character's GPU cost or establish crowd capacity. Locomotion is exercised during warmup to load its visible materials before sampling; earlier runs with overlapping shader work were rejected. The current clips and short scripted path verify the pilot, while speed-matched locomotion blends, navigation and resident behavior integration remain future work.

PIE separately passed ground contact, idle/walk, 8.42 m of swept travel and a clean sampling interval. The editor's original game mode was restored, and the village map's on-disk hash remained unchanged. An editor-only Lumen surface-cache warning cleared when `r.LumenScene.SurfaceCache.CardTexelDensityScale` was reduced from 100 to 50 after measurement. The PIE launcher now applies this preview setting and disables automatic source-file imports for that session. The standalone comparison retains its original settings. Editor timings are not compared against standalone timings.

## Core Data setup for another machine

This installation is complete on the development machine. For a clean installation:

1. Close Unreal Editor.
2. Open **Epic Games Launcher → Unreal Engine → Library**.
3. On the **Unreal Engine 5.8** installation tile, click the small **down arrow beside Launch**.
4. Select **Options**.
5. Check **MetaHuman Creator Core Data**, then click **Apply** and wait for the download to finish.
6. Run the preflight below. Sign in to Epic inside the official UI when requested; no passwords or tokens belong in the scripts or profile.

This component contains presets, grooms, texture models and other required data. Installing the Creator plugin alone does not install it. Epic's [UE 5.8 setup guide](https://dev.epicgames.com/documentation/metahuman/getting-started-with-metahuman-creator-in-unreal-engine?application_version=5.8) also confirms that auto-rigging and texture synthesis use cloud services.

## Repeatable stages

Run from the repository root. `-EngineRoot` can override the local default `E:\U.E\UE_5.8`.

```powershell
.\Scripts\metahuman_pilot.ps1 -Action Preflight
.\Scripts\metahuman_pilot.ps1 -Action Create
.\Scripts\metahuman_pilot.ps1 -Action Inspect
```

`Create` reuses an existing pilot asset. It does not overwrite authoring work. `Inspect` records the installed wardrobe paths and saved character selections in `Saved/MetaHumanPilot/inspect.json`. The [design profile](../../Assets/MetaHumans/manpreet.json) now selects six installed Epic assets. The wardrobe stage scans the optional content registry, validates each slot selection by value, and explicitly saves the character package because nested collection edits do not always mark it dirty.

After Core Data and wardrobe selections are ready:

```powershell
.\Scripts\metahuman_pilot.ps1 -Action Style
.\Scripts\metahuman_pilot.ps1 -Action Wardrobe
.\Scripts\metahuman_pilot.ps1 -Action Edit
```

`Edit` opens Creator over a lightweight engine template map. Review the face, body and wardrobe there, and complete any required Epic sign-in. Close this project's editor before each automated build stage:

```powershell
.\Scripts\metahuman_pilot.ps1 -Action Rig
.\Scripts\metahuman_pilot.ps1 -Action Textures
.\Scripts\metahuman_pilot.ps1 -Action Assemble
```

The scripted target is an **Optimized / Medium** assembly under `/Game/MetaHumanPilot/Assembled`. The rig stage requests joints and blendshapes (`JOINTS_AND_BLEND_SHAPES` in the tested UE 5.8.4 Python API) so the stored blendshape flag can verify completion. The texture stage checks its stored high-resolution flag. Assembly retains wardrobe validation and requires a current successful wardrobe report. The runner uses a normal editor session and defers assembly until editor initialization, because Texture Graph did not initialize in Python commandlets, including with `-AllowCommandletRendering`. Shader workers are limited on this machine. A fresh actor Blueprint on disk is required before assembly can pass.

Epic's [Python scripting guide](https://dev.epicgames.com/documentation/metahuman/metahuman-creator-python-scripting-in-unreal-engine?application_version=5.8) describes the subsystem editing/commit workflow and blocking cloud requests. The installed API was checked directly where its enum spelling differed from the documentation.

The tested UE 5.8.4 assembly reported four legacy reroute diagnostics and dropped two numeric Control Rig connections. The driver recognizes only those exact diagnostics, requires the engine's current assembly-success message, and saves the generated assets explicitly. It restores the two reported source-to-target connections only when their inputs are disconnected, then recompiles and checks the graphs. Repairs apply to the generated copies under `/Game/MetaHumanPilot/Assembled/Common/Face`. Unknown errors or conflicting inputs fail the stage.

To recheck a successfully generated and saved assembly without repeating rigging, texture synthesis or mesh generation:

```powershell
.\Scripts\metahuman_pilot.ps1 -Action ValidateAssembly
```

Recovery requires the current design profile and a report confirming that engine assembly and asset saving completed. A fresh validation session confirmed that both repaired connections persisted.

## Isolated village runtime pilot

The runtime driver selects a separate native game mode through the map URL; the normal village modes and eight residents keep their existing behavior. The test uses the mapped Residential Lane viewpoint and the installed MetaHuman idle/walk clips. A swept capsule supplies pilot collision, and component-space foot motion distinguishes real skeletal animation from actor translation. The attached visual actor ignores its parent capsule to avoid self-blocking. A 2 cm floor clearance prevents initial penetration, and the mesh's +Y forward axis is aligned with the probe's +X axis.

```powershell
.\Scripts\metahuman_pilot_runtime.ps1 -Action Check
.\Scripts\metahuman_pilot_runtime.ps1 -Action Play
.\Scripts\metahuman_pilot_runtime.ps1 -Action PIE
```

Close this project between launches. `Check` runs the same view with and without Manpreet at 1440 x 900, 67% screen percentage and a 60 FPS cap, collecting 40 seconds of frame times after a 25-second warmup. Warmup restarts while shaders are compiling, with a ten-minute limit; compilation during measured frames fails the check. A close-up camera follows the measurement period. It saves separate baseline/character reports, screenshots and a comparison under `Saved/MetaHumanPilot`. This is a short local measurement with other applications open, not a crowd benchmark or release soak. `PIE` temporarily sets the editor world's game mode, restores it once the play world exists, and does not save the village map. Its report is separate from the standalone comparison.

`Play` opens an interactive standalone village with Manpreet. Use WASD and mouse look to inspect him. Locomotion is exercised during warmup, followed by idle and a short back-and-forth walk after 45 seconds. `PIE` first runs the automated checks, then returns movement and look control to you and leaves the editor open. Add `-SkipCompile` only when the current native sources have already been built. Use `M` for the village map.

The existing V2/V2.5/V3 packaging profile disables the new pilot plugins for its procedural-world builds. It does not cook the isolated MetaHuman folder. Integrating MetaHumans into a distributable village build requires a new runtime/package validation pass; the earlier V3 performance result is not evidence for a MetaHuman build.

Reports include the design profile's SHA-256 and stage scope. Errors remain errors; a base asset or an old report is not treated as a successful assembled character. The build driver does not accept or store credentials. Cloud stage failures should be resolved through Epic's UI and the matching local log.

## Wardrobe and integration milestones

The first appearance/performance pilot can use suitable Epic-supplied clothing once it is installed. That does not fulfill the custom Punjabi wardrobe milestone. Pagri, kurta-pajama, salwar kameez/chunni and jutti need separately authored meshes, fitting, skinning/cloth setup and visual review. A pagri should be fitted/skinned headwear; loose garments can use cloth where appropriate.

Epic's [wardrobe documentation](https://dev.epicgames.com/documentation/metahuman/tailoring-your-own-wardrobe-items?application_version=5.8) distinguishes fixed skeletal clothing from resizable Chaos outfits. Parametric outfits require suitable source sizes and setup; an arbitrary garment mesh does not automatically fit every body.

Before replacing residents, complete custom Punjabi clothing, review garment fit through movement, inspect LODs/hair cards, implement speed-matched navigation and animation, and measure a representative crowd and packaged build. The existing procedural resident animation consists of component transforms, not a skeletal locomotion animation set that can simply be retargeted. The pilot clips and collision probe do not replace that behavior system.

## Source and licensing

The profile and project-authored orchestration are published with the repository's source license. Epic technology and generated MetaHuman binary art are **not** relabelled MIT. All pilot `.uasset` files remain under the ignored `Content` tree. No downloaded grooms, garments, DNA or textures are added to Git by this workflow.

For UE 5.8, Epic's current [MetaHuman licensing page](https://www.metahuman.com/license) points to the [Unreal Engine EULA](https://www.unrealengine.com/eula/unreal). The proposal's older MetaHuman Creator EULA reference is not the basis for this implementation. Keeping binary art local is this repository's publication policy, not a claim that every form of MetaHuman asset distribution is universally prohibited. Any later release must follow the applicable Epic and individual asset terms.

The NPC policy's numeric state data remains separate from MetaHuman assets. The pilot workflow does not use MetaHuman characters, DNA, animation or rendered output as AI/ML training data.

Reference implementation locations in the installed engine: `MetaHumanCharacter/Content/Python/examples/` and `MetaHumanCharacter/Source/MetaHumanCharacterEditor/Public/`. No Epic source files are copied into the repository.
