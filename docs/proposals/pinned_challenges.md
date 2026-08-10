# PROPOSAL — Pinned Challenges (5-slot tracker under Secondary Objectives)

Status: **PLANNED** — design only, no game files modified by this document.
Author pass: 2026-08-04. Every claim about existing behaviour carries a `file:line`.

> User statement of intent: *"let's build a pin system too, you can pin up to 5 challenges and
> they will appear under your secondary objectives in game with progress x/x and marked
> completed once done."*

---

## 0. TL;DR — the chosen architecture

| Decision | Choice | Why |
|---|---|---|
| Where it draws | **Extend `ui/coop_objectives.urc`** with a 6th block below the two Secondary Objective rows | "Under your secondary objectives" *is* that panel. The panel is client-side and 100% cvar-driven, so the server pushes text the same way it already pushes the side objectives (`objectives.scr:32-52`). |
| ihuddraw slots consumed | **ZERO** | The URC panel is not huddraw. `88-93` are *reserved but unused* for a possible future always-on variant (see §4). |
| Storage | 4th persistence channel next to the 3 that exist: cvar `coop_pins_<id>` + `coop_mod/save/pins_<id>.dat`, value `"cid|cid|cid|cid|cid"` | Byte-for-byte the shape of the existing `unlocks_` channel (`challenges.scr:531-539`). Loaded in the same place (`chal_ensure`). |
| Pin/unpin UX | **Click a row in the lobby's clickable Service Record panel** (primary) + a `,pn<NNN>` name-append bus index (fallback / future menu buttons) | The lobby cursor + click are already **server-side** player fields, and the rows are already hit-tested (`lobbyui.scr:162-195`). Zero new wire protocol for the primary path. |
| Update loop | 1 Hz per-player guarded singleton, signature-gated delta push | Copies `objectives.scr::coop_objPanel_monitor:499-513` exactly. Steady-state network cost when nothing changes: **zero**. |
| Engine change | **None** | `cg_servercmds_filter.cpp:138` whitelists every cvar whose name starts with `coop_`, so new `coop_cp*` cvars pass the client-side stufftext filter with no cgame rebuild. |

---

## 1. How the objectives HUD actually works (verified)

**It is not huddraw and it is not always on screen.** It is a client UI *hud menu*:

- `ui/coop_objectives.urc:6` — `menu "coop_objectives" 640 480 FROM_LEFT 0.25`
- `ui/coop_objectives.urc:7` — `align left centery` → the 640x480 box is left-anchored and
  **vertically centred on the physical screen** (`uiwidget.cpp:1461-1483`, `WA_LEFT|WA_CENTERY`).
- `ui/coop_objectives.urc:11` — `virtualres 0` → coordinates are **raw pixels, unscaled**
  (`uiwidget.cpp:1424-1429` sets `m_bVirtual` only when the arg is non-zero;
  `uiwidget.cpp:1125-1136` then falls through to the `uid.bHighResScaling` branch, which
  `cl_ui.cpp:4035` only enables **above** 1920x1080 — `maxWidthRes/maxHeightRes` at
  `cl_ui.cpp:147-148`). At 1080p and below the panel is a fixed 640x480 px rectangle.
- It is added/removed with `ui_addhud "coop_objectives"` / `ui_removehud`
  (`ui/coop_objectives/obj_add.cfg:1`, `obj_rem.cfg:2`) and toggled with the `o` key
  (`autoexec.cfg:928` → `bind o "vstr coop_obj"`).
- It is **force-closed on every (re)spawn**: `obj_reset.cfg:18` `ui_removehud` +
  `obj_reset.cfg:26` `set coop_objOpen "0"`, and `obj_reset.cfg` is exec'd per spawn from
  `global/objectives.scr:629`.
- While it is open, `coop_objOpen 1` (`obj_add.cfg:5`) tells the cgame to hold the whole HUD
  unfaded (`cg_drawtools.cpp:2060`).

### The Secondary Objectives block — the exact thing we sit under

`ui/coop_objectives.urc:1018-1138`, i.e. the last block before `end.` at `:1139`:

| Widget | rect | gating cvar |
|---|---|---|
| Header `"Secondary Objectives:"` | `10 366 640 16` (`:1029`) | `coop_so1d` |
| Row 1 grey plate | `10 386 550 20` (`:1042`) | `coop_so1d` |
| Row 1 checkbox | `10 386 24 16` (`:1051`), `filledbox.tga` / `emptybox.tga` | `coop_so1d` |
| Row 1 text (completed, 50% alpha) | `36 386 640 16` (`:1065`), `linkcvar coop_so1` | `coop_so1d` |
| Row 1 text (active, full alpha) | `36 386 640 16` (`:1079`), `linkcvar coop_so1` | `coop_so1a` |
| Row 2 | same at `y=406` (`:1093-1137`) | `coop_so2*` |

