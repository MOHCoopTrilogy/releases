# HISTORY archive - everything before the buglog began (2026-06-26)

Split out of `docs/HISTORY.md` on 2026-08-17 to bring that file back under its 30 KB ceiling.
Nothing was edited; this is the original text. The live timeline continues in `docs/HISTORY.md`.

## Pre-history — 2020-01 to 2026-02

| When | What |
|---|---|
| 2020-01-08 | First commit `527e0d0` — chrissstrahl / Smithy. The `[200]`/`[201]`/`[202]` comment tags throughout `coop_mod` are theirs. |
| 2020 | Heavy development on the original HZM Coop Mod. `hzm_changelog.txt` runs back to 2019-03-13, ending at VERSION 2.05. |
| 2021–2025 | Near-dormant: 1–8 commits/year. **A single commit in all of 2025.** |

*Design intent from this era is unrecoverable from this workspace — it exists only as inherited code
and that changelog.*

---

## Current era begins — 2026-03 to 2026-06-20

| When | What |
|---|---|
| 2026-03 | Project picked up by the current author. The 2026 era alone is 1,382 files changed, +156,001/−21,080 across just **44 commits**. |
| 2026-06-19 → 06-25 | The SP→coop conversion campaign. ~55 root-level `.md` files date from here (`COOP_CONVERSION_MASTER.md`, five `convert_*_report.md`, nine `fix_*.md`, objective audits). |
| — | **Scope correction that still holds:** all e3/t-series targets already had `coop_mod/main.scr::main` — they were **partially** converted; the work was per-element 16-player scaling + bug fixes, not initial hookup. |
| 2026-06-21 | `V` Officer boss spawn player-confirmed working on re-test. |
| 2026-06-22 | `V` Signal smoke no longer strips German grenades — it was a world `Weapon` entity hitting `PickupWeapon`'s MP grenade branch, not a TIK problem. |
| 2026-06-25 | `V` `MAX_SOUNDS` 512→1024; the 6 hardcoded configstrings made computed; `sound_index` widened 9→10 bits. |
| 2026-06-21 | `KNOWN_WORKING_STATE.md` last updated — **it has been stale ever since**, and asserts a rule CLAUDE.md now says is wrong. |

---

