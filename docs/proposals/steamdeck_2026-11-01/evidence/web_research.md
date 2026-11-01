# Steam Deck research: HZM MOHAA Coop (OpenMOHAA fork)

Researched 2026-11-01 with about 24 web searches and fetches. Tags used below:
- **[V]**: I checked this on the cited page.
- **[S]**: secondary or community source.
- **[U]**: unverified, from background knowledge, or an inference. Check it before relying on it.

---

## 1. Upstream OpenMOHAA on Linux and Steam Deck

**Release assets [V].** The latest upstream release is v0.82.1-beta (Aug 2025). Its Linux assets are:
- `openmohaa-v0.82.1-linux-amd64.zip`
- `-linux-arm64.zip`
- `-linux-armhf`, `-i686`, `-powerpc`, `-ppc64` and `-ppc64el` zips
- a macOS multiarch zip
- Windows arm64 `.msi` files

The page showed only 12 of its 19 assets. Windows x64 is surely among the hidden ones. Whether an AppImage is there is **[U]**.
https://github.com/openmoh/openmohaa/releases

**Flatpak and AppImage.** Neither appears in the README or the install doc [V]. A Flathub search for "openmohaa" returned 0 results. That page is JS-rendered, so treat "no Flathub app" as likely but **[U]**.
https://flathub.org/apps/search?q=openmohaa

**Distro packages [V].** Debian and Ubuntu package `openmohaa` 0.82.1+dfsg (contrib). Solus has it too.
- https://packages-picconi.debian.org/sid/i386/openmohaa-server
- https://launchpad.net/ubuntu/+source/openmohaa
- https://appstream.getsol.us/unstable/main/metainfo/openmohaa.html

None of these packages help us: our fork changes protocol constants, so we need our own binaries.

**Build requirements [V].**
- CMake ≥ 3.25
- GCC ≥ 9.4 or Clang ≥ 7.0.1
- Flex ≥ 2.6.4 and Bison ≥ 3.5.1
- `libsdl2-dev` and `libopenal-dev`
- `libcurl4-openssl-dev`, which is optional and used only for the update check

The default install prefix is `/usr/local/lib/openmohaa`.
https://raw.githubusercontent.com/openmoh/openmohaa/main/docs/markdown/04-coding/01-compiling.md

**Install layout [V].** Extract the OpenMOHAA zip into the MOHAA folder, the one that contains `main/`, `mainta/` and `maintt/`.
- On Linux, the GOG setup.exe is unpacked with `innoextract`, which writes to `app/`.
- Launchers are `launch_openmohaa_base`, `_spearhead` and `_breakthrough`.
- The binaries are `openmohaa` and `omohaaded`.

https://raw.githubusercontent.com/openmoh/openmohaa/main/docs/markdown/01-intro/01-installation.md

**Home path [V].** The Linux default is **`~/.openmohaa/<main|mainta|maintt>`**, *not* `~/.local/share`. It can be overridden with `fs_homepath`. `com_target_game` 0/1/2 selects the game, and the protocol follows it.
https://raw.githubusercontent.com/openmoh/openmohaa/main/docs/markdown/02-running/01-running.md

**FAQ [V].**
- The log lives in `~/.openmohaa/main`.
- For a custom resolution, set `r_mode -1` plus `r_customwidth` and `r_customheight`.
- After a crash on Xorg, gamma can be reset with `xrandr --gamma 1:1:1`.
- The FAQ says nothing about case sensitivity or controllers.

https://raw.githubusercontent.com/openmoh/openmohaa/main/docs/markdown/02-running/03-faq.md

**Case sensitivity [U/partial].** The install doc itself lists `Pak*.pk3` under `main` but `pak*.pk3` under `mainta` and `maintt` [V], so GOG file names are mixed-case. PK3 internal paths are looked up case-insensitively in id-tech-3 descendants **[U]**. Loose files on ext4 are case-sensitive, so the mod should ship everything inside pk3s and use lowercase paths.

**Steam Deck experience [S].** One GOG forum user ran the upstream v0.81.1 Linux amd64 build on a Deck under Bazzite. Their steps:
1. Unpack the GOG installer with innoextract into `~/GOG Games/MOHAA`.
2. Unzip OpenMOHAA into the same folder.
3. Mark the `.x86_64` launchers executable.
4. Add them as non-Steam games.

Other users in the thread had problems:
- A Heroic/Wine user saw a "grey box then crash". The likely cause is that they ran the original Windows exe.
- One user hit a windowed-only problem and solved it without saying how.
- Heroic's `~/Games/Heroic/...` folder was mentioned as a possible location but not tested.

