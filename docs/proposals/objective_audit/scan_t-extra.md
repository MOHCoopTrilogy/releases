# Objective-toast audit - t-series + non-m/e story maps [user 2026-08-09]

Scanner scope: maps/t1l1 - t3l2 (t3l3 does not exist; the t-series ends at t3l2), maps/lib*.scr
(none exist), plus coop-integrated story maps outside m*/e* (test_BoB_Foy). Excluded per task:
dm/, obj/, briefing/, training.scr, co_lobby*, cov/, and the uppercase M*.scr files (m-series,
covered by the m-scanner).

## Grounded semantics (verified this scan)

- The New Objective card fires ONLY from `global/objectives.scr::add_objectives <idx> 2`
  (hook at global/objectives.scr:43-44, `if( local.status == 2 )` -> thread
  `coop_mod/objectives.scr::coop_obj_toast_all local.index local.objective`).
- `current_objectives` never toasts (global/objectives.scr:222+). Status 1 (hidden) and 3
  (complete) never toast.
- `coop_obj_toast_all` (coop_mod/objectives.scr:679) exits on `local.text == NIL || ""`
  (line 680) and on `$player.size < 1` (line 681). Per-player once-key is
  `coop_objToastSeen m<idx>` set in `coop_obj_toast` (coop_mod/objectives.scr:72-73), i.e.
  keyed on the objective INDEX, set only when a toast actually draws.
