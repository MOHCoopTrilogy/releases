# Omaha ramp: making the underwater beat feel like drowning (research, 2026-09-06)

Research only, nothing built. Every claim below is anchored to code read this session; log lines are
from `G:\mohaa-gl2\home\maintt\qconsole.log`, run of 2026-09-06 17:10 (the 13:03 slot the brief names
was overwritten by the 17:08 map load; the markers are the same beat). The user is removing
`coop_uwBoatLook` and shortening the segment, so nothing here lengthens it - the proposals are
intensity-per-second on a ~23 s cut. Two removal hazards are in section 3d: the waders and the
Higgins sink are both keyed to the boat look and go silent with it.

Read order: `docs/TRAPS.md` (T3, T8, T11, T14, T22, the TIKI section), then this.

## 0. The sequence as it ran (RAMPUW start = 17:10:21, pace 1.0)

| t | marker | camera (`coopified.scr`) | screen / ears |
|---|---|---|---|
| -3 | `RAMPAUD cut sfxduck=0.05` / `MUFFLE arm str=0.90 duck=0.050` | arc still flying | world 26 dB down, global lowpass on |
| 0 | `RAMPUW impact f=0.952` -> `start` -> `bed start vol=1` -> `plunge` | BEAT 1, 0.55 s, pitch 52->22, roll 0->-28 (:12967-12990) | `UWFX v3 enter amt=0.085` (eased in), impact + wash + heart loop + 26.5 s bed |
| +1 | `gear placed=3`, `tumble` | BEAT 2, 0.70 + 0.60 s, roll through +28, ends pitch -48 (:13001-13037); dizzy 2.9 stuffed (:12999) | `RAMPFOG down why=water` |
| +2 | `bottom`, `airhook armed`, `eyes` | BEAT 3, 0.26 s snap + jolt 0.55/1.9 with `coop_uw_hitsand` (:13051-13053); BEAT 3b 2.0 s leg under a 2.0 s `fadeout 0 0 0` (:13079, :13099) | `coop_uw_airout needs an alias` (owed) |
| +4 | `black` | BEAT 3c, 2.30 s held pose, unpaced (:13111-13113) | nothing on screen |
| +6 | `wake` | `fadein 0.18` + jolt 0.30/2.4 + dizzy 1.2 + 0.50 s hold (:13123-13140) | `coop_uw_wake needs an alias` (owed) |
| +7 | `sand` | BEAT 4, 1.55 s, still (:13163) | |
| +10 / +12 | `try1 failed` / `try2 failed` | BEAT 5, push-give-lie 1.51 s and 1.70 s, each ending in jolt + `coop_uw_hitsand` (:13502-13547) | swim swoosh on each push |
| +13 | `up` | 1.50 s rise + 0.90 s knees, pitch crosses zero (:13218-13231) | second wash, dizzy 1.8 |
| +14..+26 | `UWLOOK start lid=1` ... `done leg=2` | `coop_uwBoatLook`, 11.5 s unpaced (:13238, :13794) - BEING REMOVED | `HIGGINSSINK band=1` at +14 is threaded FROM the look; `UNDERWADE seat=1..5` at +21..+23 |
| +26..+36 | `stroke 1 of 6` ... `6 of 6` | BEAT 6, six 1.72 s strokes, pitch -2 -> +13 (:13267-13319) | one swoosh + one jolt (`coop_uw_strain`) per stroke; 4 wader kills at +27..+29 |
| +36 | `gather` | 1.25 s, pitch to +26, z dips (:13341-13347) | |
| +37 | `break` -> `bed stop` -> `gasp` -> `done t=37.775` | 0.55 s, off the rail to z -488 (:13355-13407) | heart stop, bed stop, `coop_uw_break`, `coop_lensSplash 0.95` |

Without the look the beat is 26.3 s (2.11 plunge + 4.8 eyes/black/wake + 7.16 sand/tries/rise +
12.1 strokes/gather/break). Getting to ~23 s means trimming the sand hold and one stroke, not the
plunge or the exit - see the envelope in section 3.

## 1. What the player sees now

