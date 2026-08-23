# HZM Coop Menu - Mission List Additions

Date: 2026-06-23
Scope: menu/UI source only, under C:\mohaa-coop-dev\hzm-mohaa-coop-mod. No pk3 rebuild,
no deploy, no game launch. Staged edits take effect at the next coordinated rebuild.

## 1. Menu file(s) and the mission-list mechanism

The coop server-start / mission-select screen is defined by:

- `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\ui\coop_start.urc`
  The screen itself (server name, password, max players, friendly fire, dedicated,
  LMS, health fields). It is opened from the multiplayer/host flow.

- `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\ui\coop_maps.inc` (included at
  coop_start.urc:330)
  Defines 10 REUSABLE map-thumbnail buttons named `coop_startMap1` .. `coop_startMap10`
  in a 5-wide x 2-row grid. These are generic slots, NOT per-map; they are
  reconfigured at runtime per selected mission.

### The two-level mission list mechanism

Level A - the mission dropdown (the master list), coop_start.urc:150-176:
A single `PulldownMenuContainer` named `coop_missionNameSel`. Each mission is one
`addpopup` line whose command execs a per-mission cfg, e.g.:

    addpopup "MENU" "Allied Assault: 1 Lighting the Torch" command "exec ui/coop_start/m1.cfg"

Existing entries (before this change): m0 (Training/Secret), m1-m6 (Allied Assault),
e1/e2/e3 (Breakthrough), t1/t2 (Spearhead).

Level B - per-mission cfg files, `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\ui\coop_start\*.cfg`:
Each cfg uses `globalwidgetcommand` to repaint the 10 shared slot buttons for that
mission. Pattern per slot:

    globalwidgetcommand coop_startMapN shader textures/mohmenu/dmloading/<mapname>
    globalwidgetcommand coop_startMapN stuffcommand "set ui_dmmap <mapname>"

Unused slots are blanked with shader `menu_button_trans` and an empty stuffcommand.
Each cfg also runs `exec ui/coop_start/disableInfo.cfg` (hides the HZM logo + the
"1.Select a Mission" hint) and sets the mission title label:

    globalwidgetcommand coop_missionName title "<mission name>"

### How a launch happens end to end

1. Player picks a mission in the dropdown -> execs `ui/coop_start/<id>.cfg` ->
   repaints the 10 slot buttons.
2. Player clicks a map thumbnail -> the slot button's stuffcommand runs
   `set ui_dmmap <mapname>`. (The selected map name also shows in the Field linked
   to `ui_dmmap`, coop_start.urc:180-192.)
3. Player clicks Apply (coop_start.urc:347-361) ->
   `stuffcommand "wait 250;exec coop_mod/start_server.cfg"`.
4. `coop_mod/start_server.cfg` sets the coop server cvars (g_gametype 2, maxentities
   2048, healrate, etc.) and ends with `ui_startdmmap 2`, which loads `ui_dmmap`.

Localized display strings: none. The `addpopup` label text and the cfg
`coop_missionName title` are literal inline strings (no .str/localization indirection).

## 2. What was added

### a) New per-mission cfg: ui/coop_start/t3.cfg  (NEW FILE)
Spearhead Mission 3 ("The Great Escape"). Mirrors the exact format of t1.cfg/t2.cfg:
- coop_startMap1 -> t3l1 (title "t3l1 Barracks", shader dmloading/t3l1, set ui_dmmap t3l1)
- coop_startMap2 -> t3l2 (title "t3l2 Sub Pens", shader dmloading/t3l2, set ui_dmmap t3l2)
- slots 3-10 blanked (menu_button_trans).
Both t3 maps carry the coop hook, so both are enabled.

### b) coop_start.urc - one new dropdown entry (after the t2 line, ~:175)

    addpopup "MENU" "Spearhead: 3 The Great Escape" command "exec ui/coop_start/t3.cfg"

No other edits. The e3/t1/t2 entries and their cfgs already existed from the prior
phase and were left unchanged.

Encoding/format hygiene: t3.cfg is ASCII, no BOM (starts with `2f 2f` = "//"), LF
line endings, no non-ASCII chars - matching t1.cfg/t2.cfg exactly. The urc edit is a
single surgical addpopup line matching surrounding syntax.

## 3. Template for adding future missions

Two steps:

