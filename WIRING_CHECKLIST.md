> Legacy village only. For the portable open world, use `Scripts/bootstrap.ps1`; see README.md.

# Village Mini-Games — Manual Wiring Checklist

Work through these in order. Steps 1–4 get the module compiled; 5–12 wire
assets; 13–16 place and verify. Placeholders you will swap for your Blender
assets are written as `<LIKE_THIS>`.

## A. Compile (one-time setup)

1. **Install the C++ toolchain** if it is not already present:
   Visual Studio 2022 Community → workload **"Game development with C++"**,
   which must include *MSVC v143*, *Windows 10/11 SDK*, and
   *.NET desktop development* (UnrealBuildTool needs it).
2. **Close the Unreal Editor** (it currently has the project open without the
   new module; it must restart to load it).
3. Right-click `rural_pardeep.uproject` → **Generate Visual Studio project files**.
   (If that menu entry is missing, run:
   `"E:\U.E\UE_5.8\Engine\Build\BatchFiles\Build.bat" -projectfiles -project="D:\rural_games\rural_pardeep\rural_pardeep.uproject" -game -engine`)
4. **Build** — either open `rural_pardeep.sln` in VS and build the
   `rural_pardeepEditor` target (Development Editor | Win64), or run:
   `"E:\U.E\UE_5.8\Engine\Build\BatchFiles\Build.bat" rural_pardeepEditor Win64 Development -project="D:\rural_games\rural_pardeep\rural_pardeep.uproject" -waitmutex`
   *Compile order is automatic — everything is one module. If you later add a
   class, just rebuild this same target. Prefer a full editor restart over
   Live Coding while iterating on these classes (they have constructors that
   Live Coding won't re-run).*
5. Reopen the project. Confirm **C++ Classes → rural_pardeep** shows
   `VillageCharacter`, the three zones, etc. in the Content Browser.

## B. Enhanced Input assets

6. In `Content/Input/Actions`, the template already has `IA_Move`, `IA_Look`,
   `IA_Jump`. **Create three more Input Actions** (right-click → Input →
   Input Action):
   - `IA_Sprint` — Value Type: **Digital (bool)**
   - `IA_Interact` — Value Type: **Digital (bool)**
   - `IA_Cancel` — Value Type: **Digital (bool)**
7. **Duplicate `IMC_Default` → `IMC_Village`** (keeps the template's WASD 2D
   composite and mouse-look wiring), then add these mappings:

   | Action      | Key                 | Notes                                   |
   |-------------|---------------------|-----------------------------------------|
   | IA_Move     | W/A/S/D, L-stick    | already present from IMC_Default        |
   | IA_Look     | Mouse XY, R-stick   | already present from IMC_Default        |
   | IA_Jump     | Space Bar, Gamepad A| already present from IMC_Default        |
   | IA_Sprint   | Left Shift          | no triggers needed (hold = Started/Completed) |
   | IA_Interact | E, Gamepad X        | hold-to-charge works off Started/Completed |
   | IA_Cancel   | Escape, Gamepad B   | Escape also ends PIE — bind **Q** too if that annoys you |

## C. Character blueprint

8. Right-click `VillageCharacter` (C++ Classes) → **Create Blueprint child** →
   `BP_VillageCharacter` (put it in `Content/ThirdPerson/Blueprints`). On it:
   1. **Mesh** component → Skeletal Mesh = `<PLAYER_MESH_PLACEHOLDER>`
      (your Blender character, or `SKM_Quinn_Simple` from
      `/Game/Characters/Mannequins/Meshes/` to start); Anim Class =
      `ABP_Unarmed` (or your own ABP).
   2. Details → **Village|Input** → assign `IMC_Village`, `IA_Move`, `IA_Look`,
      `IA_Jump`, `IA_Sprint`, `IA_Interact`, `IA_Cancel`.
   3. **Village|Footsteps** → Footstep Dust System = `<DUST_NS_PLACEHOLDER>`
      (your Niagara dust puff; `NS_JumpPad` works as a stand-in).
   4. **Village|Animation** → assign `<ANIM_PLACEHOLDER>` montages when you
      have them: Dart Throw / Marble Flick / Kite Pull. (Safe to leave empty.)
   5. **Village|Interaction** (on the InteractionComponent) → HUD Widget
      Class = `WBP_GameHUD` (step 10).
9. Open `BP_ThirdPersonGameMode` → **Default Pawn Class = BP_VillageCharacter**.

## D. HUD widget

10. Right-click `GameHUDWidget` (C++ Classes) → Create Blueprint child →
    `WBP_GameHUD` in `Content/UI/`. Implement the events (Graph → Override):
    - `ShowInteractPrompt` / `HideInteractPrompt` — a centred bottom text
      block: `Press E to play {GameName}`.
    - `ShowGamePanel(PanelName)` / `HideGamePanel` — a Widget Switcher (or
      three Border panels) keyed by name: `Darts`, `Kancha`, `Kite`.
    - `UpdatePowerMeter(Power01, bVisible)` — a ProgressBar; also add a small
      **centre-screen crosshair** to the Darts panel (aim is screen-centre).
    - `UpdateDartsHUD(Score, DartsLeft, LastThrow)` — three text blocks.
    - `UpdateKanchaHUD(MarblesRemaining, MarblesWon)` — two text blocks.
    - `UpdateKiteHUD(AltitudeCm, StringLengthCm, KitesCut, Meter, bContest)`
      — divide the cm values by 100 for metres; show the contest meter
      ProgressBar only while `bContest` is true (0.5 = even tug).
    - `ShowStatusMessage(Message)` — a fading banner ("BUST!", "Bo kata!").

## E. Footstep dust notifies

11. Physical material: the surface types **Dirt (SurfaceType1)** and
    **Dust (SurfaceType2)** are already registered in `DefaultEngine.ini`.
    Create `Content/Materials/PM_Dirt` (right-click → Physics → Physical
    Material), set its **Surface Type = Dirt**, and set it on your landscape
    layer / ground materials (Material → Phys Material slot).
12. Anim notifies: open your walk and run sequences → notify track →
    right-click at each foot-plant frame → **Add Notify → New Notify** named
    `Footstep`. Then in the ABP's Event Graph add **AnimNotify_Footstep**
    events → Cast owner to `VillageCharacter` → call **On Footstep**.
    (Two plants per walk loop, two per run loop.)
    *Until you author physical materials, the character's Dust Surface Types
    array can be emptied to puff on every surface — handy for testing.*

## F. Zone art placeholders

13. On the placed `MG_DartsZone` (or a `BP_DartsZone` child if you prefer):
    - `DartboardMesh` → `<DARTBOARD_MESH_PLACEHOLDER>` (your Blender board).
      Keep the scoring-face normal along the component's **up axis** (the
      placeholder is a flattened cylinder) or re-tune `ScoreRings` radii.
    - `PlayAreaDecal` / `ThrowLineDecal` → assign chalk-line decal materials.
    - Optional: point `DartClass` at a BP child of `DartProjectile` with your
      dart mesh.
