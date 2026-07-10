# MOH Coop Trilogy

![MOH Coop Trilogy](docs/badge.png)

> *The MOH Trilogy Coop Mod is a love letter to the early Medal of Honor franchise.*

Play **Medal of Honor: Allied Assault War Chest** cooperatively — the complete *Allied Assault*, *Spearhead*, and *Breakthrough* campaigns, mission by mission, with up to 16 players (4 players for the true experience).

Built on the [HaZardModding Coop Mod](https://github.com/HaZardModding/hzm-mohaa-coop-mod) by chrissstrahl and a custom fork of the [OpenMOHAA](https://github.com/openmoh/openmohaa) engine, then heavily extended: modern movement and gunplay, a full audio overhaul, HD visuals with post-processing on the classic renderer, and dozens of coop-specific systems. One installer, automatic updates at every launch, and your original game folder is never touched.

> [!WARNING]
> **Early alpha.** This project is under heavy active development: expect bugs, rough edges, and
> frequent updates. When something breaks, please report it — either through the built-in
> **Start menu -> "MOH Trilogy Coop - Report a Problem"** tool (one click, sends your logs straight
> to the dev team) or by [opening an issue](https://github.com/MOHCoopTrilogy/releases/issues).
> Bug reports are the single most helpful thing you can do for the project right now.

**[Download the latest release →](https://github.com/MOHCoopTrilogy/releases/releases/latest)**  |  **[Join our Discord →](https://discord.gg/Br9FDB3KU)** — release announcements, find people to play with, report bugs, follow development

| Repo | What it holds |
|---|---|
| [MOHCoopTrilogy/releases](https://github.com/MOHCoopTrilogy/releases) | This repo — downloads, the auto-update manifest, build & installer pipeline |
| [MOHCoopTrilogy/hzm-mohaa-coop-mod](https://github.com/MOHCoopTrilogy/hzm-mohaa-coop-mod) | Mod source (scripts, UI, configs, assets) |
| [MOHCoopTrilogy/openmohaa](https://github.com/MOHCoopTrilogy/openmohaa) | Engine fork source (GPLv2) |

## Requirements

- A GOG installation of [Medal of Honor: Allied Assault War Chest](https://www.gog.com/game/medal_of_honor_allied_assault_war_chest)
- Windows, and roughly 6 GB of free disk space

That's the whole list. The engine, renderer, runtimes, and all mod content are bundled. The installer detects your GOG install automatically and reads the original game data from it **without modifying it** — everything installs side-by-side into its own folder, so your vanilla game keeps working exactly as before.

## Install

1. Go to [Releases](https://github.com/MOHCoopTrilogy/releases/releases/latest) and download the latest `MOHCoopTrilogy-Setup-<version>.exe` **together with all of its `.bin` parts** (the payload is split into ~2 GB slices — the exe needs them next to it).
2. Keep the exe and the `.bin` files in the same folder and run the exe.
3. Launch the game through the **MOH Trilogy Coop** shortcut (desktop or Start menu). Every launch quietly checks for updates and downloads only what changed — typically a few megabytes. If the check fails for any reason, the game simply starts with what you have; updates never block play.

**Already on a 1.0.x test build?** Grab the small `MOHCoop-Upgrade` zip from Releases instead of the full setup — after that one patch, the auto-updater keeps you current.

**Something broke?** Start menu → **MOH Trilogy Coop – Report a Problem** collects your logs and system info and sends them to us in a couple of clicks. GitHub [Issues](https://github.com/MOHCoopTrilogy/releases/issues) work too.

### Playing

Host: launch the shortcut, then **Multiplayer → Start Game → HaZardModding Coop Mod**, pick a mission tile, hit Apply. Friends join over LAN/Internet via **Multiplayer → Join Game** or `connect <ip>` in the console.

## Features

### Full-campaign co-op

- All three War Chest campaigns playable start to finish in coop — 50+ missions with working objectives, cutscene moments, escorts, and vehicle rides
- Objectives HUD with main and side objectives, mission-progress respawn points, and map-to-map transitions
- **Down-But-Not-Out**: instead of dying you go down — crawl, hold on (heartbeat and breathing close in), and self-revive with a medkit, or bleed out
- Optional **Last Man Standing** mode with a shared pool of lives
- AI difficulty and enemy counts scale with how many players are in — more players means more Germans, within sane caps
- **Officer boss encounters**: named officers with reinforcement waves, death battalions, German voice lines, and heal-and-retreat behavior
- **Officer forces scale with your squad**: reinforcement health, accuracy, and unit sizes grow with player count — and scale *down* below the two-player baseline, so solo runs get smaller bodyguard details, squads, and battalions
- **Reward items** from officer kills: binoculars that call in airstrikes, and signal smoke that summons a C-47 supply paradrop — including an AI medic who can get downed players back up
- Server-tunable rules via cvars: player health, DBNO on/off, LMS lives, corpse persistence, and more

### XP, ranks & insignia

- **Persistent XP** earned per player and saved across sessions — 13 authentic US Army WW2 ranks with metallic insignia, shown on the scoreboard next to your name
- XP for everything: kills (bonuses for headshots, melee, long range), **assists**, **valor** (saving a teammate under fire, fighting while downed, guarding the fallen), officer bounties, denied officer heals, airstrike/paradrop support calls, paratroopers you keep alive, objectives, mission completion, and deathless runs — plus **blindfire** and **fighting-from-cover** kill bonuses
- A tiny **"+2 Kill" popup by the crosshair** per kill (toggleable in Coop Settings), with the brass progress bar appearing at every 100-XP milestone instead of spamming
- **Promotion ceremony**: your new insignia front and center, scored with a cinematic M1 Garand ping (reverb tail, then reversed)
- **Animated end-of-match debrief**: the bar fills from where you started to where you ended — rolling through every rank you gained with a ping and insignia swap — while your per-category totals click in one at a time
- Rank thresholds are locked: they double as the spine for the planned skill trees

### Combat & movement

- **Aim-down-sights** on right mouse, individually tuned for 24 weapons
- **Over-the-shoulder third-person aiming**: hold aim in third person for a true shoulder camera — the gun stays raised and level while you move in any direction, middle-mouse swaps shoulders, mouse-wheel-up hands off into first-person irons
- **Three view modes on one bind**: first person → third person → third person **free cam** (mouse-orbits the camera freely, WASD moves without turning it, crosshair projects your true aim)
- **Take Cover** *(beta — actively being polished)*: face a wall or low obstacle and hit your cover bind — auto third-person, blind-fire around corners or over the top exactly where your crosshair points, hold aim to peek out (you rise over low cover to actually shoot), release to tuck back in
- **Mounted-gun third person** *(experimental)*: man the jeep .30cal in third person with a proper standing gunner stance
- **Sprint & stamina** — weapon lowers, gear rattles, stamina drains and recovers; walk quietly on ALT
- Weapon **bash** on its own key, plus lean
- **Player emotes**: salute, at-ease, and stretch on bindable keys
- **8-second spawn protection** so reinforcements aren't farmed
- **Medkits** — carry self-heal charges, pick up dropped health, and get patched up by the paradrop AI medic
- Deployable **ammo box** (team resupply) and **sandbag cover** anyone on the team can use
- **MG42 overheat** on mounted guns — for you *and* for German gunners
- **Supersonic bullet cracks and zings** — rounds that nearly hit you snap past your head and feed the suppression system
- **Smoke whips** — lingering muzzle and impact smoke; shell casings and per-surface impact sounds
- **Weapon weight** — view weapons carry momentum and lag naturally with movement
- **Corpse impact physics** — explosions actually throw bodies
- **Blood trails** from wounded enemies you can follow
- **Suppression**: near misses desaturate and tighten your view
- **Tinnitus** and muffled hearing after close explosions
- **Death voices**: a 334-scream pool with distance filtering — far-away kills sound far away
- Headshot kill audio cue

### Audio overhaul

- Every weapon re-voiced — gun sounds redesigned from professionally recorded, licensed sound libraries
- **Environmental reverb**: interiors classify themselves (room, stone hall, bunker) and gunfire reverberates to match
- **Sound occlusion** — fights on the other side of a wall sound like they're on the other side of a wall
- **HRTF** 3D audio for headphone users
- **Distance layering**: distant gunfire gets true far-field tails instead of the same close-up bark
- Full in-game **audio mixer**: Master, Music, SFX, Ambience, and Dialogue sliders, plus an **output-device picker**
- **Footstep overhaul** — new stone/dirt/foliage/metal/sand/snow/water steps, and enemies you can actually hear coming
- Radio squelch framing on officer calls, gear rattle while sprinting, and hundreds of new battlefield one-shots (artillery rumbles, thunder, glass, debris)
- Per-map ambience beds and dynamic weather you can hear roll in
- Battle-aware ducking so big scripted moments read clearly over the noise
- Engine-level sound fixes: 2x the vanilla sound limit, output limiter against clipping, audio follows your Windows default device

> Early-alpha note: the audio stack is new — some SFX and advanced sound settings may still be buggy. Reports welcome.

### Visuals

- Bundled **HD texture, character, world, FX, and skybox packs** (see credits), wired through a DDS override pipeline so the HD versions load reliably everywhere
- Post-processing on the classic renderer: **bloom**, **contrast-adaptive sharpening**, and suppression/low-health screen effects
- Decal **shadows** under characters
- Overhead **teammate icons** so you stop shooting your friends
- **Dynamic weather** — rolling rainstorms driven through the engine's native weather system
- Full-detail models at all distances, HD-upscaled menus and UI art
- Experimental **3D grass** (off by default — toggle in Video options)

### Quality of life

- One-click installer, side-by-side with your GOG install — nothing in the game folder is ever modified
- **Automatic updates** at launch, usually only a few MB — followed by a one-time declassified **field report** in the menu telling you what's new
- In-game **coop settings hub** (find the desk telephone) plus rebuilt **advanced audio and video options** — mixer, output device, speaker/HRTF setup, post-FX and grass toggles
- **FOV slider that actually works** — applies in first person and persists across restarts (as do your view-mode preferences)
- **Console copy/paste** — Ctrl+V or Shift+Insert pastes into the in-game console
- Bindable coop commands (deployables, objectives recap, view-mode cycle, emotes, coop actions)
- Corpse persistence control — keep the battlefield littered or tidy
- Objectives recap toggle on a key
- **Report a Problem** tool in the Start menu

### Known rough edges (help us test!)

Honesty corner — these shipped recently and are still settling:

- **Take Cover** — pose detection on odd geometry, peek transitions, and blindfire aim are under active tuning; expect occasional weirdness
- **Jeep .30cal third person** — the gunner stance and camera are new; firing effects and pose alignment were just reworked
- **Free cam** — recently rebuilt (mouse-only rotation, projected crosshair); report any camera locks or snaps
- **Shoulder-aim movement animations** — the legs still use standard run/strafe cycles while aiming; dedicated aimed-locomotion animations are in the works
- **Audio stack** — some SFX and advanced sound settings may still misbehave (see above)
- **XP debrief and popups** — brand-new presentation; layout oddities on unusual resolutions are possible (ultrawide is tested)

## Per-map fixes & polish

Beyond the systems above, a long tail of mission-specific work keeps the campaigns actually finishable in coop. Highlights:

- **Trilogy-wide objective failsafes** — plant-to-destroy objectives (nebelwerfers, flak guns, AA batteries, cannons) now count *however* you destroy them: airstrike, grenades, tank shells. No more missions stalling because you got creative
- **Objective-tool protection** — guns the mission *needs* you to use (the Ardennes nebelwerfer, the t1l3 flak cannon, the t1l1 AA gun, the escape tank) can no longer be accidentally destroyed early and soft-lock the map
- **t2l1 Ardennes** — full officer/reinforcement integration, late-map respawn point, restored missing battle-sound gates (sirens included)
- **t2l2** — the halftrack/truck convoy ride rebuilt for coop: solid riders, locked cameras, everyone arrives together
- **m1l3a / m1l3b** — jeep rides with proper coop seating and respawns; **m1l1** — restored truck sequence
- **m1l2a** — SAS escort fixed; **m2l1** — Grillo escort + officer staging; **m2l2 / m2l3** — U-boat pens and train-station finales staged for coop
- **m3l1a Omaha** — landing-craft audio pacing and beach ambience; **m3l2** — HOLD-line battalions and defend waves
- **t1l3** — the colonel can no longer be killed by your own bombing run mid-cutscene (script-breaker fixed)
- **e3l4** — five separate crash fixes; the map no longer takes the server down
- **AI polish everywhere** — paradrop/airborne death animations, pain-handler fixes, smoke grenades no longer eat your frags, corpse-stuck AI fixed
- All Spearhead and Breakthrough missions run under a **single unified launch profile** — no juggling separate game modes

## Roadmap

In design and research — being built in the open, no dates promised:

- **Play online without port forwarding** — a tiny rendezvous service + UDP hole-punching so a friend can join with a memorable code instead of router surgery *(in active development)*
- **Skill trees** — the shipped XP ranks become spendable in three trees: **Ranger** (assault), **Corpsman** (medic/support — reviving teammates is planned as a Corpsman unlock), and **Pathfinder** (recon/officer hunting)
- **Carryable machine guns** — the portable MG42 (carry it, deploy it on its bipod/tripod, pack it back up) as an equippable loadout option, later as map pickups and enemy MG teams; a .30 cal variant to follow
- **New player animations** — proper aimed-movement, sprint, mantling, and richer death/pain variety, re-authored in-house on the game's own skeleton
- **Between-mission lobby** — a staging area with a ready-up system between maps
- **In-game update notifications** — an "update available" notice in the menu when a release lands while you're playing

## Credits

This project stands on a lot of other people's work. Thank you:

- **chrissstrahl, Smithy (1337Smithy), and HaZardModding** — creators of the original [HZM Coop Mod](https://github.com/HaZardModding/hzm-mohaa-coop-mod), the coop framework this entire project builds on, plus the HZM testers and community ([hazardmodding.com](http://www.hazardmodding.com))
- **The OpenMOHAA team** — the open-source [engine](https://github.com/openmoh/openmohaa) that makes any of this possible
- **HD content packs**, bundled with attribution to their authors:
  - *MOHAA HD Project* (AA HD Project paks)
  - *HRRTM — HD Realism Texture Mod* (texture, model, and weapon paks plus the blood-effects addon)
  - HD gun sounds, geared soldiers, and HD foliage packs by their respective authors
  - Additional in-house upscale and gap-fill packs (character skins, world, FX, skybox, DDS overrides) produced for this project
- **Sound design** — additional weapon and world audio built from licensed professional sound libraries
- **2015, Inc. / Electronic Arts** — the original *Medal of Honor: Allied Assault* trilogy

*MOH Coop Trilogy is an independent, non-commercial fan project. It is not affiliated with, endorsed by, or sponsored by Electronic Arts, 2015 Inc., or any other rights holder of the Medal of Honor series. Medal of Honor and all related trademarks and assets remain the property of their respective owners. A legitimate copy of the original game is required to play.*

## License

- **Engine fork** — GPLv2, source at [MOHCoopTrilogy/openmohaa](https://github.com/MOHCoopTrilogy/openmohaa) (upstream: [openmoh/openmohaa](https://github.com/openmoh/openmohaa))
- **Mod scripts and content** — under the original HZM Coop Mod's terms; see `hzm_legal.txt` in the [mod repo](https://github.com/MOHCoopTrilogy/hzm-mohaa-coop-mod)
- **Game assets** — remain the property of their respective owners and are not covered by the above

## Feedback & community

**[Discord](https://discord.gg/Br9FDB3KU)** is the project's home — release announcements land there the moment they ship, and it's the fastest way to reach the devs, report bugs, or find a squad to play with.

Found a bug, or something just feels off? Use the **Report a Problem** tool in the Start menu (it attaches the logs we need), post in Discord, or open an issue on [this repo](https://github.com/MOHCoopTrilogy/releases/issues). Mission-breaking bugs in any of the 50+ maps are the highest priority — tell us the map and what you were doing.

---

*About this repo: alongside Releases, it hosts the project pipeline — `build.ps1` (packs the mod tree into pk3s and deploys a dev install), `installer/` (Inno Setup sources + the problem reporter), `updater/` (the launch-time auto-updater), and `publish_release.ps1` (manifest generation and release publishing).*
