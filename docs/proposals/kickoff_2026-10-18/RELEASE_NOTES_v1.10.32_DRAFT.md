## MOH Coop Trilogy v1.10.32 - Lobby, Armory and Battlefield Update

DRAFT for the publish step (`publish_release.ps1 -NotesFile`). Plain language, ASCII only. Trim or reorder before publishing; anything the final regression marked as not proven should be removed here first.

**A pre-mission lobby before every mission, a new Showroom Armory, and a much busier battlefield.** This update needs the new game files (the updater brings them): the new menus, the hold ring and the controller support ride on the new program, not only the scripts.

### Before and between missions
- **A lobby before every mission, not only in the full campaign.** Start any single mission from the menu and the squad first lands in the lobby: change uniform, open the Armory, ready up. Between levels you also pass through the lobby, and progress is saved before you go in.
- **New Showroom Armory.** Every gun is shown on a card with its stats, the picture fills the card (rifles and SMGs are no longer tiny strips, pistols no longer spill over), locked guns tell you how to unlock them when clicked, and the screen keeps its proportions on wide monitors.
- **The progress screen after a mission no longer draws text over the rank bar.** Layout fixed for 720p, 1080p, 1440p and 4:3.
- **Loading screen movie.** The first mission now shows a short movie while it loads (more missions to follow).

### The battlefield
- **Alarms and the final counter-attack are tougher and fairer.** The finale now has a DEFEND zone marked on your compass: the clock only runs while someone stands in it, and if the Germans hold an empty zone too long the defence starts over. Alarm switches and bells were re-placed so they sit where you can reach them. (Alarm vehicles - trucks and half-tracks - are built but stay off by default.)
- **Snipers take rooftops when an alarm is raised.** Stay out of the open.
- **Mortar crews.** The Germans, and your own paratroopers, can set up a mortar. Shells whistle before they land: keep moving, or kill the crew.
- **Searchlights** sweep the night maps.
- **Surrender is rarer.** Only a wounded last man with no officer nearby gives up, a few times per mission at most, and surrendered men are left alone by your allies.
- **Officers drop binoculars or signal smoke (one of the two).** The binoculars give one bombing run, thrown smoke is used up, and on maps with no usable sky the officer drops an ammo and health cache instead. Rewards can no longer get lost in water or fall out of the map.
- **Paratroopers re-arm** when they leave the .30 cal. The MG42 team now paces its fire properly. Ardennes escorts (the Ardennes trucks missions) now scale, go down and can be revived like everywhere else.
- **More to do in missions.** A log-and-hold objective on the last jeep mission (m1l3c) and radios to deal with in m2l1.
- **New Mauser C96 model** (model by no12u, CC BY 4.0) with proper bolt, hammer and trigger animation and two-handed aimed reloads, plus the Trench C96.

### Screen and controls
- **One hold ring.** Reviving, healing, searching and every other "hold" action now share one smooth ring around the crosshair.
- **Icon prompts replace the big text.** Healing a friend, resupplying, removing sandbags, converting a prisoner, contain, distract, radio, ready-up and more show a small icon with the key under it.
- **Tidier event feed.** Messages stack above the subtitles instead of on top of them, long lines wrap and stay up long enough to read.
- **Controller support for menus.** Pull-down menus stay open after A, the D-pad moves the highlight, sliders and check boxes work with the pad, B cancels. (In-game pad play is still off by default.)
- **Loading tips updated** to match all of the above.

### Fixes
- Server join and lag fixes from the last update are unchanged.
- Fixed a game-script error in the lobby chain that only showed up with the new lobby rule.

### Which download?
- **MOHCoopTrilogy-WebSetup.exe**: pick this for a normal install. It finds your game and downloads everything.
- **MOHCoopTrilogy-NoInstaller zip (several parts)**: pick this if Windows blocks the installer, or you prefer to unzip by hand. Engine files, all mod files and INSTALL.txt; unzip every part into your game folder and keep a backup of your old exe and dll files.
- There is no "mod files only" zip this time because the program files (exe and dll) changed in this update.

Windows blocked something? See [Windows security warnings and how to get past them](https://github.com/MOHCoopTrilogy/releases/blob/main/docs/public/WINDOWS_SECURITY.md).

### Checksums (SHA-256)
`publish_release.ps1` now appends the "Which download?" and checksum blocks itself (and uploads SHA256SUMS.txt), so this draft only needs the body above. Check a download with `Get-FileHash .\<file> -Algorithm SHA256`; it must match exactly.

Thanks to everyone playing on the public servers - keep reporting in the Discord.
