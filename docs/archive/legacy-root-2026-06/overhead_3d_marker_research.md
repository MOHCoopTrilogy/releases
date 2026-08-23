# Overhead 3D Faction Marker Research (MOHAA / OpenMOHAA Coop)

Goal: a reliable floating faction symbol above every combatant — an AXIS military
insignia (Balkenkreuz / Iron Cross) over German officer + bodyguards + reinforcements,
and an ALLIED marker (white star / roundel) over the paradrop soldiers. The current
2D screen-space sprite is hard to see; evaluate a 3D world-space marker instead.

All cites are read-only observations; no files were modified.

---

## 1. How the current 2D system works, and why it is fragile

### Dispatch
`code/cgame/cg_modelanim.c:1520-1528` — inside `CG_ModelAnim`, after the actor's
refEntity is built, if the entity is `ET_MODELANIM`/`ET_MODELANIM_SKEL`, has
`RF_COOP_BOSS` set, and is not `EF_DEAD`, it calls:
- `CG_ActorBossIcon` when `EF_AXIS` is set (enemy), else
- `CG_ActorAllyIcon` (allied paratrooper).

`RF_COOP_BOSS` is the gate flag, defined `code/qcommon/q_shared.h:1935` (`1<<27`),
set from script via `rendereffects "+coopboss"` which maps to the mask at
`code/fgame/entity.cpp:3982-3983`.

### The 2D draw path (the fragile part)
`CG_ActorBossIcon` / `CG_ActorAllyIcon` (`cg_modelanim.c:265-302` and `313-350`) do
**manual world→screen projection by hand**:
1. Take the actor origin, find the `"eyes bone"` (fallback `"Bip01 Head"`) tag via
   `cgi.Tag_NumForName` + `cgi.TIKI_Orientation`, add `+40` Z (or `+96` if no tag) — `cg_modelanim.c:272-283`.
2. Subtract `cg.refdef.vieworg`, dot against `viewaxis` to get fwd/rgt/up — `:285-289`.
3. **Early-out `if (fwd <= 1.0f) return;`** — anything not in front of the camera is dropped — `:287`.
4. Compute a projection scale from `cg.refdef.fov_x`/`width` and convert to screen x/y — `:291-294`.
5. Distance-scale the icon size 20..96 px — `:296-299`.
6. `CG_PushCoopIcon(sx, sy, size, isEnemy)` into a deferred buffer — `:301 / :349`.

The icons can't be drawn at this point because `R_DrawStretchPic` issued during entity
processing is overwritten by `R_RenderScene`. So they are buffered (`g_coopIcons[64]`,
`cg_modelanim.c:215-232`) and flushed later by `CG_DrawCoopIcons` (`:235-256`), which is
called from `CG_Draw2D` after the 3D scene renders (`code/cgame/cg_drawtools.cpp:1529`,
declared `:28`). The flush registers `textures/hud/axis_headicon` / `allies_headicon`
with `R_RegisterShaderNoMip` and blits each with `R_DrawStretchPic` (`:242-253`).

### Why it is unreliable / hard to see
- **Pure 2D blit with no depth.** It is a flat HUD sprite. It does not occlude behind
  walls (can show through geometry) yet is also easy to lose against busy backgrounds.
- **Hand-rolled projection** duplicates the engine's view math and is brittle: it depends
  on `cg.refdef` being correct at the exact call site, the `fwd<=1` cull, and FOV math.
- **Tied to the per-entity render pass.** It only runs while `CG_ModelAnim` is processing
  that actor's refEntity; if the actor's model fails to build a refEntity that frame, or
  the tag lookup behaves oddly, no icon. The user confirms the dispatch fires (debug
  prints) but the result is faint/hard to see — consistent with a small, flat, depth-less
  2D blit that washes out.
- **Single fixed texture per side**, no real depth cue, no silhouette. Reads poorly at
  combat range against terrain.

In short: the mechanism *works* but it's a 2D HUD overlay reconstructed from scratch
every frame, which is exactly the class of thing that is finicky and low-visibility.

---

## 2. The 3D options

### 2a. `attachmodel` (fgame script command) — RECOMMENDED primitive

Event definition `code/fgame/entity.cpp:379-395`:

