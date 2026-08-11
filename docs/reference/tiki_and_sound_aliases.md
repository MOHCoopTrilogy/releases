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
