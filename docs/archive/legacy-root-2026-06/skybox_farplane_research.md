# Sky Ceiling / Far-Plane Research — High-Altitude Paradrop Culling

Goal: make a C-47 + paratroopers at ~1800 units above ground render correctly (currently
forced down to ~750). Read-only investigation of the OpenMOHAA-HZM engine source and the
shipped `.bsp` worldspawn data.

TL;DR: The cutoff is **not** a sky-dome height cap and **not** the server PVS/snapshot cull.
It is the **client renderer far-clip plane (slant range from the camera)**, driven by the
**per-map `farplane` worldspawn key** (m4l3 = `2700`). The renderer honors a global cheat
cvar `r_farplane` that, when non-zero, **overrides every map's baked farplane**. That is the
clean global lever. A script `$world farplane <n>` per-map override also exists.

---

## 1. Mechanisms found (file:line citations)

### A. Per-map far plane lives in worldspawn, pushed to clients via CS_FOGINFO
- `fgame/worldspawn.cpp:545-595` — `World::World()` sets `farplane_distance = 0` by default
  (0 = "no far plane / unlimited"), but the `.bsp` worldspawn key **overrides** it on spawn.
- `fgame/worldspawn.cpp:163-207` — `"farplane"` is a worldspawn key **and** a runtime
  script setter (`EV_World_SetFarPlane` / `EV_World_SetFarPlane2`, both → `World::SetFarPlane`).
- `fgame/worldspawn.cpp:651-683` — `World::UpdateFog()` packs `farplane_cull`,
  `farplane_distance`, `skybox_farplane`, color, etc. into configstring `CS_FOGINFO`
  and calls `gi.SetFarPlane(farplane_distance)` (server side).
- `cgame/cg_main.c:455,920-967` — client parses `CS_FOGINFO` into
  `cg.farplane_distance` / `cg.skyboxFarplane` / `cg.farplane_cull`.
- `cgame/cg_view.c:538-549` — copies those into `cg.refdef.farplane_distance` every frame.

**Confirmed baked values (extracted from the shipped BSPs):**
| Map     | worldspawn `farplane` |
|---------|-----------------------|
| m4l3    | **2700**              |
| m6l1b   | 1600                  |
| m2l1    | 14500                 |
| m1l1    | (none → 0 = unlimited)|

So the ceiling is per-map and small on confined maps. m4l3's `2700` is the value biting us.

### B. Renderer turns farplane_distance into a hard far-clip frustum plane + fog
- `renderergl2/tr_scene.c:631-686` (gl1: `renderergl1/tr_scene.c`) — copies
  `fd->farplane_distance` into `parms.farplane_distance` for the view.
- `renderergl2/tr_main.c:773-792` — **`r_farplane` cvar override**: `else if (r_farplane->integer) { dest->farplane_distance = r_farplane->value; ... }`.
  When the cvar is non-zero it **replaces** the map's value outright.
- `renderergl2/tr_main.c:794-818` — when `farplane_distance` is set, the renderer adds
  `frustum[4]` (a 6th far-clip plane at that slant distance) and enables exponential fog
  at `fog.len = farplane_distance`. Anything farther than `farplane_distance` **from the
  camera** is clipped. gl1 mirror: `renderergl1/tr_main.c:643-690`.
- `renderergl1/tr_init.c:1526` & `renderergl2/tr_init.c:1585` —
  `r_farplane = Cvar_Get("r_farplane", "0", CVAR_CHEAT)`. Default 0, so maps use their own value.

### C. Client-side entity sphere cull also uses farplane_distance
- `cgame/cg_view.c:773-786` — `CG_FrustumCullSphere()`:
  `if (cg.refdef.farplane_distance && cg.refdef.farplane_distance + fRadius <= fDotFwd) return qtrue;`
  i.e. an entity whose forward distance exceeds the farplane is culled before drawing.
  This is the same `farplane_distance`, so raising it fixes both the world clip and the entity cull.

### D. Server entity transmission cull (PVS/snapshot) — present in coop, but NOT the cause
- `server/sv_snapshot.c:744-754` — **only in non-singleplayer** (so it DOES run in coop):
  every entity is run through `EntityDistCheck(...)`; `CULL_OUT` entities are not sent.
- `server/sv_snapshot.c:745-748` — `farplane = sv.farplane; if (farplane < 1) farplane = 12000; if (farplane > 12000) farplane = 12000;`
- `server/sv_game.c:1469-1479` — `SV_SetFarPlane`: `sv.farplane = (farplane + 32)^2`.
  Because the value is **squared**, any real map farplane (e.g. 2700 → ~7.4M) and 0/unset
  both end up clamped to **12000** at line 748. So the server transmits entities out to a
  flat ~12000-unit window regardless of map. **12000 >> 1800, so the server is not clipping
  the paradrop.** (Escape hatches if it ever mattered: `SVF_NOFARPLANE` g_public.h:51,
  `SVF_BROADCAST` g_public.h:41, or `RF_ALWAYSDRAW` q_shared.h:1934 — sv_snapshot.c:703,728.)

### E. Sky / sky portal — does NOT impose a height cap on real entities
- `fgame/worldspawn.cpp:415-423,697-701` — `skyportal` / `skyalpha` only toggle the portal-sky
  pass. `renderergl2/tr_sky_portal.cpp:105-185` renders the portal sky as a **separate view**
  with its own tiny origin and its own `skybox_farplane`; it does not bound where world-space
  entities can be. The sky is a shader on brush faces, not a physical ceiling. Not relevant.

---

## 2. Most likely cause of the ~1800-unit cutoff (m4l3)

