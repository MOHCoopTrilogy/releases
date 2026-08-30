# HISTORY — condensed chronology

One line per item. Status codes: `V` verified · `U` unverified · `D` code-disabled · `R` reverted ·
`O` open · `P` planned. Full detail in [FEATURES.md](FEATURES.md); open items in [OPEN.md](OPEN.md).

**⚠️ Coverage boundaries.** `.wolf/buglog.json` — the only structured record — begins **2026-06-26**.
Its first id is `bug-535`; **bugs 1–534 are not in the file**, and ~28 ids cited in source comments
(including bug-237, bug-239, bug-241) have no entry at all. The mod's own git history is real (1,393
commits back to 2020-01-08) but commits are enormous snapshot-shaped batches, so it cannot be
bisected usefully. **"Since day one" in practice means since 2026-06-21.** Dates before that are
lineage, not record.

---

## Before the buglog (2020-01 -> 2026-06-20)

Moved to **[archive/history-pre-2026-06-26.md](archive/history-pre-2026-06-26.md)** on
2026-08-17 to keep this file under budget: pre-history, the current era's opening, and the
pre-buglog months.

## 2026-06-26 -> 07-10  (archived)

Moved to [archive/history-2026-06-26-to-07-10.md](archive/history-2026-06-26-to-07-10.md) on
2026-08-24 to keep this file inside its ceiling. The buglog begins; the coop framework, officer
waves and the first engine fixes land.

## 2026-07-11 → 07-20

| When | What |
|---|---|
| 07-11 | `U` e1l4 alarm can now be silenced (v1.1.45). |
| 07-11 | Feel/engine/challenges batch — challenge total reaches 185. |
| 07-12 | `U` ARMORY loadout picker Phase 1 (69 guns). ⭐ Required an **engine** fix — `FindResponder` v2. |
| 07-12 | `V` Retail objective audit: ~630 scripts, **no P0s**; 2 P1 strand risks on t2l1. Fixed `maps/m2l2b.scr:87` calling a label that never existed. |
| 07-12 | **Objectives script-panel RETIRED** — the user saw both displays at once ("obnoxious"). |
| 07-12 | `U` King Tiger 2nd-player MG gunner slot prototype. |
| 07-12 | `U` Frontline PS3 extraction: 339 cues / 175 ambience beds. ⭐ `main.musx` → chunk-walk split → rename `.asf` → vgmstream. |
| 07-13 | `V` Helmet pop-off mechanic fixed — **not cut content**; pops were firing all along but invisible. |
| 07-13 | `U` Cut-content dig + dialogue restoration wave 1 (~15 lines / 5 maps). ⭐ **The MP hitmarker is disabled at retail by a `null.wav` alias.** |
| 07-13 | `P` Bipod design research — BUILD weapon-stance supported aim, REJECT turret swap. |
| 07-13 | **Deployables skill tree REJECTED by the user.** |
| 07-16 | `U` Weapon unlock progression + cosmetic unlocks built + deployed. |
| 07-17 | `U` Build-mode geometry (14 primitives) + blueprint system. |
| 07-17 | `U`→**ON** Reactive Difficulty Director built and wired (`director.scr`) — recorded as "PLANNED, DO NOT BUILD," enabled by default in `autoexec.cfg:381`. |
| 07-17 | `V` Vehicle-turret invisible-to-1P-driver fixed (bug-647, game.dll only). |
| 07-17 | `U` ARMORY V3 rebuild. |
| 07-18 | `U` All four gore tiers built + deployed (`tr_gore.c`, 836 lines). |
| 07-18 | `R` **Decapitation v1 shipped → "the AI went all glitchy" → pulled** (bug-861). |
| 07-18 | `U` Corpse gurgle + wet blood-leak loop. ⭐ bug-822 root cause: `Actor::Remove` calls `Unregister(STRING_DEATH)`, so `self delete` on a live scenic actor fires the parked `waittill death`. |
| 07-18 | `U` Blast tinnitus in the engine (`RadiusDamage` stamps `coop_blastPing`). |
| 07-18 | `V` Weapons-on-back shipped — **EA shipped the system and disabled it with comment slashes**; 79 retail TIKs had commented `holstertag` lines. |
| 07-18 | `V` xw pack full shader audit: **pack is CLEAN** (9 dead paths, all unreferenced). Do not re-audit. |
| 07-18 | `U` Armory stufftext quote-truncation fixed, rcon-verified (bug-758). |
| 07-18 | **v1.2.0 release notes finalised — and never published.** The line continued 1.1.49 → 1.1.55. |
| 07-19 | `R` **Decapitation reverted from SOURCE** during the `MAX_MODELS` three-binary rebuild (bug-892), so a rebuild cannot reintroduce it. |
| 07-19 | `V` `MAX_MODELS` 1024→2048 (at 1024 full, further enemies register as model index 0 = **invisible**). ⚠️ `q_shared.h:1680` credits this to bug-866; it is bug-892. |
| 07-19 | WinDbg `cdb` installed; `game.pdb` now ships next to `game.dll` so dumps resolve exact lines. |
| 07-20 | `V` **The entity-pool saga resolves.** `set maxentities 2048` had shipped for years against a 10-bit wire — it added no entities, it **disabled `AllocEdict`'s overflow guard**, so the allocator handed out slot 1022 (WORLD). One lie = a weekend of use-after-free minidumps. Fixed by `GENTITYNUM_BITS` 10→11 + ~25 guards + `g_droppeditemlife 60`. |
| 07-20 | `V` e1l2 invisible walls solved — three species (33 solid landmines → `CONTENTS_WEAPONCLIP`; artillery TIK setsize tightened; a 225-segment retail playerclip web). |
| 07-20 | `R` Regional clip-strip **zones retired** — wrong-grained, let players out of bounds. Replaced by `cmpatch/<map>.txt` brush surgery. ⭐ **The server loads `<name>_sml.bsp`.** |
| 07-20 | `V` `MAX_ENTITIES_IN_SNAPSHOT` + `MAX_PARSE_ENTITIES` raised (bug-934). |

