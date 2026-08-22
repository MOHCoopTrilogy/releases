# OPEN.md section archived 2026-08-22 - the 2026-08-18 evening playtest batch

Moved out of `docs/OPEN.md` to bring it back under its 45 KB ceiling. Everything here was
AWAITING a playtest on 2026-08-18; the v1.4.0, v1.4.1 and v1.4.2 releases have since shipped
and the items were either verified in play or superseded. Kept verbatim because a few carry
root-cause detail (the MG42 spread average, the cut-VO batch, the loadout deep-trace wave)
that is worth finding again, but none of it is a live question any more.

## Awaiting the next playtest (2026-08-18 evening batch)

All deployed, boot-verified 0 script errors, committed. Root causes in buglog 1919-1923.

- **m3l3 Ramsey conversation now keys on the halftrack's death** (bug-1924): wave stops, 12s
  mop-up grace, then the reveal + conversation fire directly - no more BSP-trigger or
  stuck-straggler stalls. Verify: kill the halftrack, Ramsey chats within ~15s worst case.

- **MG42 accuracy ROOT-CAUSED AND FIXED (bug-1940, 2026-08-19)**: manned turrets never read
  bulletspread - all three prior tunes were placebos; the real knob (m_vAIBulletSpread /
  `aibulletspread`) is now fed by coop_mg42AiSpread (seeded 300, retail band 300-450),
  trilogy-wide. VERIFY on m3l3: guns should spray suppressive near-misses (+-37u at 500u per
  shot). PROOF PROBE: `set coop_fireDebug 1` in console -> every AI turret shot logs
  `^~^~^ TURSPREAD ... vSpread=(0.0 0.0) aiSpread=(300.0 300.0)` - zero proves the old bug,
  300 proves the fix. Tune live with coop_mg42AiSpread if 300 feels too loose/tight.
- **Cut-VO restoration batch 1 SHIPPED (2026-08-19)**: 1,389 never-played retail takes folded
  into the aivoice driver via generated pools (gen_chatter_pools.py -> ubersound/
  coop_chatter.scr, retail map-gates stripped): BT Global Dialog classified by its own meaning
  comments into cover/backup/attack/contact pools for all four nationalities; allied
  suppressing-fire calls (574) on a new loop branch keyed off the engine's coop_suppressedAt
  stamp on the ALLY'S TARGET; allied reload shouts (283) into the existing reload situation
  (zero new hooks); den_fear (166) rides the suppression pose; German idle banter
  (laugh/joke, 26) on a sparse idle branch; "HANDS UP!" (6) from the nearest German on a
  disguise bust. VERIFY in play: ally calls "suppressing fire" when you pin someone near him;
  Germans laugh/joke when unaware; pinned Germans sound afraid; bust = hands-up shout.
- **CUT-CONTENT DEEP SCAN complete (2026-08-19)** - three verified digs (logic/audio/assets)
  over all 17 retail pk3s; full record in _research/cutdig_2026-08-19.md. ~40 major finds
  awaiting a restoration-batch decision; headliners: Omaha mortar-death choreography, e2l1
  glider flak, balcony jumpers, BT global squad-chatter layer (331 barks), suppression/reload
  shout categories, 13 staged-but-unwired ambience beds, dormant landmine+mine-detector
  system (engine-complete), Kar98 rifle-grenade, cut intel economy, 32 posed statues, 14
  briefing BSPs, zonespawner library (Holdout-ready).
- **Cut-content animation wave 2 (2026-08-19)**: locational hit reactions (92-row census
  whitelist: stand/crouch flinch by head/back/arm/leg from self.fact.location; arm hits can
  play the rifle/thompson dropgun flinch), mortal-wound crawl-to-death theater (collapse ->
  floor drag -> die in place, pose kept via stub deathhandler), crate-cover crouch combat
  (crate_alert for 8 groups + over-the-cover blindfire bursts for bar/thompson/vickers),
  fear facial + post-fire alert scan on suppression, anger facial on the runfire charge.
  Cvars: coop_aiHitReact 55, coop_aiCrateFight 35, coop_aiCrawlDeathChance 30. Skipped
  deliberately: curious01/02 idles (no clean generic hook) and directional walk sets.
  **First live session 2026-08-19 (odometer + error census): hitreact/dropgun/variant/g43
  all ZERO and alert/floorcrawl/surrender threw unknown-animation** - four stacked roots,
  all fixed + redeployed same day (buglog 1942-1945): always-true painhandler guard,
  actor weapon getter returning raw loadout string, anim packs (human_mp40/rifle/sten/
  vickers/pistol + scientist) not unconditionally included, and the shellshock cgame hook
  spliced into the dead PMF_CAMERA_VIEW branch. Re-verify NEXT session via AIBEHAV3
  (expect hitreact/variant/g43 > 0), `^~^~^ SHELLSHOCK` on any near blast, zero
  unknown-animation lines, and the m1l1 truck ride as the anim-budget canary. MG42
  "sometimes they don't fully overheat" (user) = designed per-gunner heat ceiling 55..95 +
  random resume, NOT a defect. TURSPREAD probe still needs `coop_fireDebug 1` set via rcon
  while a session is live.
