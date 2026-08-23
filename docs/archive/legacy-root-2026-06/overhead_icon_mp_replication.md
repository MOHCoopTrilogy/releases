# Overhead Icon: Replicating the MP Player Team-Icon Path for AI Actors

Research date: 2026-06-22
Engine source: `C:\mohaa-coop-dev\openmohaa-hzm`
Mod scripts: `C:\mohaa-coop-dev\hzm-mohaa-coop-mod`

---

## TL;DR (the bug and the fix)

The real MP player icon (`CG_PlayerTeamIcon`) draws a **world-space 3D sprite** via
`cgi.R_AddRefSpriteToScene` (`reType = RT_SPRITE`). The renderer makes it a
camera-facing billboard sized by `iconEnt.scale`, anchored at a world position
20 units above the **"eyes bone"** tag.

The mod's current `CG_ActorBossIcon` / `CG_ActorAllyIcon` do **NOT** use that path.
They compute the same world head position but then **manually project it to 2D screen
coords** and queue a `R_DrawStretchPic` (a flat 2D HUD blit) in `CG_DrawCoopIcons`.
That is why the icon is "too small / off / broken": the 2D projection + the
`64*256/dist` pixel-size heuristic do not match the engine's true sprite scaling,
and any error in fov/width math throws the position off.

**Fix:** delete the 2D projection/stretchpic machinery and instead build a
`refEntity_t` exactly like `CG_PlayerTeamIcon` does (lines 99-206) and call
`cgi.R_AddRefSpriteToScene(&iconEnt)`. The actor's `refEntity_t model` passed into
these functions already has valid `tiki`, `origin`, `axis`, and `scale`, so the same
tag lookup + distance scale/fade code works verbatim.

---

## TASK 1 — The MP player team-icon render path (authoritative reference)

### Function
`CG_PlayerTeamIcon(refEntity_t *pModel, entityState_t *pPlayerState)`
File: `C:\mohaa-coop-dev\openmohaa-hzm\code\cgame\cg_modelanim.c:56`

### Call site
`C:\mohaa-coop-dev\openmohaa-hzm\code\cgame\cg_modelanim.c:1515-1517`
```c
if (cent->currentState.eType == ET_PLAYER && !(cent->currentState.eFlags & EF_DEAD)) {
    CG_PlayerTeamIcon(&model, &cent->currentState);
}
```
This is inside `CG_ModelAnim` (`cg_modelanim.c:1144`). By this point `model`
(a local `refEntity_t`) is fully populated:
- `model.origin` / `model.oldorigin` <- `cent->lerpOrigin`  (line 1214-1215)
- `model.axis` <- `AnglesToAxis(cent->lerpAngles, model.axis)` (line 1255)
- `model.scale` (lines 1281-1283)
- `model.tiki` <- `cgi.R_Model_GetHandle(...)` (line 1287)
- `model.renderfx |= s1->renderfx;` (line 1333)  <-- RF_COOP_BOSS lands here

### Anchor tag and world-position math (cg_modelanim.c:123-147)
```c
memset(vTmp, 0, sizeof(vTmp));
AnglesToAxis(vTmp, iconEnt.axis);          // identity axis (sprite is billboard anyway)
iconEnt.scale              = 0.5f;
iconEnt.renderfx           = 0;
iconEnt.reType             = RT_SPRITE;     // <-- KEY: world sprite, not 2D pic
iconEnt.shaderTime         = 0.0f;
iconEnt.frameInfo[0].index = 0;
iconEnt.shaderRGBA[0..2]   = -1;            // white (0xff) RGB
VectorCopy(pModel->origin, iconEnt.origin);

iTag = cgi.Tag_NumForName(pModel->tiki, "eyes bone");
if (iTag == -1) {
    iconEnt.origin[2] += 96.0f;            // fallback if no eyes bone
} else {
    orientation_t oEyes = cgi.TIKI_Orientation(pModel, iTag);
    for (i = 0; i < 3; ++i)
        VectorMA(iconEnt.origin, oEyes.origin[i], pModel->axis[i], iconEnt.origin);
    iconEnt.origin[2] += 20.0f;            // 20 units above the eyes bone
}
```
- **Tag name:** `"eyes bone"` (preferred); fallback `+96` on origin if absent.
- **Z offset above the resolved tag:** `+20.0f`.
- The tag's local-frame origin is rotated into world space by accumulating
  `VectorMA(origin, oEyes.origin[i], pModel->axis[i], origin)` over the 3 model
  axes — this is the canonical "get a tag's WORLD position" pattern in cgame
  (`cgi.TIKI_Orientation` returns the tag orientation in the model's local frame;
  multiplying by `pModel->axis[]` lifts it to world). This is the function set you
  use for actor tags too.