```
Event EV_AttachModel
(
    "attachmodel",
    EV_DEFAULT,
    "ssFSBFFFFV",
    "modelname tagname scale targetname detach_at_death removetime fadeintime fadeoutdelay fadetime offset",
    ...
);
```

**Exact signature** (positional; `s`=string, `F`=optional float, `S`=optional string,
`B`=optional bool/int, `V`=optional vector):

```
<entity> attachmodel <modelname> <tagname> [scale] [targetname] [detach_at_death]
                     [removetime] [fadeintime] [fadeoutdelay] [fadetime] [offset]
```

Handler `Entity::AttachModelEvent` (`code/fgame/entity.cpp:4302-4393`): it `new Animate`,
`setModel(modelname)`, `setScale`, optional `SetTargetName`, `detach_at_death` flag,
optional auto-`EV_Remove` after `removetime`, fade in/out events, optional `offset`
vector. It resolves the tag with `gi.Tag_NumForName(edict->tiki, bone)` and calls
`obj->attach(this->entnum, tagnum, true, offset)` then `NewAnim("idle")`.

`Entity::attach` (`code/fgame/entity.cpp:3709-3757`) wires the child into the parent:
sets `edict->s.parent`, `tag_num`, `attach_use_angles`, `attach_offset`, then
`setOrigin()`. **The attach is by parent entnum + tag_num stored in the entity state**,
so the engine re-derives the child's world transform from the parent's tag **every frame
automatically** — no per-frame script thread is needed, and it follows the head bone as
the actor animates. Cleanup is automatic: `detach_at_death=1` drops it on death, and the
parent's `KillAttach`/child-removal (`entity.cpp:3759-3781`) cleans children when the
parent is removed.

**Networking:** the attachment lives in the entity state (`s.parent`, `s.tag_num`,
`s.attach_offset`), so it replicates to all coop clients like any other networked entity —
every player sees the marker, computed client-side from the parent tag. This is the same
mechanism MOHAA uses for helmets/backpacks/weapons on actors.

**Tag names available on human actors:** `"eyes bone"` and `"Bip01 Head"` are both present
(the 2D code already probes them — `cg_modelanim.c:273-274`). Use `"Bip01 Head"` with a
positive Z offset, or `"eyes bone"`, plus an `offset` vector like `(0 0 32)` to float it
above the helmet.

No existing usage of `attachmodel` in the coop scripts today (grep found only the event
definition + handler in fgame; the coop scripts use synced `script_model` glows instead).

### 2b. Synced `script_model` (what the mod does today for glows/chutes)

The mod already spawns a `script_model`, sets a model, and updates `.origin` every frame:
- `coop_mod/officer.scr:655-667` `coop_wave_glow` — spawns `models/fx/dummy.tik`, sets a
  red light, and loops `local.glow.origin = local.actor.origin; waitframe` while the actor
  is alive, then `delete`s it.
- `coop_mod/paradrop.scr:228-235` `coop_chute_sync_vis` — syncs the trooper visual 70u
  below the chute each `wait 0.05`.

Pros: full script control of model/scale/color, no dependence on a tag existing. Cons:
**one extra entity AND one extra script thread per actor**, the origin lags by up to a
frame (visible jitter on fast head movement), and it does not inherit head-bone motion
(it tracks `.origin`, i.e. the feet, so you must add a fixed Z). With 10-20 actors that's
10-20 extra threads churning every frame.

### 2c. Billboard (always-face-camera) — the visibility win

The renderer supports camera-facing sprites via the shader keyword `spritegen`
(`code/renderergl1/tr_shader.c:2390-2402`, also gl2 `tr_shader.c:2630-2642`):
`spritegen parallel` (face camera, upright-free), `parallel_oriented`, `parallel_upright`.
A model whose surface shader uses `spritegen parallel` renders as a flat quad that always
faces the viewer — exactly the "flat symbol readable from any angle" behavior, but drawn
by the **normal 3D model renderer** (depth-tested, world-space).

The base game already ships the canonical billboard model: **`models/fx/corona_red.tik`**
(`Pak0`), which is a `skelmodel models/fx/unitsquare.skd` (a 1-unit flat quad,
`models/fx/unitsquare.tik`) with a sprite shader. The mod's own
`scripts/coop_hud_sprites.shader` and the existing `textures/hud/axis_headicon` /
`allies_headicon` shaders are **already declared `spritegen parallel`** (confirmed in the
base-game-style shader bodies). So the billboard texture work is essentially done.

