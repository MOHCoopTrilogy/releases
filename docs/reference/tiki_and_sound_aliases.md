# TIKI and sound-alias reference

Moved out of `docs/TRAPS.md` 2026-08-10 to stay under its 60 KB ceiling. This is *reference*
material about TIKI parsing and sound-alias syntax rather than a cross-cutting way the project
breaks itself, so it belongs here. Nothing was cut - the whole section is below verbatim.

## TIKI and sound-alias traps (found the hard way, 2026-08-03, e2l1 glider)

### A frame-command line inside `server{}` / `client{}` MUST start with a frame keyword
`TIKI_ParseFrameCommands` (`tiki/tiki_parse.cpp:113-133`) consumes the **first token of every line**
as the frame specifier. If it is not `start/first/end/last/every/exit/entry/enter` or a number, it
falls to `framenum = atoi(token)` — which silently yields frame 0 and **shifts the whole line left**:
`args[0]` becomes the first *argument*, and `fgame/animate.cpp:304/370` then fires an event named
after it. Retail `CG4Aglider.tik:332` and `:398` are bare `surface glider_body_glass -skin1 +skin2`
inside `bank_left`/`bank_right`, producing `Event 'glider_body_glass' does not exist` and no cracked
windscreen. **`enter` is a valid alias for `entry`** — do not "fix" that.

**The inverse is more dangerous:** in `setup{}` a bare `surface <name> shader <name>` is *correct and
required* — `setup` has no frame-specifier layer (`CG4Aglider.tik:9-20` are all bare). A regex for
"surface lines without a frame keyword" flags those as false positives, and prefixing them with
`entry` destroys every surface→shader binding on the model. **Validate by positive assertion on the
target lines, never by scanning for a negative.**

### A `ubersound` / `uberdialog` alias without a `maps "..."` spec never loads

The **narrow** spec is the same trap and easier to miss: `flak_snd_fire1..4` list `maps "m3l2 m5l2 m5l3 t1l3"`, so on m3l1b the alias simply is not there and the gun animates in silence. Proof is cheap - grep the session log for the wav name (`Flak88Fire`); zero loads means zero alias. Contrast `explode_flak88` (`maps "m e t"`) and `flak_snd_move` (`maps "m1 m2 m3 ..."`), which prefix-match and load fine on the same map. Verify the spec covers your map before touching anything else (bug-1548).
`bLoadForMap` (`cgame/cg_commands.cpp:4251`) prints
`ERROR bLoadForMap: <alias> alias with empty maps specification.` and returns false. The match is a
**prefix** compare (`Q_stricmpn(token, mapname, strlen(token))`), so `"e2l1 "` matches `e2l1.bsp`;
the working e2l1 dialogue aliases all end `maps "e2l1 "`. Un-commenting a retail alias is not enough
if the retail line lacked the spec. Symptom is silence with no PlaySound error.

This class is now testable instead of playable. **`python docs/tools/audit_weapons.py`** checks
every player weapon for exactly the five ways the FG42 was broken at once, and it has since found
the same defects on other guns: 14 alias lines across 7 weapons still scoped `maps "dm lib obj"`
(silent on every campaign map, bug-1885), and `kar98_snd_reload_end` / `_single` referenced by
**eight** bolt-action rifles and defined nowhere, not even in retail (bug-1886). Note the variant
rule does not rescue a suffix: `foo` is satisfied by `foo1`/`foo2`, never by `foo_end`.

### Judge an animation by its frame count, never its file size (bug-1887)

A `.skc` states its length outright when it is version 13: `numFrames` sits at byte offset 44, after
`ident/version/flags/nBytesUsed/frameTime/totalDelta[3]/totalAngleDelta/numChannels/ofsChannelNames`.
Version 14 is pre-processed and does not expose it - report those as unknown rather than guessing.

