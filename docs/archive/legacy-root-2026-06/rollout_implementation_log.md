# HZM Coop Trilogy Rollout — Implementation Log

Session start: 2026-06-22. Implementing per the two blueprint plans
(feature_scaleout_plan.md, coop_base_functionality_plan.md).

Mod tree: C:\mohaa-coop-dev\hzm-mohaa-coop-mod
Baseline (must remain byte-identical behavior): AA map m4l3.

PARSE-KILLER discipline: after every .scr edit, byte-verify ASCII-only + scan for
BOM / em-dash / smart quotes / bare-negative-in-parens / spawn-keyvalue / unknown commands.

## Pre-edit findings
- officer_positions.scr::getAnchor is a flat if/else-if chain keyed on level.coop_mapname,
  returns coop_officer_anchor; sets z_ref/z_tol/verify_ingame. 26 AA + 9 e + 7 t entries.
- officer.scr model literals (to be made theater-aware via resolver, additively):
  L173-176 officer skin pool; L270 bodyguard; L829 battalion; L915 elite; L1016 infantry;
  L1084/1104 MG team (deprecated, unreferenced); L1159 sniper; L1302 grenadier;
  L1505/1521 AT team; L1690/1703 dogs; L1713 handler. Dogs/handler theater-agnostic.
- WEHRMACHT SPELLING: working baseline uses lowercase 8-char "german_wehrmact_officer.tik"
  and "german_wehrmact_colonel.tik" (officer.scr L174-175, precache.scr L129/136). This is the
  PROVEN form that loads on m4l3. PRESERVED byte-for-byte. (Memory catalog's capital-W claim is
  NOT what ships; do not "correct" it.)
- main.scr::main L121: thread coop_mod/officer.scr::coop_officer_init  (single injection point).
- e-series mod-tree precache files: NONE call exec coop_mod/precache.scr (confirmed all 11).
  e1l3_precache.scr is fully commented-out cache list ("temporary disabled") - special case.
- AA precache files DO start with `exec coop_mod/precache.scr` (confirmed m1l1_precache.scr L1).
- e3l2.scr has main:{} with prespawn@19, spawn@37, no coop hook (class c quick win).

---

## PHASE 0

### INCIDENT + RECOVERY (officer_positions.scr)
- A Python `open(p,'wb').write(...)` to strip em-dashes truncated the file to 0 bytes when
  encode('ascii') raised on a stray U+2192 arrow (write opened 'wb' before encode threw).
  File is UNTRACKED in git so could not be `git checkout`-restored.
- RECOVERED by full rebuild via Write tool from in-context content. All original anchors
  preserved byte-for-byte (m4l3 anchor ( -263 -1066 9 ) verified present).
- LESSON: never use raw Python file writes on .scr; use Write/Edit tools only. Em-dash cleanup
  done in-tool. Pre-existing em-dashes (4) in comments were converted to ASCII '--'.

### officer_positions.scr (MODIFIED — rebuilt)
- Added Phase 0 schema to the getAnchor reset block: level.coop_theater="aa",
  coop_feature_boss/waves/paradrop/binoc/voice=1, coop_wave_mask=255 (defaults = current AA behavior).
- Added explicit theater resolver after `local.m=...`: e1*->afrika, e2*/e3*/t1*/t2*->wehr, t3*->russ;
  default "aa". No substring ops (none exist in MOHAA script) — explicit map equality only.
- Phase 1 reductions folded in: m5l2b (boss+paradrop off), m5l3 (wave_mask 63 = no AT/dogs),
  t2l2 + t3l2 (boss+paradrop off, vehicle maps). All t-series flagged verify_ingame=1 (TODO capture).
- BYTE-VERIFY: len 12534, ASCII-only, no BOM, no em/smart-quote, no bare-negative-in-parens. PASS.

### officer.scr (MODIFIED — additive only, working combat funcs untouched)
- ADDED coop_model_for local.role:{...} resolver (role -> TIK by level.coop_theater). Defaults to
  exact AA set; afrika/wehr/russ branches per ai_model_catalog. dog/handler theater-agnostic.