**Bottom of the existing content = y 426.** The 8 primary objectives occupy `y 20..364` at a
fixed 40px pitch (two lines each: `46/66 … 326/346`), so the layout below 366 is static
regardless of how many objectives the map actually uses.

The push mechanism is 4 unquoted `set`s per line, per player
(`coop_mod/objectives.scr:47-50`):

```
$player[local.p] stufftext ( "set coop_so" + local.so + "d " + local.dval )   // visible
$player[local.p] stufftext ( "set coop_so" + local.so + "a " + local.aval )   // active (white)
$player[local.p] stufftext ( "set coop_so" + local.so + "s " + local.sval )   // checkbox
$player[local.p] stufftext ( "set coop_so" + local.so + " "  + local.text )   // the text
```

Unquoted multi-word values are safe: `Cvar_Set_f` takes `Cmd_ArgsFrom(2)`
(`qcommon/cvar.c:953`), i.e. the whole remainder of the line. This also matches the bug-758
lesson (quoted stufftext was truncated on the wire).

### The script-drawn alternative, and why not to use it

`objectives.scr:307-535` (`coop_objPanel_refresh` / `coop_objPanel_monitor`) is an ihuddraw
re-implementation of the same panel on slots 156-215. It is **off by default**
(`autoexec.cfg:942` `seta coop_objPanel 0`) because it double-displayed with the URC menu
(`objectives.scr:514-517`). It draws with `ihuddraw_virtualsize … 1` — a **640x480 virtual
space scaled to the screen** — while the URC panel uses **raw unscaled pixels centred
vertically**. The two coordinate systems only coincide at exactly 640x480. Therefore:

> **An ihuddraw block cannot be reliably positioned "just below" the URC secondary
> objectives at arbitrary resolutions.** This is the single strongest argument for doing the
> pin block in the URC.

---

## 2. Challenge data, progress and persistence (verified)

`coop_mod/challenges.scr`, 2122 lines, header contract at `:1-19`.

- **Catalog**: `chal_def id cat title desc stat target reward` (`:455-471`) appends to parallel
  arrays `level.coop_chal_id/cat/title/desc/stat/target/reward[i]`, `i = file order`, count in
  `level.coop_chal_count`. 283 `chal_def` lines today. It also builds the per-stat reverse
  index `level.coop_chal_statIdx[stat][k]` (`:465-468`).
  **There is no cid → index reverse map.** This proposal adds one (§6.C).
- **Progress**: `self.flags["coop_chalP_" + cid]` (int) and `self.flags["coop_chalD_" + cid]`
  (1 = done). Written only through `chal_apply` (`:736-764`), which is fed only through
  `chal_bump` (`:712-730`). Target is `level.coop_chal_target[idx]` (`:748`).
- **Identity**: `self.flags["coop_chal_id"]` = the XP id (guid, else `"n_"+netname`)
  (`:504-519`).
- **Persistence — three parallel channels**, all loaded in `chal_ensure` and all with the
  identical "session cvar first, then file" shape:

  | Channel | cvar | file | format | site |
  |---|---|---|---|---|
  | progress | `coop_chal_<id>` | `coop_mod/save/chal_<id>.dat` | `cid:n\|cid:n\|…` | `:522-528`, write `:643-651` |
  | unlocks | `coop_unlocks_<id>` | `coop_mod/save/unlocks_<id>.dat` | `\|`-delimited ids | `:531-539` |
  | pending unlock names | `coop_pend_<id>` | `coop_mod/save/pend_<id>.dat` | `~`-delimited names | `:545-553` |

  A missing channel reads `""` and is treated as empty — **pre-feature saves need no
  migration** (`:543-544` states this explicitly). The pin channel inherits that property.
- **Flush**: `chal_autosave_loop` every 30 s (`:477-484`), plus `chal_grant` (`:776`) and
  `chal_mission_complete` (`:1446`). `chal_flush` (`:657-668`) walks `$player` and saves each.
- **The closest existing "show me my challenges" features**:
  - `chal_review` (`:1562-1607`) — console dump, grouped by category, `[X]`/`[ ]` +
    `(progress/target)`. Reached from name-append **bind index 34** (`variables.scr:168`
    `" ,ch"`, dispatch `player.scr:581`).
  - `chal_menu` / `chal_menu_draw` (`:1628-1856`) — the **in-game / lobby on-screen Service
    Record panel** on ihuddraw slots 150-174 + 196-249. This is what bind 34 actually opens
    today (`player.scr:581`); each press cycles a page, past-last closes. It already renders
    exactly the row content the pin block needs: `"[X]  "`/`"[  ]  "` + title (`:1781-1787`),
    a bar track/fill (`:1791-1809`) and `"p / t"` (`:1812-1818`).
