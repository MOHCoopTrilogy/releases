# HISTORY — condensed chronology

One line per item. Status codes: `V` verified · `U` unverified · `D` code-disabled · `R` reverted ·
`O` open · `P` planned. Full detail in [FEATURES.md](FEATURES.md); open items in [OPEN.md](OPEN.md).

**⚠️ Coverage boundaries.** `.wolf/buglog.json` (the only structured record) begins **2026-06-26** at
`bug-535`; bugs 1-534 are absent, and ~28 ids cited in source (bug-237/239/241) have no entry. Git
history reaches 2020 but in snapshot-shaped batches, so it cannot be bisected. "Since day one" means
since 2026-06-21; earlier dates are lineage, not record.

---

## Before the buglog (2020-01 -> 2026-06-20)

Moved to **[archive/history-pre-2026-06-26.md](archive/history-pre-2026-06-26.md)** on
2026-08-17 to keep this file under budget: pre-history, the current era's opening, and the
pre-buglog months.

## 2026-06-26 -> 07-10  (archived)

Moved to [archive/history-2026-06-26-to-07-10.md](archive/history-2026-06-26-to-07-10.md) on
2026-08-24 to keep this file inside its ceiling. The buglog begins; the coop framework, officer
waves and the first engine fixes land.

## 2026-07-11 → 07-20  (archived)

Moved to [archive/history-2026-07-11-to-07-20.md](archive/history-2026-07-11-to-07-20.md)
on 2026-09-08 to keep this file inside its ceiling. Weapons-on-back, the armory and
loadout system, the entity-pool saga, and the first ADS work.

## 2026-07-21 → 07-29 (archived)

Moved to [archive/history-2026-07-21-to-07-29.md](archive/history-2026-07-21-to-07-29.md)
on 2026-09-14 to keep this file inside its ceiling. Addon-spawner restore, engine constant
limits, gl2 migration, combat-verification rig, doc set commissioning.

---

## Release line

| Version | Note |
|---|---|
| 1.1.33 (07-05) | Spawn protection, DBNO corpse-revive, sniper 3P parallax, What's New pipeline |
| 1.1.36 (07-06) | HUD fade batch |
| 1.1.39 | DBNO cinematic anims, 3P free cam |
| 1.1.40 | Cover system (EXPERIMENTAL) |
| 1.1.45 (07-11) | e1l4 alarm |
| 1.1.48 | Weapons-on-back, cut dialogue, battle chatter, 150 death cries, 7 ambience beds, helmet switcher, armory, lobby — **all in one commit** |
| 1.1.49 (07-18) | Shipped. `zzzzz_xw_weapons.pk3` sourced from here. |
| **1.2.0** | **Notes finalised 07-18, NEVER PUBLISHED.** The `_final.md` file is unmarked and reads as authoritative — a trap. |
| 1.1.50 | `renderer_opengl1.dll` still sourced from here in the current manifest |
| 1.1.51 (07-21) | `openmohaa.exe`, `cgame.dll`, `renderer_opengl2.dll` still sourced from here |
| 1.1.52 – 1.1.54 | |
| **1.1.55** (07-26) | **Current.** `game.dll` from here; everything else older. |

---

## What the timeline shows

1. **Velocity is high, verification is not** — ~75 systems in ~5 weeks, ~15 recorded confirmations; the backlog is playtests, not features.
2. **The most expensive bugs were all silent** (entity-pool stomp, grenade veto, grade uniform, `Hunk_Clear` static, snapshot discard); the biggest wins came from *proving execution*, not reading code.
3. **Two records systems degraded predictably**: the append-only ones (`memory.md`, `cerebrum.md`) became unreadable; the structured `buglog.json` kept working. **Structure + a lookup key is the whole difference.**

---

## 2026-08-02 — PDF defect sweep, the limp, and two gl2 rendering bugs

46 buglog entries (bug-1251 -> 1296), **most silent-veto and found by the runtime log, not static
audit**: RC1's charges detonated ~0.3 s into load across 16 sites; `coop_painThread` was an uncleared
bullet-sponge latch; 11 maps took the armory loadout back; one `1e-5` gl2 fog epsilon exempted
everything past 88-98% of zFar. The three lessons (a failed `waittill` does not abort; shared-source
reviewers are not corroboration; the expensive fix refuted by measurement) live in
[TRAPS.md](TRAPS.md) T3/T11; per-bug detail in the buglog.

