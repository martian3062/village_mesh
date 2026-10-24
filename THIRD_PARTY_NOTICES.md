# Third-party notices

## Unreal Engine

This project requires Unreal Engine 5.8. Engine binaries and BasicShapes are
loaded from the user's licensed installation; they are not distributed here.
The engine is subject to [Epic's Unreal Engine license](https://www.unrealengine.com/en-US/eula/unreal).
The project source is open source; Unreal itself is not MIT-licensed.

## The Well

[PolymathicAI/the_well](https://github.com/PolymathicAI/the_well) is included as
a Git submodule pinned to `aac88c0b5eb9cbe4b7b2797eaaa550a43706fb44`.
Its source is BSD-3-Clause; see `ThirdParty/the_well/LICENSE`.

`Content/Well/wind.csv` is adapted from the shear-flow dataset by Rudy Morel,
CCM, Flatiron Institute, distributed by The Well / Polymathic AI under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Source: [shear_flow on Hugging Face](https://huggingface.co/datasets/polymathic-ai/shear_flow).
The exact revision, file, spatial point, trajectory and checksum are recorded
in `Content/Well/wind.source.json`.

Changes: one spatial velocity trace was extracted, normalized by its peak
speed, mapped to horizontal XY wind, retimed to 120 seconds, and given a
matching endpoint for looping. No endorsement by the authors is implied.
This is visual playback of simulation data, not a real-time fluid solver,
atmospheric forecast, or scientific validation of village weather.

Research citation: Ohana et al. (2024), *The Well: a Large-Scale Collection
of Diverse Physics Simulations for Machine Learning*, NeurIPS 37,
44989–45037. For the shear-flow solver: Burns et al. (2020), *Dedalus:
A Flexible Framework for Numerical Simulations with Spectral Methods*,
Physical Review Research 2, 023068.

## Poly Haven textures

The downloader retrieves these [CC0 assets](https://polyhaven.com/license):

- [Brown Mud Leaves 01](https://polyhaven.com/a/brown_mud_leaves_01)
- [Red Brick 03](https://polyhaven.com/a/red_brick_03)
- [Rough Plaster 03](https://polyhaven.com/a/rough_plaster_03)

`Assets/textures.lock.json` records source URLs, channel, resolution URLs,
MD5 and SHA256. The exact pinned source downloads are now included through Git LFS; see `Docs/LFS/assets.json`.

## Existing local content

The pre-existing `Content/Village`, mannequins, imported architecture,
maps, textures and binary assets are excluded from publication because
their redistribution provenance has not been established. They remain on
the original workstation. The portable generator has no dependency on them.

## Geographic data

Pandori Nijjaran roads: copyright OpenStreetMap contributors, ODbL 1.0.
Buildings: Overture Maps Foundation, release 2026-10-21.0, ODbL 1.0.
The extract includes Microsoft Global ML Building Footprints (ODbL 1.0)
and Google Open Buildings (CC BY 4.0). Source records and provider metadata
are retained in `Assets/Geodata`, with source URLs and hashes. Generated
geographic databases remain under ODbL; MIT covers original code only.
See https://docs.overturemaps.org/attribution/#buildings and
https://www.openstreetmap.org/copyright.

## Additional CC0 vegetation

Poly Haven `tree_small_02` and `shrub_01`, geometry and textures, CC0 1.0.
Download paths and checksums are pinned in `Assets/models.lock.json`.
Public village photos/videos are reference links only and are not redistributed.

## V2.5 Gurmukhi font

Noto Sans Gurmukhi, copyright The Noto Project Authors, SIL Open Font License
1.1. The font and original OFL text are included under `Assets/Fonts` and staged
with the V2.5 package. The exact source commit, URL and SHA256 are recorded in
`Assets/v25_assets.lock.json`. Source: https://github.com/google/fonts/tree/main/ofl/notosansgurmukhi.

The V2.5 action policy was trained from this repository's original synthetic
controller and is distributed under the repository MIT license. No external
pretrained language, speech-recognition or voice model is included. The current
character/vehicle prototype geometry is original procedural code. Quaternius
assets were researched but not acquired or included after a download quota error.

## V3 atlas, regional architecture and farming

V3 building, landmark, animal and farm geometry is original procedural code under
the repository MIT license. `Assets/World/v3_world.json` and the atlas image are
derived from the pinned OSM/Overture geographic inputs and retain the geographic
data attribution and ODbL obligations above; they are not solely MIT data.

Public landmark listings are linked in `Docs/V3/README.md`: Wikimapia Shiv Temple,
Yappe Gurudwara Nihang Singh and iCBSE GPS Pandori Nijjaran. These support reference
context, not surveyed game positions or verified facades. No listing photographs,
external map tiles, private resident details or third-party landmark meshes are
redistributed. All nine in-game public sites are marked representative.

## MetaHuman authoring pilot

The separate Manpreet pilot uses Epic's installed MetaHuman Creator APIs. Epic
technology and generated MetaHuman assets retain their applicable Epic terms;
they are not relicensed under this repository's MIT source-code license. Pilot
binary assets under `Content/MetaHumanPilot` are now included through Git LFS as generated character assets under the applicable Epic terms. The user requested this publication after the initial local pilot.
The pilot references Epic's installed MetaHuman neutral idle and forward-walk
animation clips. These remain local and retain their applicable Epic terms.
The Pardeep third-person preview reuses that generated visual through a separate
Blueprint under `Content/VillageMeshV3/Player`. It is a user-approved temporary
appearance, not a reconstruction of Pardeep. Its project-authored blend space
references the installed Epic idle, walk and run clips; the raw clips are not
redistributed. The generated visual and its dependencies retain the same Epic
terms. No personal photo archive or face-recognition data is included.
The generated character includes its assembled grooms, garment, rig and textures. The full Creator Core Data library, engine/plugin binaries and plugin example source files are not redistributed. See `Docs/LFS/README.md` for the publication scope and current license references, and `Docs/MetaHumanPilot/README.md` for the verified setup
state, original orchestration scripts, and current official licensing links.