**The camera.** Every player rides his own `Camera` in the `$boatCamera` array; the script drives
them identically per frame with `movetopos` + `turnto` (`coop_rampPose`, instant sets per
`camera.cpp:1159-1180`). Fov is pinned to 80 by `Camera::Camera` (`camera.cpp:710`), so fov_y is
64.4 on 16:9. Every submerged pose funnels through `coop_uwPose` (:13981-14013): yaw rail 74..106,
pitch -62..54, roll +-46, z -572..`coop_uwZTop`; hits are counted and the beat printed
`clampXY=0 clampZ=0 clampA=0`, so the table sits inside its envelope. The body is glued, hidden,
notsolid in the boat for the whole beat (bug-2306), which is why nothing physical happens to a player.

**Client-side motion on top of the table.** Two channels, both already used by the beat:
- `coop_uwJolt` (:14030-14045) spawns a `ViewJitter` per player (`main.scr:1927-1958`,
  `earthquake_player`), felt through the camera only because `showquakes 1` sets
  `PMF_DAMAGE_ANGLES` and `cg_view.c` subtracts damage angles inside the camera branch. It is a
  symmetric random shake - no directional kick exists on this path.
- `coop_uwDizzy` (:14333-14345) stuffs `set coop_dizzy <sev>`; `CG_ApplyShellShock`
  (`cg_view.c:671-704`) restarts only if the new severity exceeds the live one or 5000 ms passed,
  then adds `sin(t*5.3)*5.5*s` roll, `sin(t*3.9+1.3)*2.8*s` pitch, 1.6 yaw, decaying as (1-t/T)^2
  over `coop_dizzyTime`(4.2)*sev seconds. Stuffed 2.9 at the tumble, 1.2 at the wake, 1.8 after up.

**The gl2 post chain while under** (`tr_backend.c:2268` -> `RB_HZMScreenFx` then `RB_HZMExtraFx`,
`tr_postprocess.c:1404-1408`). In order:
1. Stock FOV warp: `CG_CalcFov` tests `CG_PointContents(cg.refdef.vieworg)` and wobbles fov
   (`cg_view.c:5766-5776`) - the camera origin is what is tested, so it fires for a cine camera.
2. **Suppression pass** (desaturate + peripheral blur + tunnel vignette, `tr_postprocess.c:1093-1116`,
   `suppressionShader`). The beat drives it today: `coop_rampSuppressAll` (0.72 / 0.88 / 0.66 /
   0.58 / 0.80 / 0.42 at :12992, :13054, :13164, :13250, :13346, :13384) -> `coop_setSuppression`
   (`main.scr`) stuffs `set coop_suppHold <0..1>` edge-triggered -> cgame publishes `r_ppSuppress`.
   This is the one script-reachable tunnel/desat lever that exists, and it is already in the beat.
3. Low-health pass (desat + luminance-red vignette + heartbeat pulse at 1.8+1.6*hurt Hz,
   `tr_postprocess.c:975-1026`) and the dizzy ghost pass (:1042-1091, `RB_HZMDizzyAmount` :760-793).
   Both key on `r_ppHealthFrac`, republished every frame from `STAT_HEALTH` (`cg_view.c:5457-5496`),
   and `coop_dbnoView`. Inert in the beat: health is 750 so frac is 1. This is the shipped
   "pulse + tunnel" machinery, and it cannot be reached from script without faking health (see 3a).
