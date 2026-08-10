# Objective-toast fix pass - adversarial review [user 2026-08-09]

Scope: the 28 script files + `.wolf/buglog.json` changed by the toast fixer batches
(bug-1626 / bug-1627). Method: `git diff --ignore-cr-at-eol` per file, byte-level
line-ending comparison against HEAD and against the deployed
`zzzzzz_co-op_hzm_mod_code.pk3` (pre-session state), text cross-check of every toast
against its map's own registration, timing check of every toast site against the map's
player gate, and a fresh run of all three verifiers on every file.

## VERDICT: APPROVE

No blocking defect found. All 08-09 hunks are strictly additive, every toast text
byte-matches its registration, every toast is gametype-gated, no label is duplicated,
line-ending style is preserved per file, and all three verifiers print OK on all 28
script files. Three scanner-OK maps re-derived from code and confirmed OK.

## What was verified

### 1. Additive-only
Every hunk tagged `[user 2026-08-09]` is a pure insertion: either a gated
`thread coop_objToastStart` line, a gated
`waitthread coop_mod/objectives.scr::coop_obj_toast_all N "text"` line, a
`coop_objToastStart` label appended at EOF, or (t2l4 only) a per-player
`coop_obj_toast` loop. No retail statement was moved, removed, or renumbered by this
pass. The only deletions anywhere in the diffs carry EARLIER session tags and are
prior uncommitted work sharing these files (m3l1b 08-07 FLAK-88 rewrite, t2l1 08-08
`iprintln`->`iprintlnbold`, t2l1_tank 08-08 `maxhealth`->`max_health`, m1l3c 08-08
convOk guards, assorted 08-08 baked-prop / challenge hunks). Out of scope for this
review; noted for provenance only.

### 2. Toast text matches registration - checked per site, all exact
| File | Toast(s) | Registration checked against |
|---|---|---|
| maps/M1L3a.scr | 1 "Reach the airfield." | :156 |
| maps/m5l1a.scr | 1 "Locate the bazooka team." | :213 |
| maps/m5l2b.scr | 1 "Escape with the King Tiger tank." | :199 |
| maps/m1l2a.scr | 1 "Find and rescue the SAS Agent." | :435 |
| maps/m2l2c.scr | 1 "Exfiltrate." | :30 |
| maps/m3l1b.scr | 1 "Clear out the bunker." | :80 (the "20mm" add at :71 is inside a `/* */` block) |
| maps/m4l0.scr | 1 "Find allied soldiers.", 2 "Take secret German documents." | :82-83 |
| maps/m6l2b.scr | 1/2/3 train station / power / radio | :82-84 |
| maps/m6l3b.scr | 1 "Acquire a gas mask." | :50 |
| maps/m6l3c.scr | 1 "Escape Fort Schmerzen." | :137 |
| maps/m6l3e.scr | 1 "Escape Fort Schmerzen." | :104 |
| maps/m1l3c.scr | 1 "Destroy all communications equipment." | :122 |
| maps/M3L3.scr | 1 "Locate and destroy the Nebelwerfers.    [4 remaining]" | matches `level.locationchecktext` with `scene7_bombcount = 4` (:134-135), incl. the 4-space gap |
| maps/M5L2A.scr | 1 "Escape with the King Tiger tank." | :116 |
| maps/e1l1/objectives.scr | 7 reveal toasts | InitObj block :28-34, all exact |
| maps/e1l4.scr | `level.objObtainPapersText` var (same var as retail add :109), "Escape the City" | :378, :392 |
| maps/e2l1/objectives.scr | 2/3/4 | InitObj :10-12, all exact |
| maps/e2l2/objectives.scr | reachAirfield / scrambleFighters / escape | :29-32, all exact |
| maps/e2l3.scr | 1 "Rendezvous with 82nd Airborne" | ObjMgr InitObj :61 (meet82nd registered first -> index 1, confirmed in global/ObjMgr.scr:141-149) |
| maps/e3l1.scr | `level.hqstring` / `level.citystring` vars (same vars as retail adds) | :298, :302 |
| maps/e3l3.scr | 3 "Search the House for Intelligence", 4 "Locate and Destroy K5 Railway Guns" | GiveObjectives :311-312 |
| maps/t1l1.scr | 1 "Rendezvous With Your Allies" | :82 |
| gags/t1l1_end.scr | 2 "Destroy Tank With AA Gun", 3 "Regroup With Your Allies" | t1l1.scr:83-84 |
| gags/t2l4_captain.scr | "m2b" "Clear Church.", "m4b" "Destroy Stuka With Artillery." | the adjacent adds :244, :775 |
| maps/t1l3.scr | 1-6 | :528-544, all exact incl. "[4 Remaining]" |
| maps/t2l1.scr | 3 "Use Sticky Bomb to Destroy Tank" | :69 |
| maps/t3l1.scr | 1-7 | initobjectives :482-488, all exact |
| maps/t3l2.scr | 1 "Destroy the South Bridge", 3 "Defend the Bridge Until Air Support Arrives" | :1014, :1016 |