- **Live refresh precedent**: `chal_menu_refresh` (`:1668-1680`) redraws the open page every
  0.5 s and self-stops on a page/token change. Note the in-file warning at `:1669-1672`
  (bug-750): a multi-line condition with a leading `&&` is a **parse killer for the whole
  file**. Keep every condition on one line.

---

## 3. Storage format (exact)

New, 4th channel — identical plumbing to `unlocks_`:

```
cvar :  coop_pins_<id>                       (server cvar, survives map transitions)
file :  coop_mod/save/pins_<id>.dat          (survives server restart)
value:  "<cid>|<cid>|<cid>|<cid>|<cid>"      1..5 entries, no trailing separator, "" = none
```

Runtime, per player:

```
self.flags["coop_chalPins"]   = the raw "|"-delimited string (authoritative, what gets saved)
self.coop_pinCid[0..4]        = parsed cids (entity-scoped array, 0-indexed)
self.coop_pinN                = how many are set (0..5)
self.coop_pinSig              = last-pushed signature string (delta gate, see §5)
self.coop_pinRun              = 1 while the monitor loop owns this player (singleton guard)
```

**Why store the cid string, not the catalog index.** The catalog index is file order
(`gen_service_record.py:49` `idx={r[0]:i …}` and `challenges.scr:456`). Inserting a
`chal_def` line in the middle re-points every index after it. A pin stored as an index would
silently become a *different challenge* after a content update. The click wire carries the
index (it is compact), but the server resolves index → cid **at click time**, inside the same
session as the catalog it came from, and stores the cid. Indices never persist.

**Cap.** `coop_pinMax` (default 5, clamp 1..5) — hard-limited by the URC having exactly five
rows. Pinning a 6th with the cap reached is refused with an `iprint`, not silently dropped.

---

## 4. HUD slots — cross-checked against `_research/hud_slot_map.md`

**The recommended design consumes no ihuddraw slots at all.** The pin block is URC widgets
driven by `coop_cp*` cvars; the lobby pin marker is drawn *inside the existing row string* on
slot `156+r`, which `chal_menu_draw` already owns (`challenges.scr:1758`).

If the always-on (no `o` keypress) variant is ever built as a follow-up, it must claim a block
of its own. **Claim `88-93`** (header + 5 rows) out of the free range `88-99`, which
`hud_slot_map.md:40` lists as free and `:46` names as "next feature's exclusive block".

Reasoning for `88-93` over the other free ranges:

- `88-99` is **below 100**, so it follows the activity HUD fade
  (`cg_drawtools.cpp:650-656`: `if (i < 100) vFadedCol[3] *= s_hudFadeAlpha;`). An always-on
  progress tracker *should* fade with the rest of the HUD; a persistent-UI block would not.
- `135-149` is explicitly reserved for "mid overlays (fade-exempt >=100)"
  (`hud_slot_map.md:47`) — wrong fade class for this feature. Do **not** take it.
- `156-249` is already double-booked mission-time (objectives panel) vs menu/lobby-time
  (challenge SR panel + bars) — `hud_slot_map.md:33-35, :42` forbids a third tenant.
- `76-78` and `84-87` belong to challenges.scr already (toast / progress popup,
  `challenges.scr:1504-1526`, `:1308-1339`) and **can co-display** with a pin block, so they
  must not be shared — exactly the bug-553 rule at `hud_slot_map.md:9-13`.

Action either way: add the row to `hud_slot_map.md` (§6.I) so `88-93` cannot be claimed twice.

---

## 5. The HUD block — exact geometry and cvars

### 5.1 Cvars (6 per row + 1 header)

| cvar | meaning | changes |
|---|---|---|
| `coop_cphd` | 1 = draw the `"Pinned Challenges:"` header | on pin-set change only |
| `coop_cp<N>` | row text = the challenge title, N = 1..5 | on pin-set change only |
| `coop_cp<N>n` | the count, `"47/250"` | **every progress change** |
| `coop_cp<N>d` | 1 = row visible (plate, checkbox, dim labels) | on pin-set change only |
| `coop_cp<N>s` | checkbox: 1 = completed | once, at completion |
| `coop_cp<N>a` | 1 = active (full-alpha labels drawn on top) | once, at completion |

Splitting the title from the count is deliberate: the title is static for the life of a pin,
so the per-tick delta push is **one** `set` per row that actually moved.

