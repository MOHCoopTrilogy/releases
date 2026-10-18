# Text feed round 5 (2026-10-18) - subtitles, missing text, challenge banner

Bugs **4006** (subtitle overlap), **4007** (missing text / old scroller), **4008** (challenge banner). The commit messages say 4005 / 4006 / 4007: a parallel session took 4005 first. Engine branch `textfeed-next`
(worktree `openmohaa-hzm-textfeed`, from `cgame-1.10.29` 776e4de5): `b9b6a528`, `0537692c`, `24746846`+`377ffab9`+`91cb8452` (one change: slow-frame slide clamp; first patched the wrong clamp, restored), cgame only. **New cgame.dll needed (md5 in the report); no exe / game.dll.** Mod branch `textfeed-next`
(worktree `hzm-mod-textfeed`, from `coop-wip` f23f4608): `139765c1`, `50c0c33e` (banner centring), code pak only. No exe / game.dll / renderer change: the
v1.10.29 cgame lineage does not contain the netfix exe, so nothing here may touch `client/`.

## Why the earlier rounds did not hold
1. **They fixed call sites, not the channel.** Rounds 1-4 (bugs 3426, 3520, 3542, 3952) converted ~530 `iprint` / `iprintlnbold` sites to
   `feed.scr`. Each ended with a "left as is" list, and every print that was not on a list (new scripts, maps, engine text, the
   `hudprint` path) still went to the old top-left box: cgame only took messages carrying a `~f` tag.
2. **The sink itself lost text** - so a correctly routed line could still vanish: wrap cut at 3 rows with "..." (200-char cap),
   same key + different wording REPLACED the older line (two "Challenge complete" lines a second apart showed one), fixed 3 s hold
   and 1.5 s minimum-show whatever the length (a 120-character hint faded half read), `coop_feed 0` and Hardcore sent non-alert lines to
   the console only, held-HUD cap 6 dropped the oldest.
3. Verification used a handful of sample sites, never an inventory of routes.

## Route inventory (all "print" / "hudprint" server commands arrive in `CG_ServerCommand`; colour byte 1 = yellow, 3 = bold)
| Route | Reaches the screen as now |
|---|---|
| `feed.scr` tagged `~fN` prints (feed_all / feed_player / feed_hint ...) | feed (unchanged); wording rules fixed (below) |
| game.dll tagged lines (`G_CoopFeedPrint*`: pickups, join / leave, votes) | feed (unchanged) |
| ScriptThread `iprintln`, Player `iprint x 0`, `G_PrintToAllClients(.., 0)`, direct `SendServerCommand("print", yellow)` (ammo.cpp, health.cpp ...) | **feed, category 2** (new, `CG_CoopFeedRouteUntagged`) |
| `iprintlnbold`, `iprintlnbold_noloc`, Player `iprint x 1`, `G_PrintToAllClients(.., 1)` (bold, white) | **feed, category 0 (amber alert, 6 s+)** (new) |
| `hudprint` (votes) | same rule as above, printed once (the old handler printed it twice) |
| bold text containing "fail" / "game over" / "defeat" (mission failed, tank lost, LMS failed) | stays on the OLD box, bold + beep (rule-critical, round-3 decision) |
| lines with no letter or digit ("--", blank `iprint ""` used to scroll the old box) | swallowed |
| any untagged line while the HUD is hidden (cinematic, lobby, briefing, intermission) | old box (the feed would hold it unseen) |
| Hardcore host rule, `coop_feed 0`, outside a coop session (MP, menus) | old box, as before (`coop_feed 0` now also shows TAGGED non-alert lines there; it used to print them to the console only) |
| chat / team chat / obituaries (colour bytes 2, 4, 5) | dmbox, never touched |
| `centerprint`, `locprint`, `svc_centerprint` (3 + 3 sites: m1l2a papers line, vehicle health) | centre-screen overlay, 4 s, unchanged, readable |
| ihuddraw cards (objectives, NEW OBJECTIVE card, challenge banner) | unchanged |
| console-only (`println`, developer prints) | console only |

Untagged routing is gated on `coop_isCoopSession` (set by coop `player.scr`), so PvP / MP modes keep the old box.
Intentional "not shown": hints already marked seen in `coop_hintSeen` (once per profile, marked when actually DRAWN) and Hardcore's
non-alert tagged lines stay console-only by the user's own rules.