Size is a bad proxy in both directions, and both directions bit us in one session. A short animation
is usually **fine**: most retail world weapons hold a 1-2 frame pose because first-person motion
comes from the viewmodel hands in `fps_anims_*.txt`, not from the weapon `.tik` - mp44's idle is two
frames. The real defect is a **frame command that points past the end of its own animation**: it
never runs, and it logs `TIKI_FixFrameNum: illegal frame number N (total: M)`. TT-33, Silenced TT-33
and Welrod all carried `18 surface clip +nodraw` / `39 ... -nodraw` copied from the retail pistol
template (LugerP08 uses that pair legitimately over 73 frames) onto animations of 7 and 1 frames -
so the magazine never disappeared during reload. The surface name was wrong too (`p38clip` and
`clip1`, not `clip`), which is why brace/size checks would never have caught it.

### In `soundparms`, pitch 0 is silence - and every check we had passed it (bug-1898)

`alias.c:188-194` reads the six numbers as **volume / volumeMod / pitch / pitchMod / dist /
maxDist**. A sound at pitch 0 never advances through its samples, so it makes no noise at all.
Two guns shipped like that - the StG44 Scoped (`WAWmp43_fire`) and the G43 Sniper (`g43_fire`) -
and the user reported both independently.

What makes this worth writing down is *why* it survived: the alias was defined, its wav existed,
and its `maps` spec covered the campaign, so both of `audit_weapons.py`'s sound checks passed a
weapon that physically cannot make a sound. "The alias resolves" is not "the alias produces
audio". The auditor now scans every alias for pitch 0 and volume 0.

A wav-existence check was written alongside it and **deliberately removed**: it returned 34,056
hits, essentially all retail dialogue, because alias paths do not resolve 1:1 against a flat pak
index (case, `.mp3`/`.wav` siblings, per-language trees). A check that noisy buries the real
findings, which is the exact failure the tool exists to prevent. Prefer no check to a loud one.

### `ordernumber` in a `.urc` is focus order, NOT draw order (bug-1896)

`uiwidget.cpp:444` defines it as *"the order the widget should be activated in"*, and
`uimenu.cpp` consumes it through `SetLastActiveWidgetOrderNum` - keyboard/focus navigation.
**Draw order follows declaration order**: a widget declared later in the file paints over one
declared earlier. That is why `fitTitle` renders on top of `fitBg` despite having no
`ordernumber` at all, and why a tile declared before `fitBg` is safely covered by it rather than
poking through.

Getting this backwards costs real work. It made the armory's pistol tab look full at 16 rows when
it was not, and sent a session looking for space to relocate a five-row overlay that already
bottoms out at y=479 of a 480-tall menu.

Two more armory facts worth having: a tile's **page** comes from its `enabledcvar` and its **row**
from its `rect`, so a tile id never has to match its category grouping - which is what allows a
weapon to be appended without renumbering. And renumbering is the thing to avoid at all costs,
because tile ids are baked into every `pNN`/`tNN`/`wNN` filename *and* every `coop_loLkVNN` lock
cvar; bugs 755/759/772/787/803 are all that numbering breaking. Regenerate with
`python docs/tools/gen_loadout.py build`, and trust it only because `check` byte-compares.

### A weapon pack can ship assets that nothing references (bug-1888)

The engine never complains about an asset no one asks for. The xw pack ships five distinct
first-person animations for the Type 100 - including a 76-frame reload - and `cg_viewmodelanim.c`
mapped `"Type 100 SMG"` to `WPREFIX_STEN`, so the engine asked for `sten_*` aliases and those five
files sat unused. Identical in shape to the FG42's `WPREFIX_MP44` mapping. `audit_weapons.py` now
reports this class, and distinguishes it from harmless dead weight (the same pack ships `ak47`
hands with no AK-47 weapon). **Verify by hash, not size** - four of the five Type 100 files share a
byte count by coincidence and look like duplicates.

⚠ **Never resolve a prefix finding by renaming a weapon.** The hand-dialled per-gun ADS table
(`s_adsGunTune` in `cgame/cg_modelanim.c`) is keyed on the weapon's exact `name "..."` string via
`Q_stricmp`; a rename silently drops its sight tuning with no error. Fix it in
`cg_viewmodelanim.c` by adding the existing name. Appending to `animPrefix_e` **and**
`AnimPrefixList` is safe - the index is client-local, never networked - but the two must stay the
same length; append rather than insert so no existing index shifts.