The `d`/`a` pair reproduces the side-objective trick verbatim (`coop_objectives.urc:1060-1087`):
a 50%-alpha "completed" label always drawn while `d`, plus a full-alpha "active" label gated on
`a` drawn over it. Completion = clear `a`, set `s` → the row dims and the checkbox fills.

### 5.2 Geometry (append before `end.` at `ui/coop_objectives.urc:1139`)

Pitch 16 with `courier-16`, matching the panel's existing font:

| Element | rect |
|---|---|
| Header `"Pinned Challenges:"` | `10 426 640 16` |
| Row N plate (Widget, `bgcolor 0.2 0.2 0.2 0.8`) | `10 <y> 550 16` |
| Row N checkbox | `10 <y> 24 16` |
| Row N title label (dim + active pair) | `36 <y> 400 16` |
| Row N count label (dim + active pair) | `440 <y> 120 16` |

with `y = 442, 458, 474, 490, 506` for N = 1..5.

### 5.3 The clipping constraint — `noparentclip` is REQUIRED

Widgets are scissored to the parent's clipped frame unless `WF_DIRECTED` is set
(`uiwidget.cpp:872-906` intersects the child frame with the parent's; `set2D()` at `:917-938`
issues the `Rend_Scissor`). The menu is declared 640x480 (`coop_objectives.urc:6`), so rows at
y 490/506 would be **silently scissored away**.

`noparentclip` (event token registered at `uiwidget.cpp:408-410`, handler `:1496-1498`) sets
exactly and only `WF_DIRECTED`, whose sole use in uilib is that clipping test — so it is a
safe, targeted opt-out. **Every widget in the pin block gets `noparentclip`.**

Do *not* instead grow the menu to `640 560`: `align left centery` would shift the whole
existing objectives panel up by 40 px.

**Resolution caveat.** With `virtualres 0` the panel is a 640x480 px box centred vertically, so
the headroom below local y 480 is `(screenH - 480) / 2`: 300 px at 1080p, 120 px at 720p, 60 px
at 800x600, **0 px at exactly 640x480**. The block needs 42 px below 480 → fine at 800x600 and
up, the last two rows are off-screen at 640x480. Mitigation if that matters: `coop_pinMax 3`.

---

## 6. Pin / unpin UX

### Recommended: click the row in the lobby's Service Record panel

`lobbyui.scr` already provides everything:

- the engine turns the frozen lobby player's mouse into **server-side** fields
  `self.coop_lobbyCurX / coop_lobbyCurY` (virtual 640x480) and `self.coop_lobbyClick`
  (`lobbyui.scr:1-14`), enabled by `coop_lobbycursor 1` (`:25`);
- `lobbyui_loop` (`:85-203`) already draws the cursor, dispatches button clicks (`:152-158`)
  and **already hit-tests each challenge row** for the hover tooltip (`:162-195`, row rect
  `y = 122 + r*13`, x from 158);
- the panel it drives is `chal_menu_draw` (`challenges.scr:1688`), which already stores
  per-row metadata on the player (`:1773-1774`).

So a pin toggle is: one more hit-test result reused in the click branch, and one call. **No new
wire protocol, no new cvars on the client, no cfg generation, no disconnected-state ambiguity —
the server already knows which row was clicked because it drew it.**

Row feedback is free: prefix the row string at `challenges.scr:1783/:1786` with a pin marker
(e.g. `"* "`), and widen `coop_uiRowNameEnd` (`:1774`) accordingly.

### Fallback / future: name-append bus index 47 = `" ,pn"`, data = 3-digit catalog index

Add `local.command["47"]=" ,pn"` to `variables.scr:180` and the matching dispatch at
`player.scr:598`. Data is the 3-digit global catalog index; the server resolves it to a cid
immediately (§3). This is the *established* menu→server recipe: `ui/loadout/open.cfg:3`
`append name ,w0o`, and `ui/loadout/w01_s1.cfg:5-7`
(`seta coop_loA1 "append name ,w101"` then `vstr coop_loA1`). `append` is a real client command
(`qcommon/cvar.c:1780` `Cvar_Append_f`) and is whitelisted for server stufftext
(`cg_servercmds_filter.cpp:281`).

With that bus index in place, `docs/tools/gen_service_record.py` can later emit a per-row PIN
Button (`stuffcommand "append name ,pn%03d"`) with no further server work — see §7.I.

### Options considered and rejected

