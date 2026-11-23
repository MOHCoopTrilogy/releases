# OPEN.md sections moved here on 2026-11-23 (stale: old playtest list, closed item)

### v1.10.56 playtest list
Norway hold last 45 s rush, two halftracks never stacked (east fallback + launch lock), pitched-roof perches 1-4 now allowed
(coop_asnCornerTol 6), bipod flush, storeroom gun pick-up after death, CC0 weapon sheets in game (PIAT canvas softer).

| Item | State | Anchor |
|---|---|---|
| **Coop test menu** — 94 tests across 10 subsystems, each with catches/drive/verify/evidence/risk | **The largest designed-but-unexecuted work in the project.** Several named probes exist, so parts may be built. **No run log or results file found.** Either schedule it or explicitly retire it. | `_research/coop_test_menu.md` (132 KB) |
| **Remastered main-menu room** (3D rebuild, `ui_menuRoom` twin in main.urc, default ON per user) | STAGED 09-28 (contact-gated, 2 QA rounds), not applied (mod frozen to v1.10.3). In-engine test harness ready; needs slot "menuroom". Other painted rooms (options_main, war_records ...) planned. | `docs/proposals/menu_redesign_2026-09-28/remaster_test/INTEGRATION.md` |
| **Bipod / supported aim** | Verdict: BUILD a weapon-stance supported aim (~250 LOC, game.dll + pk3); REJECT the turret-swap approach. Needs no new usercmd bit, no new PMF, no new stat. | `bipod_design.md` |
| **Limb dismemberment** | ⚠️ Read bug-861 and bug-892 first — the phase-0 precursor shipped and was pulled the same week. | `_research/limb_dismemberment_plan.md` |
| **Cover-peek physical step-out** | User verdict on peek v1: *"VERY janky - you dont actually pop out from the door opening."* Root cause understood: peek v1 only releases the torso and swings the camera; **the BODY never physically steps toward the corner**, so the muzzle stays behind the wall edge. Design queued: slide origin ~24–32u toward the detected open side (traced, collision-safe), slide back on release, keep velocity zero. | bug-311 |
| **Jeep .30cal manning pose** | Measure-first, explicitly not to be guessed. | bug-309 |
| **Blender sprint carry-pose** | Pipeline 100% working; **the user paused mid-edit** at arm-bone selection. | `blender_sprint_edit.md` |
| **Installer** | Built (Inno Setup 6, git-tracked). **DO NOT EXECUTE until explicitly asked.** | `installer/hzm_coop.iss` |
| **gl1 post-FX → gl2 ports** | 7 remaining; bloom is the template. | see [gl2](#gl2) |
| **Shadow mapping Phase B/C** | Not started. Phase A decal shadows shipped and user-approved. | `shadows_status.md` |
| **NAT phases 2+** | Phase 1 committed and locally verified. | `nat_holepunch_plan.md` |
| **Weapon-weight Phase 2** | Movement drag + rotational muzzle swing. | `weapon_weight_research.md` |
| **m3l1b FLAK objective v2** | Gun crews, back-field defenders, plant animation. | `m3l1b_cut_flak88_objective.md` |
| **Deployables skill tree** | **REJECTED by the user** — building their own model. Doc kept, marked superseded. | `skilltree_plan.md` |

**gl2 render upgrades** (designed 2026-09-13, `_research/gl2_render_upgrades_design.md`) — **BUILT + SHIPPED**
in `renderer_opengl2.dll`, menu-wired (`coop_postfx.urc`), seeded (`coop_defaults.cfg`). Verified in the
engine 2026-09-15: exposure-aware bloom (`r_ppBloomMode 1` default), render-scale supersampling + FSR1
(`r_renderScale`/`r_fsrSharpness`, 1.0 native default), soft particles (`r_softParticles 1`), MSAA
(`r_ext_multisample`), tonemap/exposure, per-map + night colour grade. (A2C: see the gfx flip entry.)
**Still awaiting a PLAYTEST** to tune/confirm, not code.

**MP armories slice 2** (designed 2026-09-13, **APPROVED, not built**;
`_research/mp_armories_slice1_plan.md`) - engine hooks E1-E7, a live dispatcher, and a side picker to
make slice 1's inert MP-only screens (committed 59fa75d7) reachable.

**Security layer 2 - exe-side server-origin taint** - now **BUILT + SELF-TESTED** (2026-09-13, bug-2580
follow-up), runtime covtrace pass pending (see Awaiting-verification above). Filters EVERY server-origin
line in the exe; a refuse-list for self-vstr'd cvars (no persisted taint); `globalwidgetcommand`
laundering stays a residual; a real cgame API handshake (v3->4).

Reference design notes, do not duplicate here: `hzm-mohaa-coop-mod/_research/compass_bar_design.md`,
`mp_decisions_2026-09-13.md`, `koth_source_notes.md`.

---

<a name="discrepancies"></a>
### 3D Join Game door - CLOSED 2026-11-02
User: the right-hand attic door (MULTIPLAYER, `scenehot "mp"`) "should go into the multiplayer menu" - which it already does (fly-in, then `pushmenu multiplayer`, where Join Game is). Nothing to build.

