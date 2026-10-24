# Pardeep player and village streets

This local iteration adds a third-person protagonist slot and a separate village map, `/Game/VillageMeshV3/Lvl_PandoriV3_Pardeep_WP`. It retains the mapped road routes, 821 building outlines, eight regional house styles, nine public-site interpretations and 41 authored fields from V3.

**Likeness review is still required.** After the temporary preview, the owner selected four local front/side/chin-up portraits. Pardeep now has a separate character asset and a manual, reference-guided facial design covering cheeks, nose, eyelids, lips and chin. This is an artistic approximation, not a photogrammetric scan or a verified exact likeness. The current T-shirt/shorts remain a temporary outfit; custom Punjabi clothing is unfinished.

The original black turban mesh has layered folds and an arched forehead edge. It follows the animated head bone, covers the scalp hair and retains the beard, moustache and eyebrows. The original Manpreet pilot is preserved. Source portraits, embeddings, messages and credentials are excluded from publication. The photo files remain local; Epic's rigging service processes the generated character data during the build.

Supporting characters can use separately selected references. The existing eight residents retain their identities; photographs in a mixed archive are not assigned to named characters automatically.

## Verified local preview — 24 October 2026

The UE 5.8.4 editor build passed. All 44 Python tests passed. The latest standalone third-person check loaded the separate Pardeep actor and recorded 26.71 m of player travel, 27.41 m of accumulated component-space foot motion, walking and running speeds, continuous grounded movement, and the turban attached to the animated head. Camera collision is enabled; that flag is not an exhaustive wall-obstruction test. The walking, idle, front portrait and hand-detail captures were reviewed. No new packaged build or sustained performance result is claimed.

A separate commandlet reloaded all 338 saved Pardeep assets and the runtime Blueprint successfully. The new character has brown eyes, retained facial hair and original black folded headwear. The portrait is a likeness preview for owner review, not a claim of identity accuracy.

The skin update uses an **Optimized High** assembly: 19,283 vertices in the most detailed exported face mesh and 25,328 in the body. The saved body has 4K colour and 8K normal/surface maps; the face has 2K colour and 4K normal/surface maps. The shader retains colour variation and subsurface scattering, with adjusted highlight roughness and fine normal detail. These are generated MetaHuman materials, not a scan of the owner's hands or body.

The default play/check commands now render at 100% screen percentage with full-resolution skin scattering. Use `-ScreenPercentage 67` with the play command if a lower rendering cost is needed. The saved texture and mesh inventory is in [skin_asset_audit.json](skin_asset_audit.json); actual close-up LOD and rendering settings are in [skin_runtime_quality.json](skin_runtime_quality.json).

The High assembly saved its packages but the editor exited with an access violation during shutdown (`-1073741819`); [character_build.json](character_build.json) records `assembly_editor_clean_exit: false`. The independent reload succeeded. One early High runtime launch encountered a GPU device-hung/page-fault error in virtual-shadow-map rendering. A retry and the final material/camera refinement check succeeded. The failure is not considered resolved by a short successful run; sustained stability remains unverified.

The initial runtime check caught a reference-pose failure despite actor movement. The generator now explicitly validates and resamples the blend space's runtime data before saving it; a fresh engine run passed after the correction.

The earlier street/temporary-player preview passed manual checks of the V first/third-person toggle, Q shoulder swap, and M full-map open/close controls. The updated appearance preview was launched after its automated checks. Manual testing of the new P inspection key was interrupted when computer control was stopped; the automated run exercised both inspection cameras.

![Third-person player walking on the brick lane](third_person_walk.png)

![Reference-guided Pardeep portrait with the original black turban](pardeep_portrait.png)

[Hand detail](hand_detail.png) · [Idle view](third_person_idle.png) · [Runtime result](runtime_check.json) · [World build result](build_report.json).

## Play

```powershell
.\Scripts\pardeep_village.ps1 -Action Play
```

| Control | Action |
| --- | --- |
| WASD / mouse | Camera-relative movement / orbit |
| Shift | Run |
| Space | Jump |
| V | Third-person / first-person view |
| Q | Change camera shoulder |
| P | Cycle face close-up, sun-facing hand close-up and third-person view |
| M | Village map |
| Tab / Enter | Select / visit map destination |
| T | Talk |
| E / right mouse | Door or physics grab / throw |
| F6 / F7 | Weather / time |