This is the part that fixes the visibility complaint: a `spritegen parallel` quad attached
above the head reads as a flat facing symbol from any angle (like the 2D sprite) **but** is
a real world entity — correct depth, correct scale with distance, no hand-rolled projection.

---

## 3. Concrete existing asset candidates

### AXIS (German) — conventional military insignia (not charged symbology)
- `textures/interior/ironcross.tga` — **Balkenkreuz / Iron Cross**. The cleanest, most
  appropriate WWII German military marker. Found in `Pak0` (`textures/interior/ironcross.tga`).
- `textures/detail/oakcross.tga` — small cross detail, alt option.
- `textures/models/submodels/eagle.tga` and `models/static/static_nazieagle.tik`
  (+`static_nazieagle2.tik`, textures `models/static/nazieagle/nazi_eagle.tga`) — Wehrmacht
  eagle. Heavier/charged; the Iron Cross is the better neutral-military choice.
- `textures/mohmenu/norwegiancross.tga` / `distinguishedcross_med.tga` — generic cross art.

### ALLIED — white star / insignia
- `textures/sprites/ampstar_white.tga` — **white star, already a sprite-dir texture.** Best
  fit for the Allied roundel/star marker. Siblings: `ampstar.tga`, `ampstargreen.tga`,
  `ampstaryellow.tga` (color variants for tinting if wanted).
- `textures/mohmenu/silverstar_med.tga` / `bronzestar_med.tga` — US service-star art.
- `textures/models/human/usmaps/insignia/army_*.tga` — US Army rank insignia (less iconic).

### Billboard model + shader machinery (already present)
- `models/fx/unitsquare.tik` + `models/fx/unitsquare/unitsquare.skd/.skc` — flat quad
  skelmodel (the billboard mesh). `Pak0`.
- `models/fx/corona_red.tik` — working reference of a quad + sprite shader.
- Mod already ships `textures/hud/axis_headicon.tga` + `allies_headicon.tga` and a
  `spritegen parallel` shader for them (`scripts/coop_hud_sprites.shader`, and the
  base-style `textures/hud/axis_headicon` block). These textures can be reused directly as
  the billboard skin, or swapped for `ironcross.tga` / `ampstar_white.tga`.

### Minimal custom TIKI recipe (camera-facing faction billboard)
Model `models/coop/axis_marker.tik` (ship in the mod pk3):
```
TIKI
setup
{
    scale 0.9
    path models/fx/unitsquare
    skelmodel unitsquare.skd
    surface all shader coop_axis_marker
}
init { server { classname animate } }
animations { idle unitsquare.skc }
```
Shader `coop_axis_marker` (add to mod `.shader`):
```
coop_axis_marker
{
    spritegen parallel          // always faces camera
    surfaceparm nolightmap
    nopicmip
    cull none
    {
        map textures/interior/ironcross.tga   // or textures/hud/axis_headicon
        blendFunc blend
        rgbGen identity
    }
}
```
Duplicate as `coop_allied_marker.tik` / `coop_allied_marker` using
`textures/sprites/ampstar_white.tga`. (Reuses the stock `unitsquare.skd` mesh — no new
geometry needed.)

---

## 4. Entity / perf considerations

- **attachmodel cost:** one extra networked entity per actor, **zero extra script
  threads** (engine drives the transform from the parent tag). The child is a tiny quad
  (`unitsquare`) with one surface. For 10-20 actors that's 10-20 small entities — well
  within MOHAA's entity budget (the mod already spawns multiple `script_model` glows +
  lights per wave). Replicates automatically to all coop clients via entity state.
- **synced script_model cost:** one extra entity **plus one busy thread per actor**
  (`while alive { .origin = ...; waitframe }`). 2c. billboard still needs this thread; only
  attachmodel avoids it. More threads = more script VM churn with large waves.
- **Lighting:** `spritegen` sprite quads ignore lightmap (`surfaceparm nolightmap`) so they
  stay bright regardless of map lighting — good for a marker.
- **Farplane:** a world entity is subject to the same farplane cull noted elsewhere in the
  KB (distant actors past the map farplane won't draw the marker — same as the actor model
  itself disappearing). This is acceptable: at normal combat range it's always visible, and
  it is strictly better than the 2D sprite, which additionally suffered the `fwd<=1` cull
  and the depth-less wash-out. The paradrop script already raises the far-clip plane for
  the C-47 (`paradrop.scr:38`); markers inherit that benefit while troopers are airborne.