- **Realistic vehicle explosions (engine, 2026-08-18)**: every vehicle death now layers a
  640u camera shake, 2-4 staged fuel/ammo cook-off pops (small real damage), a burning-wreck
  fire (45s, coop_vehicleFxTime) and a lingering smoke column - on top of coop_vehicleWrecks'
  persistent hulls. Covers explode-flag deaths AND script-owned wrecks (m3l3 halftrack).
  coop_vehicleFx 0 disables. VERIFY: blow a truck/tank (m1l3b jeep run, m5l3 tanks, m3l3
  halftrack) - feel the shake, watch the cook-offs, wreck burns then smokes out.
- **LOADOUT OVERHAUL - the vetted deep-trace fix wave (bugs 1928-1938, 2026-08-18 late)**:
  three parallel deep-traces + line-by-line cross-verification found ~15 independent defects;
  all four fix phases deployed and boot-clean. PLAYTEST CHECKLIST: (1) mid-mission finish/
  variant/weapon click lands in hands in ~2s WITH the right gun raised; (2) rapid-click several
  finishes then close - server converges to the LAST click within ~10s of closing; (3) re-enter
  a slot with gold applied - viewer shows GOLD not base; (4) variants cycled from slot 2/3 no
  longer touch slot 1; (5) armory browse + quit no longer loses finishes; (6) USE MAP DEFAULT
  then rejoin - no deny beeps; (7) apply while DBNO - lands on revive; (8) a player name with a
  trailing space still gets applies; (9) locked map says "kits are scripted on this mission".
- **Armory apply loop, take 3 (bugs 1926-1927)**: the regive now REBUILDS the resolved kit
  first (it was faithfully re-issuing the stale list - toast said applied, hands unchanged); the
  120s gate is deleted (no map ever set its supposed beneficiary flag; m2l2a now sets
  coop_loadoutLocked properly); finish clicks now show their finish in the 3D viewer (the 36
  fin cfgs never fired the armed previews). VERIFY: mid-mission, change a weapon AND a finish,
  hit nothing - both should be in your hands in ~2s; gold shows on the viewer soldier.
  Housekeeping: fin_/mvp_ cfg families are one-off-generated - fold into gen_loadout.
- **Armory apply loop, fully closed**: server no longer touches menu visuals (`exec` APPENDS -
  client finp/mvp chains are sole viewer authority); every finish/variant success path kicks a
  debounced regive marked COSMETIC so the 120s mid-mission gate lets it through. "Equipped"
  should now mean in-hands within ~2s, no Done needed.
- **m3l3 MG42s at effective spread 300**: AI fire uses (base+max)/2 and the tik has no max, so
  earlier tunes half-applied. All 14 guns now set all four args. Feel check: pressure, not sniping.
- **Corner cover deaths**: wall-anim family resolver (8 live groups, rifle fallback) ends the
  standing-corpse / frozen-grenadier hangs on both corner scripts.
- **AI weapon-variant randomizer** (`coop_aiVariantChance` 35): every actor chance-rolls onto a
  model variant of his own gun; faction guard skips the British SMLE under the Springfield host.
- **Two-handed sprint = Omaha Thompson beach charge** (pistol/grenade keep the alert dash).
  ⚠ .st errors only surface at first PLAYER SPAWN (ERR_DROP), not dedicated boot - first join is
  the real verification.
- **Officer heal metered to 60s**, and the 11-behaviour AI animation program (suppression pose,
  squad surrender, grenade martyr, corner nades, arrival slide, runfire, wounded variety, MG42
  side-steps, long-range prone dwell) - all feel-unverified until played.