https://www.gog.com/forum/medal_of_honor_series/openmohaa_your_best_option

**Other sources [S].**
- Batocera ships OpenMOHAA as a system (a precedent for gamepad-first handheld front-ends): https://wiki.batocera.org/systems:mohaa
- A 2022 thread runs the *original* game via Heroic and Proton: https://steamcommunity.com/app/1675200/discussions/0/5267542371396281732

**Gaps.** I found no OpenMOHAA GitHub issues about Steam Deck or controllers. Upstream has no gamepad story, so our SDL2 gamepad work is ahead of upstream **[U]**, because the search was not exhaustive.

---

## 2. Getting the GOG War Chest data onto a Deck

**Heroic Games Launcher.**
- Supports GOG through its own `gogdl`: https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher
- The default install folder is `~/Games/Heroic` [S]: https://github.com/heroic-games-launcher/heroicgameslauncher/issues/25
- On the Deck, Heroic is the Flatpak. Paths outside its sandbox permissions are hidden from it [S]: https://peachpie.theatl.social/post/93425

Heroic installs the Windows build, but the data files are platform-neutral pk3s. A native engine can point at `~/Games/Heroic/<Medal of Honor ...>/`, which holds `main/`, `mainta/` and `maintt/`. The GOG forum user suggested this but did not test it [S].

**innoextract** is the officially documented path in the OpenMOHAA install doc [V]. It is a CLI tool, so it is Desktop Mode only.

**Lutris and minigalaxy [U].** Both are Flatpaks that can log into GOG. Minigalaxy is aimed at native GOG Linux games, and MOHAA has no Linux GOG build, so it is weak here. I did not research these further.

**Pointing the engine at the data.** OpenMOHAA uses `fs_basepath` (the install folder) and `fs_homepath`. A launcher script can pass `+set fs_basepath "<gog dir>"`. This is standard ioq3 behaviour **[U for OpenMOHAA specifics]**.

---

## 3. Proton route (Windows build as a non-Steam game)

Wine translates WGL calls to the host's GL. On the Deck that is Mesa radeonsi, with no DXVK in the path **[U, standard Wine architecture]**.

Old Wine bugs with the *original* MOHAA include an iPixelFormat failure and a crash caused by the long GL extension string. Quake 3 era engines overflow on long extension lists. OpenMOHAA likely has this fixed **[U]**.
- https://list.winehq.org/hyperkitty/list/wine-bugs@list.winehq.org/thread/MSVM75YU7NQQIEW5KSS7PFT43CM4KDWE/
- https://mail.winehq.org/mailman3/hyperkitty/list/wine-bugs@winehq.org/message/7HISVMSGJO7MIDFZCEQWO3J3SAD23CZC

A 2024 report says 32-bit GL programs crash under Wine on NVIDIA, while the native Linux MOHAA does not. Not Deck-relevant, but it shows native is more robust:
https://list.winehq.org/hyperkitty/list/wine-bugs@list.winehq.org/thread/57J35BFDVIZAEDNAUAEKXETZWCKDIUEV/

I found no OpenMOHAA-under-Proton reports, good or bad.

Costs of the Proton route **[U]**:
- Wine's GL thunking adds CPU overhead.
- The SDL2 HIDAPI and joystick path goes through Wine's XInput/winebus layer, which risks double input. See the SISR report in §4.
- The `fs_homepath` will sit inside the Proton prefix (`compatdata/<id>/pfx/...`).

---

## 4. Steam Input and SDL2 on the Deck

**What SDL2 sees [S/U].** With Steam Input on, which is the default for non-Steam shortcuts, SDL2 sees the **Steam Virtual Gamepad**. On Linux that is VID 0x28DE, PID 0x11FF, an Xbox-360-style uinput device. SDL source treats 28DE/11FF as the Steam virtual gamepad:
https://git.axiodl.com/encounter/SDL/commit/03250690d68bc09a9e60628a74424fb5b40a1085

Steam sets `SDL_GAMECONTROLLER_IGNORE_DEVICES` to the physical pad's VID/PID so that SDL ignores the raw device and you get no double input:
- https://git.objectionable.solutions/Sara/behaviour-tree-test/commit/8de98dbf21ba734feb26d5568151bd810d566817
- https://lemmy.4d2.org/comment/5138407