4. **Underwater volume v3** (`tr_postprocess.c:1523-1684`, `glsl/underwater_fp.glsl`): cgame
   publishes `r_ppUnderwater` eased at 3.3/s in, 1.0/s out (`cg_view.c:5784-5801`); the pass does
   refraction ripple (glsl:130-137), depth-reconstructed per-channel Beer-Lambert absorption with
   sigma R/G/B = 3.1/1.0/1.9 over `r_ppUnderwaterVis` 900 (:1618, glsl:187), multiplicative density
   noise (glsl:181-183), a 12-tap scatter blur of `9 * height/1080` texels at full murk (12 px at
   1440p in the log, :1565, glsl:195-218), two mote layers (glsl:239-261), top-biased light bands
   (glsl:264-275) and a deliberately small vignette `(0.06 + 0.14*r^2) * a` (glsl:279-282).
   Sky (`zw >= 0.9999999`) is forced to solid silt (glsl:160-164). `u_Color.w` is passed as a literal
   `1.0f` (:1623) and documented "unused" (glsl:53) - a free channel for an air signal.
   The eight artist dials (`Amt/Vis/Blur/Particles/Shafts/Ripple/Silt/SiltBoost`, :1442-1471) are
   `CVAR_ARCHIVE` and read per frame, but **the server cannot set any `r_pp*`**: the stufftext
   whitelist (`cg_servercmds_filter.cpp:32-97`) carries `s_volume/s_musicvolume/s_ambientvolume/
   s_sfxduck` and the `coop_duck*` markers only, and the prefix pass at :173 admits `coop_*` alone.
   Driving the look from script therefore needs a `coop_*` poke consumed by cgame - the
   `coop_lensSplash` / `coop_lensBlood` / `coop_dizzy` idiom (`cg_view.c:5288-5293, 5826-5857, 678-686`).
5. Lens blood after the water pass (`:1686-1739`); the water kills its specular and runs 6x faster
   under (`cg_view.c:5813-5816`). Log: `LENSBLOOD amt=0.699 ... uw=0.00` at the ramp, so the
   plunge does wash it.

**The blackout** is `fadeout 2.0 0 0 0 1` - a flat `ps.blend` colour (`Player::CalcBlend`,
`player.cpp:7805-7849`), not a vignette. It is a LATCH: alpha = 1 - remaining/start and holds at 1;
`fadein` starts at alpha 1. The beat's own guard and `coop_uwBlackSafety` (:14311-14325) exist
because of that. It cannot be pulsed (each fadein restarts at full black), so any "eyes" rhythm
beyond one close/open belongs in the post chain, not in `fade*`.

**The eyes beat** as authored: the surface dims for 2 s while the head settles to pitch -49, 2.3 s
of black, then a 0.18 s snap open with a 2.4 jolt and a low sway. The airout line was meant to sit
under the fade and the wake line on the snap; both are still unaliased (log +2, +6).

**The lid.** `coop_uwLidHide` only hides `$ocean_wavy` inside the boat look (:13838-13840), for the
nine seconds the pitch is high enough that the frustum cannot contain it; `coop_rampHandoff`
restores it. With the look gone nothing touches the lid, and `deepbluesea` is opaque from below by
omission of a `blendFunc` (`water_omaha_2026-09-05/WATER_MODERN_TECHNIQUES.md` 3.5). The mod already
owns a restated copy, `scripts/zz_coop_ocean.shader`, m3l1a-only (bug-2478) - the override site exists.

## 2. What he hears now

Mix state for the whole beat: `s_sfxduck 0.05`, `coop_voxCut 0`, `coop_muffle 1`, `tmvolume 1.5`,
ambient duck to exactly 0 in 0.3 s (`coop_rampAudioCut`, :12557-12572). The muffle is
`coop_muffle * (1 - s_sfxduck)^2` = 0.90 (`S_HZM_UpdateMuffle`, `snd_openal_new.cpp:2963-3005`),
an EFX lowpass at `s_muffleHF 0.95 / s_muffleGain 0.10` on every channel that is not exempt
(:3028-3048), 2D channels included (:3068-3086). So the WORLD is muffled - but every sound the beat
plays is exempt from both duck and muffle, by path (`S_HZM_CueTier` :3968-3987, `S_HZM_DuckExempt`
:4050-4094):