## Feed sink fixes (cg_coopfeed.c)
6 rows / 360 chars for every category; hold = max(category hold, 1.2 s + 55 ms per character) up to 12 s; a line is guaranteed
1.5 s + 25 ms per character (max 4.5 s) before a newer line may take its row; same key replaces a line only when the two differ in
digits alone ("Recovered 5 Health" -> "7"), anything else is its own line; held cap 10.

## Subtitles vs the feed
The subtitle block belongs to the exe (`View3D::DrawSubtitleOverlay`: x 20, first line 10 facfont-20 heights above the bottom, one
line per `subtitle0-3`, wrapped at 80 % width). Rejected: moving it (needs an exe that is not in this lineage). Done: cgame reads
`subtitle0-3`, rebuilds the block with the same formula and, when the feed would meet it (8 px clearance), the feed stands above
the block until the subtitles are gone (smoothed, stays lifted while they show, never pushed off screen). All numbers are
fractions of `vidHeight / 480`, so 720p, 1080p, 4:3 and ultrawide behave alike.

## Challenge banner (bug 4008)
The 2026-10-05 declutter made `chal_toast_show` return early with one feed line. The early return is gone: two verdana-10 lines at
the top centre ("CHALLENGE COMPLETE", the title typed in step with the 7 key-stroke sounds), no third line; the debrief card entry
stays (`feed.scr::feed_chalList`). Not on the bottom left, so it cannot meet the feed or subtitles. Non-capable clients keep the
same banner as before.

## Proof
`contact_sheet.jpg` (this folder) and `media/`. Harness: `tools/run_textfeed.py` (dedicated server straight on m1l1, RELEASED
exe + game.dll, textfeed-next mod pak, the new cgame on the client only, DISPLAY2, engine `screenshot`), overlay driver
`tools/overlay/coop_mod/coop_selftest_xp.scr` (TEST ONLY), `tools/make_sheet.py`. The real m1l1 hint ("Climb the stairs and find
the MG42 ...", a bold `iprintlnbold` that used to land on the old box) is released by setting the two level flags its thread waits for.

## Proof status
- `contact_sheet.jpg`: cells 1-4 are the same scenario (3 long feed lines + an alert, 3 subtitles) on the RELEASED cgame (collides) and the new one (clear) at 720p and 4:3; cell 5 1080p; 6 long wording; 7 a bold `iprintlnbold` + `iprintln` (same calls as maps/m1l1.scr:2667 and items) arriving in the feed; 8 the banner. GIF: `media/challenge_banner_typewriter.gif`.
- Harness: runs tf720h / tf1080h / tf43h (new), tfold720 / tfold43 (released cgame), tf720ja (banner, old-route), archived in G:\mohaa-hudfeed5
uns_textfeed.
- Real m1l1 MG42 hint: its log line (`FEEDUNTAGGED ... Climb the stairs`) arrived once (run tf720b), never again (the thread needs the intro/ending beats); the screenshot cell uses the same call from the overlay. Real untagged engine lines (`That weapon is currently banned.`, `Picked Up ...`) were routed in every run.
- Harness trap found: the client runs at ~1000 fps, `wait N` is N frames (a fraction of a second): real-time pauses must be python sleeps; ihuddraw needs `cg_hud 1` (`set cg_huddraw_force 1`) in m1l1's intro.
- Not verified: 2560x1440 / ultrawide (DISPLAY2 clamps to 1080p), 1080p true size, two-player remote client, Hardcore, a multi-line wrapped subtitle block beyond 3 lines, the banner on a non-feed-capable (old cgame) client, sound of the typewriter.

## Round 2 (coordinator QA: subtitles ran across the item row / health cluster)
Engine `ba72a485`: in a coop session cgame draws the subtitles itself (same text, 80 % wrap, timing and envelope as the exe) with
the block's bottom 6 px above `CG_CoopItemsTopPx` (clears the item row, labels and health cluster), and sets the exe's `subAlpha`
to 0 so its copy is invisible (put back outside coop). The feed stands above the new block. Opacity: archived `coop_subAlpha`
(0.65). cgame.dll md5 `c94af88916b2e4c1e6e6f1e5bca1d906`. Cells 2, 4, 5 re-shot (runs tf720ka / tf1080ka / tf43ka).