`SDL_GameControllerGetType` usually reports the Xbox 360 type for the virtual pad. Recent SDL and Steam can expose the real type through `SDL_GameControllerGetSteamHandle` or by mapping names **[U]**. Glyphs should therefore follow what Steam reports. For Deck detection, check `SteamDeck=1` in the environment (SDL uses this; see §5), and default to Xbox-style ABXY labels, which match the Deck's physical buttons.

**Gyro [S].** Gyro is not reachable through the virtual pad. SDL has `SDL_HINT_JOYSTICK_HIDAPI_STEAMDECK` (an SDL3 hint, documented since 3.2.0) and a HIDAPI Steam Deck driver, with sensors on by default on Deck:
- https://wiki.libsdl.org/SDL_HINT_JOYSTICK_HIDAPI_STEAMDECK
- https://cdn05042023.gitlink.org.cn/zinface/SDL/commit/e7f03de468792812a7aef668ac207ae35ede1945

One developer cleared Steam's ignore env var to reach the HID driver and got zero gyro readings while Steam held the device:
https://discourse.libsdl.org/t/gyroscope-on-steam-deck-using-hid-driver/69064

The practical approach is to let Steam Input map gyro to the mouse ("gyro as mouse") in the layout, and have the game accept mouse and gamepad together (mixed input). Valve explicitly recommends mixed input:
https://partner.steamgames.com/doc/steamdeck/recommendations [V]

**Shipping a layout for a non-Steam game [S].**
- Community layouts for non-Steam shortcuts are keyed by the **shortcut name**, so a stable shortcut name lets users find a published layout under Browse Configs: https://wiki.archlinux.org/title/Steam_Input_Configurator
- Sharing is otherwise awkward. The workaround is to copy the layout `.vdf` into `steamapps/common/Steam Controller Configs/<id>/config/...`: https://old.lemmy.dbzer0.com/comment/10743596 and https://gist.github.com/denilsonsa/ae764073d285f1f15dad4f6a4de22e99
- An installer script could drop a template `.vdf` in place, but the folder layout is undocumented **[U]**.

**Recommended template [U].** Use the built-in "Gamepad" template if the game's native SDL gamepad bindings are complete; this is best for our fork, which has a weapon wheel, deadzones and aim assist. Add gyro-to-mouse-when-touching-right-pad as an option. Back buttons L4/L5/R4/R5 can map to keyboard keys such as scoreboard, console and voice.

---

## 5. On-screen keyboard for a non-Steam game

**Steam + X** opens the Steam keyboard manually in any game launched from Steam. It is the only route for games that do not call the Steamworks `GamepadTextInput` API [S]:
https://steamcommunity.com/app/1675200/discussions/0/3370405530908624210

**SDL2 X11 backend [V].** SDL2's X11 backend implements the Deck keyboard itself:
- Show: `X11_ShowScreenKeyboard` → `SDL_OpenURL("steam://open/keyboard?XPosition=0&YPosition=0&Width=0&Height=0&Mode=%d")`
- Hide: `steam://close/keyboard`
- Gate: only when `is_steam_deck` is set, which SDL derives from the `SteamDeck` env var
- Source: https://raw.githubusercontent.com/libsdl-org/SDL/SDL2/src/video/x11/SDL_x11keyboard.c
- Added Nov 2022: https://discourse.libsdl.org/t/sdl-x11-add-support-for-the-steam-deck-on-screen-keyboard/39748
- SDL3 later passes the input rect (May 2025): https://discourse.libsdl.org/t/sdl-pass-text-input-rect-to-steam-deck-keyboard-invocation/59927
- SDL3 also added `SDL_HINT_ENABLE_STEAM_SCREEN_KEYBOARD` (3.4.12): https://discourse.libsdl.org/t/sdl-added-sdl-hint-enable-steam-screen-keyboard/68554

**Implication for us [U].** A *native* SDL2 build running in Game Mode, which uses gamescope with XWayland and the X11 driver, gets the Steam OSK for free whenever it calls `SDL_StartTextInput()`, with `SDL_HINT_ENABLE_SCREEN_KEYBOARD` left at its default of on. This needs a recent enough SDL2 (≥ 2.26). ioq3-derived engines often leave text input always on, or never call it. The fork should call `SDL_StartTextInput` and `SDL_StopTextInput` when a UI text field or the console gains or loses focus. Under Proton this path is not available, because the game is not using the Linux SDL.

