# Harness and reproduction reference

Moved out of `docs/TRAPS.md` 2026-08-10 to stay under its 60 KB ceiling. This is how-to material for
reproducing and testing rather than a way the project breaks itself, and much of it is now embodied
in `launch_dedicated_2player.ps1` / `launch_2player_m2l2a.ps1` and in section 12 (the remote-client
test rig) of `docs/proposals/server_topology_and_limits.md`. Nothing cut - verbatim below.

## T15 — Harness and reproduction gotchas

Each of these cost at least one session.

| Gotcha | Detail |
|---|---|
| **Check tools exist before citing them** | `scratchpad/` is wiped periodically. A working rcon client lives at `scratchpad/rcon.py` (rebuilt 2026-08-07) - if it is missing, rewrite it: the connectionless prefix is `b'ÿÿÿÿ'` and `lstrip("print
")` is a **character set**, not a prefix, so it eats the payload. In-repo tools that persist: `docs/tools/scrlint.py`, `hzm-mohaa-coop-mod/_research/cov_report.py`. |
| **rcon needs the direction byte** | Every rcon client must send the connectionless prefix `b'\xff\xff\xff\xff\x02'`. Without it the server logs `bad connectionless packet`, **silently runs nothing, and the harness still looks successful** — so every capture is wrong (bug-1143). |
| **The ESC menu cannot be opened with `keybd_event`** | SDL ignores synthetic keys. Use `rcon pushmenu dm_main` / `popmenu 0`. `dm_main` **is** the ESC board. |
| **Use an isolated homepath** | Harness cvar pollution once stomped the user's real `omconfig` (`r_customwidth`, fullscreen) and surfaced as a "4:3 bars" bug report (bug-1134). And `CVAR_ARCHIVE` probe values are silently retained by every later boot — force them in the boot cfg **and** on the command line. |
| **Coop join takes ~3 clicks and ~20s to settle** | Capture earlier and you get the 3P spawn pose with no HUD. |
| **`g_scriptcheck` + coop `game.*` vars = a fake crash** | `G_ArchivePersistant` `Com_Error`s on non-empty coop `game.*` vars if `g_scriptcheck` is on. Looks exactly like a crash. Force it 0. |
| **Load maps the real coop way** | `set ui_dmmap <m>` + `exec start_server.cfg` / `ui_startdmmap 2`. `devmap` is single-player and plain `map` does nothing on a running coop server. |
| **`.st` parse errors `ERR_DROP` the server** | Opposite of `.scr` silent-fail. And `LoadStateTable` needs a CLIENT, so **dedicated boots never parse it** — the first *listen* launch after any `.st` edit is the real test. |
| **An incremental fgame build skips a `.cpp` on a header-only change** | Touch the `.cpp` (cost a session on `actor.cpp`). |
| **`iprintlnbold` reaches `qconsole.log`; `println` does not** (without `developer 1`) | Use `iprintlnbold` for in-game bisect prints — but never ship dev prints to players. |
| **`rcon meminfo`** | The measurement tool for any renderer-zone question (`TAG_STATIC_RENDERER`). |
| **cdb / crash dumps** | Build RelWithDebInfo, reproduce, `.ecxr` for the **real** fault context - `0xc0000409` fail-fast masks an underlying `0xC0000005`. `game.pdb` ships next to `game.dll` so dumps resolve lines; `.symopt+0x40; .reload /i` force-maps a stale PDB. Some diagnoses come from the **Windows Application event log**, not the game log. |
| **Reproduction preconditions are load-bearing** | bug-1144 needed a **fullscreen menu over a LIVE session** — disconnecting does *not* reproduce it, because `UI_ClearBackground` clears depth once `clc.state <= CA_PRIMED`. Every earlier hunt saw a clean menu and concluded wrongly. |
| **Concentrate the test** | Morale break needs a *concentrated* map — m2l1's ~41 enemies never drop below the threshold under a localized damage-sim. |
| **The bot rig sets its own cvars** | A feature "verified" only by the rig may still be `SHIPPED-CODE-DISABLED` for players — the rig enables the gate itself. This is exactly what happened to the AI maneuver mover. |
| **Never attribute a log event by proximity to a map banner** | `COV MAPDONE` marks a map's **END**, so binning lines by "nearest preceding MAPDONE" labels every event with the **previous** map - off by exactly one, uniformly, and plausibly enough to survive review (it misfiled a 12,690-error storm and produced two bug entries against the wrong files). **A Morpheus script error prints its own `(path/file.scr, LINE)` - that pair is ground truth and needs no map attribution at all.** |
| **The engine TRUNCATES `qconsole.log` on every launch** | A driver that relaunches to make progress destroys the results it is collecting. Rotate the log per launch **and** have the reader scan `qconsole*.log` as a set — doing only one of the two silently loses runs (the observed symptom was a completion count going *down*, 34 → 32). |

---
