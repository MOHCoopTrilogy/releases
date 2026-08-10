# 90 — Unverified / Folklore

Claims that appear in the record but **could not be anchored** to a bug id, a commit, or a
`file:line` during this pass — or that were once asserted and are now known to be wrong. They are
kept here rather than silently dropped or silently asserted.

---

## A. Claims already DEBUNKED by the record itself

These circulated as facts and were later disproved. Do not reintroduce them.

| Debunked claim | Reality | Anchor |
|---|---|---|
| "`spawn <class>` with inline keyvalues is a parse killer" | **FALSE.** 192 working occurrences including `coop_mod/main.scr:40`. Remove it from mental checklists. | cerebrum 2026-07-05 |
| "t-series (Spearhead) maps need a separate `com_target_game 1` launch" | **Inverted.** BT (target 2) mounts main+mainta+maintt, so t-series runs fine under the normal launch. Under **target 1 the coop pk3s never mount at all**. | CLAUDE.md correction, verified 2026-07-05, 9/9 coop-active boots |
| "Same-name ubersound alias pooling is not supported" | **Too broad.** `Alias_ListFindRandom` resolves a sorted range of identically-named aliases and picks by weight. | cerebrum 2026-07-03 |
| "There is no surrender animation" | **FALSE.** `scientist_surrender` exists, plus `prisoner_1/2` kneel and KneelingCycle/Cower loops. Old alias names `higginsflinch01`/`shakinghelploop`/`hurt01`/`custompain` are **nonexistent**; the real ones are `higgins_ride_flinch01-06`, `fallen01-03`, `m3l1_pain`. | cerebrum 2026-07-06 |
| "`idle/atease.skc` is the parade-rest (hands-on-hips) pose" | **FALSE.** `atease` and `00A100_idle` are both arms-at-side. The hands-on-hips pose is `misc/00G100_Axis_idle.skc` (the **axis** selection idle). | cerebrum 2026-07-08 |
| "`misc/00A100_idle.skc` is hands-on-hips" | **FALSE** — it is the character-**select** idle, arms at sides. The old lobby plan mislabelled it. | cerebrum 2026-07-08 |
| "Ladders are an engine gap in coop" | **FALSE.** Fully implemented, no gametype/MP gate. `FuncLadder`'s NULL `EV_Use`/`EV_Touch` entries are **normal upstream** — the grab is driven by the player statemap. A ladder that "won't climb" is approach angle / <52u proximity / facing / blocked base. **Do not blind-edit the engine.** | cerebrum 2026-07-02 |
| "Weapon-weight sway is PLANNED / not built" | **FALSE at the time it was believed.** A full `cg_weaponLag` block had been live in `cg_view.c` for a day, plus autoexec seeds. The memory *index line* was stale while the memory *file body* said so. **Grep the code before rebuilding anything marked planned.** | cerebrum 2026-06-29 |
| "Auto environmental reverb needs implementing" | **FALSE.** `CG_UpdateEnvReverb` already exists in `cg_view.c`. Set `s_reverb 1`. | cerebrum 2026-07-03 |
| "`maxentities 2048` has been in a shipped config for years" | **FALSE** — a code comment in `level.cpp` asserted it; zero cfg files anywhere set it. | cerebrum 2026-07-28 |
| "`MAX_ENTITIES` (gl1) can't be increased without changing drawsurf bit packing" | **FALSE** — gl1's own sort key already budgets 12 entity bits. (The raise was still reverted for unrelated reasons.) | cerebrum 2026-07-28 |
| "`MAX_CONFIGSTRINGS` must stay 4096 to keep the same 12-bit index width" | **FALSE** — bulk send is `MSG_Write/ReadShort` (16 bits, sign-extending → true ceiling 32767); live updates are a text reliable command parsed with `atoi`. | bug-1180 |
| "The 39 `Channel named <X> not added` warnings indicate model corruption" | **RED HERRING** — every failing name is in the engine's hardcoded `bogusNameTable` (`bonetable.cpp:123-150`); stock retail deliberately rejects arm **position** channels. | bug-1184 |
| "A `.skc` with duplicate channel names is corrupt" | **Not automatically.** `LoadAnim` dedups via `AddChannel` while `EncodeFrames` walks the file ordinal, so they desynchronise only if a duplicate appears **before** the last distinct name. In all 10 such files in the game data the duplicates are trailing. **Benign — do not re-chase.** | cerebrum 2026-07-28 |
| "PrintScreen staleness is an exclusive-fullscreen/DWM issue" | **CORRECTED root cause**: front/back buffer split — the game's own screenshot reads `GL_BACK` (current), Windows PrintScreen captures the displayed `GL_FRONT` (previous swap, ~1 frame behind). Persists in Borderless too. | bug-523 |
| "The turret-camera regression root cause was the `g_coopTurretCam` override" | **Partially wrong.** That was one layer. The **shared** root across all turrets was an orphaned `bThirdPerson \|= PMF_TURRET` line in `cg_modelanim.c`. The cerebrum contains both the original diagnosis and its correction — read the later entry. | cerebrum 2026-07-01 (two entries) |
| "`coop_noChatter` silences a story actor's combat barks" | **FALSE** — it only gates our `flchatter`/taunt rolls. Story-character barks are the engine's native `Anim_Say` VO, and `self silent` does not help either. | bug-839 |
| "The helmet-pop mechanic is verified working on players in coop" | **FALSE** — zero of 313 player TIKs carry `sethelmet`. That note was about **actors**. | cerebrum 2026-07-28 |