### Retail MOHAA forces a custom gun to borrow a stock gun's hands. Our fork does not.

Soares93 states the rule on his pack's ModDB page: the game will not load a custom weapon unless
you tell it it is one of the stock weapons, and it then **must share that stock weapon's
first-person animations**. This is why almost every MOHAA weapon mod ships as a *replacement* and
why "includes animations" on a mod page usually means re-timed stock anims, not an independent set.
It is the upstream cause of the defect we chased twice in one day - the FG42 wearing StG 44 hands,
and the Type 100 wearing Sten hands.

**We are not bound by it, because we own the engine.** `CG_GetVMAnimPrefixIndex` in
`cgame/cg_viewmodelanim.c` is just a name-to-prefix lookup; adding an entry to `animPrefix_e` **and**
the index-aligned `AnimPrefixList`, then returning it for the weapon's own name, gives an imported
gun a genuinely independent first-person set. Proven twice on 2026-08-17: `WPREFIX_FG42` (bug-1878)
and `WPREFIX_TYPE100` (bug-1888). Append, never insert - the index is client-local and never
networked, but the two lists must stay the same length. **Never** achieve a match by editing the
weapon's `name "..."`; see the ADS warning above.

So when judging a candidate weapon mod, "does it ship first-person animations" is the question that
matters, and a mod that ships them but hard-points them at a stock gun is still worth taking - the
re-pointing is a few lines on our side.

### Researching moh-db.com programmatically

`moh-db.com` is a Nuxt SPA; listing pages render empty to a plain fetcher. Two entry points work:
`https://www.moh-db.com/sitemap_index.xml` -> `/__sitemap__/en.xml` enumerates every mod and map
URL, and `https://api.moh-db.com/api/v1/mods?size=500&page=N` returns the full catalogue as JSON
(Spring Page format) including the complete readme text, creator, file name/size, download count and
screenshot URLs. Single mod: `/api/v1/mods/<vid>`, where `vid` is the number in `/mods/<vid>`.
Surveyed 2026-08-17: 1,671 mods, 288 in the weapon category, of which only about four are new
period-plausible WW2 weapons - the rest are modern-weapon conversions, joke skins and stock
recolours. A regex sweep of all 1,671 found **zero** MOHAA mods for MG34, Panzerfaust, Bren,
Gewehr 41, DP-28 or a player flamethrower, so those do not exist to be downloaded.

### A shader file is all-or-nothing, and brace-balance cannot prove it well-formed

One bad token makes the engine print `WARNING: Ignoring shader file <name>` and discard **every**
shader in it, which is how a single orphan name in `soviet_weapons.shader` turned the Nagant
sniper, silenced PPSh-43 and both TT-33s invisible at once. An orphan leaves braces perfectly
balanced, so the test that works is structural: at top level every token must be a name
**immediately** followed by a `{ }` body. **`python docs/tools/audit_shaders.py`** checks all 393
shader files the game can see, and also lists the third-party files our pak overrides.

### Per-map `includes <mapname...>` blocks gate anim registration (bug-1621, 2026-08-09)

Anim `$include`s inside `includes <map tokens>` blocks in `new_generic_human.tik` resolve at TIKI
LOAD by case-insensitive PREFIX match of each token vs `sv_mapname` (`TIKI_ParseIncludes`,
tiki_parse.cpp:320-374). A non-matching block is skipped with ZERO output at any developer level.
So the same spawn recipe animates on one map and floods `unknown animation` on another: m3l1b
lists `human_mg42.tik` (retail native nests), m2l2a/b and every custom map do not - the MG42 nest
gunner stood upright while firing. **Fix recipe:** add the pack to the UNCONDITIONAL coop include
set at the top of the mod's `new_generic_human.tik` (now mp44/bar/bazooka/thompson/coop_medic/
mg42). Cap is MAX_TIKI_LOAD_ANIMS 8192 / 13-bit net index; the m1l1 truck ride is the canary.