- 2026-08-05: coverage sweep shipped (engine covtrace + maptest Phase 3 covwalk + diff reporter); layer-1 static scan found 170 dead alias refs on 43 trilogy maps
- 2026-08-07: V m1l1 loading screen rebuilt as a single BSP-rendered "case file" composite (recon photo + retypeset OSS letter + 3 stock briefing-slide photos, pinned on a corkboard); single 2048x2048 POT texture replaces the old two-tile TGA pair, new explicit `coop_load_m1l1` shader (force32bit) closes the one real gap vs. vanilla UI shaders
- 2026-08-07: U XP rebalance (downed fight/officer kill/assist/vehicle-destroy retuned, attacker-only vehicle-kill via new `coop_vehKillerNum` engine plumbing, air-strike-kill + Searchlight Disabled bonuses added) + Service Record reward-name overlap fix (curated 180+-entry `REWARD_NAMES` table, Armory-matched weapon names) + 11 named-NPC trilogy skins shipped as real armory unlocks (bug-1521)
- 2026-08-07 (later): pinned-challenge popup restricted to pins only (bug-1522) + pin checkbox made clickable + "N/5 Pinned" summary added (bug-1523, required an openmohaa.exe rebuild) + native MP-options skin selector redirected to the Armory instead of writing dm_playermodel directly (bug-1524)
- 2026-08-07 (even later): Service Record description-truncation fix (shrink-to-fit instead of ellipsis, bug-1525) + helmet-nodraw whole-roster audit (4 real overlap gaps fixed, bug-1526) + Armory model-viewer unlock-caption overlap fixed with a backing panel (bug-1527) + MEDALS & BADGES shipped: 12 category-derived meta-achievements, new Service Record tab, procedural placeholder art (bug-1528)
- 2026-08-07 (v1.2.2 release): U Service Record reorganized - 23 category tabs collapsed to 9 with a wraparound pager (the 5 weapon categories share one WEAPONS tab), per-challenge reward moved out of the baked row onto a `hovershader` reveal, several challenges recategorized. Same release: 13 new helmets/headgear each gated on a thematic challenge or rank, all 135 armory skins made bare-headed so a chosen helmet fits, helmet roster renumbered contiguous 1..135. Frost-on-lens REMOVED from snow (bug-1547, publisher deleted in cgame so it is inert regardless of a stale archived `r_ppFrost`). m1l3c fog profile; Grillo OSS-uniform gore on m2l1; fog-editor save fixed (`coop_fog_mapName` parsed a nullable `level.script`).
- 2026-08-07: R Service Record completion checkmark REVERTED after six attempts (bug-1546). The pin box is back to the v1.2.1 widget pair (`pinbox` + `pinmk` on `coop_uiP`); both the `coop_uiD` tick and the `coop_uiC` shader-path box are gone. Root cause of the whole saga: `CL_SyncSR_f` (`coop_srsync`) never executes from the disconnected menu, so five successive fixes living inside it could not take effect - see [TRAPS.md T3](TRAPS.md#t3). Standing rule from this: do not replace a working UI widget with an unverified rewrite.
- 2026-08-07 (v1.2.201 hotfix): V SFX-slider routing fixed (bug-1556) - CHAN_LOCAL/CHAN_LOCAL_SOUND were treated as menu chrome and never got the `s_sfxvolume` multiplier, so the challenge typewriter, injured cue, `snd_gasp` sprint breathing and `coop_headshot` stayed at unity while the rest of the world scaled; with the user's slider at 2.0 that read as "quieter even with the dial turned up". Diagnosed live over rcon. Same release: per-shot `COOP_BINOC_CHECK` print removed from `game.dll` (it shipped to players in 1.2.2, one console line per bullet) and the stock per-change music `DPrintf` removed so `developer 1` stays usable - it has to stay on, because build mode reports placements through `println`, which developer gates.
- 2026-08-07: V m3l1b full coop pass - it had NO spawn coverage end to end. Start spawns + a checkpoint on the map's own `level.clear_bunker >= 6` gate; 27-strong rear garrison spawning when the FLAK 88 objective opens; 34 build-mode props baked in. Three root causes closed on the restored FLAK objective: `$88mm_weapon1/2` are class **Animate** not TurretGun so `startFiring`/`setAimTarget` had never worked (bug-1553, driven by the model's own `fire_scripted` anim now); no flak FIRE alias listed `m3l1b` in its `maps` spec so nothing was audible either (bug-1548); and `bomb_thinker` hardcodes its own `bomb_tick_time`/`bomb_set_time` over ours, giving a silent 45s fuse that read as a dud (bug-1549 - now a 15s visible stopwatch and a one-press plant).
- 2026-08-07: O Build mode is a CAPTURE tool, not persistence - it writes `coop_mod/save/build_<map>.dat` and nothing loads it at runtime, so placements are lost on map reload until baked into a script (bug-1554). Not communicated to the user before they placed 34 objects.
- 2026-08-08: U helmet unlock gate made wear-time, not just pick-time (bug-1578) - `helmet_apply` range-checks and re-validates the stored index, falls back to a DETERMINISTIC index 1, and `helmet_lockNotice` says "locked" once per distinct item, not on every `,hn` resend. Same batch: m6l1c conversation-guard pass (bug-1579, TRAPS T16); two manned MG42 nests baked into `maps/m3l2.scr`. **None deployed** - the game was running, which `build.ps1` refuses.
- 2026-08-08 (later): U crewed AA emplacements - all three placeable AA guns get an animated gunner; the two mannable ones hand off to a player on mount and take the crew back on dismount. Two verified mechanisms: `QueryTurretSlotEntity 0` addresses a runtime-`spawnturret` cannon (retail does the same at e2l1 `FlakGunSetup`), and the `flak88_driver`/`aagun_driver` poses are in the SHARED human anim set. Same session: 4 manned MG42 nests on t2l1, `max_health` fix in the t2l1 tank gag (268 errors/session), officer radio NIL guard.
- 2026-08-08 (v1.2.3): U allied squads made survivable - health scales with player count and they go DOWN instead of dying, with the player's own DBNO animation, revivable by proximity at no medkit cost (allysquad.scr). That made it safe to narrow the engine blast shield to an opt-in flag (bug-1586), so mortars can finally wound and gib allies - the damage was being dropped before it, not the gore. Same release: new-objective toast, ambient barrage, crewed AA, t2l1 'keep the squad alive' objective, 29 dev prints gated, MAX_CVARS 4096->8192 (bug-1582).
- **2026-08-10** m2l2a stealth: master plan v2 vetted in 3 adversarial rounds (40 agents, ~270 findings). **Phase A shipped** - bug-1631 freeze arm deleted (VERIFIED: the papers guard now accepts and stays animated), all six disguise anim gates made per-target and latch-free (they had been unconditionally true - `thread` in a boolean returns a handle), one aggro rule via `attackentity` instead of the one-way `attackplayer` latch, scene-actor wreckers exempted after A3 instrumentation measured `coop_apply_personality` proning the card man, a Naxos watcher and an alarm runner. Full mission, zero Script Errors.
- **2026-08-10** **v1.2.5 released** (github + discord + baked field report). Phase A + B0 + B1 of the m2l2a plan: papers-checker freeze, six always-true disguise gates, latch-free aggro, scene-actor protection, MG42 per-map anim gating, engine null-deref crash fix, collision latch judged against the real bumper. Also the first release where auto-cover actually ships with its engine half (v1.2.4 shipped the toggle alone, bug-1635). Pre-publish gate added: staged game.dll sha256-matched against the built and live copies, and string-checked for the features it claims.
- **2026-08-10** - Player limping restored (bug-1669). Script `getcvar` is `Cvar_Get(name,"",0)`, so the first script read of an unregistered cvar CREATES it empty and permanently defeats the engine's own default; `coop_limpWarn` did exactly that to `coop_limp` at player setup. Fixed by pre-registering the engine-owned `coop_*` cvars in `G_InitGame`. Same fix silently restored `coop_tinnitusBlast` and `coop_goreDripCorpseTime`.
- **2026-08-10** - **Phase C: the player-initiated contain on m2l2a** (bugs 1682-1691). Nine defects in one session, each found by a probe not a hypothesis: `disable_ai` is only `enableEnemy = 0`, so the stagger never stunned anyone (damage is the only lever on an actor's think); the bust pistol had no ammo; it lost a RAISE RACE to the loadout's own pickups; a THIRD papers path ate the trigger; drawing any weapon clears `m_bIsDisguised`, so the room aggroed and the mechanic was unwinnable by construction; `coop_isProtectedActor` is true for the whole m2l2a cast, so reusing it for 'who notices a corpse' vetoed everybody; **`coop_stealthArmOnHurt` has no caller anywhere and has never run** - two earlier bugs reasoned about it as live; every proximity test was a 3D sphere reaching through floors. Two of my own diagnoses were wrong and were retracted in place rather than left as folklore.

- 2026-08-17 - TRAPS T11: the bug-1173/1184 example retired here - a `+180` roll fix on m1l1 recorded as applied, reverted hours later; a later session read only the first entry. `FIX_INDEX.md` now exists and both protocol files mandate it.

- 2026-08-19 - **MV wave 3 shipped**: 31 credited texture variants (Hobbs / GUANShire / DirtyHarry, DS-Servers archive) across 12 existing + 6 new host guns (kar98/p38/bazooka/mosin/svt/L42A1); fid ceiling 13->19; Leon excluded on explicit no-redistribute readmes (contact-first, SKIN_CREDITS.md). ui_wiring_audit caught wire_mv2's template stomping the loadout deep-fix wave (bug-1947) - the generator's loadout_finish rewrite is retired; the file is maintained in place.
- 2026-08-19 - **Leon wave shipped** (user decision: archive-era content = credit + remove-on-request, superseding Leon/East contact-first): 21 variants incl. the 16-gun Team Tactics pack; armory now 77 credited variants across 23 hosts. Six Leon DS singles = lost media (0-byte store node).
- 2026-08-19 (evening) - **Live-playtest mega-wave shipped**: surrender conversion (hold USE recruits a surrendered german), grenade kick, vault/mantle, gore package (corpse impulse, explosion chunks, decap re-add per bug-866 safe pattern, headshot brain chunks + eyeball dangle), 10s shellshock envelope, reload camera sway, colt thump A, 10s prone dwell, m3l3 church-clear re-gate, vehicle AI gunner tuning trio, weapon.scr variant normalization, TIKI_Error un-gated (bugs 1941-1953).
- 2026-08-21 - **v1.4.0 / v1.4.1 RELEASED** (176 commits since v1.3.1). Headline: the Armory (F7, 357 finishes + model variants, challenge/rank-gated unlocks), weapon weight and the whole feel system, ragdolls, the gore package, AI that takes cover/goes prone/surrenders, 60 new explosion recordings behind 79 aliases, 1,389 restored retail VO takes, and 4 new guns (C96/Johnson/DP-28/M10; Panzerfaust removed). v1.4.1 flipped `coop_ragdoll` ON by default at the user call - safe with no migration because the cvar first existed 08-19, AFTER v1.3.1 was cut, so no shipped client had it archived. Pre-release audit caught two live defects: `coop_decapMax` seeded 16 over the engine's corrected 32, and `coop_goreDebug`/`coop_profProbe` still forced on from temporary diagnoses.
- 2026-08-22 - **m1l1's scripted ride fixed at the root after five attempts** (bug-2064): `notarget` is declared twice as `EV_NORMAL`; for players the *cheat toggle* won the name lookup, so every `notarget 1` FLIPPED the flag. Engine now sets on an argument, toggles on none, plus an `EV_GETTER`. Four live 2-player rides: engaging=0 throughout, canSeePlayer 8-10. Same pass: truck allies stay seated (2065), kit issued once not thrice (2067), gun flicker confirmed as EF_UNARMED on give (2066).
- 2026-08-23 v1.4.4 - user CONFIRMED in play: weapon mass, sprint at 1.12 and gore wounds all
  feel right. Notable because all three had been silently wrong for a long time: our own
  autoexec.cfg was shipping coop_sprintMult 1.9 and coop_goreWounds 0, and autoexec execs
  LAST, so every engine-default change made to them had reached nobody.
- 2026-08-24 - **Feel batch + two softlock-class fixes.** `coop_countasdead` (bug-2091): recruiting an
  enemy now releases his `waittill death` waiters, so objectives that count PER-ACTOR deaths complete -
  bug-2088 had only fixed the ARRAY-counting kind and shipped untested, and the m3l1b softlock was
  absolute because same-team damage is filtered in every gametype. `Actor::setModel` now carries surface
  bits across a composite rebuild BY NAME instead of memset-ing them (bug-2075) - that memset was wiping
  the ranger tik's own `surface bang* +nodraw`, hence bangalores through every ally. Feel: Part F stress
  perturbation (breathing reads `CoopWFeelStress()` via max-not-sum, ADS damping releases under stress,
  an irrational third term so the hands never settle twice in the same place), sprint-to-slide,
  hit flinch on the real `STAT_DAMAGEDIR` bearing, and quick-grenade on G. bug-2092: `g_viewkick_roll`
  had NEVER applied - `damage_angles.z` was clamped from `.y` - fixed and retuned 0.15 -> 0.08.
  Method note: the session opened by being sent to re-fix the ADS jolt, which had shipped in v1.4.4 four
  days earlier; the plan's header still said "PLAN ONLY - nothing built" (bug-2089, TRAPS T11).

- **2026-08-25** - bug-2101: head tracking and torso counter-rotation had been **inert since they
  shipped**. `TickCoopLook` wrote the player's bone controllers from `ClientThink`, and
  `PmoveAdjustAngleSettings` - their sole writer - rewrites all four with `VectorCopy` from `EndFrame`,
  after it. Proved with a sentinel the other writer cannot produce (head `11/22`): readback `0.00/0.00`
  on 328/328 samples. Fixed by moving application to `Player::ApplyCoopBoneOffsets`, called immediately
  after the pmove call and applied ADDITIVELY so the vanilla view-pitch spine distribution survives.
  Same site now carries the prone spine bias, which is why a prone player aiming level had a vertical
  chest: at pitch 0 every share of that distribution is 0, so the spine is straight. I had reported head
  tracking as working-but-subtle the message before measuring it (bug-2102, TRAPS T14).

- **2026-08-25 (later)** - prone made actually playable, by measurement rather than iteration.
  bug-2103: crawling was never a terrain problem - `PM_Friction` uses a FLAT floor of `pm_stopspeed` 50,
  so movement needs `pm_accelerate*wishspeed > 50*pm_friction`, i.e. wishspeed > ~41; crawl speed was 45.
  Probe showed velocity pinned at 1-5 while nrmZ was 0.97-1.00 and walking=1. Floor now scales with the
  stance cap. bug-2104: both speed FLOORS discounted for crouch and not prone, so aiming RAISED a prone
  player to ~172. bug-2105: `PMF_VIEW_PRONE` is overloaded - MOVECONTROL_CROUCH raises it too, so the
  spine bias fired during scripted crouch set pieces. bug-2108: the exit condition was the DESIGN - prone
  demanded holding crouch forever; the broken standup trace hid it, an escape valve exposed it, and it is
  now edge-triggered. bug-2109: prone reload swapped to the real body-space animation, accepting that its
  length becomes the reload duration. bug-2106: stress now widens the spread cone via a server-side
  mirror, ending 'the gun shakes but the crosshair is steady'. Head tracking defaulted off at user
  request (bug-2110) - one message after bug-2101 finally made it run.

- **2026-08-26** **v1.4.5 released** (github + discord + baked field report). Prone made playable:
  the crawl fix (`PM_Friction`'s flat `pm_stopspeed` floor, bug-2103), both speed floors respecting
  prone (bug-2104), the exit rewritten as an edge-trigger after the hold-to-stay design produced two
  opposite symptoms (bug-2108), and the prone reload swapped to the one body-space animation the game
  ships. Stress now widens the weapon spread cone (bug-2106) so a shaking gun costs accuracy. Head
  tracking and torso lag, inert since they shipped (bug-2101), were fixed and then head tracking was
  turned off by preference. **Published UNPLAYTESTED at the user's explicit call after the risk was
  put to them** - specifically the prone reload duration, which changes for every weapon and could not
  be measured offline because retail `.skc` files are obfuscated. Pre-publish gate earned its keep: the
  dry run refused because the What's New card still said v1.4.4.

- **2026-08-26** - v1.4.5 shipped, then a fix pass: bug-2111 the grenade-kick detector never matched the
  German `steilhandgranate`; bug-2112 a DOWNED player shared the prone hull and got the DBNO camera under
  the floor; bug-2114 one elite challenge unlocked a gun's entire variant cycle (now 77 generated
  per-variant challenges); bug-2113/2115 prone reload, three attempts - the NOTETRACKS perform the
  reload, so the real animation now runs at zero torso weight. Enemies that walk up and stand there
  remained OPEN.
- 2026-08-27: Gun bracing shipped (automatic surface support: spread/recoil/sway/lag/stress damping, procedural crosshair pip, local thunk). Prone/supine geometry corrected - the supine body yaw target was view+180 on a false premise and cancelled to a no-op.
- **2026-09-02** — m3l1a Omaha, second batch: the "Not the Actual Events" challenge (fires off the smoke
  radio); naval gunfire flashing out at sea with its report arriving a beat late; rounds punching into the
  water during the underwater cinematic; a ~120-piece drowned-kit wreckage field seated by world trace;
  the shock sequence rebuilt to 17.4s (plunge → seabed → 12s on the bottom → swim up) with the user's new
  shellshock and underwater beds and 15 reverb-baked "voices from the past"; and real bunker-MG tracer
  fire into the Higgins with visible bullet impacts on the men. One 0xC0000005 in ntdll (bug-2341, open).
- **2026-09-05** - Omaha, the six in-flight lanes landed (bugs 2473-2483): flank MG42 crews fire (a
  gunner NAME mg42_active could never bind), the radioman goes silent and the player transmits, the 044a
  voices came back from a local.ok int/array collision, waders and seabed kills retimed into the swim,
  hull sparks, ocean flap calmed, obstacle wash, the quick-draw primary placed in view; then water
  research #1, the wet-sand swash (bug-2485; gl2 drops `alphaGen tCoord` without a deform, 2486).
- **2026-09-06** **v1.5.2 released** (github + discord + baked field report) after two runs: the
  Higgins sink had never moved (a clip, then a model swap, 2487/2496), beach fire vetoed since 08-31
  (2497), the captain's exchange never fired (2490); quick-draw flipped (2491/2499), ragged wet line
  (2493), hedgehog crowd (2495/2498); ricochet research filed. Evening: drowning pass (2507)
  and ocean pass (2508); sink end, caustics, urgency (2509-11).
- **2026-09-07/08** Omaha realism and the drowning QTE (2512-2529), all `U`. The ocean got an
  open-sea Airy mesh, a surf-zone bore layer and a painted trough shadow, after establishing that
  deformed water cannot be lit in this engine at all (ENGINE.md 3.6); boat overlaps and the
  shore/ocean seam closed; the "thunder" was an HD shell roll, not weather. Five beach medics in
  hedgehog cover heal on approach (2522/2523/2526). **The drowning cinematic became a tap-Use QTE
  (2528)** - per-player failure, LMS-exempt, never `missionfailed`; the input edge was proven in
  game before the feature was written. Smoke barrage now waits for the shore party (2529).
- **2026-09-09** **v1.5.3 released** (github + discord + field report card, 7 assets / 2,015 MB)
  after a round that started from four user reports. The QTE regression was mine: `+ coop_qteWatchBump`
  in both ramp watchdog CONDITIONS against a var assigned later in the beat, and a throw in a `while`
  test skips the whole loop - both watchdogs ran their timed-out branch at t=0 and forced the handoff
  one second into the ride (2530). Four more defects in the same graft (2530), and the fixer that fixed
  them re-committed the comment-lost-its-`//` trap eight times over, which produced `prosecheck.py`
  (2531). Then: the fires were sand geysers from two barrages the first fix missed (2532, 2536); the
  sink delivered 45.5 of a commanded 72 because the trim lifts the bow (2537); the beach serviced
  players sequentially so four men took 4x as long to die (2442); DBNO could never fire on this map at
  all (2539); the Higgins interior had never been upscaled and 57 installed HD textures never loaded
  (2533); the swell was deleted at the plunge and never restored (2538); the bore beat against it
  (2541); the quick-draw barrel sat 37 degrees up (2542); and shells now take landing craft down,
  written fresh after the reuse design was refuted on a 277-unit pivot offset (2543).
- **2026-09-13** - MP stops using the coop armory, which had been writing coop saves (2571). The menu theme picker had been compiled out and moved to the live sound file (2572). Cinematic audio ducks and Master volume now reset on every exit from a map (2573).
- **2026-09-13** - MP friendly fire fixed (2574): coop's same-team damage filter had covered every player; narrowed and proven with bots on a dedicated server.
- **2026-09-13** - Main-menu theme picker: drawn arrow buttons replace stretched retail icons (2575); a theme advances to the next when it ends (2576).
- **2026-09-13** - Field Settings redesigned (2578, `U`): a generated two-column sheet of 20 player rows, host rows on a new Host Rules sheet, and autoexec no longer overriding player choices.
- **2026-09-13** - The MP/coop isolation gate runs before packing with a self-test proving it can fail; a failed build aborts the release (2579).
- **2026-09-13** - Stufftext filter hardened (SEC1 layer 1, 2580): splits commands as the engine does and checks `vstr` expansions; runtime-verified with a real client.
- **2026-09-13** - SEC1 layer 2 (dab3af77): the exe filters every server-origin command by per-byte origin tag, sharing `cmd_filter.c` with cgame; API handshake v3->4; review closed 5 holes (2589-2592).
- **2026-09-13** - Modern compass bar (`U`, engine d580485a): a coop-only top-of-screen arc with ticks, cardinals, a boxed heading and an objective marker in metres, following the HUD fade (2581). Runtime-verified m1l1/m2l1/m3l3.
- **2026-09-13** - e1l2 dedicated map-checksum + longjmp crash fixed (2585): a client forcing `r_largemap 1` mismatched `sv_mapChecksum` and took a longjmp crash; it now drops cleanly (the client-follows-checksum path M2 is deferred).
- **2026-09-14** - The gl2 visual queue shipped and deployed: an ACES film grade that survives every map load with exposure-aware bloom (2584, 1149), better shadows incl. foliage (69cdb4d7), 45 per-map fog profiles (subtle depth, moodier under the HD skies), render-scale supersampling + AMD FSR 1 (c01bad53), soft particles (a63fe340) and a light per-map colour grade (120c7fc0, server-published, MP-safe). The stamina arc now hard-fades with the HUD (2593).
- **2026-09-14** - MP armories build A (2597, 2598): game.dll E4/E5 hooks (`mp_mapscript_hook` starts the framework on script-less/third-party MP maps; `mp_weaponselect_redirect` opens the side armory on team join) plus a live dispatcher (`mp_armory.scr`) that applies the kit at spawn (hp=100, bots random-class). Runtime-verified; coop airtight (zero mp leakage on m4l1); isolation clause 14 active. The always-ask chooser stays build B - it needs coop-file edits.
- **2026-09-14** - v1.6.0 "The Long View" released to MOHCoopTrilogy/releases: the visual overhaul + compass bar + Field Settings/Host Rules + security layer 2 + the MP armory groundwork, with the Discord announcement, README and in-game What's New card refreshed.
- **2026-09-14** - MP speed fix (2629): autoexec.cfg's `sv_dmspeedmult 0.6` for coop leaked into MP modes (287*0.6=172 instead of 287*1.1=316). mp.scr now resets both cvars before Hardcore captures its memo; start_server.cfg restores coop values.
- **2026-09-14** - Bot leak fix (2630): sv_maxbots/sv_numbots persisted from MP into coop. start_server.cfg now zeros them.
- **2026-09-14** - Build-A-Base and Base Assault modes shipped: two-phase build/fight and 3-base plant/defuse respectively, with full UI infrastructure (12 bridge cfgs, settings rows, menu buttons, seam switches in mp.scr). Cvar naming mismatch between bridge cfgs and mode scripts caught and fixed pre-playtest (2631).
- **2026-09-14** - Cheapest-wins sweep: omconfig decoy deleted, hzm_cvars typo fixed, 3 stale comments corrected, `r_globalFogDebug` restored to CVAR_CHEAT. 8/10 resolved.
- **2026-09-14** - MP armories build B+C: cgame.dll E1/E2/E3 (carried-kit userinfo, `hzm_armory` cmd + `coop_mp_session`, glove override), side picker + defaults screens, game.dll M8 (Gun Game melee demote) + E6 (voice reads worn model). Coop untouched.
- **2026-09-14** - GL2 styled-lightmap red pulse fixed (`U`, bug-1331): the rend2 deluxe-mapping heuristic (`renderergl2/tr_bsp.c`) misfired on MOHAA BSPs; loader now honours `r_deluxeMapping`, autoexec ships it 0. Needs playtest (e2l1/e2l2).
- **2026-09-14** - MP Progression slice 1: `mp_progression.scr` credits team-blind class + per-weapon session counters off a generated `mp_prog_wpnmap.scr` (never coop's attribution); arch A carry. Bot-verified.
- **2026-09-15** - Post-1.7.0 MP work (`U`, bot-verified; render/placement client-gated): MP walks at coop pace + `coop_mpFastRun`; loadout HOLDS on team-join. MP armory/SR rebuilt beat-by-beat to the coop loadout (`gen_mp_armory.py`): 3D char viewer per side, marker-free cosmetics (userinfo carry, `apply` enforces `cosUnlocked`, bug-2633), generated Service Record ladder. MP helmets fixed to coop's exact-fit recipe (bug-2634). Base Builder rebuilt as a faithful AlienX `basebuild.scr` port (bug-2635). **Push runs on the 7 SP campaign maps** (bug-2637): engine `mp_force_arena` gate (one-shot `sv_mpForceArena` blanks the map script → script-less arena → E4 starts MP), generated `mp_push_maps.scr` script-spawns frontline+chain, new `mp.scr::mp_modeInit` pre-spawn seam. (Gotcha: `omohaaded` runs no scripts without `developer 1` - TRAPS T3.)
- **2026-09-14** - MP Progression slices 2-6 shipped (v1.7.0): **S2** `mp_sign`/`mp_verify` HMAC builtins (game.dll, vendored SHA-256; self-test good/tamper/wrong-guid); **S3** signed userinfo `coop_mpProgBlob` carrier + arch-A load/verify/push with a per-guid server high-water anti-rollback ledger; **S4** per-class unlock thresholds + rank (`coop_mpUnlockC_*`/`coop_mpRank`, verified `unlock class=mg at=2`); **S5** every armory tile commits, server enforces unlocks in `mp_armory::applyMarker`; **S6** Service Record `coop_mp_record.urc` off pushed `coop_mpCnt_*`/`coop_mpTotal`/`coop_mpRank`. Engine bot-verified; armory UX + SR render need a client.
- **2026-09-15** - MP feature batch (`U`, all boot-verified where scriptable; interactive loops playtest-gated): **Base Assault SP treatment** (bug-2639, authored spawns+bases on 5 SP arena maps, dynamic 1-3 base count); **Spawn Protection** (bug-2640, `mp_spawnprotect.scr`, post-spawn invuln that drops on fire, default-on); **Prop Hunt** new mode (bug-2641); **Vehicle system** (bug-2643, `mp_vehicles.scr` + harvested `mp_vehicle_maps.scr`: team-aware AT pickups, mannable flak88/nebelwerfer FixedTurrets, drivable jeep/tank with native crewing, tanks rocket-only-vulnerable); **symmetric Demolition** (bug-2645, either team plants on the enemy's spawn-derived site, gt2 team board); **Freeze Tag meltgun** (bug-2644). Fix: **MP medkit exploit** (bug-2642, user-reported - heal ceiling was 9999 under DBNO so you could channel at full health and refill the pool; now capped at real max_health).