Step 1 - create `ui/coop_start/<id>.cfg` (ASCII, no BOM, LF):

    exec ui/coop_start/disableInfo.cfg
    globalwidgetcommand coop_missionName title "<Mission display name>"
    globalwidgetcommand coop_startMap1 title "<label>"
    globalwidgetcommand coop_startMap1 shader textures/mohmenu/dmloading/<mapname>
    globalwidgetcommand coop_startMap1 stuffcommand "set ui_dmmap <mapname>"
    ... repeat for coop_startMap2 .. up to coop_startMap10 ...
    (blank any unused slot:)
    globalwidgetcommand coop_startMapN shader menu_button_trans
    globalwidgetcommand coop_startMapN stuffcommand ""

To show a map but make it NOT launchable (no coop yet), set a title, use the
`menu_button_trans` shader, and leave stuffcommand empty - see t1.cfg/t2.cfg.

Step 2 - add one line to the PulldownMenuContainer in coop_start.urc:

    addpopup "MENU" "<Mission display name>" command "exec ui/coop_start/<id>.cfg"

Only 10 map slots exist; a mission needing more than 10 maps would require adding
buttons to coop_maps.inc.

## 4. t-series (Spearhead) target constraint and how it was handled

Confirmed via memory/pak_target_mapping.md + level_scripts_sh_bt.md:
- e-series BSPs live in `maintt\` (Breakthrough pak).
- t-series BSPs live in `mainta\` (Spearhead pak) - the counterintuitive mapping.
- The CURRENTLY RUNNING Phase 2 launch is the Breakthrough profile
  (com_target_game=2, mounts only `main\` + `maintt\`). `mainta\` is NOT mounted.

Consequence: e3l2/e3l3/e3l4 load fine under the existing Breakthrough launch. The
t-series (t1/t2/t3) CANNOT load under that launch - their BSPs are in the unmounted
mainta. They require a separate SPEARHEAD launch profile (com_target_game=1, mounts
main+mainta).

How handled in the menu:
- `coop_mod/start_server.cfg` does NOT set com_target_game; it only does
  `ui_startdmmap 2`. So the menu CANNOT switch the player from a Breakthrough launch
  to a Spearhead one - that is a launch-profile decision made before the engine
  starts, not something a menu cfg can flip at runtime.
- The Spearhead missions are kept as clearly-labeled separate dropdown entries
  ("Spearhead: 1/2/3 ..."), consistent with the existing t1/t2 entries. They are
  selectable in the menu, but will only actually load when the game was started under
  a Spearhead launch profile. This matches the existing convention (the prior phase
  already added t1/t2 the same way); this change extends it with t3.

BLOCKER / FLAG: There is no menu-level mechanism to guarantee the correct launch
profile. Selecting a Spearhead mission from a Breakthrough launch will fail to load
the BSP (mainta not mounted). A Spearhead launch profile + its own maptest run is
required to actually host t-series (out of scope for menu edits; tracked in
pak_target_mapping.md).

## 5. Map set confirmation and coop-script status of added entries

Confirmed exact sets by listing scripts in the mod:
- Breakthrough mission 3: e3l1, e3l2, e3l3, e3l4 (all four).
- Spearhead: t1l1, t1l2, t1l3, t2l1, t2l2, t2l3, t2l4, t3l1, t3l2 (nine).

Coop-hook status (grep for `waitthread coop_mod/main.scr::main` in
hzm-mohaa-coop-mod\maps):
- e3l1, e3l2, e3l3, e3l4 - HAVE the coop hook. (e3 dropdown entry + e3.cfg already
  existed; left as-is.)
- t1l1, t1l2, t1l3 - all HAVE the coop hook.
- t2l1, t2l2, t2l3, t2l4 - all HAVE the coop hook.
- t3l1, t3l2 - both HAVE the coop hook. (Newly exposed via t3.cfg this change.)

STALE-FLAG NOTE (pre-existing cfgs, not changed by me): t1.cfg disables t1l1 and
t2.cfg disables t2l2/t2l4 with "(not coop yet)" labels. As of now those three map
scripts DO contain the coop hook - the menu flags are conservative/stale relative to
the separate map-build task. They were left untouched per "minimal surgical edits";
they can be enabled (give them a dmloading shader + `set ui_dmmap <map>` stuffcommand)
once the map-build task confirms those maps are coop-complete.

Entries added THIS change (t3l1, t3l2): both have the coop hook present. Whether their
coop integration is fully finished is owned by the separate map-build task; if t3 work
is still in progress, treat t3.cfg as menu infrastructure staged ahead of completion.

## Files changed
- C:\mohaa-coop-dev\hzm-mohaa-coop-mod\ui\coop_start\t3.cfg  (NEW)
- C:\mohaa-coop-dev\hzm-mohaa-coop-mod\ui\coop_start.urc     (+1 addpopup line)
