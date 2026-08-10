# Open Defects, Reverts, and Record-vs-Code Discrepancies

Source: `.wolf/buglog.json` (snapshot 639 entries, 2026-07-29) cross-checked against the live tree.
**Where the record and the code disagree, the code wins.** Those cases are section D.

---

## A. OPEN - known defect, no fix in the tree

| id | Area | Defect | Evidence |
|---|---|---|---|
| bug-1218 | m3l2 script | `Could not find label 'level_end_trigger' in maps/m3l2.scr`. **Code-confirmed:** `maps/m3l2.scr:2854` does `$level_end_trigger remove` but the file has **no** `level_end_trigger:` label - unlike `m4l0.scr:431`, `m6l1a.scr:57`, `M6L1b.scr:52` which define it. | buglog + `maps/m3l2.scr:2854` |
| bug-1219 | engine capacity | `SV_FindIndex overflow (max=1280, start=2100)` x243 on m3l2 - sounds silently dropped. Logged against a **1280** build; source is now 1600 (see D-2). | buglog; `q_shared.h:1742` |
| bug-1220 | e2l2 script | 12x `command applied to NULL listener` (`origin`/`hide`/`notsolid`/`triggereffect`/...). Needs BOTH NIL and NULL guards (trap T5). | buglog |
| bug-1213 / bug-1184 | m1l1 actors | `2nd-ranger_private` actors render **mangled** (limbs stretched to spikes, faces flattened); the captain in the same truck is fine. Six investigations; mod data **exonerated with proof**; no fix shipped. Diagnostic `tiki_posecheck 1` (`^~^~^ POSECHK`) added instead. | buglog; open task #16 |
| bug-1026 | t2l2 | 265 script errors on coop boot: 36x `Couldn't load models/nil.tik`, missing `models/vehicles/panzerwerfer42.tik`. "Map is degraded not dead." Fix field literally reads *OPEN*. | buglog |
| bug-1027 | e3l4 | `maps/e3l4/outro.scr was not properly loaded` + 251x binary-op-on-none cascade. BT campaign ending broken. Suspected parse killer (trap T1). Fix field reads *OPEN*. | buglog |
| bug-923 | engine physics | Weapons dropped by dying AI **float and spin in mid-air forever** when the 24x24x14 item box spawns inside geometry. Exact patch proposed, *"NOT YET FIXED - investigation only"*. | buglog |
| bug-330 | dedicated server | game.dll segfaults loading bare DM maps (`obj/obj_team1`) under a dedicated server; coop maps unaffected. Likely a coop hook assuming coop init. *"none yet"*. | buglog |
| bug-gl2-ztagmalloc | gl2 | `Z_TagMalloc, Negative or zero size 0 tag 12` spammed every gl2 menu frame; clean under gl1. Cause unknown. | buglog |
| bug-gl2-decal-red-dds | gl2 | Some bullet-hole decals render **red**. `rgbGen` refuted. Deliberately **not guessed at** - a blind change risks 2,370 working DDS textures. | buglog |
| bug-gl2-e2l2-briefing-npc-invisible | gl2 | The e2l2 briefing NPC (`$lyndon`) is invisible in gl2 only, on that one map. Accepted as a low-impact quirk. | buglog |
| bug-165 | cgame | Reload camera dip never visible; signal chain source-verified end to end. *"PENDING runtime data"* (`cg_reloadCamDebug 1`). | buglog |
| bug-898 | coop items | Mine detector possibly still lost after DBNO revive. Diagnostic only (`coop_missionItemDebug 1`), *"UNRESOLVED - needs live confirmation"*. | buglog |
| bug-309 | vehicles | Jeep .30cal manning pose never plays (player stands with gun holstered). *"QUEUED: instrument the live legs state ... Do NOT guess condition semantics - measure first."* | buglog |
| bug-1149 (partial) | gl2 | Of gl1's post-FX chain (SSAO / DoF / bloom / god rays / grade / FXAA / sharpen / heat haze / rain), **only bloom** is ported to gl2. The rest is absent. | buglog |
| bug-1194 (latent) | sound | Guard corrected, but **`MAX_SFX_INFOS` is still 1000** (`snd_local_new.h:182`) - capacity itself never raised. | `snd_local_new.h:182` |