- ADDED coop_officer_skin:{...}: AA keeps original 4-skin randomint pool; afrika/wehr/russ return
  single command model. coop_officer_spawn now does local.officer_model = exec ...coop_officer_skin
  (replaced the inline 4-line skin pool; AA result identical).
- ADDED coop_feature_boss guard in coop_officer_init (end before radio/officer threads if 0).
- ADDED coop_feature_waves guard at top of coop_officer_reinforcements (end if 0).
- ADDED coop_wave_allowed local.t:{...} bit-test helper (no bitwise op -> int div/modulo) + reroll
  loop (max 16 tries, fallback to type 1 infantry) in coop_call_reinforcements.
- Routed model literals through coop_model_for via a local var then `spawn local.var` (proven pattern,
  matches existing L244 spawn local.officer_model): bodyguard(infantry), battalion(infantry),
  elite squad(elite), infantry squad(infantry), sniper(sniper), grenadier(grenadier),
  AT gunner(at)+loader(infantry), dog handler(handler). Dog model kept literal (bark-loop model
  compare depends on it). Deprecated/unreferenced coop_spawn_mg_team left untouched.
- ADDED coop_feature_paradrop / coop_feature_binoc guards in coop_officer_death_drops (each reward
  drop now conditional; announcement text adapts; defaults drop both = AA behavior).
- ADDED coop_feature_voice guard at top of coop_german_bark_loop (end if 0).
- BYTE-VERIFY: len 85427, ASCII-only, no BOM, no em/smart-quote/arrow, no bare-negative-in-parens,
  code-only brace balance 0, code-only paren balance 0 (string-literal parens benign). wehrmact
  lowercase + Afrika capital-A confirmed present. PASS.

### e-series precache gap fix (11 files MODIFIED)
- Prepended `exec coop_mod/precache.scr` as line 1 to all e*_precache.scr in the mod tree:
  e1l1, e1l2, e1l3, e1l4, e2l1, e2l2, e2l3, e3l1, e3l2, e3l3, e3l4.
- e1l3_precache: its heavy cache list is "temporarily disabled" (commented) for server-load reasons;
  the single coop exec line is cheap and added above the comments.
- BYTE-VERIFY: all 11 ASCII-only, no BOM; each has exactly 1 coop precache exec on line 1. PASS.
- This makes officer/paradrop/binoc assets (radio, cardtable, c47fly, smoke, dog, stuka) precached
  on BT maps. (t-series precache fix deferred to Phase 2 with t-series integration.)

## PHASE 0 COMPLETE.
Net result on AA maps: theater defaults to "aa" + all features on + wave_mask 255 => behavior
identical to before (m4l3 baseline unchanged). New plumbing only activates when a map sets
non-default values (e/t theaters, the m5l2b/m5l3/t2l2/t3l2 reductions).

## PHASE 1 (AA theater + feature toggles)
- AA theater is "aa" by default (resolver), so no per-map theater edits needed for m-series.
- REDUCTIONS set in officer_positions.scr getAnchor chain:
  - m5l2b: coop_feature_boss=0, coop_feature_paradrop=0 (tank-drive 2).
  - m5l3: coop_wave_mask=63 (types 0-5 only; drops AT(6)+dogs(7)); boss kept (on-foot reachable).
  - m4l0: coop_feature_boss=0, coop_feature_paradrop=0 (vehicle escort) - new SKIP-BOSS branch (no anchor).
  - t1l1/t2l2/t3l2 boss-off handled (t-series; t1l1 new SKIP-BOSS branch).
- TODO anchors needing in-game capture (fallback active, coords NOT invented): m1l1, m1l3c, m3l1b
  (all AA, flagged coop_officer_verify_ingame=1 in table). 4 precache-only AA maps
  (m1l3a/m3l3/m5l2a/m6l1b) have no level script -> remain dynamic-only/skipped (out of scope).
- BYTE-VERIFY officer_positions.scr: ASCII, no BOM, code paren/brace balance 0, no bare-neg. PASS.

## PHASE 2 (integrate unintegrated maps)

