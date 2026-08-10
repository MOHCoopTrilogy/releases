# Source of Truth — Part 1: Chronology Backbone

**Compiled:** 2026-07-29. **Method:** git history of all three repos + release manifests + file mtimes.
**Scope:** what actually shipped, when, and where the record is missing. Other SOT parts hang off this.

Status vocabulary used throughout the SOT set:

| Status | Meaning |
|---|---|
| `SHIPPED-VERIFIED` | in the code AND confirmed working in play |
| `SHIPPED-UNVERIFIED` | in the code, never confirmed by a playtest |
| `REVERTED` | was done, then undone |
| `PLANNED` | designed, not built |
| `OPEN` | known defect, no fix |

---

## 1. Repo topology — there are THREE git repos, not one

This is the single most important structural fact, and it is not in CLAUDE.md.

| Path | Repo? | Commits | Branch | Tracks |
|---|---|---|---|---|
| `C:\mohaa-coop-dev\` | yes | 54 | `main` | **Release pipeline ONLY.** `.gitignore` line 2 is `/*` — an allowlist repo. Tracks 47 files: `build.ps1`, `publish_release.ps1`, `installer/`, `updater/`, `manifests/`, `README.md`. |
| `hzm-mohaa-coop-mod\` | **yes** | **1393** | `coop-wip` (ahead 4 of `org/coop-wip`) | The mod source. **Explicitly gitignored by the root repo** — easy to miss and has been missed. |
| `openmohaa-hzm\` | yes | 4980 | `hzm-coop-working` (ahead 1 of `org/…`) | Engine fork. |

Evidence: `.gitignore:2`; `git -C hzm-mohaa-coop-mod log --oneline | wc -l` = 1393; `git -C openmohaa-hzm status -sb`.

> **Correction to prior folklore:** memory notes say the engine repo is on "detached HEAD". It is not —
> it is on branch `hzm-coop-working`, 1 commit ahead of `org/hzm-coop-working`. The *uncommitted*
> part of that claim is true and is the real hazard (see §6).

---

## 2. Eras

| Era | Dates | Owner | Commits | What it is |
|---|---|---|---|---|
| **E0 — Upstream HZM** | 2020-01-08 → 2025-02-14 | chrissstrahl / HaZardModding | 1349 | Original HaZardModding Coop Mod. Reached tag `Release-204` / changelog `VERSION 2.05`. Changelog itself says "Changelog started 2019.03.13". |
| **E1 — Quiet fork** | 2026-03-05 → 2026-04-11 | this project | 18 | Legal/README rework, then a run of small "Coopified" commits (e3l1, jeep gunner). Low volume, single-file diffs. |
| **E2 — Engine fork opens** | 2026-07-01 | this project | — | `openmohaa-hzm` baseline commit `eaac51be` "HZM coop: engine working baseline (restore point)", 88 files / +6191. Forked from upstream openmoh/openmohaa at `a72bc153` (2025-08-03). |
| **E3 — Release era** | 2026-07-04 → now | this project | 26 mod + 12 engine | Installer, auto-updater, manifest pipeline, v1.1.0 → v1.1.55. All heavy feature work. |

**"Day one" of *this* project's AI-assisted work = 2026-06-25** (`.wolf/` scaffolding created 2026-06-25 16:16; first buglog entry 2026-06-26). Everything before that is upstream or the quiet fork.

> ⚠️ **The 2026-06-25 → 2026-07-01 week has NO commits in any repo.** Mod repo jumps 2026-04-11 → 2026-07-01. That week's work (60+ buglog entries, per-map coop conversion) landed inside the squashed snapshot commit `4fa27cd` (337 files, +42954/-4875, 2026-07-01 12:32). Its individual history does not exist.

---

## 3. Release timeline (authoritative — from `manifests/manifest-*.json`)

Each row lists only the assets whose download URL points at *that* version, i.e. what actually changed.
`code.pk3` = `zzzzzz_co-op_hzm_mod_code.pk3` (scripts/UI/config). Headline from the matching mod commit.

| Ver | Date | Binaries changed | code.pk3 | Headline (mod commit) |
|---|---|---|---|---|
| 1.1.0 | 07-05 | exe, cgame, game, gl1, gl2 | ✓ | First release. 3-way pk3 split, launch-time updater, Inno installer, all HD/HRRTM packs. |
| 1.1.1 | 07-05 | — | — | updater + report_problem only |
| 1.1.2 | 07-05 | — | ✓ | Coop menu: SH map tiles + BT mission 3 (`cabef98`) |
| 1.1.3 | 07-05 | — | ✓ | Menu polish: 6-per-row boards, m6l3e finale, ghost-label root fix (`fdef366`) |
| 1.1.31 | 07-05 | — | ✓ | *(version scheme jumps 1.1.3 → 1.1.31; 1.1.4–1.1.30 never existed)* |
| 1.1.32 | 07-05 | exe | ✓ | + snd pk3, hd_skybox |
| 1.1.33 | 07-05 | exe, cgame, game | ✓ | Spawn protection, DBNO corpse-revive, strike warnings, deployable QoL (`dd34fe3`). Updater v3 + What's New card introduced. |
| 1.1.34 | 07-06 | exe, cgame, game, gl1, gl2 | ✓ | Officer wave cooldown + accuracy nerf, paratrooper buffs (`6de6f9c`). DXT `hdmem` pack (1.0 GB) added. |
| 1.1.35 | 07-06 | exe, game | ✓ | m1l3c label-mangle fix (campaign sweep 46/46 clean), Garand any-time reload, AB41 squad ride (`57a9c79`) |
| 1.1.36 | 07-06 | exe, cgame, game | ✓ | 3P shoulder-ADS defaults + HUD-fade cvars, e3l3 officer removed (`9c3cc33`) |
| 1.1.37 | 07-06 | cgame | ✓ | sniper hotfix (`8115ed3`) |
| 1.1.38 | 07-06 | — | ✓ | m1l3a full-squad jeep ride (`059b5d8`) |
| 1.1.39 | 07-07 | exe, cgame, game | ✓ | 3P free cam, emotes, sprint anim, DBNO cinematics, FOV slider (`3eb8f9b`) |
| 1.1.40 | 07-07 | exe, cgame, game | ✓ | XP system Phase 1, take-cover (experimental), turret 3P, freecam v2, build mode (`8efdc7e`) |
| 1.1.41 | 07-07 | exe, cgame, game, gl1, gl2 | ✓ | Cover 2.0 aim-follow, .30cal gunner overhaul, officer player-count scaling, 1P FOV fixes (`f7012fb`/`9c226e5f`) |
| 1.1.42 | 07-09 | exe, cgame, game, gl1, gl2 | ✓ | **Coop lobby** + full campaign, XP overhaul, build-mode categories (`8ced1b4`/`e3efec1c`) |
| 1.1.43 | 07-10 | exe, cgame, game, gl1, gl2 | ✓ | Omaha bunker cut-content restore, report-a-bug, display modes (`81bed9a`/`7035adb2`). **`zzzzz_xw_weapons.pk3` first ships.** |
| 1.1.44 | 07-11 | exe, cgame, game, gl1, gl2 | ✓ | updater regenerates `coop_reportwebhook.cfg`; KUN weapons pack dropped |
| 1.1.45 | 07-11 | cgame, game | ✓ | — |
| 1.1.46 | 07-12 | — | ✓ | — |
| 1.1.47 | 07-13 | exe, cgame, game | ✓ | — |
| 1.1.48 | 07-14 | exe, game | ✓ | **Weapons-on-back** (holster data live in 37 tiks), cut dialogue wave 1, Frontline chatter + 150 death cries + 7 ambience beds, helmet switcher, armory phase 1, lobby (`1561019`/`a5b498ee`) |
| 1.1.49 | 07-19 | exe, cgame, game, gl1, gl2 | ✓ | Weapon unlock progression 3-route system + armory padlock gate (`52b6e1f`, committed 07-16) |
| 1.1.50 | 07-20 | exe, cgame, game, gl1, gl2 | ✓ | — |
| 1.1.51 | 07-22 | exe, cgame, game, gl2 | ✓ | **e1l2 invisible-wall resolution** (cmpatch), all-maps void guardian, artillery objective fix, build-mode structures/blueprints (`92aeb06`, 784 files/+39056) |
| 1.1.52 | 07-23 | — | ✓ | Co-op stability pass: 4-player full-trilogy sweep, ~45k script errors eliminated, 46/54 maps clean (`425dc4d`, 44 files/+8978) |
| 1.1.53 | 07-23 | game | ✓ | Server crash fix + tank-aim storm + long-tail 4p fixes (`fdd006a`) |
| 1.1.54 | 07-23 | — | ✓ | **FIX the 1.1.53 crash fix — `autoexec.cfg` negated it** (`f10ac19`) |
| 1.1.55 | 07-27 | game | ✓ | last shipped release |

**Currently deployed binary set (per `manifests/latest.json`, v1.1.55):**
`openmohaa.exe` and `cgame.dll` from **v1.1.51**, `game.dll` from **v1.1.55**, `renderer_opengl1.dll` from **v1.1.50**, `renderer_opengl2.dll` from **v1.1.51**. The renderers are the stalest shipped components.

---

## 4. Engine commit timeline (`openmohaa-hzm`, HZM-authored only)

12 HZM commits + 1 upstream merge point. Everything else on this branch is upstream openmohaa.

| Commit | Date | Files/+ | Content |
|---|---|---|---|
| `a72bc153` | 2025-08-03 | — | **Fork point.** Last upstream openmohaa commit before HZM work. |
| `eaac51be` | 07-01 00:17 | 88 / +6191 | HZM coop engine working baseline (restore point). Includes `code/tools/md5_2_skX` converter. |
| `95c74f48` | 07-01 12:37 | 1 / +7 | duckable-glued (seated) players can stand |
| `7f513fb5` | 07-01 16:12 | 1 / +3 | `MoveVehicle` skips glued riders (don't crush passengers) |
| `0d0a79d0` | 07-01 21:08 | 6 / +145 | vehicle ride: smooth glued-rider view, damage-while-riding, hold-crouch |
| `69806d8e` | 07-02 00:41 | 3 / +102 | tempmodel PVS-cull + Phase-A directional shadow + ADS tune-seed |
| `6da53e80` | 07-04 21:10 | 26 / +978 | full audio stack + post-FX + gameplay engine work (ships as v1.1.0) |
| `9c226e5f` | 07-07 14:18 | 37 / +2612 | v1.1.41: cover aim-follow, crosshair in cover, .30cal seat, shoulder speed floor, `cg_freecam` ARCHIVE |
| `565f561e` | 07-07 17:29 | 14 / +388 | freecam batch [237-239], console paste, XP cover/blindfire stamps, NAT rendezvous phase 1 (engine side) |
| `8cdd85f2` | 07-08 16:29 | 5 / +319 | coop lobby engine support (frozen parade-rest pose) |
| `e3efec1c` | 07-09 00:40 | 5 / +86 | v1.1.42: coop lobby input, wallbang XP flag, HUD-fade exemption |
| `7035adb2` | 07-10 19:24 | 21 / +523 | report-a-bug POST, console/intro + display-mode fixes, `coop_*` servercmd whitelist, rain sky-gate |
| `a5b498ee` | 07-16 21:06 | 22 / +455 | v1.1.48: helmet EV_Stop settle + `g_helmetlife` + clank, holsterOffset pass-through, FindResponder v2, MAX_CVARS 4096, head bob, bsinc resampler |
| `819a6e93` | **07-23 10:28** | 4 / +536 | 3 dev-debug cvars defaulted OFF (server crash + spam fix) — **LAST ENGINE COMMIT** |

---

## 5. The uncommitted tail — the biggest hole in the record

| Repo | Uncommitted | Untracked |
|---|---|---|
| `openmohaa-hzm` | **119 files, +10076 / -478** | 20+ new files incl. `tr_gore.c` (gl1 **and** gl2), 15 new GLSL post-FX shaders (bloom, dof, fxaa, chromab, filmgrain, frost, heathaze, lowhealth, raindrops, sharpen, suppression, tonemap_hzm, underwater, globalfog) |
| `hzm-mohaa-coop-mod` | **65 files, +2478 / -1307** | 81 paths incl. `coop_mod/aibehav.scr`, `aicombat.scr`, `aimaneuver.scr`, `aisquad.scr`, `aivoice.scr`, `coop_selftest*.scr` (5 files) |
| root (release repo) | `build.ps1` only | — |

**Everything from 2026-07-23 10:28 (engine) / 2026-07-23 11:27 (mod) to 2026-07-29 exists only in the working tree.** That is ~6 days covering the largest single-day buglog spikes of the whole project (07-27: 43 entries, 07-28: 75 entries). It is unbacked-up and un-bisectable.

Largest uncommitted engine hunks: `fgame/sentient.cpp` +902 (gore), `renderergl2/tr_postprocess.c` +842, `tr_shade.c` +791, `tr_backend.c` +734, `tr_model.cpp` +686, `renderergl2/tr_shader.c` +429, `tr_light.c` +424, `qcommon/cm_load.c` +208 (the e1l2 cmpatch brush surgery).

> ⚠️ `renderergl2/*` is being **concurrently edited by another workflow** as of this writing — those numbers move.

Also unpushed: the mod repo is 4 commits ahead of `org/coop-wip` (v1.1.51–v1.1.54 snapshots), and the engine repo 1 commit ahead.

---

## 6. Where history is missing or squashed

| Gap | Effect |
|---|---|
| **Mega-squashes** — `4fa27cd` (07-01, 337 files/+42954), `ddf0930` (07-04, 152 files/+21302), `1561019` (07-16, 383 files/+22143), `52b6e1f` (07-16, 352 files/+3313), `92aeb06` (07-21, 784 files/+39056) | ~128k inserted lines land in 5 commits. `git log <file>` and `git bisect` are near-useless for the fork era. |
| **2026-06-25 → 07-01 dead week** | No commits anywhere; the first coop conversion sweep is only inside `4fa27cd`. |
| **2026-07-23 → 07-29** | Uncommitted (see §5). |
| **Buglog id holes** | `.wolf/buglog.json` has **585** `bug-N` entries + 55 slug-id entries = 634, but ids run 1 → 1217 → **633 ids missing (52%)**. Large contiguous holes: 169-220, 503-525, 555-585, 649-701, 963-1000, 1029-1048, 1070-1102, 1107-1121. A recovery event happened 2026-07-27 (`buglog.json.recovered_bak`, 635 KB, alongside `buglog.json.bak_20260727_0115` of identical size). **Treat "no bug-N found" as "unknown", never as "did not happen".** |
| **`.wolf/memory.md` (1.30 MB) / `cerebrum.md` (525 KB)** | Append-only, no index, no status field. Cannot be read end-to-end. Useful only as a grep target. |
| **`hzm_changelog.txt`** | Upstream HZM only, stops at VERSION 2.05. **Zero fork-era content.** Not a source of truth for anything after 2025. |
| **`CLAUDE.md`** | Last substantive content predates the release era; does not mention the three-repo topology, the manifest pipeline, or any v1.1.x feature. |

---

## 7. Record-vs-code protocol (and the case that motivated it)

**Rule: when a record and the code disagree, the code wins, and the discrepancy gets flagged here.**

**The m1l1 +180 roll case — resolved, and the lesson is different from the folklore.**

- `bug-1173` (2026-07-28) — *"Added `local.a[2] = local.a[2] + 180` (roll correction) immediately after each of the 3 passenger `gettagangles` calls."* Reads as SHIPPED.
- `bug-1184` (2026-07-28) — *"REVERTED my own unverified +180 roll correction on guy01/guy2/guy3 (bug-1173) — it was based on a gimbal-lock theory I never confirmed, the live result is contortion rather than a clean rotation."*
- **Code check:** `hzm-mohaa-coop-mod/maps/m1l1.scr` — no `+ 180` near any `gettagangles` (lines 750, 781, 1620, 1629, 1674). Line **1683** carries an explicit `// REVERTED (bug-1184):` comment.

So the buglog was **not wrong** — it recorded both the apply and the revert. The failure was **navigational**: an append-only log with no per-item status means a reader who finds `bug-1173` and stops has a confidently wrong answer. This is exactly why every SOT claim carries a status field and why superseding entries must be linked. Status: **REVERTED**, evidence `maps/m1l1.scr:1683` + `bug-1184`.

Second flagged discrepancy, same shape: `bug-1183` — a `MAX_SOUNDS` raise was attempted and **reverted to the known-good 1280** (`openmohaa-hzm/code/qcommon/q_shared.h`), because of a reliable-command / MAX_CONFIGSTRINGS constraint. The memory index still advertises "MAX_SOUNDS 512→1024" and separately "1024→1280"; the live value is **1280** and there is an inline comment warning the next attempt off.

---

## 8. Unverified / folklore (no anchor found)

Recorded here rather than silently asserted or dropped:

- **"t-series maps need a separate `com_target_game 1` launch."** CLAUDE.md itself marks this obsolete ("verified 2026-07-05, 9/9 coop-active dedicated boots") but the claim still circulates. No commit anchors either side.
- **"Engine repo is on a detached HEAD."** Contradicted by `git status -sb` → `hzm-coop-working`. Probably true at some earlier point; stale.
- **"~45k script errors eliminated / 46 of 54 maps clean" (v1.1.52).** Commit-message claim only; no artifact in the repo backs the count. Treat as SHIPPED-UNVERIFIED pending the sweep log.
- **Mod-file mtime spike 2026-07-27 (468 files).** All 458 `.cfg` are under `ui/loadout/` — a bulk regeneration by the armory generator, not 458 hand edits. Do not read mtime spikes as authorship.
- **`hzm-mohaa-coop-mod/README.md`** says "up to 16 players (4 for the true experience)" and the root README repeats it. No test artifact for >4 players exists; the only sweep harness is 4-player (`fourplayer_trig.ps1`).

---

## 9. How to use this file

1. **Dating anything?** Use the release table (§3) — manifests are the only self-verifying record (sha256 + URL per asset).
2. **"Did X ship?"** Check whether the binary that carries X appears in a manifest *after* the commit that added it. A `game.dll` change committed 07-28 has **not** shipped (latest game.dll = v1.1.55, built 07-27).
3. **"When was X written?"** For fork-era code, `git log` will lie by pointing at a mega-squash. Cross-check the buglog id range and the manifest date instead.
4. **Anything dated after 2026-07-23** is working-tree-only. Confirm against the file on disk, never against a commit.