14. Kancha zone: assign a chalk-ring decal material; marbles default to engine
    spheres — set a glass material on `MarbleActor`'s mesh (or a BP child via
    `MarbleClass`).
15. Kite zone: create `BP_Kite` (child of `KiteActor`), assign your patang
    mesh to `<KITE_MESH_PLACEHOLDER>`, set it as `PlayerKiteClass` /
    `RivalKiteClass`. The debug-line strings can be replaced with Cable
    Components later (enable the Cable Component plugin).

## G. Place, build nav, play

16. Restarted editor with the compiled module? Then run the placement script
    in the Output Log's `Cmd` box:

    ```
    py "D:/rural_games/rural_pardeep/Scripts/place_minigame_zones.py"
    ```

    - With World Partition, **load the village region first** (World
      Partition minimap → drag-select → Load Region From Selection).
    - Check the Output Log summary; re-running cleans up `MG_*` and replaces.
17. Press **P** in the viewport — green NavMesh should cover the zones. If
    not (script warns if the volume spawned without brush geometry), drag a
    **NavMeshBoundsVolume** over the area and **Build → Build Paths**.
18. PCG foliage: add difference/exclusion volumes over the three zones and
    regenerate PCG so grass doesn't grow through the play areas.
19. **PIE test**: walk into each zone → `E` starts, `Esc` leaves.
    - Darts: mouse aims, hold-release E throws, 501 counts down (switch
      `GameMode` to Best-of-3 on the zone instance to compare).
    - Kancha: mouse orbits aim, hold-release E flicks; hits claim marbles.
    - Kite: climb the outside stair, E on the roof; WASD steers, Space lets
      out, Shift reels in, mash E during a pech.
    All tuning values are `EditAnywhere` on the zone instances — tweak live.