---

## 2026-07-21 → 07-29

| When | What |
|---|---|
| 07-21 | **`openmohaa.exe` deployed to the GOG root — and never updated since.** Everything after this date is source-only for players. |
| 07-21 | `O` **bug-1001 — build-mode blueprints render as featureless squares.** Zero `BUILD_BP_PLACE` lines in the session log. |
| 07-21 | `O` bug-1172 — **sandbox engine constants were pushed into the real install** by routine `build.ps1` runs. Emergency revert. |
| 07-21 | Game-accurate structures: BSP→blueprint extraction + shape kit (`bpv1`). |
| 07-22 | `V` **Addon-spawner restore — the strongest measured win in the project.** `addon_*` markers carry their model in `$ai_model`, not `.model`, so `spawner_create` recorded NIL and the engine spawned `models/nil.tik` in a loop. Storm ~7,000+ → 25; **~550 German AI restored trilogy-wide**; t2l1 1960→0, t2l2 3045→0, t1l3 1470→0. |
| 07-22 | `V` `$player`-array gag overrides (t2l3 14,501→0; t3l1 4766→0; t2l4_captain 20 sites). |
| 07-23 | `V` Autonomous combat-verification rig — `coop_botInput 1` injects the host usercmd and **fires real bullets** (a script `damage` event does not acquire a target). ⭐ Its headline catch: the ET3 jink **silently never fires**. |
| 07-23 | `D` AI dynamics step 1 (global personality) + step 2 (engine juke/hide timers) — measured, but gated on an **unseeded** cvar. |
| 07-23 | **Engine HEAD `819a6e93`. Everything after this is uncommitted.** |
| 07-23 | Mod HEAD `f10ac19` (v1.1.54). Everything after this is uncommitted. |
| 07-24 | **`game.dll` deployed — and never updated since.** |
| 07-24 | gl2 migration **rescoped** onto a fully isolated install at `G:\mohaa-gl2`. Empirically gl2 is healthy: boots, renders, 0 crashes, 0 real GLSL failures. |
| 07-24 | `D` AI squad brain (`aisquad.scr`) built — gate cvar unseeded. |
| 07-26 | **Manifest 1.1.55** — the current release. `openmohaa.exe` and `cgame.dll` still point at v1.1.51. |
| 07-27 | ⚠️ **A post-write hook clobbered `buglog.json`** with its own schema. 523 entries rebuilt from ~1.2 GB of transcripts. All 8 `.bak` snapshots later diffed: **zero historical loss**. |
| 07-27 | m3l3 groundfix pak built — **never shipped**, and built 19 minutes *after* the screenshot later cited as "the fix didn't work." |
| 07-28 | `V` gl2 batch: gun-over-menus (depth **rejection**, not draw order), settings-apply crash, renderer-zone leak (+53 MB/apply), frozen 2D shader clock, HZM grade never executing, invisible actors (**two independent mechanisms**). |
| 07-28 | `U` `MAX_SOUNDS` 1280→1600 + `MAX_RELIABLE_COMMANDS` 512→1024 + `MAX_CONFIGSTRINGS` 4096→8192, with a compile-time `#error` guard. |
| 07-28 | `V` `MAX_SNAPSHOT_ENTITIES` 1024→2048 — **bug-934's missed 4th member, found 8 days later**, silently discarding every entity past the 1024th with no log line. A warning was added alongside the fix. |
| 07-28 | `U` Headshot kill-cue hook **moved** `BulletAttack` → `ArmorDamage`; sandbox-verified 20/20. |
| 07-28 | `U` `coop_unsponge` bullet-sponge reconciliation sweep (bug-1212). |
| 07-28 | `R` **The +180 roll on `maps/m1l1.scr` — applied (bug-1173), reverted the same evening (bug-1184)** as an unverified guess. An in-code revert comment at line 1683 names the bug. **This is the doc set's commissioning example.** |
| 07-28 | `O` bug-1213 — m1l1 mangled actors, **six investigations, no guess shipped**; a gated `^~^~^ POSECHK` diagnostic delivered instead. |
| 07-28 | `V` `MAX_SKELMORPH` 12800→131072 (silent OOB write). |
| 07-28 | `V` `cgame.dll` + `renderer_opengl1.dll` deployed (22:57). **`openmohaa.exe` was not.** |
| 07-29 01:07–01:41 | Current binaries built in `.cmake` — **exe, game.dll and gl2 never deployed to the real install.** |
| 07-29 | `O` **Three S0 regressions found by a brand-new harness**, all correctly marked NOT FIXED: bug-1218 (m3l2 missing `level_end_trigger` label), bug-1219 (`SV_FindIndex overflow max=1280` — the deploy gap), bug-1220 (e2l2 NULL-listener ×12). |
| 07-29 | `U` Officer heal budget `coop_officerMaxHeals` (bug-1215). |
| 07-29 | The regression harness at `_research/regression/` becomes **the project's only working automated verification.** |
| 07-29 | This doc set written. |

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