This preview launcher uses `-V25NoSave`, so it does not write the normal village-life save.

The spring arm retracts against camera collision. Movement turns the visible character independently of camera yaw. A three-sample locomotion blend space follows actual horizontal speed. Jump physics work; a dedicated airborne animation is not included. The HUD adds heading, speed and the material under the player's feet while retaining the village map and destination distances.

## Street design

The 71 mapped routes receive 9 asphalt connector roads, 35 tile-paved lanes, 17 brick lanes and 10 dirt tracks. Existing OSM surface tags take precedence when supplied; remaining surface assignments follow the requested artistic design. These are not surveyed pavement conditions. The road widths also remain inferred.

Paving has metre-scaled joints, small bevel normals and rain-driven color/roughness. The geometry provides a shallow crown, shared cross sections at bends and earthen shoulders. Clear road edges receive solar-panel streetlamp models. The lamp models do not simulate an electrical or sensor network. Existing Punjabi-style verandas, courtyards, balconies, roof terraces, jali details and shop homes remain regional interpretations rather than verified facades.

## Rebuild and verify

Save and close this project's editor before rebuilding:

```powershell
python -m unittest discover -s Tests -v
.\Scripts\pardeep_village.ps1 -Action Build
.\Scripts\pardeep_village.ps1 -Action Check
```

The build creates a copy of the V3 source map, removes inherited uniform road actors from that copy, imports the replacement surfaces and converts it to World Partition. The player blend space references the installed MetaHuman idle/walk/run clips; those raw Epic clips are not redistributed in the repository. UE 5.8.4 with the installed MetaHuman content is the development target. The original approved temporary appearance remains available as a fallback.

## Rebuild the reference-guided appearance

The separate actor is `/Game/MetaHumanPilot/Pardeep/Assembled/BP_Pardeep`. Its source character is `/Game/MetaHumanPilot/Pardeep/Characters/MH_Pardeep`. The original temporary visual remains a fallback if the new actor is unavailable.

```powershell
# Compile the project module before using its editor asset helpers.
& 'E:\U.E\UE_5.8\Engine\Build\BatchFiles\Build.bat' rural_pardeepEditor Win64 Development "-Project=$PWD\rural_pardeep.uproject" -WaitMutex -NoHotReloadFromIDE
# Initialize a separate character from the preserved pilot and build the turban.
.\Scripts\pardeep_appearance.ps1 -Action Prepare
# Apply the saved artistic face design, rig and assemble. Requires Epic sign-in.
.\Scripts\pardeep_appearance.ps1 -Action Character
# Rebuild just the original cloth mesh/material after headwear edits.
.\Scripts\pardeep_appearance.ps1 -Action Turban
# Update cloth, eyes, hair and skin materials without repeating facial rigging.
.\Scripts\pardeep_appearance.ps1 -Action Refine
# Reload every saved Pardeep asset in a fresh editor process.
.\Scripts\pardeep_appearance.ps1 -Action Verify
.\Scripts\pardeep_village.ps1 -Action Check
```

The face design is recorded in `Assets/MetaHumans/pardeep_face_design.json`. A saved design hash prevents cumulative application of the same sculpt. A different design requires an intentionally reviewed baseline, rather than applying another set of deltas silently. `Saved/PardeepPlayer` holds local reference metadata, build evidence and the runtime portrait. Photographs are not required by the published build scripts.

Character assembly runs in a normal editor because Texture Graph is unavailable in the commandlet path. The generated character packages are saved directly without rendering editor thumbnails, avoiding the allocation spike that exhausted memory on this development laptop. The save helper is restricted to `MetaHumanPilot/Pardeep`; it does not resave other project assets. A failed assembly remains failed in the report even if its source sculpt and rig have been saved successfully.

Local build evidence is written to `Saved/VillageStreets/build_report.json`. The standalone runtime check writes `Saved/PardeepPlayer/runtime_check.json` and walking/idle captures. Runtime results, likeness approval, packaging and a sustained performance test are separate gates; generated source assets alone do not establish those outcomes. The existing V3 packaging script excludes the MetaHuman pilot and should not be used to claim a packaged Pardeep build.