### Distance scale (cg_modelanim.c:149-161)
```c
VectorSubtract(iconEnt.origin, cg.refdef.vieworg, vTmp);
fDist = VectorLength(vTmp);
if      (fDist < 256.0f) iconEnt.scale = fDist / 853.0f + 0.2f;
else if (fDist > 512.0f) iconEnt.scale = (fDist - 512.0f) / 2560.0f + 0.5f;
// (256..512 keeps the default 0.5)
if (iconEnt.scale > 1.0f) iconEnt.scale = 1.0f;
```
Note the behavior: near = smaller, far = larger (clamped to 1.0). This keeps the
icon a roughly constant *screen* size because the renderer shrinks a fixed-scale
world sprite with distance; the increasing scale compensates so it stays readable.

### Distance alpha / fade (cg_modelanim.c:163-185)
```c
if      (fDist > 256.0) fAlpha = 1.0f;
else if (fDist >= 72.0f) fAlpha = (fDist - 72.0f) / 184.0f;   // fade in 72..256
else                     fAlpha = 0.0f;                       // hidden when very close
// team-based dimming:
fAlpha *= (STAT_TEAM == ALLIES || AXIS) ? 0.65f : 0.4f;
iconEnt.shaderRGBA[3] = (int)(fAlpha * 255.0f);
```

### Submission (cg_modelanim.c:187-206)
```c
if (fAlpha > 0.0 || bSpecialIcon) {
    ...
    cgi.R_AddRefSpriteToScene(&iconEnt);   // <-- THE call
    ...
}
```
- **Shader/material:** registered via `cgi.R_RegisterModel("textures/hud/axis_headicon.spr")`
  (or `allies_headicon.spr`, `talking_headicon.spr`, `inmenu_headicon.spr`,
  `inmenu_artilleryicon.spr`). These are `.spr` sprite models, assigned to
  `iconEnt.hModel` (NOT `R_RegisterShaderNoMip`).
- **Scale:** the `iconEnt.scale` computed above (0.2..1.0).
- **Radius:** there is no explicit radius; for `RT_SPRITE` the renderer derives the
  billboard half-size from the sprite's own width × `ent->scale`. See
  `renderergl2/tr_scene.c:740` (`spr->scale = ent->scale;`),
  `renderergl2/tr_main.c:1676` (`case RT_SPRITE:`) and `:2275`
  (`radius = model->d.sprite->width * model->d.sprite->scale * 0.5;`), dispatched to
  `RB_SurfaceSprite()` at `renderergl2/tr_surface.c:1181-1182`. This is what makes it
  a true camera-facing world billboard. The renderergl1 path is equivalent.

### Entity-state gating (why actors can't currently use it)
- `CG_PlayerTeamIcon` early-outs unless `cgs.gametype > GT_FFA` (line 84-86) and the
  observed player is on the viewer's team / talking / in menu / artillery
  (lines 76-93). It also keys off `EF_ALLIES`/`EF_AXIS`/`EF_ANY_TEAM` player flags.
- The **call site** only invokes it for `eType == ET_PLAYER` (line 1515). AI actors are
  `ET_MODELANIM` / `ET_MODELANIM_SKEL`, so they never reach this function — and even if
  they did, the `bInTeam` team-membership logic is written around real MP clients and
  `cg.clientinfo[...]`, plus the `cgs.gametype <= GT_FFA` early return kills it in coop
  (coop runs as FFA/`GT_SINGLE_PLAYER`-style). So the player function is not directly
  reusable for actors; we replicate its *sprite-building body*, not its gating.

---

## TASK 2 — Driving the SAME RT_SPRITE path for an AI actor

Yes — `R_AddRefSpriteToScene` is entity-type agnostic. It takes a bare
`refEntity_t` with `reType = RT_SPRITE`, `hModel` = a `.spr`, an `origin`, a `scale`,
and `shaderRGBA`. It does not care whether the source centity is a player or a
MODELANIM actor. We build a fresh throwaway `refEntity_t` (`iconEnt`) just like the
player code does; the actor's own model entity is only used as a *source* for the
head position and axes.

### Tag availability on actor models
- The actor `refEntity_t model` passed into `CG_ActorBossIcon/AllyIcon` already has a
  valid `model.tiki`. The same `cgi.Tag_NumForName(model.tiki, "eyes bone")` lookup
  used for players works for AI human skeletons.