- `global/obj.scr` (t2l1's channel) is a thin wrapper: word status -> numeric, forwards to
  add_objectives (global/obj.scr:9-19). `current` == status 2, so texted `obj.scr N current`
  calls DO toast.
- `waitForPlayer` (coop_mod/replace.scr:99) releases on `level.coop_playerReady == 1`, which
  player.scr:1070 sets AFTER `coop_isActive = 1` (player.scr:1047) - so a toast fired
  immediately after waitForPlayer lands on the first player. The m2l2a `wait 2` buffer is
  belt-and-braces, not load-bearing.

## The t-series failure modes are NOT the m2l2 one

Every t-map gates its objective flow behind `waitthread coop_mod/replace.scr::waitForPlayer`
(t1l1:42, t1l2:31, t1l3:42, t2l1:31, t2l2:48, t2l3:62, t2l4:32, t3l1:48, t3l2:122), so the
"all adds fire into an empty server" defect (m2l2a/b) does NOT occur here. Two different
defect classes do:

1. **BARE status-2 flips** - `add_objectives N 2` with NO text argument. The hook forwards
   NIL text and coop_obj_toast_all exits at the text check (coop_mod/objectives.scr:680).
   Never toasts, players present or not. This kills t1l1, t1l3, t3l1 entirely and half of t3l2.
2. **Index reuse vs. per-index once-key** - t2l4 reuses index 2 and index 4 for DIFFERENT
   objectives; the second texted add is suppressed by the `coop_objToastSeen m<idx>` key set
   by the first. NOTE FOR FIXER: the standard recipe
   `waitthread coop_mod/objectives.scr::coop_obj_toast_all N "text"` will ALSO be suppressed
   for these two sites (same key). Needs a per-player `coop_obj_toast <player> <unique-key>
   <text>` loop or a keyed variant of toast_all.

Count-republish suppression (t2l1 nebels, t1l2 flaks, t2l1 squad count) is BY DESIGN and
correct - first count toasts, later counts update quietly.

## Classification table

| Map | Class | Start toast | Mid-mission toasts |
|---|---|---|---|
| t1l1 | BROKEN | never (obj 1 never status-2 at all) | none (all flips bare) |
| t1l2 | OK | works | works |
| t1l3 | BROKEN | never (bare) | only obj-5 "[3 Remaining]" count republish |
| t2l1 | PARTIAL | works (obj 5 intro) | works except obj 3 (no status-2 site exists) |
| t2l2 | OK | works (sole objective) | n/a |
| t2l3 | OK | works | works (objs 4/5 are retail-dead code) |
| t2l4 | PARTIAL | works | 2 of 6 suppressed by index reuse |
| t3l1 | BROKEN | never (bare) | none (all 7 flips bare) |
| t3l2 | PARTIAL | works | objs 1 and 3 never toast (bare) |
| test_BoB_Foy | N/A | no objectives in map | - |

## Per-map evidence

### t1l1 - BROKEN (zero toasts possible on the whole map)

Spawn gate maps/t1l1.scr:42. Registrations maps/t1l1.scr:76-78, all status 1 (hidden), texted.
All transitions live in gags/t1l1_end.scr and are BARE.

| # | Text (from registration) | Registered | Set in-progress | Completed |
|---|---|---|---|---|
| 1 | Rendezvous With Your Allies | t1l1.scr:76 (s1) | NEVER - no status-2 site exists anywhere | gags/t1l1_end.scr:497 |
| 2 | Destroy Tank With AA Gun | t1l1.scr:77 (s1) | gags/t1l1_end.scr:600 `2 2` BARE (+current :601) | gags/t1l1_end.scr:836 |
| 3 | Regroup With Your Allies | t1l1.scr:78 (s1) | gags/t1l1_end.scr:837 `3 2` BARE (+current :838) | gags/t1l1_end.scr:902 |

Missing: (a) start toast for obj 1 - m2l2a recipe thread (waitForPlayer -> wait 2 ->
toast_all 1 "Rendezvous With Your Allies") from maps/t1l1.scr after line 42; note obj 1 also
never becomes current in retail (goes straight to complete at end:497) - toast-only fix, do
not add a status flip. (b) gated toast lines with explicit text next to gags/t1l1_end.scr:600
and :837.

### t1l2 - OK

Spawn gate maps/t1l2.scr:31; everything below runs post-player.

| # | Text | In-progress (toasts) | Completed |
|---|---|---|---|
| 1 | Destroy the artillery emplacements [2 left] | t1l2.scr:150 texted s2, post-gate -> toasts at start; [1 left] republish :641 updates quietly (key m1, by design) | t1l2.scr:656 |
| 2 | Regroup and advance through the town | t1l2.scr:657 texted s2, mid-mission -> toasts | t1l2.scr:691 |

### t1l3 - BROKEN (only toast a player can ever see is a mid-count republish)

Spawn gate maps/t1l3.scr:42. Registrations texted s1 in initobjectives (t1l3.scr:525,
lines 528-544; called from main at :166, post-gate). Every flip is BARE.

| # | Text (from registration) | Set in-progress | Completed |
|---|---|---|---|
| 1 | Track and Eliminate the Colonel | t1l3.scr:556 `1 2` BARE (objective1, threaded from officer_trig1 :739) | t1l3.scr:574 |
| 2 | Destroy the Tiger Tank with the Flak Cannon | t1l3.scr:590 BARE | t1l3.scr:601 |
| 3 | Use a Demolition Charge to Destroy the Flak Cannon | t1l3.scr:608 BARE | t1l3.scr:620 |
| 4 | Acquire Explosives from the Air Drop | t1l3.scr:627 BARE | t1l3.scr:640 |
| 5 | Plant Demolition Charges on the Bridge [4 Remaining] | t1l3.scr:655 BARE; texted count republishes :911 [3], :916 [2], :921 [1] - the FIRST plant toasts "[3 Remaining]" (key m5 unset until then) | t1l3.scr:929 (texted s3) |
| 6 | Return to the Captain Before the Charges Blow | t1l3.scr:930 BARE (+current :931) | gags/t1l3_bridge.scr:83 |

Missing: gated toast beside each bare flip (556, 590, 608, 627, 655, 930) using the
registered texts; obj 5's toast should carry "[4 Remaining]" so the :911 republish then
updates quietly.

### t2l1 - PARTIAL (obj 3 has no status-2 site at all)

All flow via `exec global/obj.scr` (wrapper confirmed toast-capable). Spawn gate
maps/t2l1.scr:31; hidden registrations :67-71 (post-gate, but hidden = no toast by design).

| # | Text | In-progress (toasts) | Completed |
|---|---|---|---|
| 1 | Destroy the Nebelwerfers [4 remaining] | t2l1.scr:1349 texted current (after halftrack kill dialogue) -> toasts; count republishes t2l1.scr:2106-2115 (nebel_objective) update quietly | t2l1.scr:2074 |
| 2 | Use Nebelwerfer to Destroy the Halftrack | t2l1.scr:1664 texted current -> toasts | t2l1.scr:1672 |
| 3 | Use Sticky Bomb to Destroy Tank | NEVER - only hidden :69 and complete :1823. No current/status-2 site exists (retail gap). Natural additive anchor: tigertank1_thread t2l1.scr:1701 | t2l1.scr:1823 |
| 4 | Use Sticky Bomb to Destroy Second Tank | t2l1.scr:1774 texted current (tank 2 starts driving) -> toasts | t2l1.scr:1840 |
| 5 | Acquire a Supply Truck | t2l1.scr:419 texted current (intro scene, post-gate) -> toasts. This is the map's FIRST shown objective | t2l1.scr:2130 |
| 6 | Keep the squad alive at all costs [N remaining] | t2l1.scr:1976 texted current -> first call toasts, count updates quiet | - |

Missing: obj 3 announcement only. A gated toast (and nothing else - do not add a retail
status flip) at tigertank1_thread (:1701) or beside tankbomb1's completion path is the
additive fix.

### t2l2 - OK

Spawn gate maps/t2l2.scr:48. Sole objective added texted s2 at t2l2.scr:67 (+current :68),
post-gate -> toasts at start. Completed t2l2.scr:1097 (`1 3`, no toast needed). No other
objectives exist.

### t2l3 - OK

No load-time adds at all. All transitions go through `setobjective` (maps/t2l3.scr:3285),
every case a texted s2 + current. Callers, all mid-mission with players present:
gags/t2l3_medic.scr:218 (num 1, sarg dialog at the front line), :220 (num 2), :491 (num 3),
maps/t2l3.scr:1949 (num 6).

| # | Text | In-progress (toasts) | Completed |
|---|---|---|---|
| 1 | Get Orders from the Captain at the Front Line | t2l3.scr:3291 -> toasts | :3297 (as numminus of case 2) |
| 2 | Locate The Medic | t2l3.scr:3296 -> toasts | :3303 |
| 3 | Escort Medic to the Captain | t2l3.scr:3302 -> toasts | :3309 (dead - see below) |
| 4 | Locate and Defend the Right Flank | case exists :3308 but NO caller anywhere (retail-dead) | - |
| 5 | Locate and Defend the Left Flank | case exists :3314, NO caller (retail-dead) | - |
| 6 | Return to and Defend the Right Flank | t2l3.scr:3320 -> toasts | t2l3.scr:2037 |

Note: since cases 4/5 never run, obj 3's numminus-complete (:3309) never fires either; obj 3
is closed implicitly when 6 completes the mission. Retail behavior - not a coop regression,
nothing to fix.

### t2l4 - PARTIAL (index reuse suppresses 2 of 6 announcements)

Spawn gate maps/t2l4.scr:32; DoStartup waitthread'd at maps/t2l4.scr:90 (post-gate) ->
$cappy thread DoOpeningDialog (gags/t2l4_start.scr:49).

| Key | Text | In-progress (toasts?) | Completed |
|---|---|---|---|
| 1 | Cross the Field Alive. | gags/t2l4_start.scr:212 texted s2, players present -> toasts | maps/t2l4.scr:480 |
| 2 | Find the captain | gags/t2l4_captain.scr:185 texted -> toasts | - (superseded by reuse) |
| 2 reuse | Clear Church. | gags/t2l4_captain.scr:243 texted BUT key m2 already set by :185 -> SUPPRESSED | gags/t2l4_captain.scr:327 |
| 3 | Clear Hotel. | gags/t2l4_captain.scr:507 texted -> toasts | :679 |
| 4 | Find the captain | gags/t2l4_captain.scr:688 texted -> toasts | :729 |
| 4 reuse | Destroy Stuka With Artillery. | gags/t2l4_captain.scr:763 texted BUT key m4 set by :688 -> SUPPRESSED | :783 |

Missing: announcements for "Clear Church." (:243) and "Destroy Stuka With Artillery." (:763).
WARNING: `coop_obj_toast_all 2 "Clear Church."` will NOT work - same m2 key. Use per-player
`coop_obj_toast $player[i] "<unique-key>" "<text>"` loops (keys e.g. "m2b"/"m4b") or add a
key-override parameter to toast_all.

### t3l1 - BROKEN (all 7 flips bare, zero toasts)

Spawn gate maps/t3l1.scr:48. initobjectives (t3l1.scr:480, texted s1 regs :482-488) and
objective1 are driven from gags/t3l1_fourrussians.scr:49 and :52 (intro scene, players
present - timing is fine; the texts are just never passed).

| # | Text (from registration) | Set in-progress | Completed |
|---|---|---|---|
| 1 | Cross the Bridge and Enter Berlin | t3l1.scr:504 `1 2` BARE | :512 |
| 2 | Locate Downed Aircraft and Map to Chancellery | t3l1.scr:530 BARE | :537 |
| 3 | Locate the Chancellery Building | t3l1.scr:555 BARE | :562 |
| 4 | Locate the Safe Containing List of Double-Agents | t3l1.scr:577 BARE | :586 |
| 5 | Locate the Combination to the Safe | t3l1.scr:601 BARE | :611 |
| 6 | Use Combination to Open the Safe | t3l1.scr:665 BARE | :674 |
| 7 | Eliminate Enemies and Commandeer a Tank | t3l1.scr:700 BARE | :724 |

Missing: gated toast beside every bare flip (504, 530, 555, 577, 601, 665, 700) with the
registered texts from :482-488.

### t3l2 - PARTIAL (start works, both later transitions bare)

Spawn gate maps/t3l2.scr:122; `waitthread initobjectives` at :226 (post-gate).

| # | Text | In-progress (toasts?) | Completed |
|---|---|---|---|
| 1 | Destroy the South Bridge | t3l2.scr:1030 `1 2` BARE (modifyobjective1, threaded :1491) -> never toasts | t3l2.scr:1043 |
| 2 | Return to the Soviet Recon Group | t3l2.scr:1015 registered DIRECTLY at status 2 WITH text, post-gate -> START toast works | t3l2.scr:1060 |
| 3 | Defend the Bridge Until Air Support Arrives | t3l2.scr:1061 `3 2` BARE -> never toasts | t3l2.scr:1072 |

Missing: gated toasts beside :1030 ("Destroy the South Bridge") and :1061 ("Defend the
Bridge Until Air Support Arrives").

### test_BoB_Foy - N/A

Coop-integrated (maps/test_BoB_Foy.scr:8) but contains zero add_objectives /
current_objectives / obj.scr sites. Nothing to do.

### Non-existent / out of scope

- maps/t3l3.scr, maps/lib*.scr: do not exist (t-series ends at t3l2, matches CLAUDE.md).
- M1L3a.scr, M1L3c.scr, M3L3.scr, M5L2A.scr, M6L1b.scr: uppercase m-series files -
  m-scanner's set (Windows FS is case-insensitive; these ARE m-maps).
- training.scr: excluded per task (has objectives, all texted s2 mid-flow, for the record).
