# Manpreet MetaHuman pilot

This is the first milestone of the character proposal: one fictional adult named Manpreet, generated locally with MetaHuman Creator in UE 5.8.3. He is a separate pilot. The existing roster is Harjit, Simran, Aman, Gurleen, Navdeep, Mehar, Kiran and Jas; none has been renamed or replaced.

## Current verified state

On 24 October 2026 the project's Creator, SDK, HairStrands, RigLogic, Chaos Cloth Asset and Chaos Outfit Asset plugins were enabled. A real Unreal commandlet loaded the Creator subsystem, confirmed its Python APIs, and created/saved `/Game/MetaHumanPilot/Characters/MH_Manpreet`. This is a base character asset, not a finished villager.

The same run reported: `MetaHuman Optional Content folder not found. MetaHuman Creator plugin initialized with limited features.` The optional content folder is absent and the wardrobe inventory is zero. Rigging, skin synthesis, a clothed rendered preview, PIE, animation integration and performance comparison have **not** passed. No MetaHuman has replaced a resident or the player, and no custom Punjabi garment has been completed.

The full Python suite passes **36 tests** (the previous 33 plus three pilot isolation/output-boundary checks). Python and PowerShell syntax checks pass. [The recorded setup evidence](setup_status.json) includes the base asset digest and unvalidated stages. The asset was created by an Unreal API probe; the staged build driver has not yet been run through the appearance/cloud stages.

## Install the missing Core Data

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

`Create` reuses an existing pilot asset. It does not overwrite authoring work. `Inspect` records the actual installed wardrobe paths in `Saved/MetaHumanPilot/inspect.json`. Choose the hair, beard and outfit paths in [the design profile](../../Assets/MetaHumans/manpreet.json) from that inventory. Null slots are intentionally unresolved; the wardrobe stage refuses to claim completion with missing selections.

After Core Data and wardrobe selections are ready:

```powershell
.\Scripts\metahuman_pilot.ps1 -Action Style
.\Scripts\metahuman_pilot.ps1 -Action Wardrobe
.\Scripts\metahuman_pilot.ps1 -Action Edit
```

Review the face, body and wardrobe in Creator, and complete any required Epic sign-in. Close this project's editor before each automated build stage:

```powershell
.\Scripts\metahuman_pilot.ps1 -Action Rig
.\Scripts\metahuman_pilot.ps1 -Action Textures
.\Scripts\metahuman_pilot.ps1 -Action Assemble
```

The scripted target is an **Optimized / Medium** assembly under `/Game/MetaHumanPilot/Assembled`. The rig stage requests joints and blendshapes so the Python API's stored blendshape flag can verify completion. The texture stage checks its stored high-resolution flag. Assembly retains wardrobe validation and requires a current successful wardrobe report. These downstream stages are prepared against the installed Epic examples and headers but remain unvalidated until the missing content and authentication gates are resolved.

The existing V2/V2.5/V3 packaging profile disables the new pilot plugins for its procedural-world builds. It does not cook the isolated MetaHuman folder. Integrating MetaHumans into a distributable village build requires a new runtime/package validation pass; the earlier V3 performance result is not evidence for a MetaHuman build.

Reports include the design profile's SHA-256 and stage scope. Errors remain errors; a base asset or an old report is not treated as a successful assembled character. The build driver does not accept or store credentials. Cloud stage failures should be resolved through Epic's UI and the matching local log.

## Wardrobe and integration milestones

The first appearance/performance pilot can use suitable Epic-supplied clothing once it is installed. That does not fulfill the custom Punjabi wardrobe milestone. Pagri, kurta-pajama, salwar kameez/chunni and jutti need separately authored meshes, fitting, skinning/cloth setup and visual review. A pagri should be fitted/skinned headwear; loose garments can use cloth where appropriate.

Epic's [wardrobe documentation](https://dev.epicgames.com/documentation/metahuman/tailoring-your-own-wardrobe-items?application_version=5.8) distinguishes fixed skeletal clothing from resizable Chaos outfits. Parametric outfits require suitable source sizes and setup; an arbitrary garment mesh does not automatically fit every body.

After a clothed pilot is assembled, the remaining gates are: place him in a separate V3 pilot scene; verify idle/walk animation and collision in PIE; measure comparable character-off/character-on frame timings; review LODs/hair cards; then opt in the resident visual replacement. The existing procedural resident animation consists of component transforms, not a skeletal locomotion animation set that can simply be retargeted. Those runtime changes are deliberately pending actual character assets and measurements.

## Source and licensing

The profile and project-authored orchestration are published with the repository's source license. Epic technology and generated MetaHuman binary art are **not** relabelled MIT. All pilot `.uasset` files remain under the ignored `Content` tree. No downloaded grooms, garments, DNA or textures are added to Git by this workflow.

For UE 5.8, Epic's current [MetaHuman licensing page](https://www.metahuman.com/license) points to the [Unreal Engine EULA](https://www.unrealengine.com/eula/unreal). The proposal's older MetaHuman Creator EULA reference is not the basis for this implementation. Keeping binary art local is this repository's publication policy, not a claim that every form of MetaHuman asset distribution is universally prohibited. Any later release must follow the applicable Epic and individual asset terms.

The NPC policy's numeric state data remains separate from MetaHuman assets. The pilot workflow does not use MetaHuman characters, DNA, animation or rendered output as AI/ML training data.

Reference implementation locations in the installed engine: `MetaHumanCharacter/Content/Python/examples/` and `MetaHumanCharacter/Source/MetaHumanCharacterEditor/Public/`. No Epic source files are copied into the repository.