- The mod's German/allied AI use the shared human skeleton (`models/human/*`,
  `new_generic_human.tik`). `"eyes bone"` is a **skeleton bone (in the .skd)**, not a
  TIKI keyword — `new_generic_human.tik` references `"Bip01 Head"` for attachmodel
  (lines 1742/1750), confirming the Bip01 hierarchy is present. The existing actor code
  already does `iTag = Tag_NumForName(... "eyes bone"); if (-1) Tag_NumForName(... "Bip01 Head")`
  (cg_modelanim.c:273-274, 321-322) — so tag resolution on actors is already proven to
  work; that part of the current code is correct. Use the same two-step lookup.
- **World position of an actor tag in cgame:** identical pattern to the player —
  `orientation_t o = cgi.TIKI_Orientation(pModel, iTag);` then accumulate
  `VectorMA(origin, o.origin[i], pModel->axis[i], origin)` over i=0..2. (This is exactly
  what lines 276-279 / 324-327 already do.) That is the canonical tag->world function.

### RF_COOP_BOSS reaches cgame intact — CONFIRMED
- Flag definition: `qcommon/q_shared.h:1935` -> `#define RF_COOP_BOSS (1<<27)`.
- Set fgame-side via `rendereffects "+coopboss"`:
  `fgame/entity.cpp:3982-3983` maps token "coopboss" -> `RF_COOP_BOSS`, OR'd into
  `edict->s.renderfx` at line 3991.
- Replicated as a full 32-bit field in **all** entityState netfield tables:
  `qcommon/msg.cpp:1358`, `:1512`, `:1666` -> `{ NETF(renderfx), 32, ... }`.
  Bit 27 is well within 32 bits, so it survives the snapshot delta intact.
- On the cgame side it is copied into the render entity at
  `cg_modelanim.c:1333` (`model.renderfx |= s1->renderfx;`) and the actor-icon gate
  reads `cent->currentState.renderfx & RF_COOP_BOSS` at `cg_modelanim.c:1521`.

So no further fgame/netcode work is required. The flag plumbing is already complete
and correct.

---

## TASK 3 — What the mod currently does, and WHY it's wrong

### Current actor implementation
- Gate / dispatch: `cg_modelanim.c:1520-1528`
  ```c
  if ((eType == ET_MODELANIM || eType == ET_MODELANIM_SKEL)
      && (renderfx & RF_COOP_BOSS) && !(eFlags & EF_DEAD)) {
      if (eFlags & EF_AXIS) CG_ActorBossIcon(&model, &cent->currentState);
      else                  CG_ActorAllyIcon(&model, &cent->currentState);
  }
  ```
  (The doc-comment on `CG_ActorAllyIcon` mentions an `RF_EXTRALIGHT` gate, but the
  actual gate is `RF_COOP_BOSS` for both. Both branches require RF_COOP_BOSS.)

- `CG_ActorBossIcon` (`cg_modelanim.c:265-302`) and `CG_ActorAllyIcon`
  (`cg_modelanim.c:313-350`) are byte-for-byte identical except the final
  `CG_PushCoopIcon(..., 1)` vs `(..., 0)` enemy flag.

- They:
  1. Compute the head world position correctly (same tag math as the player). **OK.**
  2. Then **manually project to screen space** (lines 285-294):
     ```c
     fwd = DotProduct(delta, viewaxis[0]); if (fwd <= 1) return;
     rgt = DotProduct(delta, viewaxis[1]);
     up  = DotProduct(delta, viewaxis[2]);
     projDist = refdef.width / tan(fov_x/360*PI);
     proj = projDist * 0.5 / fwd;
     sx = (refdef.x + width*0.5)  + rgt*proj;
     sy = (refdef.y + height*0.5) - up *proj;
     ```
  3. Pick a pixel size by a hand-rolled heuristic (lines 296-299):
     `iconSize = 64*256/fDist`, clamped to [20, 96].
  4. Queue a deferred 2D blit: `CG_PushCoopIcon(sx, sy, iconSize, isEnemy)`.

- `CG_DrawCoopIcons` (`cg_modelanim.c:235-256`) is flushed from
  `cg_drawtools.cpp:1529` (declared `extern "C"` at `cg_drawtools.cpp:28`) and draws each
  queued icon with **`cgi.R_DrawStretchPic(sx-sz/2, sy-sz/2, sz, sz, 0,0,1,1, h)`**,
  using shader handles from `R_RegisterShaderNoMip("textures/hud/axis_headicon")` /
  `allies_headicon`.

### Why this is broken / too small / off
- It is a **2D HUD stretch-pic**, not the engine's `RT_SPRITE` world billboard. None of
  the player path's renderer-side sprite sizing is used.