| alias | wav (len) | channel / path | when | status |
|---|---|---|---|---|
| `coop_uw_impact` | `coop_tinnitus/coop_uw_impact01.wav` 6.6 s | local on `$higgins1_playerspot` (bug-2452) | f >= 0.95 of the arc | real |
| `coop_underwater_wash` | `coop_tinnitus/coop_underwater01.wav` 14.0 s | local on `$player[1]` via `coop_uwSay` (:14091-14107, ONE play) | +0 and after `up` | real; tier-1 cue |
| `coop_shellshock_uw` | `coop_shellshock02.wav` 10.0 s | local on player | at the blast, same entnum/channel as the ring one line later (bug-2456 OPEN: the ring is killed) | real |
| `coop_heartbeat` | `coop_heart/coop_heart01.wav` 1.21 s | `playlocalsound ... 1` loop (:14128-14143) | +0 to break | audible only since bug-2432/2465 (09-05); no marker exists, so the log cannot testify (T14) |
| `coop_uw_bed` | `coop_swim/coop_uw_bed01.wav` 26.5 s one-shot | local on a broadcast carrier 1200 u up-beach, alias 1.8 x trim (:14221-14257) | +0 to break | real |
| `coop_uw_swim` | `coop_swim/coop_uw_swim01.wav` 0.78 s, pitch +-0.12 | `auto` = 3D on the player: alias volume discarded (bug-2455 OPEN) | 9 plays: 2 tries, rise, 6 strokes, gather | real |
| `coop_uw_hitsand` | placeholder -> impact01 at 0.6 / pitch 0.86 (bug-2494) | `playlocalsound` per player from `coop_uwJolt` | bottom, try1, try2 | PLACEHOLDER |
| `coop_uw_strain` | placeholder -> uwbreath01 at 0.8 / 0.92 (bug-2494) | `playlocalsound` per player from `coop_uwJolt` | 6 strokes | PLACEHOLDER |
| `coop_uw_airout`, `coop_uw_wake` | none | `coop_uwSay` | eyes, wake | OWED by the user; armed no-ops, one marker + one error line each |
| `coop_uw_break` | `coop_tinnitus/coop_uwbreath01.wav` = `breath_out.wav` 3.1 s | local on player - deliberately cuts the wash | gasp | real |
| `coop_memvoice01-06` | `coop_memory/*.wav` | 3D emitters (DuckExempt, no sidechain) | `coop_memoryVoices` across the hold | real |
| `breath_in.wav` 1.63 s | `sound/coop_breath/` | cgame-local only (`cg_view.c:2355`, ADS) | never in this beat | unaliased asset, free to use |

Two things the placeholders did that the earlier silent no-ops did not (code-derived, listen for
them): **(i)** `coop_uwJolt` plays via `playlocalsound`, i.e. `gi.Sound(entnum, CHAN_LOCAL)`, and
`S_OPENAL_PickChannelBase` end_samples a live channel on a matching (entnum, CHAN_LOCAL) pair - the
same mechanism bug-2436/2452 hit. The wash started at +0 on `$player[1]` is therefore cut at +2 by
`coop_uw_hitsand`, and the second wash (after `up`) is cut by the first stroke's `coop_uw_strain`.
**(ii)** both placeholders live under `sound/coop_tinnitus/`, which is cue tier 1 (:3982-3984); a
tier-1 one-shot arms the 350 ms music/ambience sidechain, so six strain jolts in ten seconds pump the
score under the swim - the exact thing bug-2344 kept the memory voices out of tier 1 to avoid.
`playsound` argstype 1 takes volume only; pitch/channel come from the alias (:14248-14250), so
per-play pitch is not available anywhere.

## 3. How to make it feel like drowning - engine-real techniques

### 3a. A breath/air ramp that drives the picture

Three routes, in cost order.

**Route 1 - script only, today's levers.** An air value 1.0 -> 0.05 across the beat, expressed as
`coop_rampSuppressAll <1-air>` steps (edge-triggered, one stufftext per change, T8-safe). Buys the
suppression pass: desaturation, peripheral blur and a tunnel vignette, under the water volume. Limits:
one fixed look, no pulse, no colour drift, and it is the same look "pinned down" uses on the beach 40 s
later. Cost zero binaries. Risk: the `coop_suppHold` release at the handoff already exists (0.42 then
the normal fade).