| Option | Verdict |
|---|---|
| Clickable pin toggles on the **existing** `ui/coop_sr.urc` rows | **Rejected as the primary path.** The rows are *baked into page textures* (`gen_service_record.py:120-136` draws title/desc/track into `coop_sr_p<N>.tga`); only the bar (`:159-161`) and count (`:163-165`) are live Labels. Buttons *could* be added (the tab buttons at `:172-186` prove the pattern) but the menu is reached from `ui/multiplayer.urc:194` — i.e. **usually while disconnected**, where `append name` reaches no server. Making that work needs client-side slot bookkeeping in `.cfg` files (which have no logic) plus a spawn-time resend volley (`loadoutpick.scr:229-231`). Viable as phase 2, wrong as phase 1. |
| Pin from the **in-game** panel (bind 34) | **Rejected.** In-game the panel is keyboard-cycled with no cursor and no row highlight — there is nothing to point at. Enabling `coop_lobbycursor` mid-mission would eat mouse-look while the player is still shootable. |
| A console command `coop_chal_pin <id>` | **Rejected as the user-facing path** (remote clients cannot run server script commands; it would have to be a bind emitting `,pn`). Kept only as the debug/testing entry via the bus above. |
| A brand-new dedicated menu page | **Rejected.** More surface area than the feature needs, and it duplicates the Service Record the player already reads. |

---

## 7. Update loop

Model it on `objectives.scr::coop_objPanel_monitor:499-513` — a guarded per-player singleton
with a **signature gate**, so a frame where nothing changed costs zero network.

```
chal_pin_monitor local.player:{
    if( local.player == NULL ){ end }
    if( local.player.coop_pinRun == 1 ){ end }          // singleton per player
    local.player.coop_pinRun = 1
    local.player.coop_pinSig = ""                        // "" => first tick pushes everything
    while( local.player != NULL && local.player.flags["coop_isActive"] == 1 ){
        waitthread chal_pin_tick local.player
        wait 1
    }
    if( local.player != NULL ){ local.player.coop_pinRun = NIL }
}end
```

`chal_pin_tick` builds `sig = cid1 + ":" + p1 + ":" + d1 + "|" + …` across the ≤5 pins, compares
to `coop_pinSig`, and on a difference calls `chal_pin_push` — which pushes only the fields whose
value actually changed (it keeps the last-pushed count string per row in
`self.coop_pinLastN[i]`).

Cost:

| Event | stufftexts |
|---|---|
| idle second | **0** |
| a pinned counter ticks | 1 per row that moved (`coop_cp<N>n`) |
| a pin completes | +2 (`coop_cp<N>s`, `coop_cp<N>a`) |
| pin set changed / forced re-push | ≤ 31 (`coop_cphd` + 6 × 5) |

Keep this in view against **bug-670** (`challenges.scr:569-579`): a join-time
`chal_ui_export` firing ~373 reliable commands while the client was still loading overflowed
`MAX_RELIABLE_COMMANDS = 512` and self-dropped the client. Rules inherited from that fix:
**never push at connect**, never push more than once a second, and let the delayed re-push
(below) cover the spawn window.

Reading progress is free — it is `local.player.flags["coop_chalP_" + cid]`, an in-memory
dictionary read (`challenges.scr:1761`). No file or cvar I/O in the loop.

Where it is started: `player.scr::manageAliveSpawning`, adjacent to the two objective threads
at `player.scr:1134-1136`. The singleton guard means later respawns are no-ops; the forced
re-push comes from the reset hook instead.

---

## 8. Multiplayer correctness

- **Pins are per player and the transport is already per player.** The URC path is
  `local.player stufftext …` — one entity, one client (the pattern
  `coop_obj_push_one` uses at `objectives.scr:74-77`).
- If the always-on ihuddraw variant is ever built: `ihuddraw_*` takes a player argument and
  resolves to a single client — `ScriptThread::EventIHudDrawString` calls
  `iHudDrawString(player->edict - g_entities, index, …)` (`fgame/scriptthread.cpp:5410`), and
  `iHudDrawString` does `gi.MSG_SetClient(cl_num)` before the CGM
  (`fgame/huddraw.cpp:334-339`). Contrast the non-`i` `HudDraw*` family, which does
  `gi.SetBroadcastAll()` (`huddraw.cpp:44`) — **using the wrong family broadcasts one player's
  pins to everybody.**
- **The stale-slot leak.** huddraw state is per client and *persists until overwritten* — it is
  not cleared on death, spectate or map change. That is why `player.scr:810-817` explicitly
  zeroes slots 50-53 when a player dies/spectates, and why `coop_objPanel_monitor` zeroes
  156-215 on exit (`objectives.scr:527-534`). Any ihuddraw variant of this feature must do the
  same for `88-93`. **The recommended URC design is immune** — its state is client cvars, and
  a disconnecting player takes them with him.