### "Missing" content is often CUT content that still ships
Before blaming the renderer or the coop layer, check whether the retail asset was ever wired up —
and search **loose files as well as archives** (`DFRUS_E2L1_GP1306`'s mp3 ships loose under
`maintt/sound/dialogue/`; a pk3-only search wrongly reported it missing). Four e2l1 glider defects
were retail authoring gaps of this kind, not bugs: a commented-out alias, 18/20 `cockpitBulletHit`
aliases never defined, the windscreen (above), and a fire/ember kit nothing references.

**But do not over-apply it: measured trilogy-wide, cut *dialogue* does not exist.** All **1,801**
map-bound VO aliases are referenced by some script (2026-08-06 scan). So when a line does not play,
the cause is always runtime, and there are only three: the thread that would play it died, the
trigger that would start it never fired, or the alias resolves to a missing wav. Check those, in that
order, instead of hunting for unwired content.

### Never leave a backup inside `hzm-mohaa-coop-mod/`
`build.ps1` packed a 6 MB `uberdialog.scr.bak_gp1306` straight into the shipped pk3. Write backups to
the scratchpad. Also: build.ps1's `Cache hit ... unchanged` line can be misleading — **verify a change
shipped by hash-comparing the source against the pk3 member**, not by reading the build log.


## Moved from TRAPS.md 2026-09-03 (budget)

**⭐ `<actor> say <alias>` IS AN ANIMATION CALL, NOT A SOUND CALL** (2026-09-02, after FIVE failed
fixes aimed at the mixer). `Event "say"` on an Actor is `EV_Actor_SayAnim` - *"the name of a dialog
animation to play"* (`actor.cpp:539`) - and `Actor::SoundSayAnim` returns the instant
`gi.Anim_NumForName` resolves it (`actor.cpp:7613`), **playing no sound at all**. The audio is a
**client** frame command inside the dialogue TIKI
(`M3L1_dialogue_US.tik`: `..._083a.skc { client { first sound streamed_..._083a } }`). Consequences:
`coop_covtrace` instruments `Entity::Sound` and is **structurally blind** to every scripted line; the
alias in the TIK need not be the alias in the script (`say ..._073a_prone` sounds `..._073a_1`); and
the direct-`Sound()` fallback - the only path that prints anything - runs **only when the anim is
missing**. `EventSayAnim` merely QUEUES; `Actor::UpdateSayAnim` (`actor.cpp:7854-7916`) starts it and
has **three silent early returns**, two of which `Unregister(STRING_SAYDONE)` in the same frame so the
`waittill saydone` releases instantly and the script sails on with no audio and no log line:
ThinkState KILLED/PAIN; `anim == -1`; and **`TAF_HASUPPER` while ThinkState is ATTACK or GRENADE**.
That last one is why a line can be word-perfect on a boat ride and silent in a firefight - but
**measure it, do not assume it**: `bHasUpper` is just "the `.skc` carries `Bip01 Spine rot` AND
`Bip01 Spine1 rot`" (`skeletor_loadanimation.cpp:326-330`), greppable straight out of the file, and on
the Omaha captain it is **false on every line**, which refuted this as his cause.

**A BARE ANIMATION ALIAS DROPS THE NOTETRACKS THAT DO THE WORK - three times now.** The ANIMATION
performs the action; the statemap only plays it. A retail alias is `name file.skc { server { <frame>
<command> } }`, and copying only the `name file.skc` half yields an animation that looks right and does
nothing: the prone ADS alias without `{ server { first fire } }` fired no rounds; the prone reload alias
without `first reloadweapon` + `clip_fill` never refilled the clip, and `Weapon::ShouldReload` latches
TRUE on an empty clip regardless of its own flag (`weapon.cpp:3980`), locking the player in the reload
unable to shoot (bug-2115); and `rifle_prone_shoot` gave a perfect prone firing animation that
discharged nothing (bug-2099). **Open the retail alias in `human_*.tik` and copy its whole notetrack
block, or do not substitute** - the cover blindfire aliases carry a "copied VERBATIM" note and it was
missed anyway. To preserve a timeline exactly change the animation's WEIGHT, not the animation -
notetracks queue once at set time and ANIMDONE runs on elapsed time, so neither depends on weight.
**Sanity-check any offset you extract from a `.skc`** (a frame count is positive, a duration is
seconds): the header offsets once written here did not reproduce on `SKAN` v14.
