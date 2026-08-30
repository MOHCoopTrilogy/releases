# Feature records archived from FEATURES.md

Moved out of `docs/FEATURES.md` on 2026-08-30 to bring that file back under its 90 KB ceiling.
**Nothing here is superseded** - these are complete, still-accurate records for work shipped
2026-08-02 to 2026-08-07. `FEATURES.md` keeps a one-line pointer for each.

---

## Low-health limp (2026-08-02)

**`SHIPPED`, awaiting playtest verdict.** *"when the player gets really low health they should start
playing the same limp animation the actors do, and you should see the limp in first person (camera
should imitate that as you move)."*

Below `coop_limpStart` (0.30) of `max_health`, on the ground, not dead/downed/vehicle/turret:

- **Server is the single authority.** `Player::TickLimp` sets `m_bCoopLimping` and stuffs
  `coop_limpView` to the owning client **on change only**. The client never re-derives a threshold —
  so `coop_limp 0` on a server genuinely disables it everywhere, not just the body.
- **Health signal is `health / max_health`.** Deliberately NOT a peak-health tracker: `healthonly`
  clamps to `max_health` (`entity.cpp`), so DBNO's `9999` can never inflate a peak — see bug-1290 for
  the audit that wrongly claimed otherwise.
- **3P body**: four `LIMP_FORWARD/BACKWARD/LEFT/RIGHT` states built from the real `WALK_*` legs
  blocks. Row order carries the design — **every armed class** gets `rifle_run_injured` (retail's only
  armed injured cycle), unarmed gets the full directional `walk_injured_*` set. The unarmed clip must
  never drive an armed player: a STAND torso takes its animation *from* the legs
  (`player_Torso.st:19-21`), so it would strip weapon posture.
- **Directional aliases fixed**: `walk_injured_back/_left/_right` all pointed at the **forward** clip;
  the real directional `.skc` files ship in retail `Pak0` and were simply never referenced.
- **FP camera** modulates the *existing* bob rather than adding an oscillator. The vertical term's
  `fabs()` gives it one lobe per footstep, so `sign(sin(phase-0.94))` **is** foot parity — one foot's
  dip deepens, the other's shallows, continuously. Plus amplitude-scaled ADS-damped roll and uneven
  step timing. Placed before the `MASK_PLAYERSOLID` traces so a deep dip cannot punch the eye through
  a floor.
- **Speed**: `coop_limpSpeedMult` 0.60 applied *after* the whole multiplier chain as a scale (mid-chain
  it would be overwritten by Alt-walk then re-scaled by `sv_dmspeedmult`). Never freezes — floored at
  `coop_limpMinFrac` 0.35 of run speed but **capped at the pre-limp speed**, so injured is never faster
  than healthy in the same stance. The 3P shoulder-aim floor is *scaled* by the limp mult, not skipped.
- **Dev**: `coop_limptest <frac>` sets health without damage. ⚠️ A large single-frame drop still trips
  DBNO, which derives damage from health deltas — step down with ~2s pauses.

*Anchors:* bug-1291, bug-1292. Cvars: `coop_limp`, `coop_limpStart`, `coop_limpSpeedMult`,
`coop_limpMinFrac`, `cg_limpDepth`, `cg_limpRoll`, `cg_limpRollAds`, `cg_limpDrag`, `cg_limpCamSpeed`.

## AI voice nationality — Russian added, French silenced (2026-08-02)

**`SHIPPED`, awaiting playtest.** *"we should never have any actors/reinforcements speaking the wrong
language."* Audited **all 1481 shipped human tiks** rather than the 111 the scripts name. Result:
American/British/German/Italian detection was already complete — every `allied_uk_*` caught by `_uk_`,
every `sc_al_brit_*` by `brit`. Only two real misroutes existed:

- **5 `soviet_*` models returned `"de"`** — Russian soldiers speaking **German**. MOHAA's team enum has
  only american/german, so Soviets fall through as german (the same reason the health exemption needed
  a model test). Added `"ru"` inside the german branch, plus a 22-alias `coop_av_ru_*` pool across 9
  situations drawn from the retail per-nationality **MP voice reel** (Russian is first-class there: 44
  files in `mainta`, 61 in `maintt`). `mandown`/`reload` stay **silent** — no honest line exists, and
  silence is this codebase's rule. `"ru"` also added to the allied CONTACT gate, which was `us||uk`.
- **French resistance** (`allied_resistance`, `allied_misc_manon`) drew **American** lines; now return
  `""` and stay silent, since no French reel ships.

*Anchor:* bug-1288.

## m1l1 loading screen — corkboard case file - 2026-08-07
SHIPPED-VERIFIED (user confirmed in-game). Replaces the stock two-tile aerial-recon TGA pair with a single BSP-rendered
composite: the aerial recon photo (officer position marked), a clean retypeset of the vanilla m1l1
OSS briefing letter (Col. Stanley Hargrove, found orphaned at `textures/mohmenu/levelbriefing/`,
never wired to any live menu), and 3 photos pulled from the stock `briefing1` slideshow (Torch map,
Grillo's dossier photo, terrain, pill), pinned together with a red string on a corkboard. Single
2048x2048 POT texture via the new `coop_load_m1l1` shader (`scripts/coop_loadscreens.shader`) — see
[DECISIONS.md § Loading screens](DECISIONS.md#loading-screens--single-pot-texture-new-work-only)
for why this replaces the old tile convention. Render pipeline: `_research/maprender/` (BSP extract
+ procedural recon-photo render), generator scripts for the letter/composite are scratch-only so
far, not yet copied into the repo.

## Coverage sweep (covtrace + covwalk) - 2026-08-05
Answer to "our trilogy sweeps missed a lot": absence doesn't log, so the sweep is now
coverage-driven. Engine (game.dll, coop_covtrace 1): one `^~^~^ COV` line per committed trigger
fire (volume centroid + targetname), per sound alias PLAY and per alias MISS, and per maps/*
label thread start. Static side: `_research/cov_manifests.json` (1,773 triggers across 30 BSPs)
+ generated `maps/cov/<map>_walk.scr` lists. `coop_maptest 3` = Phase 3: the rotation tick
teleports every connected player round-robin through every trigger volume, then advances.
`coop_covwalk_force 1` additionally direct-fires named triggers (chaotic - throwaway runs only).
Report: `python _research/cov_report.py` -> `_research/cov_report.md` (never-fired triggers per
map, runtime-confirmed dead aliases, labels run). Static layer 1 results:
`scratchpad dead_aliases_confirmed.json` - 170 dead alias refs on 43 maps, families
(bombtick/plantbomb/pickup_papers/door_locked) look retail-dead = restorable content.