### 3. Gametype gates
Every added toast/thread call is wrapped in `if( level.gametype != 0 )` (t2l4's loop
additionally checks `$player != NULL` and per-player `coop_isActive`). No exceptions
found.

### 4. Labels
`coop_objToastStart` appears exactly once in each file that gained it (15 files).
m6l3e / M3L3 / M5L2A use the braced `label:{ ... }end` form, the rest the plain
`label:` ... `end` form - both are valid and depthscan passes on all.

### 5. Line endings, BOM, ASCII
No file has MIXED endings, no BOM, zero non-ASCII bytes in any of the 28 files.
Eight files (M1L3a, m1l2a, e3l3, m6l3b, gags/t1l1_end, t3l2, e1l4, e3l1) are entirely
bare-LF - but they were already entirely bare-LF BEFORE this session (verified
against the deployed pk3's copies). The fixer correctly preserved each file's
existing style; converting the new lines to CRLF would have created mixed-ending
files, which is the actually dangerous state. The other 20 files are all-CRLF, as
before. The huge raw diff on m3l1b (5771 lines) is a git-normalization display
artifact (HEAD blobs are LF-normalized); on-disk bytes are consistent CRLF.

### 6. Verifiers
`depthscan2.py`, `quotecheck.py`, `linecheck.py` re-run on all 28 script files this
review: all OK, zero exceptions.

### 7. Timing of every toast site (the failure mode the fix exists for)
- Every load-time-add map got the m2l2a start-toast thread
  (`waitForPlayer -> wait 2 -> toast_all`), never a bare toast.
- Every added mid-mission toast sits in a flow already gated behind a player:
  e2l1 "start" fires from gliderride.scr:435, downstream of e2l1.scr:80
  waitForPlayer; e2l2's transition sites run after e2l2.scr:46 waitForPlayer;
  t3l2's initobjectives (:226) runs after :122 waitForPlayer; e1l4's first toast
  (:103) runs after :64 waitForPlayer. t-series objectiveN labels are all
  trigger-driven mid-mission.
- t2l4's index-reuse sites correctly bypass the per-index once-key with unique keys
  "m2b"/"m4b" via direct per-player `coop_obj_toast`, exactly as the scan doc's
  fixer note demanded.

### 8. Spot-check of three scanner-OK maps - all genuinely OK
- **t1l2**: waitForPlayer :31 precedes texted status-2 add :150; the :641 count
  republish updates quietly on the same index key; obj 2 texted status-2 at :657. OK.
- **t2l2**: waitForPlayer :48 precedes the sole texted status-2 add :67; completion
  :1097 is status 3. OK.
- **t2l3**: obj push is threaded to wait for players (:21 comment, :62 gate); every
  in-progress add (:3291-3321) is texted status-2 mid-mission. OK.

### 9. Skipped item
e2l2 obj `getToJeep` is registered `add_objectives level.getToJeep_no 1 NIL`
(e2l2/objectives.scr:28) - genuinely no retail text exists. Skip is legitimate;
inventing text is a design decision, not a mechanical fix. Confirmed.

### 10. buglog.json
Valid JSON, 1000 entries; bug-1626/bug-1627 cover the two fixer batches with the
schema fields intact.

## Findings (informational - none block)

1. **t2l1 comment inaccuracy** (maps/t2l1.scr:1710-1712): the claim "obj 3 never gets
   a status-2 site anywhere" is wrong - gags/t2l1_tank.scr has three texted
   `obj.scr 3 current` sites (:455 TankDialogDeathCheck, :464 ShowStickyBomb,
   :492 DoTank1Dialog), and DoTank1Dialog is reachable (threaded at :371/:380).
   The scan doc `scan_t-extra.md` carries the same error. **Behavior is unaffected**:
   the per-index once-key makes the new toast and the gag flip idempotent - the new
   toast simply front-runs the squadmate dialogue by a few seconds, and covers the
   real gap (speaker already dead when the death-check path also can't fire because
   an all-dead squad fails the mission). Fix stands; the comment overstates the gap.
2. **m1l3c casing trap**: git tracks the file as `maps/m1l3c.scr` (lowercase), the
   on-disk name is `M1L3c.scr`. A `git diff -- maps/M1L3c.scr` pathspec silently
   returns EMPTY even though the file is modified - this review nearly misread the
   map as untouched. The fix is present and correct under the tracked path. When
   scripting against this repo, resolve paths via `git ls-files` first
   (`core.ignorecase=true`, index casing wins).
3. **t2l1.scr has no trailing newline at EOF** - introduced by the 08-08
   build-structs append, not this pass. depthscan/quotecheck/linecheck all pass and
   the closing `end` is complete; cosmetic, but the next append to that file must
   insert a newline first.
4. **Shared-file provenance**: many of these files also carry unrelated uncommitted
   08-07/08-08 work (baked props, challenges, t2l1 squad watch, m3l1b FLAK-88
   rewrite, m1l3c conversation guards). Anyone committing the toast pass will drag
   that work along unless staged hunk-by-hunk.
