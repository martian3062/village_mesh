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
MD5 and SHA256. Downloads are cached locally and excluded from Git.

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