1. **Velocity is extremely high and verification is not.** Roughly 75 systems in ~5 weeks, of which
   ~15 have a recorded confirmation. The backlog is not features — it is playtests.
2. **The most expensive bugs were all silent.** The entity-pool stomp, the grenade veto, the grade
   uniform, the `Hunk_Clear` static, the snapshot discard: none of them logged anything. The project's
   biggest wins came from *proving execution*, not from reading code.
3. **The deploy pipeline is the current bottleneck.** The last full engine deploy was 07-21. Eight
   days of engine work — including three protocol constants — sits built but undeployed, and a live
   log (bug-1219) is already reporting the old limit.
4. **Two records systems degraded predictably**: the append-only ones (`memory.md`, `cerebrum.md`)
   became unreadable; the structured one (`buglog.json`) kept working. **Structure and a lookup key
   are the whole difference.**

---

## 2026-08-02 — PDF defect sweep, the limp, and two gl2 rendering bugs

46 buglog entries (bug-1251 -> 1296). The day's shape: **most of the damage was silent-veto**, and
the runtime log — not static audit — found nearly all of it. RC1 detonated every watched demolition
charge ~0.3 s into map load across 16 sites; `coop_painThread` was a latch nothing cleared, making
every enemy a permanent bullet sponge; 11 maps were taking the armory loadout back after issuing it;
and one `1e-5` depth epsilon in the gl2 fog pass exempted everything past 88-98% of zFar, explaining
two separately-reported symptoms at once.

*The day's three lessons — a failed `waittill` does not abort, agreement between reviewers sharing a
source is not corroboration, and the expensive fix refuted by measurement — now live in
[TRAPS.md](TRAPS.md) T3/T11, which is where they get read. Per-bug detail is in the buglog.*

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
- 2026-08-08: U helmet unlock gate made wear-time, not just pick-time (bug-1578) - `helmet_apply` now range-checks and re-validates the stored index and falls back to a DETERMINISTIC index 1, and a new `helmet_lockNotice` says "locked" once per distinct item instead of on every archived `,hn` resend (every join, every armory close). Same batch: m6l1c conversation-guard pass (bug-1579) - the `waittill animdone` outside its guard in `sciencesayto` was a guaranteed strander that would have taken the whole science-chat sequence and its actor release with it; 7 of 196 sweep sites done, 189 left. Two manned MG42 nests baked into `maps/m3l2.scr` from the 08-08 build-mode capture. **None of it is deployed** - the game was running, which `build.ps1` refuses.
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

- **2026-08-26** - v1.4.5 shipped, then a long fix pass on top of it. bug-2111: the grenade-kick
  detector tested model names for "grenade", so the German `steilhandgranate` (GRANATE) never matched -
  the prompt had never once appeared for an enemy grenade. bug-2112: my prone work derived
  `PMF_VIEW_PRONE` from hull height alone and a DOWNED player shares that hull, putting the DBNO camera
  under the floor. bug-2114: one elite challenge unlocked a gun's ENTIRE variant cycle; now 77 generated
  per-variant challenges on an accelerating curve capped at 750. Extending `check_challenges.py` to see
  the new file immediately exposed a false green, and `gen_service_record.py` had the same blind spot -
  it baked 367 SR rows against 444 live challenges, which the deployed-truth stamp caught in play as
  `SELFTEST FAIL ... MIXED DEPLOYMENT`. bug-2113/2115, prone reload, three attempts: the real mechanism
  is that NOTETRACKS on the animation perform the reload (`first reloadweapon`, `clip_fill`), so a bare
  substituted alias left the clip empty and locked the player out of firing. Final approach runs the real
  animation at zero torso render weight, leaving the duration bit-for-bit unchanged. Enemies that walk up
  and stand there remain OPEN: notarget and count-scaling replicas both ruled out by measurement.
- 2026-08-27: Gun bracing shipped (automatic surface support: spread/recoil/sway/lag/stress damping, procedural crosshair pip, local thunk). Prone/supine geometry corrected - the supine body yaw target was view+180 on a false premise and cancelled to a no-op.