The map's baked **`farplane 2700`** sets the renderer's far-clip frustum plane and fog
horizon to **2700 units of slant distance from the player's camera**. A C-47 at ~1800 units
of *altitude* is also some horizontal distance from the player, so its straight-line distance
to the eye quickly exceeds 2700 → it crosses `frustum[4]` (tr_main.c:794-808) and is hidden,
and `CG_FrustumCullSphere` (cg_view.c:784) drops the entity. Chutes at altitude hit the same
wall. Lowering the drop to ~750 keeps the slant range under 2700, which is why that "works".
This is a **distance-from-camera** clip, not an absolute Z ceiling — confirming it's the
far plane, not the sky.

---

## 3. Ranked options to raise the ceiling globally

### Option 1 (RECOMMENDED) — set `r_farplane` cvar in autoexec.cfg
- **What:** A non-zero `r_farplane` overrides the per-map worldspawn farplane in BOTH
  renderers (tr_main.c:773-775). One value, every map, no BSP edits.
- **How:** add to the mod's `maintt/autoexec.cfg` (already deployed):
  ```
  seta cheats 1          // CVAR_CHEAT gate; defaults to 1 already (cvar.c:1752)
  seta r_farplane 12000  // match the server's 12000-unit transmission window
  // optional, so the far horizon isn't a wall of fog:
  seta r_farplane_nofog 1
  ```
  `r_farplane` is `CVAR_CHEAT`; it is honored whenever `cheats`/`sv_cheats` is non-zero
  (cvar.c:653). Coop already runs with cheats on, so no engine change is needed. Verify in
  console with `r_farplane` after map load.
- **Trade-offs:** It is global and uniform, so it also lifts the fog/draw distance on every
  map. Setting it very high (or `r_farclip 0`) loses the atmospheric fog that some maps use
  for mood and can cost fps on open maps by drawing more geometry. 12000 matches the server
  cull so you never draw an entity the server didn't send. `r_farplane_nofog 1` keeps the
  extended clip but suppresses the fog recolor. Because it's a client cvar, each player's
  client must have it (ship it in the mod's autoexec, which you already do).

### Option 2 — per-map script override via `$world farplane`
- **What:** `farplane` is a runtime script setter on the world entity (worldspawn.cpp:172-207,
  table line 505/508). The world is targetnamed `"world"` (worldspawn.cpp:625), so script can
  raise it for just the maps that do a paradrop.
- **How:** in the map/coop script, before/at the drop:
  ```
  $world farplane 8000
  // (to restore the original look afterwards) $world farplane 2700
  ```
  This re-runs `UpdateFog()` → new `CS_FOGINFO` → clients pick up the larger value, which
  raises both the render far plane and `CG_FrustumCullSphere`.
- **Trade-offs:** Surgical (only the maps you touch, only while needed) and server-authoritative
  (no client cvar/cheat dependency, works for everyone). But it changes the fog horizon for
  that map while active, and you must script it per drop map (m4l3 etc.) and optionally revert.
  This is the most "correct"/portable approach if you don't want to rely on the cheat cvar.

### Option 3 — combine: script `farplane` + keep fog look
- Use Option 2's `$world farplane 8000` and also `$world farplane_cull 0` (worldspawn.cpp:153-162,
  SetFarPlane_Cull) so the far plane stops *culling* even though fog still renders — entities
  beyond the fog distance are kept. Or pair with `$world skybox_farplane` if a portal sky is used.
- **Trade-offs:** `farplane_cull 0` (maps to renderer `farplane_cull`, tr_main.c:811) means the
  6th frustum plane isn't added, so distant entities draw but may appear *through* heavy fog.
  Good when you want to keep the map's fog mood but still see the plane.

### Option 4 (NOT recommended) — edit each BSP worldspawn `farplane`
- Decompile/recompile or hex-patch the worldspawn `"farplane"` value in every `.bsp`.
- **Trade-offs:** Per-map, brittle, large binary edits, breaks pak integrity, exactly the
  "edit/recompile each .bsp" path you want to avoid. Listed only for completeness.

### Option 5 (NOT recommended) — engine patch
- Remove the `CVAR_CHEAT` flag from `r_farplane` (tr_init.c:1585 / :1526) or raise the
  sv_snapshot 12000 clamp. Unnecessary: cheats are already on in coop, and 12000 already
  exceeds what we need. Only consider if you ship a custom engine and want `r_farplane`
  usable without cheats.

---

## 4. Recommended approach for the coop mod

Primary: **Option 1** — add `seta r_farplane 12000` (and `seta r_farplane_nofog 1`) to the
already-deployed `maintt/autoexec.cfg`. It's one line, global across all 34 maps, needs no
BSP edits, and aligns the client draw distance with the server's existing 12000-unit
transmission window so high paradrops at 1800+ units render everywhere. Default `cheats`/
`sv_cheats` is `1`, so the CVAR_CHEAT gate is already satisfied.

Belt-and-suspenders / if you'd rather not depend on the cheat cvar: also (or instead) use
**Option 2** in the paradrop script — `$world farplane 8000` right before the drop on maps
that use it. This is server-side and unconditional. The two are complementary: the cvar is
the global baseline, the script call guarantees the specific drop maps regardless of any
client cvar state.

Do **not** raise it past ~12000 — beyond that the server (`sv_snapshot.c:748`) won't transmit
the entity anyway, so the client would clip nothing useful and you'd just pay fps for extra
world geometry and lose fog atmosphere.

### Quick verification plan
1. Set `r_farplane 12000` in console on m4l3, re-trigger the 1800-unit drop, confirm plane/
   chutes visible. 2. If fog horizon looks bad, add `r_farplane_nofog 1`. 3. Confirm fps on the
   most open map (e.g. m2l1 already uses 14500, so it's a good worst case).
