# End-of-mission debrief, take two (branch `debrief2`, target v1.10.62 / v1.10.63)

User, 2026-11-03: "Can we do an overhaul of the progression at the end of each level, make a more visually appealing
rank up bar, make sure the rank insignia look crisp. The unlock items would be nice if it came on screen one at a time
with a picture of what it unlocked... like modern games do."

## What was wrong with the old card

`xp.scr::xp_summary_card` drew ~20 script huddraw slots (62-73, 127-134). The bar, the title and the insignia were on the
640x480 *virtual* layer, which scales x by W/640 and y by H/480: a 128 px emblem drawn 56 units square came out 168x126
px at 1920x1080 (a third too wide) and was upscaled from 128 px, hence soft. Every animation step was a network message,
and the unlocks were a column of names. bug-4004 had already had to re-anchor the text layers because the two scaling
systems drifted against each other.

## The decision: draw it in cgame

| option | why not / why |
|---|---|
| keep script huddraw, swap textures | fixes the blur, not the stretch (the virtual layer is non-uniform), no picture cards, every slide/fade = traffic |
| huddraw with `virtualsize 0` | uniform scale, but slide-ins still per-frame `ihuddraw_rect` messages; 20+ more slots in a band the slot map says is full |
| **cgame, fed once per mission** (chosen) | the event feed already proved the wire (`iprint` + tag, cg_coopfeed.c); smooth at the client frame rate; one scale `u = vidHeight/1080` centred = same shape at 4:3, 16:9, 21:9; skip is local; no huddraw slots, so no hudresend claims and nothing for `srtopright` to collide with |

An older cgame (no `cg_hzmDebrief 1` in its userinfo) keeps the old card unchanged; `coop_debrief2 0` on the server forces
the old card for everyone.

## Sequence (cg_coopdebrief.c)

1. 0.65 s: the screen darkens (veil + vignette) and a War Department service-record sheet slides up.
2. The XP bar (brass on a recessed track, ten ruled segments, a glowing leading edge) fills from the XP the player had
   when the mission started, bracket by bracket. At each rank crossed: a flash on the bar and behind the insignia, the
   insignia swaps with a small pop, the rank-up ping plays, a red PROMOTED rubber stamp thumps onto the sheet; the bar
   empties and the overflow fills the next rank's bar. Three or more promotions compress the bar so it stays ~6.5 s.
3. The citations (the old category tally) are typed in with typewriter keys, dot leaders to the XP.
4. Each new unlock comes in from the right as its own card: picture on a dark plate, kind (WEAPON, WEAPON FINISH,
   HEADGEAR, UNIFORM, GLOVES, PERK, EMOTE, MEDAL AWARDED, CHALLENGE COMPLETE, PRESTIGE ...), name, what it is / where to
   use it, "n / N", paper sound; holds 2.3 s, leaves left. At most 6, then a "+N MORE" card.
5. The sheet stays with an "ADDED TO YOUR KIT" strip of thumbnails until the server changes the map.

USE or JUMP (Space, pad A) skips: the bar to its end (one promotion moment if any), the tally to complete, the current
card to the next. The server holds the map for the longest client's sequence (`level.coop_db2Need`, never more than 40 s;
default `coop_xpSummaryTime` 28 s stays the minimum) and never waits on a client.

## Wire (coop_mod/debrief2.scr -> cgame)

Per-player script `iprint`, `~d<op>~fields|joined|by|pipes`, same colour-byte guard as the feed's `~f`:
`B` begin (hardcore, map XP, rank0, rank1, XP from, XP to, mission), `K` rank rows, `T` tally rows, `U` cards (kind,
picture shader, name, description), `M` more, `G` go. ~15 reliable commands in one frame.

The per-map reveal list `coop_mapRevealList` ("token^name" joined by "~") is fed by `challenges.scr::chal_add_unlock`
(every reward token, except `xp_rank_unlock`'s connect-time backfill, which is owed, not earned) and by
`feed.scr::feed_mapList` (medals, challenges, prestige stars). The old `coop_mapUnlockList` and the LAST MISSION page are
unchanged.

## Art (docs/tools/gen_debrief2.py, all vector / procedural, nothing AI-made)

* 22 rank insignia, 256 px, nomipmaps + nopicmip: the 1942 enlisted chevrons (khaki on dark blue, technician T,
  first sergeant's lozenge, rockers), the Private's brass "U.S." collar disc, gold / silver bars, gold / silver oak
  leaves, the colonel's eagle, one to four stars and the General of the Army's ring of five.
* Category pictures in the use-to-loot icon finish (cream fill, keyline, halo): helmet, uniform, gloves, dog tags (perk),
  scope (attachment), commendation (challenge), saluting hand (emote), star (prestige).
* Weapon finishes: the rifle silhouette filled with gold, chrome, blued, bloody, woodland, winter, desert.
* Medals: the Service Record's own medal design (`gen_service_record.py::draw_medal_icon`, lifted by ast) at 600 px.
* Weapons reuse `textures/hud/loot/w_*` (the guns' own world-model silhouettes); a gun without one gets its class
  silhouette. Paper, brass fill, track, glow, vignette, soft shadow, PROMOTED stamp, brass pip.

New textures ship in the fixes pak (`docs/tools/assets/fixes/textures/hud/coop_db2/`, manifest `new`), never the
1.3 GB texture pak. The mod gets `scripts/coop_debrief2.shader` and `coop_mod/debrief2_gen.scr` (token -> picture).

## Test

`tools/run_db2.py <run> [--res 1280x720,1024x768,1680x720] [--video] [--big] [--skip] [--old]` - dedicated server + one
fake-identity client on the second display (joinflood plumbing), the debrief2 cgame swapped in, overlay pk3 with the
textures and `tools/overlay/coop_mod/coop_selftest_xp.scr`, which makes the player safe (`god`, `notarget`,
`nodamage`), earns a finish, an emote, a medal, a challenge and a helmet through the real paths, awards XP across one
rank (`--big`: six ranks) and ends the mission through `coop_mod/missioncomplete.scr`. `db2_test [ranks] [cards]
[rank0]` in the client console stages a local debrief with no server (QA of layout only).