- **The cvar-blanking trap (this one WILL bite).** `obj_setup.cfg` re-seeds the whole
  `coop_so*` family to `""`/`0` (`obj_setup.cfg:48-55`) and `obj_reset.cfg` never restores
  them — that is precisely the defect `coop_obj_repush_player` /
  `coop_obj_player_watcher` exist to paper over (`objectives.scr:82-137`), including the
  `wait 1` at `:135` that lets the spawn-time reset finish first so the re-push wins the race.
  The pin block inherits the same exposure and needs the same treatment: seed the cvars in
  `obj_setup.cfg`, and re-push after every (re)spawn and late join from
  `global/objectives.scr:741`, right beside the existing `coop_obj_repush_player` call.
- `$player` is 1-indexed and becomes an array with 2+ connected (TRAPS T5). All loops here
  follow the existing `while( local.i <= $player.size )` shape (`challenges.scr:659-667`), and
  the per-player loop never indexes `$player` at all — it holds the entity.

---

## 9. Per-file implementation checklist

### A. `hzm-mohaa-coop-mod/ui/coop_objectives.urc` — **insert before `end.` at :1139**

One `//PINNED CHALLENGES` comment block, then 31 resources: 1 header Label + 5 × (Widget plate,
CheckBox, 2 title Labels, 2 count Labels). Geometry per §5.2. Every resource carries:

```
borderstyle "NONE"
font courier-16
textalign left
noparentclip
enabledcvar "coop_cp<N>d"        (or coop_cp<N>a for the active-pair labels, coop_cphd for the header)
linkcvar "coop_cp<N>"            (title labels) / "coop_cp<N>n" (count labels) / "coop_cp<N>s" (checkbox)
```

Checkbox shaders copy `:1056-1057`: `checked_shader "textures/OBJECTIVES/filledbox.tga"`,
`unchecked_shader "textures/OBJECTIVES/emptybox.tga"`.

### B. `hzm-mohaa-coop-mod/ui/coop_objectives/obj_setup.cfg` — **insert after :55**

Seed the family so it always exists and starts hidden (mirrors the `coop_so` seeds at
`:48-55`):

```
seta coop_cphd "0";
seta coop_cp1 "";  seta coop_cp1n "";  seta coop_cp1d "0";  seta coop_cp1s "0";  seta coop_cp1a "0";
…through coop_cp5…
```

### C. `hzm-mohaa-coop-mod/coop_mod/challenges.scr`

| # | Where | What |
|---|---|---|
| C1 | `chal_def`, after `:463` | `level.coop_chal_idx[local.id] = local.i` — the missing cid → index reverse map. One line, no behaviour change, makes every lookup below O(1). |
| C2 | `chal_ensure`, after the pend block ends at `:553` | Load the 4th channel: `coop_pins_<id>` cvar, else `coop_mod/save/pins_<id>.dat`, else `""` → `flags["coop_chalPins"]`, then `waitthread chal_pin_parse local.player`. Must sit **before** the done-flag pass at `:556` so a pinned-and-already-complete row renders correctly on the first push. |
| C3 | new, after `chal_pin_parse` | `chal_pin_parse local.player` — walk the `"\|"`-delimited string into `coop_pinCid[0..4]` / `coop_pinN`, dropping cids that are not in `level.coop_chal_idx` (content removed between sessions). Copy the character-walk shape of `chal_deserialize:586-616`; GameScript has no split. |
| C4 | new | `chal_pin_save local.player` — rebuild the string from `coop_pinCid`, `setcvar ("coop_pins_"+id)`, `fs_write_content ("coop_mod/save/pins_"+id+".dat")`. Mirrors `chal_save_player:643-651`. |
| C5 | new | `chal_pin_isPinned local.player local.cid` → 0/1; `chal_pin_toggle local.player local.cid` → add (respecting `coop_pinMax`, `iprint` on refusal) or remove + compact, then `chal_pin_save`, then force `coop_pinSig = ""` so the next tick does a full push. |
| C6 | new | `chal_pin_bus local.player local.data` — the `,pn` entry point: `int(local.data)` → index, bounds-check against `level.coop_chal_count`, map to cid, call `chal_pin_toggle`. |
| C7 | new | `chal_pin_tick` / `chal_pin_push` / `chal_pin_pushOne` / `chal_pin_clear` / `chal_pin_monitor` / `chal_pin_repush_player` per §7. `chal_pin_repush_player` = `wait 1` then force `coop_pinSig = ""` (same delay rationale as `coop_obj_repush_delayed:134-137`). |
| C8 | `chal_menu_draw`, at `:1773-1774` | Add `local.player.coop_uiRowCid[local.r] = local.cid` so the lobby click can resolve a row → cid. Prefix the row string at `:1783`/`:1786` with a pin marker when pinned, and widen the `coop_uiRowNameEnd` estimate at `:1774` to match. |
| C9 | `chal_apply`, after the done branch at `:760-763` | Optional: if the completed cid is pinned, `local.player.coop_pinSig = ""` so the row flips to completed within the same second rather than the next tick. |