---

## B. Claims with no independent anchor

Recorded once, never re-verified, and not checked against code during this pass. Treat as leads.

| Claim | Where it came from | What would settle it |
|---|---|---|
| Officer wave dialogue German VO pools + heal-retreat medkit fallback work as designed | memory `officer_dialogue_and_heal` | A live officer-wave playtest |
| `t2l2` coop seating (solid riders, client view-lock) is verified | memory `t2l2_coop_seating`; built + deployed with an explicit "UNTESTED (test tomorrow)" note in the journal, never re-confirmed | Ride the halftrack and truck with 2+ players |
| "MOHAA teams are only american/german" as an exhaustive statement | cerebrum 2026-07-28 (VO pool rule) | It is the *practical* truth for VO routing; whether the engine has other team enums was never checked |
| `MAX_SKELBONES` interaction with gl2 cascade-shadow views as a candidate for the mangled-actor bug | bug-1184 candidate list | Never tested — listed as an unruled-out hypothesis, not a finding |
| "AI corpses vanishing in coop = the engine 10s death-sink, not the body queue" **and** "AI corpses despawn at the engine body-queue cap, not `coop_corpseLife`" | Two cerebrum entries (both 2026-06-28) giving **different** primary causes | Both mechanisms are real (`EV_DeathSinkStart` at +10s **and** `MAX_BODYQUEUE`); which one bit in a given report was never separated |
| "`r_uselod 0` = max poly" as a user-facing quality lever | memory `graphics_lod_and_hd_assets` | Never measured |
| Blender sprint-edit pipeline is "100% complete, user paused at arm-bone selection" | memory `blender_sprint_edit` | Paused work, no artefact verified |
| CoD1 rig is "bone-name-identical to bip01" | memory `cod_anim_port_research` | Asserted from research; a clean-room re-author was the recommendation anyway, so it was never exercised |
| ~1000 unimplemented `addon_*` entities across 20 SH+BT maps | memory `addon_class_inventory` | The count was never re-derived after the bug-1022 finding that TIKI-classname fallback makes many of them work fine |

---

## C. Records that are structurally untrustworthy

- **`.wolf/memory.md`** is ~91% auto-generated `| HH:MM | Edited <file> | added N condition(s) |`
  journal lines with no semantic content. The ~500 non-journal lines are session summaries, some of
  which are the only record of a change. It is not a knowledge base and should not be read as one.
- **`.wolf/cerebrum.md`** contains genuine knowledge but is append-only, ~1700 very long lines, and
  **carries superseded entries alongside their corrections with no marking**. Several sections
  explicitly say "supersedes earlier notes" — those earlier notes are still physically present
  above them. Anything read from cerebrum needs a check for a later correcting entry.