---

## 5. Does 3D solve the visibility problem?

Yes. A `spritegen parallel` quad attached above the head is drawn by the normal model
renderer: it is depth-correct, scales naturally with distance, faces the camera from any
angle (the same readability as the 2D sprite), and does not rely on hand-rolled
`cg.refdef` projection or the `fwd<=1` early-out. It removes every fragile element of the
2D path except the farplane (which equally affects the actor model, so it never "loses" a
marker on a visible enemy). It is the more robust solution and works uniformly for all
actor types (officer, bodyguard, reinforcement infantry/sniper/MG/dog-handler, paratrooper)
because the attach is by tag on the standard human skeleton.

---

## RANKED RECOMMENDATION

**#1 (recommended): `attachmodel` a `spritegen parallel` billboard quad to `"Bip01 Head"`.**
No per-frame thread, auto-follows the head, auto-cleans on death, replicates to all
clients. Best perf and reliability.

**#2: synced `script_model` billboard** (reuse the existing `coop_wave_glow` /
`coop_chute_sync_vis` pattern) — use only if a specific actor type lacks the head tag or
you want script-side scale/color animation. Costs a thread per actor.

**#3: keep the 2D sprite** — only as a fallback; it's the current, hard-to-see path.

### Implementation sketch (no code changed; this is the plan)

**Assets to add to the mod pk3** (`maintt/zzzzzz_co-op_hzm_mod_mohaa.pk3`):
1. `models/coop/axis_marker.tik` and `models/coop/allied_marker.tik` (the unitsquare-based
   TIKIs from section 3).
2. Shader blocks `coop_axis_marker` (map `textures/interior/ironcross.tga`) and
   `coop_allied_marker` (map `textures/sprites/ampstar_white.tga`), both `spritegen parallel`,
   added to an existing mod `.shader` (e.g. alongside `coop_hud_sprites.shader`). Optionally
   tint via `rgbGen` constant (red-ish axis / blue-or-white allied) to color-distinguish.

**AXIS — single chokepoint, `coop_mod/officer.scr` `coop_wave_glow` (`:647`).**
Every enemy actor (officer, bodyguards `:835`, infantry `:913/:1013/:1295`, MG gunner/loader
`:1495/:1511`, sniper `:1154`, spotter `:1095`, dog handler `:1699`, etc.) already routes
through `thread coop_wave_glow`. Inside it, right after the `german` line (`:649`), add:
```
local.actor attachmodel "models/coop/axis_marker.tik" "Bip01 Head" 0.9 "" 1 -1 0 -1 -1 (0 0 34)
```
`detach_at_death=1` (5th arg) auto-removes on death; the existing `while alive` glow loop
and `delete` need no change. One line covers all axis types. (Dogs use a different
skeleton — gate the attach with a model/tag check or skip dogs as the bark loop already
does `:652`.)

**ALLIED — `coop_mod/paradrop.scr`, in the landed-actor block (`:178-203`).**
Right where it currently does `local.actor rendereffects "+coopboss"` (`:202`), add:
```
local.actor attachmodel "models/coop/allied_marker.tik" "Bip01 Head" 0.9 "" 1 -1 0 -1 -1 (0 0 34)
```
Applies to all 5 troopers (bar/thompson/rifle/sniper/medic) since they all pass through
this block.

**Color / distinguish:** different model+texture per side (iron cross vs white star) is the
primary cue; optionally add `rgbGen` tint in each shader (warm/red axis, cool/white-blue
allied) for instant friend-foe reading.

**Cleanup on death:** handled by `detach_at_death=1`. As a belt-and-suspenders option you
can also `local.actor removeattachedmodel "models/coop/axis_marker.tik"` in any death
handler, but it is not required.

**Migration note:** this can run *alongside* the existing 2D `RF_COOP_BOSS` path during
testing; once the 3D markers are confirmed, the `CG_ActorBossIcon`/`CG_ActorAllyIcon`
dispatch in `cg_modelanim.c:1520-1528` can be left in place (harmless) or removed. The 3D
path needs **no cgame/fgame code changes** — `attachmodel` and `spritegen` already exist.