### D. `hzm-mohaa-coop-mod/coop_mod/lobbyui.scr`

Hoist the row hit-test out of the tooltip block (`:162-195`) into a `local.rowHover` computed
**before** the click handler at `:152`, then extend the click branch:

```
if( self.coop_lobbyClick == 1 ){
    self.coop_lobbyClick = 0
    if( local.hover >= 0 ){ … existing button dispatch … }
    else if( local.rowHover >= 0 && self.coop_uiChalPage != NIL && self.coop_uiChalPage > 0 ){
        self playsound coop_ui_click
        waitthread coop_mod/challenges.scr::chal_pin_toggle self ( self.coop_uiRowCid[local.rowHover] )
        waitthread coop_mod/challenges.scr::chal_menu_draw self self.coop_uiChalPage
    }
}
```

Use the full row width for the pin click (x 158..470), not the tooltip's title-only span — the
tooltip stays hover-only, so the two do not fight.

Also add a PIN hint to the lobby button row (`lobbyui_dispatch:222-225` builds
`< PREV / CLOSE / NEXT >`); the footer slot 174 is already blanked in the clickable view
(`:220-221`), so the hint belongs in the panel subtitle at `challenges.scr:1731-1741`.

### E. `hzm-mohaa-coop-mod/coop_mod/player.scr`

| # | Where | What |
|---|---|---|
| E1 | `manageAliveSpawning`, after `:1136` | `thread coop_mod/challenges.scr::chal_pin_monitor local.player` — next to the two objective threads it belongs with. |
| E2 | `playerNameCommand`, after `:598` (index 46) | `else if(local.arrayIndex==47){ thread coop_mod/challenges.scr::chal_pin_bus local.player local.dataExtract }` |

### F. `hzm-mohaa-coop-mod/coop_mod/variables.scr`

`getNameAppendCommands`, after `:180`: `local.command["47"]=" ,pn"  //[303] challenge pin toggle (data: 3-digit catalog index)`.
**This table and the `player.scr` dispatch chain must be edited in the same commit** — an index
present in one and not the other silently dispatches the wrong action.

### G. `hzm-mohaa-coop-mod/global/objectives.scr`

`coop_objectivesResetForPlayer`, after the existing side-objective re-push at `:741`:

```
if(local.entity != NULL){
    waitthread coop_mod/challenges.scr::chal_pin_repush_player local.entity
}
```

This is the (re)spawn + late-join safety net; it is the same hook that already repairs the
`coop_so*` family.

### H. `hzm-mohaa-coop-mod/autoexec.cfg` or `coop_defaults.cfg`

`coop_pinMax` default 5. Put it in **`coop_defaults.cfg`**, not `autoexec.cfg` — per
SOURCE_OF_TRUTH §4, `autoexec.cfg` runs *after* the saved player config and would wipe a menu
change every launch. (`coop_challenges`, the master gate, self-seeds at `challenges.scr:30`;
`chal_pin_*` must respect `level.coop_chal_enabled` the same way every other entry point does.)

### I. `docs/tools/gen_service_record.py` — phase 2, optional

After the count Label at `:163-165`, emit a per-row PIN Button gated by the same
`enabledcvar "coop_srP<pi>"`, with `stuffcommand "append name ,pn%03d" % gi`. `gi` is already
in scope (`:157`). Requires nothing new server-side once §9.E2/§9.F land. Note the file writes
both `ui/coop_sr.urc` **and** all 19 `textures/mohmenu/coop_sr_p*.tga` page textures (`:189-190`)
— it is a full regeneration, so leave the baked rows alone and only add the button geometry.

### J. `hzm-mohaa-coop-mod/_research/hud_slot_map.md`

Add a row: pinned challenges = **0 ihuddraw slots** (URC-driven), with `88-93` **reserved** for
a possible always-on variant, and remove `88-93` from the "Free ranges" line at `:40` /
"Reserved" list at `:46`. Rule 4 of that file ("Update this table when you claim slots") makes
this mandatory even though the count is currently zero — the point is to stop a future feature
from taking the reservation.

---