`ShowFloatingGamepadTextInput` (Steamworks) needs a Steam appid and the Steam API, so it is not realistic for a non-Steam GOG-data mod [V for the API's existence]:
https://partner.steamgames.com/doc/steamdeck/recommendations

---

## 6. Valve Deck Verified guidelines [V]

Source: https://partner.steamgames.com/doc/steamdeck/compat
- **Input:** the default controller configuration must give access to all content, with no in-game setting change needed. Glyphs must match the active input, and keyboard/mouse prompts must not appear when the controller is in use. Text entry must use the Steamworks OSK API or a built-in controller-usable entry method.
- **Display:** run at a supported resolution, ideally 1280×800 (or 1280×720). *"The smallest on-screen font character should never fall below 9 pixels in height at 1280x800"*. 12 px is recommended, and text must be readable at about 30 cm.
- **Seamlessness:** launchers must be fully controller-navigable, and requiring one is strongly discouraged. No "unsupported device" warnings.
- **Performance:** the default configuration must be playable, meaning 30 fps at 800p.

Recommendations page: https://partner.steamgames.com/doc/steamdeck/recommendations
- Support many aspect ratios.
- Use mixed input.
- Avoid glyph flapping when the mouse moves.
- Store graphics settings per device.
- Prefer Vulkan for battery life.

The page does not mention OpenGL.

---

## 7. Performance budget

**Hardware [V]** (https://www.steamdeck.com/en/tech):
- CPU: Zen 2, 4 cores / 8 threads, 2.4–3.5 GHz
- GPU: 8 RDNA2 CUs up to 1.6 GHz, 1.6 TFLOPS
- RAM: 16 GB LPDDR5-6400, shared
- APU power: 4–15 W
- Display: 1280×800, up to 90 Hz on OLED (the LCD is 60 Hz [U])

**UMA frame buffer [S].** The BIOS setting defaults to 1 GB and allows up to 4 GB. Guides recommend 4 GB, but the evidence is anecdotal:
- https://pimylifeup.com/steam-deck-increase-vram/
- https://retrodeck.readthedocs.io/en/latest/wiki_devices/steamdeck/steamdeck-optimize/

A 4 GB UMA allocation should comfortably hold our HD texture packs. With 1 GB, the driver spills to GTT (system RAM), which on a UMA device costs little bandwidth **[U]**. Texture *upload* stutter on map load matters more.

**OpenGL driver [S].** radeonsi is the default. Zink (GL on Vulkan) reached about 93% of radeonsi on RDNA2 in 2022 testing, with lower CPU use, and was "competitive" in 2023. Users report more glitches with Zink. Try it with `MESA_LOADER_DRIVER_OVERRIDE=zink`.
- https://www.phoronix.com/review/zink-radeon-august2022
- https://Phoronix.com/review/radeon-zink-summer23/4
- https://www.gamingonlinux.com/forum/topic/5213/

**Targets [U].**
- id-tech-3-class geometry is trivial for this GPU. The cost is GLSL post-FX (bloom, SSAO-like passes) at 1280×800 and fill-rate on large HD textures.
- Plan presets for 40/45/60 fps with a frame cap, using gamescope's per-game frame limiter and refresh slider. On OLED, 45 fps at 90 Hz is a clean divisor.
- Post-FX should have a "Deck" preset with half-res bloom and no expensive passes.
- radeonsi keeps an on-disk shader cache (`~/.cache/mesa_shader_cache`), so first-run GLSL compile hitches vanish on the second launch. Precompiling shaders at the loading screen avoids mid-game hitches.
- Steam's shader pre-caching does not apply to non-Steam GL games.

---

## 8. Distribution options

**Flathub precedent [V].** `com.etlegacy.ETLegacy` is Flathub-community-maintained, downloads its own game assets, is fully sandboxed (no home access) and keeps its config in `~/.var/app/.../.etlegacy`:
https://github.com/flathub/com.etlegacy.ETLegacy

**Sandbox pitfalls [S].** OpenJKDF2's Flathub build couldn't see the game files because it had no filesystem access. Users had to copy data into `~/.var/app/org.openjkdf2.OpenJKDF2/data/`, and file-name case mattered:
https://github.com/shinyquagsire23/OpenJKDF2/issues/322

Same pattern for Quakespasm-based Flatpaks: https://flathub.org/ru/apps/io.github.lavenderdotpet.LibreQuake

**Flatpak (self-hosted `.flatpakref` or a Flathub app) [U].**
- Pros: Discover (Desktop Mode) installs it, it survives SteamOS updates, and it ships SDL2/OpenAL/glibc via the runtime. Flathub could even host an "extra-data" download.
- Cons: it needs a filesystem permission for the Heroic/GOG folder, so pk3 data paths get awkward. Our 3+ GB pk3 set changes per release, which makes Flathub review and update cadence a poor fit. A self-hosted repo is possible but adds friction.

**AppImage [U].** One file and self-contained. Needs FUSE, which SteamOS supports. "Add as Non-Steam game" works directly. There is no auto-update unless we embed one, though AppImageUpdate and zsync exist.

**Tarball + install script [U].** A tarball with an install script run once in Desktop Mode is the most common fan-project route and the easiest to control. The script would:
- find the GOG data (Heroic default, `~/GOG Games`, or a prompt)
- unpack the engine and pk3s into `~/.local/share/hzm-coop` or beside the data
- set `fs_basepath`
- add the Steam shortcut by writing `shortcuts.vdf` while Steam is closed (as steam-rom-manager does)
- drop SteamGridDB art and a Steam Input layout

**Native binaries [V/S].** Build in Valve's **Steam Linux Runtime 3.0 (sniper) SDK** container, which Valve recommends for new native games. That avoids glibc-too-new failures like the GLIBC_2.43-vs-2.41 report.
- https://github.com/ValveSoftware/steam-runtime
- https://forum.godotengine.org/t/steam-deck-cant-launch-linux-build-due-to-outdated-glibc-version-build-targeting-newer-glibc-version/143218
- Runtime 4.0 (Debian 13) is newer: https://www.gamingonlinux.com/2025/11/valve-put-up-a-new-steam-linux-runtime-4-0-with-a-move-towards-64-bit

As a non-Steam shortcut you can force a runtime through the shortcut's compatibility setting, or bundle SDL2 and OpenAL yourself **[U]**.

**Least friction for gamepad-only users [U, judgement].** Desktop Mode is unavoidable once, for a GOG login and the first install. After that:
- Best: a one-shot Desktop-Mode installer (AppImage or script) that writes the Steam shortcut, art and layout. The updater then runs from inside the game or from a Game-Mode-launchable "Update" shortcut.
- Second best: Decky plugins. They are another dependency, so I don't recommend them as a requirement.

**Fan-project survey.** Not researched individually within budget **[U]**. From memory: ET:Legacy, ioquake3, yquake2 and OpenJK have Flathub or community Flatpaks, and Unvanquished ships a Flathub app plus an updater.

---

## 9. 4-player co-op hosting from a Deck

**Ports [S].** MOHAA uses UDP 12203 for game traffic and UDP 12300 for queries/GameSpy. Some reports list 12203 and 12300 as enough for a server. Treat the extra GameSpy ports as legacy.
- https://icculus.org/pipermail/mohaa/2003-May/002664.html
- https://sources.debian.org/src/qstat/2.15-1/qstat.cfg
- https://eggs.pterodactyl.io/egg/games-mohaa

A fork that changed protocol constants may also have changed ports. Check the fork's `net_port` default **[U]**.

**Firewall [S/U].** SteamOS ships without an active firewall frontend. A 2022 user had to reinstall `ufw` after every OS update, because the root filesystem is read-only and image-based. Inbound UDP to a LAN listen server should simply work. Internet hosting needs router port forwarding, or a relay/VPN such as Tailscale or ZeroTier.
https://steamcommunity.com/app/1675200/discussions/2/3385030647942607157/?l=schinese

**CPU load [U].** A listen server runs the game VM (script threads, AI and pathing for coop waves) on the same 4-core Zen 2 as the client. The Deck's per-core speed is roughly a 2017–2019 desktop. For 4 players plus heavy AI, expect the server frame to cost a few ms. Test with `sv_fps` and the AI count.

Options for heavier missions:
- run `omohaaded` as a separate process pinned to a core
- recommend that the strongest machine (often a PC) hosts

Wi-Fi latency and jitter on the Deck matter more than CPU.

---

## Recommendation

**Native Linux build of the fork.** Reasons:
1. The fork's protocol changes mean the binaries must come from us either way. Building x86_64 Linux in the sniper SDK is a single CI job.
2. Native SDL2 gives the Steam OSK for free via the X11 `steam://open/keyboard` path, which Proton cannot use.
3. Controller handling is cleaner on the virtual-pad path, with no Wine XInput double input.
4. GL goes directly to radeonsi, with Zink available as a fallback.
5. `fs_homepath` stays in a sane place.
6. There is precedent: a user report shows upstream's Linux build working on a Deck.

Keep the Windows build working under Proton as a documented fallback, since the Proton route needs zero porting.