---

# Also archived 2026-08-22: m2l2a Phase A state snapshot (2026-08-10)

Superseded by the acceptance test that PASSED on 2026-08-11.

## m2l2a stealth - state after Phase A (2026-08-10)

Plan: `docs/proposals/m2l2a_coop_stealth_master_plan_v2.md` (1448 lines, 25 steps, vetted 3x).
Baseline allowlist: `docs/proposals/m2l2a_phaseA/TP-BASE_allowlist.md` (EMPTY - any Script Error is new).
Failure ledgers live in `.wolf/buglog.json` under `failed_attempts` - **READ THEM BEFORE RETRYING.**

**Shipped and verified in play:** papers-checker freeze gone (bug-1631); full mission completed with
zero Script Errors; Naxos quiet sabotage; two guards accepted papers.

**VERIFIED IN PLAY 2026-08-10 (card players flawless, welders welding, crate guy has his crates; prone 4->0, hurt 6->0, path-failures 138->0, zero Script Errors over ~12k lines):** A4 scene-actor exemptions (card man, welders, crate guys, wrenchman,
sledgehammer man, scientists, the 14 ai_alarm runners). Expect: no card player stands, welders weld,
and the 138 `Path not found in Actor::MoveToPatrolCurrentNode` warnings drop to ~0.

**Open, blocking Phase C design (bug-1652):** a checker that genuinely opens fire escalates NOTHING -
no alarm, no other actor. Our alarm guard tests only the player's disguise, with no "a german is
already shooting him" term, and the T5 backstop as re-derived in vetting round 3 EXCLUDES halt-origin
attacks, which is exactly how this bust arrives. Resolve deliberately before Phase C.

**Open, engine (bug-1651):** a checker beyond ~256u goes halt -> ATTACK after 1.5s with no disguise or
papers test. Vanilla mechanism; decide whether coop gets a grace window to approach.

**Blueprint pickup - MEASURED at last (bug-1665, was bug-1632).** Nine attempts. The resolver probe
sampled 90 consecutive failures and every one said the same thing: `player_closestTo` returned NULL
while an inline `$player` scan TWELVE LINES BELOW read both players fine (`hp=750 team=allies act=1
noclip=0`, `want=` matching a live entnum). Fix deployed 2026-08-10: owner resolved INLINE by string
entnum, "closest player" dropped as the semantic (each player has a private copy). **Awaiting the
run where `BP OWNER ok` prints for the first time.** Ruled out BY MEASUREMENT, not argument: all
four filter fields, and noclip.

**Open (bug-1666) - not fixed, deliberately deferred.** `flags["coopDevNoclip"]` is a LATCH: noclip
on -> die -> `developer.scr:548` early-exits on `health <= 0` -> the flag survives the respawn -> that
player is filtered out of `player_closestTo` / `player_closestTargetable` for the rest of the map,
with no message and no error. Two-line fix (clear it in the spawn path; let the toggle run while
dead) held back so it could not muddy the in-flight blueprint test.

**Open (bug-1664) - dedicated server never loads a map.** `omohaaded.exe` opens its socket and then
processes NO command-buffer entry at all: not `+exec`, not a bare `+map`. Harness reverted to the
listen server; `launch_dedicated_2player.ps1` kept for when it boots. The motivation is measured, not
cosmetic: `common.c:2354` hands `SV_Frame` the WHOLE main-loop time, so on a listen server the "slow
server" warning really means "the host fell below ~36fps", and the host's own inputs are acknowledged
instantly while a remote client's are not - a distortion present in every 2-player test to date.

**Still open:** bugs 1641..1645 (shipped-code defects found during vetting, none fixed), bug-1662
late-join disguise lockout (Phase C covers it).

**Next:** verify the blueprint fix in play, then Phase C (unarmed route + Situation Contained), which
is gated on resolving bug-1652 first.

### Scripted-conversation guard sweep (TRAPS: waittill outranges its guard)

`docs/proposals/conversation_guard_sites.json` lists **196** sites, of which **48 are do-not-guard**
(alarm cues - silencing those soft-locks a mission). Helper `replace.scr::convOk`.
**m6l1c done; 189 remain.** The failure shapes and the rule live in `docs/TRAPS.md`.