## 10. Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | **`noparentclip` has no precedent anywhere in the mod's 101 `.urc` files** (verified: zero occurrences under `ui/`). If the token behaves differently than `uiwidget.cpp:1496-1498` reads, rows 3-5 vanish with no error. | **HIGH** — this is the single biggest unknown | Build the block **rows-first**: ship rows 1-2 (y 442/458, inside the 480 box, no clipping question) and confirm on screen; only then add 3-5 with `noparentclip`. If it fails, fall back to `coop_pinMax 2`… or restructure to a 2-column 3+2 layout inside the box. |
| R2 | Reliable-command flood on join/spawn → client self-drop. This is bug-670 (`challenges.scr:569-579`), which cost a "Server disconnected for unknown reason" on every campaign start. | HIGH | 1 Hz cap, signature gate, delta push, **never at connect**, spawn re-push delayed 1 s via `chal_pin_repush_player`. Worst case is 31 commands, ~8% of the 512 ring. |
| R3 | Spawn-time `obj_setup.cfg`/`obj_reset.cfg` blanking the cvars → block goes blank after a respawn, exactly like the original side-objective bug (`objectives.scr:82-107`). | HIGH (near-certain if the hook is skipped) | §9.G hook + `coop_pinSig = ""` forcing a full push. |
| R4 | Catalog index drift between the wire token / baked SR menu and the runtime catalog. | MEDIUM | Indices are resolved to cids at click time and never persisted (§3). `gen_service_record.py` and `challenges.scr` must be regenerated together — that coupling already exists today for the bars (`gen_service_record.py:46-49`). |
| R5 | A challenge title containing `;` or `"` would break the unquoted `set` on the wire. | LOW today | Verified: **none** of the 283 `chal_def` titles contain `; " $ \` and the longest is 33 chars. Add a guard in `chal_pin_pushOne` that refuses a title containing `;` rather than corrupting the client's console. Keep pushes **unquoted** (bug-758). |
| R6 | Editing `variables.scr` + `player.scr` out of lockstep → wrong bus dispatch, silently. | MEDIUM | Same commit; the `println ("^~^~^ NAMECMD: dispatch index …")` at `player.scr:537` makes it verifiable from the log in one press. |
| R7 | Parse killers taking the **whole file** down (challenges.scr is 2122 lines and carries the whole system). Multi-line conditions with a leading `&&` are the specific one this file has already hit — bug-750, `challenges.scr:1669-1672`. Also bare `(-1)`, em-dash, BOM. | HIGH impact / low probability | Conditions on one line; `developer 1` (mandatory — script errors are developer-gated, SOURCE_OF_TRUTH §2.4); depth-scan the file rather than counting braces (bug-239). |
| R8 | 640x480 players lose rows 4-5 to the physical screen edge (§5.3). | LOW | `coop_pinMax`. Document in `hzm_cvars.txt`. |
| R9 | Lobby-only pinning if phase 2 (§9.I) is skipped — a player who never sees a lobby cannot pin. | MEDIUM (UX) | Ship the `,pn` bus (§9.E2/F) in phase 1 even without the buttons; it makes phase 2 a pure UI change and gives testing an entry point immediately. |
| R10 | `chal_menu_draw` is already paced with `waitframe` every 4 rows to stay inside one frame's CGM budget (`challenges.scr:1747-1749, :1821-1829`). Adding a pin marker per row does not add elements, but adding a *column* would. | LOW | Keep the marker inside the existing row string on slot `156+r`. Do not add a per-row element. |

---

## 11. Verification plan

`developer 1` first — script `println` **and** script compile errors are both developer-gated
(three early-returns at `fgame/scriptthread.cpp:2858/:2869/:2883`); a parse error is otherwise
completely silent (bug-911).

1. **Compile**: load any coop map, confirm no `Script Error` in
   `%APPDATA%\openmohaa\maintt\qconsole.log`, and confirm the challenge system still boots
   (`chal_init` runs from `main.scr:106`).
2. **Persistence**: pin 2, check `coop_mod/save/pins_<id>.dat` contains the two cids; change map
   via `stuffsrv "map <name>"`; confirm the pins are still drawn (cvar channel) — then restart
   the server and confirm again (file channel).
3. **Geometry**: press `o`, screenshot at 1920x1080, 1280x720 and 800x600. Row 5 must be fully
   visible in all three. This is the R1 gate.
4. **Respawn**: die and respawn with the panel open; press `o`; the block must repopulate within
   ~2 s (R3).
5. **Multiplayer**: two clients, different pin sets, confirm neither sees the other's rows
   (§8) — the `$player`-array storm class (TRAPS T5) only appears at 2+ connected.
6. **Wire**: with `coop_pinMax 5` and 5 kill-counter challenges pinned, watch a firefight and
   confirm the per-second push count stays ≤ 5 (R2). Instrument with a rate-limited `println`
   behind `level.cMTE_coop_challenges` rather than shipping a debug print to players.