- **`.wolf/buglog.json` is missing ~637 numeric ids** destroyed on 2026-07-27 and unrecoverable (the
  session transcripts don't reach back far enough). A bug number referenced in code comments or in
  these docs that you cannot find in the file is probably lost, not invented. See
  [03-record-vs-code.md](03-record-vs-code.md) §9.
  **⚠️ CONTESTED — see D-8 below. Two records disagree on whether these ids were destroyed or never
  assigned, and neither demonstrated its claim.**
- **`.wolf/anatomy.md`** indexes 141 of 1,667+ source files. Absence from it means nothing.

---

## D. Corrections verified against live code, 2026-07-29

Added by the SOURCE_OF_TRUTH pass. These **override** any conflicting statement elsewhere in the doc
set, including in sections A–C above. Each was checked against the working tree on the date given.

### D-1. `MAX_SOUNDS` was NOT misattributed, and no buglog entry is missing
Two earlier audit items claim `q_shared.h`'s `MAX_SOUNDS 1600` comment wrongly credits "bug-1186" and
that the 1280→1600 re-raise has no buglog entry. **Both are false.** `q_shared.h:1731` reads
`[HZM 07-28] 1280 -> 1600 (bug-1180)`, and **bug-1180 exists** (`error_message`: "Sound capacity
permanently blocked: SV_FindIndex overflow warnings (max=1280)…"; `fix`: "(1) MAX_CONFIGSTRINGS 4096
-> 8192, and rewrote the misleading comment…"). Same correct attribution at `:1785` for
`MAX_CONFIGSTRINGS`. The audit almost certainly grepped the wrong id. **The genuinely-true residue:
bug-1219's live `max=1280` is the DEPLOY gap, not a missing raise** — see [OPEN.md](OPEN.md#p0).

*The `MAX_MODELS` misattribution in the same item IS real:* `q_shared.h:1680` credits **bug-866**
(decapitation) for the 1024→2048 raise; the actual work is **bug-892**.

### D-2. The empty-array `.size == -1` trap has NO unguarded sites
An earlier audit reported 5 unguarded `arr[arr.size + 1]` append sites remaining in `coop_mod/`
(bug-909 idiom). **Not reproducible.** Every alleged site is seeded or branch-guarded:
`aihandler.scr:521` appends to `level.coop_actorArray[group.team]`, seeded at
`coop_mod/variables.scr:92-93`; `eventsystem.scr:91-96` is an explicit
`if(!list){[1]=…}else{[size+1]=…}`; `itemhandler.scr:1467/1471` are preceded by
`local.weaponArray[1] = NIL` at `:1464`; `loadout.scr`'s 108-site cluster is seeded at `:16`.
**116 total append sites in `coop_mod/`; 2 carry the explicit clamp, the rest are covered.**
⭐ **Lesson: a grep for the FIX is not a test for the BUG.** The audit searched for the clamp comment
and read its absence as exposure.

### D-3. `.bak` rollback sprawl is 157 files, not ~31 — and gl2 has ZERO
Per-binary in the GOG root: `game.dll` **75**, `openmohaa.exe` **37**, `cgame.dll` **25**,
`renderer_opengl1.dll` **19**, `renderer_opengl2.dll` **0**, plus `omohaaded_pre_ent2048_bak.exe`.
The naming scheme is `<binary>_pre_<feature>_bak.<ext>`, not `<binary>.dll.<x>_bak` — which is likely
what an earlier count mis-globbed (it attributed **11 backups to `renderer_opengl2.dll`, which has
none**). The correction *strengthens* the finding: the manual rollback system is **5× larger** than
recorded, and the most-churned module has no rollback point at all.

### D-4. `C:\mohaa-coop-dev\scratchpad\` does not exist
Every tool path cited across the record — `rcon.py`, `depthscan2.py`, `coopaudit/*.ps1`,
`coopaudit/REVERT_botinput.md`, `gen_sr4.py`, `gen_gore_skins.py`, `gen_cosmetic_unlocks.py`,
`split_options_persist.py` — is dead. "scratchpad" resolved to a session-scoped temp directory.
`.wolf/anatomy.md` corroborates this: its entries are Temp-path scripts (`curry_brace.py`,
`metavfs.py`). **Full impact list in [OPEN.md § Tooling lost](OPEN.md#tooling-lost).**

### D-5. There are TWO `_research` trees and the records conflate them
`C:\mohaa-coop-dev\_research\` (54 entries, includes the regression harness — **never at ship risk**)
vs `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\_research\` (30 entries — **was shipped to players**).
`build.ps1:27`'s exclusion only affects the mod tree. See [TRAPS.md § T12](TRAPS.md#t12).

### D-6. The regression harness now EXISTS
Recorded by an earlier pass as "a harness that did not exist on disk when I scanned." A concurrent
workflow finished writing it: `C:\mohaa-coop-dev\_research\regression\` (README, baselines, fixtures,
hzmreg, regress.ps1, regress.py, roster.json, runs). It produced bugs 1218–1220 and is **currently
the project's only working automated verification.**

### D-7. `.cmake/Release/openmohaa.exe` POSTDATES the header edit — an earlier item states it backwards
`q_shared.h` mtime **21:25**; `.cmake/Release/openmohaa.exe` mtime **21:46** (2026-07-28). The exe is
21 minutes **newer**, so it almost certainly *does* carry `MAX_SOUNDS 1600` / `MAX_CONFIGSTRINGS 8192`
/ `GENTITYNUM_BITS 11` — corroborated by its byte-size (1,710,592) matching the gl2 sandbox exe copied
at 22:22. **This narrows the diagnosis usefully: the problem is not "we don't know if a current exe
exists," it is "a current exe exists and was never copied,"** because `build.ps1` has no exe deploy
block. Fix is a copy, not a rebuild.

### D-8. buglog id-loss extent is UNRESOLVED — do not assert either version
`cerebrum.md` asserts 637 numeric ids "remain permanently lost." A parallel audit counts ~632
unassigned in `bug-1..bug-1222` and concludes they were **never assigned** (sessions guessed at the
next number rather than reading the tail). **Both are inferences from the same gap count; neither was
demonstrated.** What IS established: the 2026-07-27 post-write-hook clobber was real, 523 entries were
rebuilt from ~1.2 GB of transcripts, and **all 8 `.bak` snapshots were loaded and diffed against the
current file and contain ZERO entries absent from it** — so no historical loss is demonstrable to
date. Note also ~25 ids are **slugs**, not numbers (`bug-gl2-ztagmalloc`, `bug-ps-home-var`,
`bug-armory-roster76`), so numeric-only tooling silently skips them. Section C above states the
"destroyed and unrecoverable" version as fact; **treat it as one of two live hypotheses.**

### D-9. Stale in-code comments that will mislead a grep
| Site | Says | Reality |
|---|---|---|
| `coop_mod/main.scr:134` | Director "default OFF" | **ON** — `autoexec.cfg:381 seta coop_ddaEnabled 1` |
| `coop_mod/blueprint.scr:5-7` | "INERT UNTIL WIRED: nothing threads into this file yet" | **22 call sites** (18 `buildmode.scr`, 4 `bunker.scr`) |
| `fgame/actor.h:306` | "MAX_GENTITIES 1024" | It is **2048** |
| `q_shared.h:1680` | `MAX_MODELS` raise = "bug-866" | It is **bug-892** |
| `hzm_cvars.txt:11` (**ships to players**) | `coop_lmsLifes` | Live cvar is `coop_lmsLives` |
| `coop_mod/main.scr:1568` | "cvar from coop_lmsLives to coop_lmsLives" | A botched rename note |

### D-10. Miscellaneous count and path corrections
- **Self-test suite is 11 files**, not 12/13/14 as variously recorded: `coop_selftest.scr` + 10
  per-subsystem (`dbno, engine, keyitems, objectives, officer, scaling, triggers, vehicles, weapons,
  xp`). There is no `_loadout`, `_ai` or `_medkit` module.
- **`MAX_ENTITIES 1023` lives at `renderercommon/new/tr_types_new.h:33`** — note the `new/`. A grep at
  the recorded path `renderercommon/tr_types_new.h` returns nothing and reads as "already fixed."
- **The developer gate is three call sites**, not one: `fgame/scriptthread.cpp:2858`, `:2869`, `:2883`.
  Citing only `:2869` will look wrong to anyone who greps.
- **`main.scr:84-281` contains ~50 `waitthread`/`thread`/`exec` statements** (an earlier count said
  53 — a regex difference; either way the documented 6 is a small fraction).
- **gl2 `SKELREG`/`SKELDIAG`/`SKELDRAW` are ungated but deduped to once per model handle**
  (`renderergl2/tr_model.cpp:50-51`) — "spams unconditionally" overstates it; they are bounded by
  model count, not frame rate. The genuinely-open loose end is `r_globalFogDebug` still registered
  `CVAR_TEMP` at `renderergl2/tr_init.c:1926`.
- **bug-1205 (armory backslash script path) is FIXED** — `loadoutpick.scr:436-440` now uses forward
  slashes with a 5-line inline comment naming the bug. Do not re-investigate.
- **`r_lodscale`'s flag-OR conflict (bug-1125) is FIXED** — both `renderergl2/tr_init.c:1799` and
  `:1945` now register `"5"` `CVAR_ARCHIVE`. It is no longer among the 8 live cross-renderer conflicts.
- **The "zero of 313 player TIKs carry `sethelmet`" figure** (section A above) is directionally
  correct but not anchorable to the mod tree: `hzm-mohaa-coop-mod/models/player/` has **28** `.tik`
  files and **0** carry `sethelmet`. The 313 must come from the retail paks, which were not opened.
- **`autoexec.cfg` and `coop_defaults.cfg` are strictly disjoint** — a `comm -12` on their
  `seta <name>` token sets returns empty. There is zero double-seeding; the only defect is which side
  of the saved config a cvar sits on.