---

## B. PLANNED - designed, not built

| id | Item |
|---|---|
| bug-311 | Cover-peek **physical step-out**: slide origin 24-32u toward the open side during peek. Peek v1 only releases the torso, so the muzzle stays behind the wall edge - *"VERY janky"*. |
| bug-923 | The proposed `Weapon::Drop` spawn-point sweep-clamp (see A). |

---

## C. REVERTED - done, then undone. The most valuable entries in the log.

| id | What was reverted | Why |
|---|---|---|
| **bug-1173 -> bug-1184** | `+180` roll correction on m1l1 `guy01/guy2/guy3` | Based on a gimbal-lock theory that was **never confirmed**; live result was contortion, and the untouched captain rendered correctly. See D-1. |
| **bug-861 -> bug-866 -> bug-892** | Blast **decapitation** feature | bug-861: shipped, *"the AI went all glitchy"*, pulled at user request. bug-866 re-implemented it safely (dead-gated, per-frame budget, short-lived, tracked, precached). bug-892 then **reverted it from source again** so a protocol rebuild would not silently reintroduce it. **Live code confirms: zero `CoopGoreTryDecapitate` / `HeadGibObject` symbols remain.** |
| **bug-1179** | `MAX_SOUNDS` 1280 -> 2000 | `SV_FindIndex: bad start index 4260`, server crash at map load. Wrong limit assumed (wire field, not configstring layout). |
| **bug-1183** | `MAX_SOUNDS` 1280 -> 1600 (first attempt) | `MAX_RELIABLE_COMMANDS` was 512; +320 sound registrations pushed the queue to 514 -> *"Server disconnected"* mid-spawn, twice. |
| **bug-1181** | `ui_checkrestart` on the post-FX APPLY button | Issuing `vid_restart` **from an open menu** made gl2 tear down and re-init while UI fonts were live -> instant `0xC0000005` in `InitShaderEx`. AO now applies on the next natural renderer init. |
| **bug-918** | `r_entlight_scale` `CVAR_CHEAT` -> `CVAR_ARCHIVE` | The A/B test value `0.3` archived itself and dimmed every entity on every launch. Restored to `CVAR_CHEAT` so it can never persist. |
| **bug-1172** | Sandbox constants (`MAX_SOUNDS 2000`, `MAX_ENTITIES 4095`, `MAX_TIKI_ALIASES 8192`) | `build.ps1` had pushed them into the **real GOG install**. See trap T3. |
| **bug-1182** | Font-atlas swap | Targeted `gfx/fonts/*.tga` when the engine actually loads `<name>@3x.tga` - the replacement was **silently inert**. Originals restored. |
| **bug-157** | 29 upscaled main-menu chrome textures | The 2x upscale pass had swept in **vanilla** textures; overrides removed so the engine falls back to stock. |
| **bug-594** | "Corrected" armory 3D-preview framing | Re-derived from bounds math; rendered upside down and off-screen. Reverted to the screenshot-proven framing, with a generator comment forbidding re-derivation without a live screenshot. |
| **bug-787** | Hidden-locked cosmetics (bug-759 / bug-772) | **User design reversal** pre-release: pickers must cycle *all* entries with a lock icon instead of skipping locked ones. 260 redirect seed/replay lines removed. |
| **bug-817** | Gore intensity (bug-796 round 4) | *"way too much"* - reverted to bug-747/754-era coverage. |
| **bug-938** | `coop_noPlayerClip` experiment | Let players push into real out-of-bounds geometry; reverted to 0 in favour of landmine `CONTENTS_WEAPONCLIP`. |
| **bug-946 -> bug-951** | Regional playerclip **zone stripping** | Wrong-grained: boundary clip and phantom-wall clip share the same regions, so stripping let players clip out of bounds. Replaced by per-brush surgery (`cmpatch/<map>.txt`). |
| **bug-menu-shader-label-invisible** | Coop-settings folder/paper shader Labels | Raw image paths do not resolve as shaders in the URC material system; reverted to solid `bgcolor` fills. |

