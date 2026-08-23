# Frontline Soundtrack Mapping — In-Game Music Research + Proposal

**Date:** 2026-06-24
**Scope:** IN-GAME, per-map / per-event soundtrack usage and a MOH: Frontline track-to-map mapping. (Main-menu music wiring is a separate agent's task and is NOT covered here.)
**Mode:** Research + propose only. No mod files edited, no build, no launch (live map-rotation test in progress).
**Bottom line on format:** Provide **MP3, 22050 Hz, stereo (2-channel), ~constant ~128 kbps**, placed under `sound/music/` in the coop pk3 and referenced by full path. See Section 2 for the hard reasons.

---

## 1. How the in-game music system works (engine + mod)

### 1a. Two parallel engine systems — only ONE is alive on this build

MOHAA's engine exposes two music subsystems:

1. **Mood/soundtrack system** (the "normal" vanilla way): script commands `music`, `forcemusic`, `soundtrack`, `musicvolume`, `restoresoundtrack`, driven by `.mus` soundtrack-definition files and per-player `current_music_mood` / `fallback_music_mood`.
   - fgame events registered: `code/fgame/scriptthread.cpp:578-625` (`music`, `forcemusic`, `musicvolume`, `restoremusicvolume`, `soundtrack`, `restoresoundtrack`).
   - worldspawn key: `code/fgame/worldspawn.cpp:45-51` (`"soundtrack"`) and `:492` dispatch.
   - server→client plumbing: `ChangeSoundtrack()` sets `CS_MUSIC` configstring at `code/fgame/g_utils.cpp:1674-1685`; mood snapshotted in playerstate (`player.cpp:2333, 7660, 7802-7811`).
   - client receives it: `cg_main.c:450` → `cgi.MUSIC_NewSoundtrack(str)`; `cg_snapshot.c:166,223` → `cgi.MUSIC_UpdateMood(...)`.

2. **Triggered-music system** (raw background-track streaming): client console commands `tmstart`, `tmstartloop`, `tmstop`, (`tmvolume`).

**CRITICAL FINDING — the mood/soundtrack system is STUBBED OUT on this NO_MODERN_DMA build.**
This build excludes the modern (`snd_*_new.cpp`) sound path and compiles `code/client/new/snd_main_new.cpp` instead (gated `#if NO_MODERN_DMA`, line 26). In that file:
- `MUSIC_NewSoundtrack()` → `// FIXME: unimplemented; STUB();` (`snd_main_new.cpp:253-257`)
- `MUSIC_UpdateMood()` → empty / no-op (`:264-268`)
- `MUSIC_UpdateVolume()`, `MUSIC_StopAllSongs()` → `STUB()` (`:275-290`)

So `music "action"`, `forcemusic`, `soundtrack music/x.mus`, mood transitions, and `musicvolume` **parse server-side and set configstrings but do nothing audible** — the client handlers are no-ops. (The fully-implemented versions live in `snd_openal_new.cpp:3697+`, which the OpenAL/modern build uses — NOT this build.)

> Note: the project memory `sound_system_reference.md` (lines 132-157) describes the mood/`.mus` system as if it works and suggests `forcemusic`/`soundtrack` for the officer fight. That guidance is **stale for this build** — those commands are inert here. Use `tmstart`/`tmstartloop` instead.

### 1b. The ONLY working in-game music path: `tmstart` → background stream

`tmstart`/`tmstartloop`/`tmstop` are registered in the active build:
- `snd_main_new.cpp:39-41` (`S_Init2` registers them on NO_MODERN_DMA).
- `S_TriggeredMusic_Start()` → `S_StartBackgroundTrack(file, "")` (`:463-471`)
- `S_TriggeredMusic_StartLoop()` → `S_StartBackgroundTrack(file, file)` (loops) (`:478-486`)
- `S_TriggeredMusic_Stop()` → `S_StopBackgroundTrack()` (`:493-496`)

These resolve to the old DMA streamer in `snd_dma.c`:
- `S_Base_StartBackgroundTrack()` → `S_OpenBackgroundStream()` → `S_CodecOpenStream(filename)` (`snd_dma.c:1415-1432, 1389-1408`).
- The stream is decoded incrementally each frame by `S_UpdateBackgroundTrack()` (`:1440-1507`) and looped by re-opening `s_backgroundLoop` at EOF (`:1493-1495`).

`tmvolume` is **NOT registered** on this build (only `tmstart/loop/stop` are added in `snd_main_new.cpp:39-41`; `tmvolume` is added only in the OpenAL path `snd_openal_new.cpp:721`). So volume-fade calls are no-ops here — see Section 2 caveat.

### 1c. How a map declares / triggers music in the mod

The HZM mod wraps everything through `global/music.scr` and a coop-safe relay in `coop_mod/replace.scr`:
- `global/music.scr` — `PlaySong`, `PlaySongLoop`, `StopSong`, `SetVolume`. Each calls `exec coop_mod/replace.scr::tmstart` / `::tmstartloop` / `::tmstop` / `::tmvolume` (`music.scr:23,28,53,58,85,92,95,112`).
- Maps either call the wrapper (`waitthread global/music.scr::PlaySongLoop "sound/music/mus_Schmerzen_01a.mp3"`, e.g. `maps/e1l1.scr:482,506`) **or** call the coop relay directly (`exec coop_mod/replace.scr::tmstartloop sound/music/mus_03c_suspense.mp3`, e.g. `maps/m1l1.scr:156,919`).

All references are `sound/music/mus_*.mp3` — i.e. **base-game MP3s shipped in pak0**. The mod ships **no music files of its own** (only `global/music.scr`); confirmed by `find` over the mod tree.

---

## 2. Coop handling + audio format / integration recipe

### 2a. Coop: music is relayed to ALL players (good)

`coop_mod/replace.scr` is the coop-compatibility shim. Each music verb loops over every connected player and `stufftext`s the client command:
- `tmstop` (`replace.scr:534-545`): `for (i=1..$player.size) { $player[i] stufftext "tmstop" }`.
- `tmstartloop` (`:553-577`): builds `"tmstop;tmstartloop <file>"` and stuffs it to every player.
- `tmstart` (`:583-609`): builds `"tmstart <file>"` (optionally `"tmstop;tmstart …"`) to every player.
- `tmvolume` (`:613-...`): loops all players. **On this build `tmvolume` is an unregistered client command → harmless no-op / possible "unknown command" console line, but no crash.**

`tmstart/tmstartloop/tmstop/tmvolume` are on the cgame server-command allowlist (`cg_servercmds_filter.cpp:72-75`), so the server stuffing them to clients is permitted.

**Verdict: in-game music is coop-correct for all 16 players** as long as you go through `global/music.scr` or `coop_mod/replace.scr`. Do NOT call `$player stufftext "tmstart …"` directly on a single player (host-only). Always use the wrapper.

### 2b. Exact format the user must provide

The DMA streamer expects the file to decode to **22050 Hz, 2-channel (stereo)**. Source:
- `S_OpenBackgroundStream` warns `"music file %s is not 22k stereo"` when `info.channels != 2 || info.rate != 22050` (`snd_dma.c:1405-1407`). It will still *attempt* to play off-spec files, but the streamer's sample math (`fileSamples = bufferSamples * info.rate / dma.speed`, `snd_dma.c:1465`) is tuned for 22k — off-rate files pitch/speed-shift and waste CPU. Match 22050 Hz stereo to be safe.

Codec availability on this build:
- `S_CodecInit()` registers codecs behind `#ifdef`s (`snd_codec.c:123-141`). **`USE_CODEC_MP3` is defined unconditionally** for the client target (`code/client/CMakeLists.txt:24`, an `INTERFACE` definition applied regardless of `NO_MODERN_DMA`). `snd_codec_mp3.c` compiles (it's a `snd_codec*.c` file, included in both CMake branches at lines 47 and effectively surviving the NO_MODERN_DMA `*.cpp`-only exclusion filter at line 57). MP3 decoding uses `mad.h` (libmad) — `snd_codec_mp3.c:34`.
- `USE_CODEC_VORBIS` / `USE_CODEC_OPUS` are NOT defined by this CMake → **OGG/Opus are NOT compiled in.** WAV is always registered last (`snd_codec.c:140`).
- Codec is selected by file extension in `S_CodecOpenStream`; with no matching extension it falls back to WAV.

**=> Supported in-game music formats on this build: MP3 (libmad) and WAV (PCM). NOT Ogg/Opus.**

**Recommended deliverable: MP3, 22050 Hz, stereo, ~128 kbps CBR.** This matches how the base game ships its music (`sound/music/mus_*.mp3`) and is what every existing `tmstart*` call references, so it is the lowest-risk, proven path.

### 2c. Size caveat — DO supply MP3, NOT full-length 44.1k PCM WAV

This project has a documented history of large 16-bit/44.1k PCM WAVs crashing the load path (see MEMORY engine-fix notes on oversized media). The background streamer reads incrementally (30 KB raw buffer, `snd_dma.c:1443`), so streaming itself is fine — but:
- A 5-7 minute track as **44.1 kHz 16-bit stereo PCM WAV** is ~50-75 MB on disk and balloons pk3 size / load memory. **Avoid.**
- The same track as **22 kHz stereo 128 kbps MP3** is ~3-6 MB and decodes on the fly. **Use this.**
- Frontline tracks range 1:55-7:18 (Section 4). Long cues (Arnhem 5:52, Escaping Gotha 7:18) are fine as MP3; they are NOT fine as PCM WAV.

**Looping:** `tmstartloop` re-opens the same file at EOF (`snd_dma.c:1493-1495`) — there is no crossfade and no gapless seam handling, so the track restarts from sample 0. For ambient/suspense beds, trim the MP3 so its head and tail are quiet/low-energy (or pick the more "loopable" cues) to avoid a jarring restart. For one-shot set-pieces, use `tmstart` (no loop) and let it stop naturally.

### 2d. Integration recipe (for when the user supplies files)

1. Place each `Frontline_<Name>.mp3` (22k stereo, 128 kbps) under `sound/music/` in the coop pk3 (alongside the existing `mus_*.mp3`). **No ubersound alias is needed** — background tracks are referenced by raw path, not by alias. (Aliases are only for `playsound`/`loopsound` positional SFX.)
2. To play it for all players at a map intro or event, call the coop-safe wrapper from the map script:
   - Looping bed: `waitthread global/music.scr::PlaySongLoop "sound/music/Frontline_OperationMarketGarden.mp3"`
   - One-shot sting/finale: `waitthread global/music.scr::PlaySong "sound/music/Frontline_Arnhem.mp3"`
   - Stop with fade-attempt: `waitthread global/music.scr::StopSong 2` (note: fade is a no-op here since `tmvolume` is unregistered; it will hard-stop).
3. Do not use `music`/`forcemusic`/`soundtrack` (mood) commands — inert on this build (Section 1a).

---

## 3. Blank-space inventory (where music is absent or sparse)

**Method:** Diffed all 53 rotation maps against every map/sub-script containing `tmstart`/`tmstartloop`/`PlaySong*`, then counted cues per map. "Cues" = number of `tmstart*`/`PlaySong*` calls (a proxy for distinct music moments).

### 3a. Fully silent maps (HIGHEST-VALUE blank-space fills)

| Map | Theater | Has music? | Notes |
|-----|---------|-----------|-------|
| **m3l1a** | AA (North Africa, Kasserine/airfield approach) | **NONE** | Zero music calls anywhere in script or subdir. Plays entirely silent. |
| **m3l1b** | AA (North Africa) | **NONE** | Zero music calls. Silent. |
| **t1l1** | Spearhead (Holland / glider/plane insertion) | **NONE** | Zero music calls. Silent. Note: ride/intro set-piece map. |
| **t2l3** | Spearhead | **NONE** | Zero music calls. Silent. |
| **t2l4** | Spearhead | **NONE** | Zero music calls. Silent. |

(Pure data note: `m4l0` and the `*_precache` stubs are not playable rotation entries and are excluded.)

### 3b. Sparse maps — single cue then long silence (HIGH-VALUE fills)

These fire music exactly **once** (one intro/suspense loop) and then run the entire mission — combat, set-pieces, finale — on that single loop or in silence after it ends:

| Map | Cues | Theater | Typical silent stretch |
|-----|------|---------|------------------------|
| e3l1 | 1 | Breakthrough (Italy/Anzio) | Whole level after intro |
| m1l2a | 1 | AA (U-boat pen / sub base) | Combat + objective hunt |
| m1l2b | 1 | AA (U-boat / sub) | Set-pieces silent |
| m1l3a | 1 | AA (sub pen finale leg) | Boss/escape silent |
| m1l3b | 1 | AA | Combat silent |
| m1l3c | 1 | AA | Finale silent |
| m2l2a | 1 | AA (Hunt the Bismarck / ship) | Long stretches silent |
| m2l2c | 1 | AA (ship) | Silent |
| m6l3e | 1 | AA (final mission leg) | Climax/finale silent |
| training | 1 | Tutorial | n/a (low priority) |

### 3c. Light coverage — 2 cues (MEDIUM-VALUE fills)

m1l1, m2l2b, m2l3, m3l2, m3l3, m4l2, m4l3, m5l1a, m5l2a, m5l2b, m6l1c, m6l3b, m6l3c, **t1l3, t2l2, t3l1, t3l2** (the Spearhead 2-cue maps are notable — Holland/Market-Garden content with almost no score). Each typically gets an intro suspense loop + one combat/surprise cue; officer fights and finales are unscored.

### 3d. Well-scored maps (likely "replace/augment" only, not blank-fill)

The Spearhead/Breakthrough e-series is the densest: e1l4 (8), e2l1 (8), e1l2 (7), e1l1 (6), m2l1 (6), e3l4 (5), m6l2a (5), plus several 4-cue maps. These already use the original Giacchino MOH:AA score (`mus_Schmerzen_*`, `mus_SniperTown_*`, etc.) and are lower priority for new music.

### 3e. Universally unscored event types (cross-map blank space)

Even on scored maps, these set-piece categories almost always play with no dedicated music:
- **Officer / boss encounters** (the coop officer feature in `coop_mod/officer.scr`) — no music hook today; mood-based `forcemusic` suggested in old memory is inert. **Prime candidate for a triggered action cue.**
- **Vehicle / on-rails rides** (t1l1 plane, t2l2 halftrack, t3l2 T-34, m1l1 ride cams) — intros often silent.
- **Finales / mission-complete** — `missioncomplete.scr` plays no victory music.
- **Stealth/papers segments** (e1l3 Sneakers, disguise anims) — deliberately sparse; respect "stealth = quiet, going-loud = score" tone rule.

---

## 4. Frontline track → map/event mapping proposal

**Frontline OST tracklist** (Michael Giacchino; conducted Tim Simonec, Northwest Sinfonia; EA 2002). 19 tracks; durations noted for the loop/size caveat:

1. Operation Market Garden (5:33) · 2. Border Town (3:37) · 3. U-4902 (4:44) · 4. Shipyards of Lorient (3:14) · 5. After the Drop (5:38) · 6. Kleveburg (3:32) · 7. Manor House Rally (3:48) · 8. The Halftrack Chase (3:41) · 9. Nijmegen Bridge (3:22) · 10. The Rowhouses (4:40) · 11. Arnhem (5:52) · 12. Emmerich Station (3:02) · 13. Thuringer Wald Express (2:52) · 14. Sturmgeist's Armored Train (3:55) · 15. Approaching the Tarmac (3:48) · 16. Clipping their Wings (3:27) · 17. Escaping Gotha (7:18) · 18. The Songless Nightingale (1:55) · 19. Untitled (5:20)
(Sources in Section 6.)

**Tags:** `[FILL]` = blank/sparse space, highest value. `[EVENT]` = new triggered cue for an unscored set-piece. `[REPLACE/AUG]` = layer onto/replace an already-scored moment (lower priority).

### 4a. Holland / Market-Garden ground & bridge maps → Frontline's Holland suite (thematic bullseye)

Frontline IS the Operation Market Garden game, so its Holland cues map 1:1 onto Spearhead's Holland content.

| Frontline track | Target map / event | Why it fits | Tag |
|-----------------|--------------------|-------------|-----|
| Operation Market Garden (#1) | **t1l1** (glider/plane insertion intro) | Main Holland theme over the airborne insertion; t1l1 is fully silent today | `[FILL]` |
| After the Drop (#5) | **t1l1** post-landing / first push; or **t1l2** opening | Literally "after the drop" — paratrooper assembly | `[FILL]` |
| Nijmegen Bridge (#9) | **t1l3 / t2l1** bridge or crossing set-piece | Bridge-assault scoring; these are 2-cue maps | `[EVENT]`/`[FILL]` |
| Arnhem (#11) | **t2l3** (silent) climactic Holland leg, or t2l1 finale | Long (5:52) dramatic siege cue for a big silent map | `[FILL]` |
| The Rowhouses (#10) | **t2l2** urban/house-to-house; or t2l4 | Urban Holland combat bed | `[FILL]` |
| Border Town (#2) | **t2l4** (silent) town fight | Town-combat action bed | `[FILL]` |
| Manor House Rally (#7) | **t3l1** objective/rally point | Rally/regroup cue for a 2-cue map | `[FILL]` |
| Kleveburg (#6) | **t1l2** / **t1l3** German-soil push | Mid-intensity combat; fills a 2-4 cue map | `[FILL]` |

### 4b. U-boat / port / dock / naval → Frontline's submarine & shipyard suite

| Frontline track | Target map / event | Why it fits | Tag |
|-----------------|--------------------|-------------|-----|
| U-4902 (#3) | **m1l2a / m1l2b / m1l3a-c** (U-boat pen / sub base, all 1-cue) | A submarine cue for the submarine missions — perfect thematic + heavy blank space | `[FILL]` |
| Shipyards of Lorient (#4) | **m2l2a / m2l2c** (Bismarck/ship, 1-cue) & port approaches | Shipyard/dockyard score for naval maps | `[FILL]` |
| The Songless Nightingale (#18, 1:55) | **e1l4** (sunk ship / map room) or any quiet dock interior | Short, somber piece for a quiet interior beat | `[REPLACE/AUG]` |

### 4c. Armored / vehicle / train pushes → Frontline's vehicle suite

| Frontline track | Target map / event | Why it fits | Tag |
|-----------------|--------------------|-------------|-----|
| The Halftrack Chase (#8) | **t2l2** (16-seat halftrack ride) | Halftrack music for the halftrack ride — exact match; ride intros are silent | `[EVENT]` |
| Sturmgeist's Armored Train (#14) | **t3l2** (T-34 / armored leg) or any train/armor set-piece | Driving armored-combat cue | `[EVENT]`/`[FILL]` |
| Thuringer Wald Express (#13, 2:52) | **t3l1 / t3l2** transit or escape leg | Train/transit motif; short and loopable | `[FILL]` |
| Rolling-thunder style action (Border Town #2 reuse) | **officer/boss encounters** (`coop_mod/officer.scr`) cross-map | Driving action bed when the officer "goes loud" — currently unscored | `[EVENT]` |

### 4d. North Africa (no Frontline-NA cue exists — use generic action/intensity)

Frontline has no desert theme, so map by *intensity*, not geography:

| Frontline track | Target map / event | Why it fits | Tag |
|-----------------|--------------------|-------------|-----|
| Approaching the Tarmac (#15) | **m3l1a** (airfield approach, SILENT) | Tense approach cue for the silent airfield map | `[FILL]` |
| Clipping their Wings (#16) | **m3l1b** (airfield, SILENT) | Aircraft-facility action; pairs with m3l1a | `[FILL]` |
| Emmerich Station (#12) | **m3l2 / m3l3** (2-cue NA maps) | General combat bed | `[FILL]` |

### 4e. Finales / escapes / stingers

| Frontline track | Target map / event | Why it fits | Tag |
|-----------------|--------------------|-------------|-----|
| Escaping Gotha (#17, 7:18) | **m6l3e** (final mission leg, 1-cue) or campaign finale | Long climactic escape cue for the silent finale | `[FILL]` |
| Untitled (#19, 5:20) | Mission-complete / `missioncomplete.scr` victory beat | Currently no victory music anywhere | `[EVENT]` |

**Loop/length notes for the user:** Escaping Gotha (7:18), Arnhem (5:52), After the Drop (5:38), Operation Market Garden (5:33), Untitled (5:20) are best used as `tmstart` one-shots on set-pieces, not seamless `tmstartloop` beds (no crossfade — Section 2c). Short cues — The Songless Nightingale (1:55), Thuringer Wald Express (2:52), Emmerich Station (3:02) — loop more gracefully.

---

## 5. Break-the-mod / coop-safety assessment

| Action | Rating | Reasoning |
|--------|--------|-----------|
| Add MP3 (22k stereo) under `sound/music/` and call via `global/music.scr::PlaySong*` on existing scored maps | **SAFE** | Identical mechanism to every existing cue; coop relay already loops all players. No engine change. |
| Add music to fully-silent maps (m3l1a/b, t1l1, t2l3, t2l4) | **SAFE** | Adding a `tmstartloop` where none exists can't regress existing audio; coop-safe via wrapper. |
| Add a triggered action cue to the officer/boss encounter | **CONDITIONAL** | Safe mechanically, but must route through `coop_mod/replace.scr` (all players), and must `tmstop`/restore the map's prior bed when the fight ends or you'll leave the wrong track looping. Test the spawn/despawn ordering. |
| Use `music`/`forcemusic`/`soundtrack`/`musicvolume` (mood/`.mus`) | **BREAKS (silently)** | Stubbed on NO_MODERN_DMA (`snd_main_new.cpp:253-290`). Audibly does nothing; relying on it = "no music" bug. Do not use. |
| Rely on `StopSong <fade>` for a smooth fade-out | **CONDITIONAL** | `tmvolume` is unregistered on this build, so the fade loop is inert and it hard-cuts. Fine functionally; just don't expect a fade. |
| Ship full-length 44.1k PCM WAV music | **BREAKS (risk)** | Large PCM WAVs have crashed this build's load path; also bloats pk3. Use MP3. |

### Phased rollout suggestion
1. **Phase A (SAFE, high value):** Drop Frontline MP3s into the 5 fully-silent maps + the 1-cue sparse maps (Section 3a/3b). Pure additive, zero regression risk. Validate one map (e.g. t1l1 with Operation Market Garden) on a private server before batching.
2. **Phase B (SAFE):** Score the Spearhead Holland 2-cue maps (t1l2/t1l3/t2l1/t2l2/t3l1/t3l2) with the Holland/vehicle suite (Section 4a/4c) — the strongest thematic matches.
3. **Phase C (CONDITIONAL):** Add the `[EVENT]` cues — officer fight, halftrack ride, mission-complete. Each needs a paired stop/restore and a coop-relay test (16-player). Bisect with `iprintlnbold` if a cue doesn't trigger for all players.
4. **Phase D (optional):** Augment/replace on already-scored e-series maps only if the user wants Frontline's flavor over the original MOH:AA score. Lowest priority.

---

## 6. Sources (Frontline tracklist)

- Medal of Honor Wiki — Frontline OST tracklist: https://medalofhonor.fandom.com/wiki/Medal_of_Honor:_Frontline_(Original_Soundtrack)
- Discogs — Michael Giacchino, MOH: Frontline (Original Soundtrack Recording): https://www.discogs.com/release/5144008-Michael-Giacchino-Medal-of-Honor-Frontline-Original-Soundtrack-Recording
- Michael Giacchino official — MOH: Frontline album: https://michaelgiacchino.com/albums/medal-of-honor-frontline/
- Internet Archive — MOH: Frontline OST: https://archive.org/details/medal-of-honor-frontline-original-soundtrack-recording

(Track names like "Rolling Thunder" / "The Horten's Nest" / "Needle in a Haystack" cited in the task prompt are NOT on the official Frontline OST release — they appear to be mission/level names or fan labels. The mapping above uses the verified 19-track release.)