### e-series quick wins (3 level scripts MODIFIED)
- e3l2.scr: inserted `waitthread coop_mod/main.scr::main` as first stmt in main:{}; replaced
  `level waittill spawn` with `waitthread coop_mod/replace.scr::waitForPlayer` (vanilla line commented).
- e3l3.scr: inserted hook as first stmt; replaced `level waittill spawn` with waitForPlayer.
  ALSO FIXED PRE-EXISTING CORRUPTION: 3 garbled lines (`$player loopsound <U+2026>` / lone ellipsis,
  not present in vanilla) removed - they were invalid syntax (no quotes/sound name) and would
  parse-error once the file is loaded as a coop map. Audio already handled by the L136
  `exec coop_mod/replace.scr::playsound DFRUK_E3L3_CM3810 wait`. Also de-accented a comment
  (aendern). e3l3 now ASCII-clean.
- e3l4.scr: inserted hook as first stmt in main:{}; replaced `level waittill spawn` with waitForPlayer.
- officer_positions.scr: added e3l4 SKIP-BOSS branch (campaign-end; base coop only, no officer).
- All BYTE-VERIFIED ASCII, no BOM, no bare-neg, hook+wfp present.
- NOTE: e2l2 (partial) left as-is per its existing main.scr::main@14; its missing-waitForPlayer
  caveat is a MEDIUM item flagged for the main session (not a quick-win edit).

### t-series on-foot quick wins (4 new level scripts + 4 precache CREATED in mod tree)
- Copied from original-scripts/spearhead/maps/: t1l2, t1l3, t2l1, t2l3 (+ *_precache.scr).
- NOTE: original t1l2.scr was read-only; cp preserved it -> Edit failed EPERM on atomic rename.
  Cleared read-only via PowerShell on all 4 + precache, then edits succeeded.
- Each .scr: inserted `waitthread coop_mod/main.scr::main` as first executable stmt (t-series are
  FLAT scripts except t2l3 which has a main: label; hook placed at top per m3l2 flat precedent),
  and replaced the MAIN-thread `level waittill spawn` with waitForPlayer. t2l3 has a SECOND
  `level waittill spawn` at L962 inside wave3_think (sub-thread) - left as-is (not the spawn gate).
- Each *_precache.scr: prepended `exec coop_mod/precache.scr`.
- maplist.scr: added e3l2, e3l3, e3l4 + t1l2, t1l3, t2l1, t2l3 (in campaign order) to the rotation.
  Vehicle/cinematic t-maps (t1l1, t2l2, t2l4, t3l1, t3l2) intentionally OMITTED (not integrated).
- All BYTE-VERIFIED: ASCII, no BOM, balanced braces/parens, no bare-neg, hook+wfp+precache present.
- DEFERRED (TODO surgery, NOT attempted): t1l1 (plane cinematic), t2l2 (halftrack drive),
  t2l4 (KillThePlayer death zones), t3l1 (tank waves + s10_3 BSP music), t3l2 (T-34 whole map).
  Music (P4 stufftext tmstart) conversion left as a refinement for the integrated t-maps -
  host-only audio, not a soft-lock; flagged for main session.

## PHASE 2 COMPLETE.

## PHASE 3 (in-game map-select menu)

### MENU SYSTEM FINDINGS
- MOHAA uses .urc menu files in ui/. The coop map-select menu ALREADY EXISTS: ui/coop_start.urc.
- Reached from main menu via: Main Menu -> Multiplayer -> "HaZardModding Coop Mod" button
  (ui/multiplayerstart.urc L270: stuffcommand "set ui_dmmap nomap;pushmenu coop_start").
- coop_start.urc has a PulldownMenuContainer (coop_missionNameSel) listing missions; each entry
  does `command "exec ui/coop_start/<mission>.cfg"`.
- Map buttons (coop_startMap1..10) are GENERIC, defined in ui/coop_maps.inc (included by coop_start.urc).
- Each mission cfg uses `globalwidgetcommand coop_startMapN shader <thumb>` +
  `globalwidgetcommand coop_startMapN stuffcommand "set ui_dmmap <map>"` to populate buttons; unused
  buttons get shader menu_button_trans + empty stuffcommand.