---

## D. Record-vs-code discrepancies found this session

### D-1. m1l1 `+180` roll - RESOLVED IN THE CODE'S FAVOUR
The premise that motivated this audit. **Verified 2026-07-29:** `maps/m1l1.scr` contains **no** roll
correction; line 1683 carries an explicit `// REVERTED (bug-1184): a +180 roll correction was applied
here on an UNVERIFIED ...` comment. The buglog is *also* correct **if read to the end** (bug-1184
supersedes bug-1173). The failure was reading bug-1173 alone. **The buglog has no supersession field
- that is the structural defect**, not the individual entry.

Separately confirmed present and correct: bug-1162's workaround at `maps/m1l1.scr:341` - `actor2`
uses `truck_idle_guy02` / `truck_twitch_guy02` instead of the duplicate-channel `guy01` clips.

### D-2. `MAX_SOUNDS` - the buglog is behind the source, and both are ahead of the shipped binary
- Source **now reads 1600** (`q_shared.h:1742`) with `MAX_RELIABLE_COMMANDS 1024` (`qcommon.h:215`)
  as the prerequisite.
- The buglog's last two `MAX_SOUNDS` entries (bug-1179, bug-1183) both record **reverts to 1280**.
  The 1280 -> 1600 **re-raise has no buglog entry of its own** - the source comment attributes it to
  *"bug-1186"*, but buglog `bug-1186` documents `MAX_SNAPSHOT_ENTITIES`. **Attribution is wrong in the
  source comment.**
- bug-1219 (2026-07-29) still reports `max=1280` from a live log -> the **deployed** binary predates
  the 1600 raise, or that build was never shipped. Verify before assuming capacity exists.

### D-3. `MAX_MODELS` attribution
`q_shared.h:1680` credits the 1024 -> 2048 raise to *"bug-866"*. bug-866 is the **decapitation
re-implementation**; the `MAX_MODELS` work is **bug-892** (which bundled it with the decap revert).
Cosmetic, but it will mislead a grep-driven lookup.

### D-4. bug-909's empty-array clamp is only half applied
The fix note says *"Same idiom exists in loadout.scr/eventsystem.scr"* - and it was never clamped there.
**Live scan 2026-07-29, 5 unguarded `arr[arr.size + 1]` append sites remain in `coop_mod/`:**
`aihandler.scr:521`, `eventsystem.scr:95`, `itemhandler.scr:1467`, `itemhandler.scr:1471`,
`itemhandler.scr:1908`. Each will silently drop its first element if the array is ever empty at that point.
Only `itemhandler.scr:1687` and `:1782` carry the clamp.

### D-5. `.wolf/buglog.json` is a live, concurrently-written file
It grew from 634 to 639 entries **during this audit** (bug-1218..1222 appended by a running
regression harness). Any ledger built from it is a snapshot, and any tool that rewrites it wholesale
can lose concurrent writes - `bug-buglog-dataloss` is already in the log, and 8 `.bak` files exist.
**Append, never rewrite.** (All 8 backups were diffed: they contain zero entries absent from the current file.)

### D-6. Id gaps are not data loss
632 of the ids in the range `bug-1 .. bug-1222` were never assigned. Sessions guessed at the next
number. Do not read a gap as a lost entry.

### D-7. The only structured status field was abandoned
`fix_verified: false` appears on exactly 17 entries (bugs 070, 072-074, 088-089, 091-092, 095-096,
098-100, 168, 229-231), all from late June. Nothing after that carries a machine-readable status -
every later status claim is prose buried in the `fix` field, which is why SHIPPED and
SHIPPED-VERIFIED became indistinguishable. **Any successor format needs `status` and `superseded_by`
as first-class fields.**