- The manual projection assumes a specific relationship between `refdef.width`,
  `fov_x`, and the actual viewport that may not hold (widescreen / fov / refdef.x,y
  offsets / split assumptions), so the **screen position drifts** ("off to the side /
  not over their heads").
- The `64*256/dist` size law and the [20,96]px clamp bear **no relation** to the player
  icon's `scale = dist/853 + 0.2` world-sprite law, so it reads as **wrong-sized**
  ("way too small").
- It has **no alpha/fade**, no team dimming, and uses `R_RegisterShaderNoMip` instead of
  the `.spr` sprite model — i.e. it is a completely different code path that happens to
  draw a similar texture.

This is exactly the regression the user described. The earlier `attachmodel`/billboard
and free-floating script_model attempts failed for the analogous reason (offset in the
wrong frame / not the engine's icon path). The 2D-stretchpic attempt is the current one.

---

## TASK 4 — Concrete recommendation (minimal cgame change)

**Replace the body of `CG_ActorBossIcon` / `CG_ActorAllyIcon` so they build a
`refEntity_t` and call `cgi.R_AddRefSpriteToScene`, mirroring `CG_PlayerTeamIcon`.**
Drop the screen-projection, `CG_PushCoopIcon`, `g_coopIcons`, `CG_DrawCoopIcons`, and the
`cg_drawtools.cpp:1529` flush entirely (they become dead code).

### Single shared helper (recommended)
Add one function in `cg_modelanim.c` near line 264, replacing both actor-icon functions:

```c
static void CG_ActorOverheadIcon(refEntity_t *pModel, qboolean bEnemy)
{
    int           i, iTag;
    float         fDist, fAlpha;
    vec3_t        vTmp;
    refEntity_t   iconEnt;

    memset(&iconEnt, 0, sizeof(iconEnt));

    /* sprite model: same .spr assets the player icon uses */
    iconEnt.hModel = cgi.R_RegisterModel(
        bEnemy ? "textures/hud/axis_headicon.spr"
               : "textures/hud/allies_headicon.spr");
    if (!iconEnt.hModel) { return; }

    memset(vTmp, 0, sizeof(vTmp));
    AnglesToAxis(vTmp, iconEnt.axis);

    iconEnt.scale              = 0.5f;
    iconEnt.renderfx           = 0;
    iconEnt.reType             = RT_SPRITE;
    iconEnt.shaderTime         = 0.0f;
    iconEnt.frameInfo[0].index = 0;
    iconEnt.shaderRGBA[0]      = -1;
    iconEnt.shaderRGBA[1]      = -1;
    iconEnt.shaderRGBA[2]      = -1;

    /* --- head world position: same tag math as CG_PlayerTeamIcon --- */
    VectorCopy(pModel->origin, iconEnt.origin);
    iTag = cgi.Tag_NumForName(pModel->tiki, "eyes bone");
    if (iTag == -1) { iTag = cgi.Tag_NumForName(pModel->tiki, "Bip01 Head"); }
    if (iTag == -1) {
        iconEnt.origin[2] += 96.0f;
    } else {
        orientation_t o = cgi.TIKI_Orientation(pModel, iTag);
        for (i = 0; i < 3; ++i)
            VectorMA(iconEnt.origin, o.origin[i], pModel->axis[i], iconEnt.origin);
        iconEnt.origin[2] += 20.0f;     /* same as player */
    }

    /* --- distance scale: identical to player path --- */
    VectorSubtract(iconEnt.origin, cg.refdef.vieworg, vTmp);
    fDist = VectorLength(vTmp);
    if      (fDist < 256.0f) iconEnt.scale = fDist / 853.0f + 0.2f;
    else if (fDist > 512.0f) iconEnt.scale = (fDist - 512.0f) / 2560.0f + 0.5f;
    if (iconEnt.scale > 1.0f) iconEnt.scale = 1.0f;

    /* --- distance alpha: player fade-in curve (no team dimming in coop) --- */
    if      (fDist > 256.0f) fAlpha = 1.0f;
    else if (fDist >= 72.0f) fAlpha = (fDist - 72.0f) / 184.0f;
    else                     fAlpha = 0.0f;
    iconEnt.shaderRGBA[3] = (int)(fAlpha * 255.0f);

    if (fAlpha > 0.0f) {
        cgi.R_AddRefSpriteToScene(&iconEnt);
    }
}
```

Then at the call site (`cg_modelanim.c:1520-1528`) replace the two calls:
```c
if ((cent->currentState.eType == ET_MODELANIM || cent->currentState.eType == ET_MODELANIM_SKEL)
    && (cent->currentState.renderfx & RF_COOP_BOSS)
    && !(cent->currentState.eFlags & EF_DEAD)) {
    CG_ActorOverheadIcon(&model, (cent->currentState.eFlags & EF_AXIS) ? qtrue : qfalse);
}
```

### Exact anchors to edit
- Replace functions: `cg_modelanim.c:265-302` (`CG_ActorBossIcon`) and
  `cg_modelanim.c:313-350` (`CG_ActorAllyIcon`).
- Update dispatch: `cg_modelanim.c:1520-1528`.
- Delete (now unused): the deferred buffer `cg_modelanim.c:210-256`
  (`coopPendingIcon_t`, `g_coopIcons`, `g_numCoopIcons`, `CG_PushCoopIcon`,
  `CG_DrawCoopIcons`) and its flush + extern decl in
  `cg_drawtools.cpp:28` and `cg_drawtools.cpp:1529`. (Leaving them compiles fine but
  they are dead; removing avoids the stray `R_DrawStretchPic` path.)

### Constants summary (copy from player path)
| Item            | Value                                                        |
|-----------------|--------------------------------------------------------------|
| Tag             | `"eyes bone"`, fallback `"Bip01 Head"`, then `+96` origin    |
| Z offset        | `+20.0f` above the resolved tag (or `+96` no-tag fallback)   |
| reType          | `RT_SPRITE`                                                  |
| hModel          | `textures/hud/axis_headicon.spr` / `allies_headicon.spr`     |
| base scale      | `0.5f`                                                       |
| near scale      | `fDist/853.0f + 0.2f` (fDist < 256)                          |
| far scale       | `(fDist-512.0f)/2560.0f + 0.5f` (fDist > 512), clamp <= 1.0  |
| alpha           | 0 below 72u; ramp 72..256u; 1.0 beyond 256u                 |
| radius          | implicit — renderer uses sprite width × scale (RT_SPRITE)    |

### Asset note
`textures/hud/axis_headicon.spr` and `allies_headicon.spr` are the stock MP sprite
models. For the swastika/allied faction art, ship overriding `.spr` (and their
referenced shaders/material) in the mod pk3 under the same paths, OR register a new
`.spr` path. The German actors already carry `EF_AXIS`, so the existing
`eFlags & EF_AXIS` branch correctly selects the axis sprite; allied paratroopers
(RF_COOP_BOSS set, no EF_AXIS) get the allies sprite.

### fgame-side support required
**None.** RF_COOP_BOSS is already set (`rendereffects "+coopboss"`,
`entity.cpp:3982`), replicated 32-bit (`msg.cpp:1358/1512/1666`), and read on the
cgame gate (`cg_modelanim.c:1521`). EF_AXIS is already set on German actors. The whole
change is contained in cgame.

---

## File:line index
- `code/cgame/cg_modelanim.c:56` — CG_PlayerTeamIcon (reference impl)
- `code/cgame/cg_modelanim.c:123-147` — tag anchor + +20 Z offset (player)
- `code/cgame/cg_modelanim.c:149-185` — distance scale + alpha
- `code/cgame/cg_modelanim.c:193,204` — R_AddRefSpriteToScene calls (player)
- `code/cgame/cg_modelanim.c:210-256` — current deferred-2D icon buffer (REMOVE)
- `code/cgame/cg_modelanim.c:265-302` — CG_ActorBossIcon (REPLACE)
- `code/cgame/cg_modelanim.c:313-350` — CG_ActorAllyIcon (REPLACE)
- `code/cgame/cg_modelanim.c:1287,1214-1255,1333` — model.tiki/origin/axis/renderfx setup
- `code/cgame/cg_modelanim.c:1515-1528` — player + actor icon dispatch (UPDATE actor branch)
- `code/cgame/cg_drawtools.cpp:28,1529` — CG_DrawCoopIcons extern + flush (REMOVE)
- `code/qcommon/q_shared.h:1935` — RF_COOP_BOSS = (1<<27)
- `code/fgame/entity.cpp:3982-3991` — "coopboss" -> RF_COOP_BOSS, OR into renderfx
- `code/qcommon/msg.cpp:1358,1512,1666` — renderfx 32-bit netfield (replication proof)
- `code/client/cl_cgame.cpp:727` — cgi->R_AddRefSpriteToScene = re.AddRefSpriteToScene
- `code/renderergl2/tr_scene.c:740` — spr->scale = ent->scale (sprite sizing)
- `code/renderergl2/tr_main.c:1676,2275` — RT_SPRITE billboard radius from width×scale
- `code/renderergl2/tr_surface.c:1181-1182` — RT_SPRITE -> RB_SurfaceSprite()