- Apply button runs `exec coop_mod/start_server.cfg` which sets g_gametype 2 + maxentities 2048 then
  `ui_startdmmap 2` (loads ui_dmmap). So selecting a map only needs to set ui_dmmap.
- BEFORE this work the menu only listed m0-m6 + e1 + e2 (no e3, no SH t-series).

### MENU CHANGES (extend existing system - no new menu engine work needed)
- CREATED ui/coop_start/e3.cfg: Breakthrough mission 3 (e3l1, e3l2, e3l3, e3l4) - all now coop-integrated.
- CREATED ui/coop_start/t1.cfg: Spearhead mission 1; selectable t1l2, t1l3; t1l1 shown disabled (not integrated).
- CREATED ui/coop_start/t2.cfg: Spearhead mission 2; selectable t2l1, t2l3; t2l2/t2l4 shown disabled.
- EDITED ui/coop_start.urc: added 3 addpopup entries (BT 3, SH 1, SH 2) to the mission pulldown.
- t-series cfgs set button TITLES as well as shaders, in case the dmloading thumbnail textures for
  t-maps are absent (titles render regardless; missing shader is non-fatal in MOHAA UI).
- BYTE-VERIFY: all 4 menu files ASCII, no BOM, no smart-quotes. addpopups confirmed present.

### MENU TODOs / completion notes
- t3 missions (t3l1, t3l2) NOT added to the menu - those maps aren't coop-integrated yet (Phase 4
  vehicle/cinematic surgery). Add a t3.cfg + addpopup once integrated.
- Loading thumbnails textures/mohmenu/dmloading/{e3l*,t1l*,t2l*} may not exist in the pak set; if a
  thumbnail is missing the button shows its title text instead (acceptable). Main session can add
  thumbnail shaders for polish.
- Difficulty selector in coop_start.urc is commented out (coop_skill) - unrelated to this task.

## PHASE 3 COMPLETE (using existing menu infrastructure).

## FINAL VERIFICATION
- 25 .scr files (modified + created) swept: 0 parse-killer failures (no non-ASCII, BOM, smart-quote,
  em-dash, arrow, ellipsis, or bare-negative-in-parens).
- 5 menu files (.urc/.cfg) verified ASCII/no-BOM.
- m4l3 baseline PRESERVED: its getAnchor block sets only anchor+reinf; inherits theater "aa" +
  all features on + wave_mask 255 => identical behavior to before this work.
- coop_model_for AA-default path returns the exact original literals; coop_officer_skin keeps the
  AA randomint-4 pool with preserved lowercase "german_wehrmact_*" spelling.

## OPEN TODOs (for main session)
ANCHORS NEEDING IN-GAME CAPTURE (fallback active, coords NOT invented):
- AA: m1l1, m1l3c, m3l1b (verify_ingame=1).
- SH t-series (all currently estimates, flagged verify_ingame=1): t1l2, t2l1, t2l3, t2l4, t3l1
  (t2l2/t3l2 boss-off so anchor moot until vehicle surgery).
MAPS NEEDING SURGERY (NOT integrated; intentionally skipped):
- t1l1 (plane cinematic), t2l2 (halftrack), t2l4 (KillThePlayer zones), t3l1 (tank waves + s10_3 BSP
  music), t3l2 (T-34 whole map). Adapt AA vehicle-coop (bt_playerTank.scr/vehiclehandler.scr).
MEDIUM CAVEATS:
- e2l2 missing waitForPlayer gate (already had main hook) - verify combat doesn't fire player-less.
- e2l3 checkpoint/cvar save - make officer state idempotent across reload.
- Music (P4 stufftext tmstart->tmstartloop) conversion for integrated t-maps (host-only audio; refinement).
MENU:
- Add t3.cfg + addpopup once t3 maps are integrated. Optionally add dmloading thumbnail shaders
  for e3l*/t1l*/t2l* (missing thumbnail falls back to button title text; non-fatal).
PRECACHE-ONLY AA STUBS (no level script; out of scope): m1l3a, m3l3, m5l2a, m6l1b.