**Route 2 - the right one: `coop_uwAir` -> `r_ppUnderwaterAir` -> `u_Color.w`.** Server stuffs
`set coop_uwAir <0..1>` per beat (auto-allowed by prefix, :173); cgame eases it beside the
`s_underwater` block (`cg_view.c:5784-5801`), clears it on connect/map change like the
`hzmClearFx` list does for `r_ppBlood`, and publishes `r_ppUnderwaterAir` (registered flag 0 like
`r_ppUnderwater`, :1443). The renderer passes it in the unused fourth component at :1623 - no new
uniform slot, nothing downstream shifts (glsl:51-52). In the shader, with `air = 1 - u_Color.w`:
tunnel `vig` weight 0.14 -> up to 0.75, a luminance mix (desat) up to 0.6, blur radius x(1 + 1.5*air),
silt darkening, and a **pulse**: `1 + 0.08*air*sin(t*2*pi*bpm/60)` on the vignette with
`bpm = 55 + 75*air`, using the `t` already in `u_Color.y`. Ships cgame.dll + renderer_opengl2.dll
(both in `build.ps1`'s six, TRAPS T10). Probe: extend the existing one-per-submersion
`^~^~^ UWFX v3 enter` line with `air=`, and add `air=` to the 1 Hz `UWFX debug` line; the script
prints `^~^~^ RAMPUW air=<v> t=<s>` at each step so the two can be joined.

**Route 3 - rejected: fake low health.** `healthonly` would light the low-health pulse and the
dizzy ghost for free, but `r_ppHealthFrac` is derived from `STAT_HEALTH` every frame and a health
DROP is also the on-hit detector (`cg_view.c:5628-5640`: `CG_AddSuppression(0.25 + sev*2.5)` plus
on-hit blood), the wound muffle stuffs `s_volume` on the wounded edge (`tinnitus.scr:174`), and limp/XP
read health. It would flash blood and fight the mix.

**The heartbeat that accelerates.** The loop cannot change pitch or rate (one `loopSound` int,
`player.cpp:18183`; alias pitch fixed). Two workable shapes: (a) three loop aliases at 55/85/120 bpm
cut from `coop_heart01.wav`, switched at air thresholds - but every switch is a
`stoplocalsound`, which takes CHAN_LOCAL down with it (:14148-14153) and would cut the wash; or
(b) **one-shot beats on a dedicated carrier entity**, the `coop_uwBedStart` pattern (own entnum, so
no CHAN_LOCAL collision; `+broadcast`; path under `sound/coop_heart/` so DuckExempt and not a cue),
fired by a script thread at an interval read from the same air curve (1.10 s -> 0.50 s). The visual
pulse in Route 2 uses the same `bpm(air)` formula, so audio and picture agree without a per-beat
message. Probe: `^~^~^ RAMPUW heart bpm=<n> air=<v>` once per change.

### 3b. Input struggle

The camera is what moves; the body is glued. Bucking that exists: the jolt (random shake, magnitude
+ duration) and the sway (per-axis sinusoids). A "thrash" = three 0.12 s jolts at 0.6/0.9/0.6 with a
roll excursion written into the leg table (roll is the one directional axis the table controls),
timed on each failed push. Zero cost. A hand-reach viewmodel is not reachable cheaply: the view
weapon is gated off under `PMF_CAMERA_VIEW` (`cg_view.c:534`, :3591, :4331), and there is no arm
asset that renders without a body (bug-2375 is the helmet version of that lesson). Do not spend on it.

### 3c. Surface light, the lid, bubbles

- **The surface from below**: add `blendFunc blend` AND `depthwrite` to the first stage of the
  m3l1a-only `zz_coop_ocean.shader` copy of `deepbluesea` (bug-2478 established it is referenced by
  m3l1a.bsp only). `depthwrite` is load-bearing: the water pass treats a pixel with no depth as sky
  and paints it solid silt (glsl:156-164), so a translucent lid without depth would vanish into murk.
  `deepbluesea_runup` is the retail precedent (`blendFunc blend` + `depthwrite`). Shader only.
- **Caustics on the sand**: retail ships `textures/misc_outside/caustic.jpg` (Pak2, HD variants in
  the AA_HD and dds paks) and `scripts/mohtest.shader` carries the recipe commented out under
  `fltwall1grim2rock`: `blendfunc add`, `tcMod scroll 0 .05`, `tcMod turb 0 .2 0 .1`,
  `tcMod scale 4 4`, second bundle scaled -3.55 with its own turb. Two multiplied tiles kill the
  tiling. Target is the submerged terrain shader (`water_omaha` 3.6 item 4, `textures/test/omaha_pjspick3`)
  - caveat from that file: it draws above the waterline too unless the shader is underwater-only.
  Shader only; verify on gl2 that `tcMod turb` survives the LIGHTALL collapse (T7's `alphaGen`
  lesson, bug-2486) before trusting it.
- **God-rays from above**: `RB_SunRays` (`tr_postprocess.c:455`) is gated to looking at the sun;
  relaxing that while `r_ppUnderwater > 0` is the water proposal's item 8. Renderer dll. The
  existing band shafts (glsl:264-275) already scale with `r_ppUnderwaterShafts`, which Route 2 can
  raise with air instead.
- **Bubbles from the mouth**: retail `models/fx/water_trail_bubble.tik` (Pak0) is one `sfx
  originspawn` of `water_trail_bubble.spr` (`effects.shader`: `bh_water_drop.tga`, `blendFunc add`,
  parallel_oriented), `accel 0 0 72`, `life 5`, `wateronly`, `swarm 10 8 4`. It cannot be spawned as
  a `script_model`: only `originemitter` blocks render on a script carrier (TRAPS TIKI, bug-2477).
  Build `models/fx/coop_uwbubble.tik` on the `coop_bloodcloud.tik` skeleton (dummy3, `+dontdraw`,
  `wateronly`, no collision) with an `originemitter` using that sprite, `accel 0 0 72`, `spawnrate`
  ~12 (x5 for `cg_effectdetail` 0.2), `scalemin/max 0.2/0.5`, plus a burst variant (`count 14`)
  for the airout/gasp-under moment. Carrier follows the camera by origin-stepping each frame
  (`moveto` no-ops on script_model): write `level.coop_uwCamPos` in `coop_uwPose` and step the
  carrier to it minus 14 u forward/down. Must spawn below -520 or every particle culls (bloodcloud
  header). Mod only. Probe: `^~^~^ RAMPUW bubbles burst=<n>` per burst.

### 3d. Bodies and waders - the density, and two removal hazards

Density is right for the shorter cut: 12 pre-placed seabed bodies (`coop_uwDeadN`, :10189),
0 sinking men (`coop_uwSinkMen`, bug-2488), 5 waders with 4 scripted kills. Two things break when
the look is deleted:

1. `coop_underwaterWaders` (:16477-16489) **exits with `UNDERWADE skip reason=no_boat_look`** when
   `coop_uwBoatLookOn` is 0 or the look's entities are absent, and its seat clock is
   `B = 4.91 + 9.16*pace` + k 7.0..8.5 (:16554-16560) = the look's blind window. Retime: the strokes
   are the on-screen window (header :16517-16520, pitch -2..+13, yaw 84..90); with the look gone
   stroke 1 opens at `B` itself, so seats become `B - 0.8 .. B + 0.6` (spawning during the last
   0.9 s knees leg, pitch +11, which puts men at 300-480 u below the frame edge - re-run the
   frustum check in that header before shipping) and deaths in strokes 1-3 keep their 5.5-7.0 s wades.
   Drop the `no_boat_look` gate to a `$boatCamera` test only.
2. `coop_higginsSink` is **threaded by the look** (:13700-13740 header; log `HIGGINSSINK band=1` at
   +14 inside `UWLOOK`); with the look off it falls back to `coop_rampHandoff`'s call, i.e. AFTER the
   surface, so `coop_rampBoatLook` at the break (:13412) would show her level again - the bug-2470
   complaint. Thread it from `up` (or `bottom`) instead; it is idempotent on
   `level.coop_higginsSinkDone`.

### 3e. Audio

- Heart cadence: 3a(b).
- Muffled shells overhead: `coop_waterBullets` (:9052) already puts rounds in; add a 2D thud alias
  under `sound/coop_swim/` (DuckExempt, NOT tier 1 - no sidechain) with the lowpass BAKED into the
  wav (the muffle is 0.90 but every beat sound bypasses it by path), fired 3-4 times off the
  `coop_waterBullets` cadence with a jolt 0.15/0.4 each. Alias + script.
- Fix the collisions in section 2: route the jolt sounds through `coop_uwSay`-style `playsound` on
  a **second carrier** (the bed pattern), and re-home the two placeholders under `sound/coop_swim/`.
  Then the wash survives to the surface and the score stops pumping.
- Exit: the gasp exists; add `coop_uw_inhale` on `breath_in.wav` (1.63 s, already shipped, unaliased)
  0.9 s after the gasp on the carrier; re-fire `coop_tinnitus_ring` on the carrier 0.1 s after the
  gasp (bug-2456 kills the blast ring today, so the surface is the first time it can be heard clean).

### 3f. A "struggle to surface" input - assess before building

Inputs that exist without a protocol change: `self.useheld` / `self.fireheld` getters
(`player.cpp:1308-1325`, handlers :2106-2107) polled per frame from script, or a `+cmd` pair (T22,
both registrations or host-only, bug-2460). Every player shares one choreography (`coop_rampPose`
writes all cameras from one thread), so an input that changes the TIMELINE for one player is a
per-player camera rewrite and a desync of the shared audio beats. Verdict: **no timeline input.**
An input that adds per-player flavour only is cheap and on-theme: mashing fire during BEAT 5 spends
air faster (his own `coop_uwAir` drops, his own bubbles burst, his own jolt fires) and the tries
still fail - "you cannot fight it". Check first that BUTTON_ATTACKLEFT on a glued, hidden body does
not fire a weapon (the body is `notarget`, weapons state unknown); `fireheld` is also the respawn
key at `player.cpp:6149`, harmless while alive. Script only, low-medium risk.

### 3g. The exit

Order at the break (all script/alias except the last): heart stop -> bed stop -> gasp
(`coop_uw_break`) -> `fadein 0.25 1 1 1 1` (a WHITE fadein starts at alpha 1 and self-clears -
the `fadein` early-out at `player.cpp:7821` - so it is a flash, not a latch) -> ring on the carrier
-> inhale at +0.9 s -> `coop_lensSplash 0.95` (exists). The water volume eases OUT at 1.0/s
(`cg_view.c:5796`), ~1 s of green after the head is up, which is the opposite of a gasp; a cgame
change to 3.3/s out when leaving water snaps it (one constant, cgame-only).

### The envelope, ~23 s cut (pace 1.0; air drives 3a, jolts are dur/mag)

| t | beat | air | bpm | picture (Route 2) | ears | jolt |
|---|---|---|---|---|---|---|
| 0.0 | plunge | 1.00 | 55 | water in, blur 12 px | impact, wash, bed, heart | - |
| 0.6-1.9 | tumble | 0.92 | 60 | ripple x1.3 (dizzy 2.9) | bubbles trail | - |
| 1.9 | bottom | 0.85 | 65 | - | hitsand (carrier), burst | 0.55/1.9 |
| 2.2-4.2 | eyes | 0.85 | 65 | fade 2.0 s | airout (owed), bubbles | - |
| 4.2-6.5 | black | 0.70 | 75 | black; heart audible over nothing | shell thud x1 | 0.15/0.4 |
| 6.5 | wake | 0.60 | 85 | snap open, tunnel 0.25, desat 0.2 | wake (owed) | 0.30/2.4 |
| 7.0-8.2 | sand (1.2 s) | 0.50 | 92 | pulse visible | memory voices | - |
| 8.2-9.7 | try1 | 0.40 | 100 | tunnel 0.4 | swim, hitsand | thrash x3 |
| 9.7-11.4 | try2 | 0.28 | 112 | tunnel 0.5, blur x1.6 | swim, hitsand, thud | thrash x3 |
| 11.4-13.8 | rise + knees | 0.22 | 118 | shafts x1.5 (looking up) | second wash | - |
| 13.8-22.4 | 5 strokes | 0.20 -> 0.08 | 120 -> 135 | tunnel 0.55 -> 0.75, desat 0.5 | swoosh + strain (carrier), waders die | 0.22/0.55 each |
| 22.4-23.6 | gather | 0.05 | 140 | tunnel 0.8, pulse 0.12 | thud | - |
| 23.6-24.2 | break | snap 1.0 | stop | white flash 0.25 s, water out fast | gasp, ring, inhale | - |

## 4. Ranked list

| # | effect | cost | risk | what the user sees | probe |
|---|---|---|---|---|---|
| 1 | Air ramp -> `coop_uwAir` -> `r_ppUnderwaterAir` in `u_Color.w`: closing tunnel, desaturation, blur climb, pulse synced to bpm(air) | cgame + gl2 renderer | low: unused component, no uniform shift; T10 pair-ship | the frame closes in and throbs faster as he fails; opens on the gasp | `UWFX v3 enter ... air=`, `RAMPUW air=` per step |
| 2 | Heart cadence rebuild: one-shot beats on a carrier at 1.10 -> 0.50 s | script + alias (mod only) | low; carrier pattern proven (bed) | heart races into the strokes, stops at the break | `RAMPUW heart bpm=` |
| 3 | Fix the placeholder collisions: jolt sounds off `playlocalsound`/CHAN_LOCAL onto a carrier; re-home hitsand/strain under `coop_swim/` | script + alias | low; removes two bug-2436-class cuts | the wash lasts the whole hold; the score stops dipping every stroke | count `COV SND coop_underwater_wash` reaching 14 s; no sidechain arm |
| 4 | Waders retime + sink re-thread for the cut without the look | script only, MANDATORY with the removal | medium: re-run the frustum check in the waders header | men still go down in front of him; she is heeled at the surface look-back | `UNDERWADE seat=` inside `stroke 1-3`; `HIGGINSSINK band=1` before `RAMPUW up` |
| 5 | Bubbles: `coop_uwbubble.tik` originemitter following the camera, bursts on airout/jolts | mod only (tik + sprite reuse) | low-medium: spawn-below-surface rule, effectdetail scaling | his own breath leaving him, rising past the lens | `RAMPUW bubbles burst=` |
| 6 | Lid from below: `blendFunc blend` + `depthwrite` in `zz_coop_ocean.shader` | shader only, m3l1a-only | low: depthwrite is the one thing that can go wrong (silt) | the surface is a lit ceiling he cannot reach instead of a wall | `UWFX debug centerDist` finite when pitched up |
| 7 | Exit polish: white flash, inhale, ring re-fire, fast water-out | script/alias; the ease is cgame | low | a real first breath | `RAMPUW gasp` then `inhale` |
| 8 | Caustics on the seabed terrain (retail recipe) | shader only | medium: above-waterline bleed, gl2 tcMod survival | light dancing on the sand and the bodies | visual only |

Shader/texture only: 6, 8. cgame: 1 (with renderer), 7 (the ease). game.dll: none. Everything
else is script, alias, tik.

## 5. Prior work

`.wolf/buglog.json` (1818 entries, 53 hits on uw/underwater/tinnitus/muffle/drown, scanned by
script): the ones that shape this beat are 2320 (the plunge and the yaw rail), 2342 (four beats,
shellshock + wash), 2345/2476/2488 (the dead: never ran, then fixed, then pre-placed), 2350 (bob ->
looking), 2355 (v2 filter) and the v3 volume (`underwater_fp.glsl` header), 2359 (blood cloud,
`wateronly` rules), 2436/2452/2456 (CHAN_LOCAL collisions - 2456 still open), 2430/2494 (strain and
hitsand: dead, then placeholders), 2431 (`playlocalsound` discards volume and pitch), 2432/2454/2465
(the heartbeat was silent for two independent reasons; fixed 09-05), 2437 (heart stop funnel), 2440/
2448 (the head), 2443 (eyes/black/wake), 2444 (the muffle), 2455 (3D path discards alias volume -
open), 2470 (the look threads the sink), 2475 (waders keyed to the look), 2487/2496 (the sink never
moved), 1158 (the post chain), 1250 (DBNO eye drop and water), 846/948/1669/1941/1942/2234/2354
(tinnitus and dizziness history). `docs/proposals/water_omaha_2026-09-05/` sections 3.5 and 3.6 and
`LANE-A` section 7 measure the water pass and the opaque lid; nothing there is contradicted here,
and item 6 above is its 3.5 with the `depthwrite` caveat added.
