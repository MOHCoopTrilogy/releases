# CLOUD BRIEF - HZM MOHAA Coop Mod, script drafts (written 2026-10-14)

You are working in a cloud copy of the repository `MOHCoopTrilogy/hzm-mohaa-coop-mod`, branch
`coop-wip` (tip `4f8a1019` = public release v1.10.22). This is a co-op mod for Medal of Honor:
Allied Assault running on the OpenMOHAA engine. The files are Morpheus game scripts (`*.scr`),
configs (`*.cfg`), UI (`ui/*.urc`) and assets.

**You cannot run the game here.** There is no engine, no game data, no test harness. Your job is to
write careful FIRST DRAFTS that a local session on the developer's PC will fetch, test and finish.
Write for that reader: small commits, one concern each, and a clear list of what is unproven.

The user is not a programmer. Report in plain language.

## Where your work goes

- Commit to a NEW branch (use the branch the cloud environment gives you, or `cloud/reinf-draft`).
  Never commit to `coop-wip`, never force-push, never open or merge a pull request into `coop-wip`.
- One commit per step (S1, S2 ... and one each for items B and C). The local session will take
  them one at a time, so each commit must leave the mod loadable on its own.
- Put your notes in `_cloud_notes/NOTES.md` on your branch (the local session will not merge that
  folder). For every step: what you wrote, which existing code you copied the recipe from
  (file + label), what you could not verify, and the exact in-game check that would prove it.

## Hard rules

1. Add NO file under `textures/` or `models/`, and change none there. A build gate refuses it
   (it would force every player to re-download 1.3 GB).
2. Do not touch the Omaha maps or anything of theirs: `maps/m3l1a*`, `maps/m3l1b*`, `maps/e3l1*`,
   `maps/e3l2*`, `maps/obj/obj_team3*`.
3. Do not edit `ui/`, `*.tik`, sound aliases' existing rows, or any `.pk3`. Script and cfg only.
   (Adding a new alias row is fine if the design needs it and the sound file already exists.)
4. Everything new sits behind its switch (`coop_reinfSmart`, default off for now). With the switch
   off the mod must behave exactly as v1.10.22 does. No change to existing behaviour by default.
5. **Copy, do not invent.** Before writing any mechanism (spawning AI, turrets, AI orders, sounds,
   weather, hints, triggers), grep `maps/`, `global/`, `coop_mod/` for a place that already does it
   and copy that exact recipe. Name the source in your notes. Only invent when the search is empty,
   and say so.
6. Do not guess engine commands. If a script command or entity field is not used anywhere in this
   repository, treat it as non-existent unless you can show it in the engine source
   (`MOHCoopTrilogy/openmohaa` on GitHub may be stale; say if you relied on it).

## Script language traps (each of these has cost a full debugging session)

- **Parse killers** - any one silently stops the WHOLE file from compiling, and the map then runs
  with no script at all: an em-dash or any non-ASCII character; a bare negative in parentheses such
  as `(-1)` (write `(0 - 1)` or use a variable); a UTF-8 BOM; a label/brace mismatch.
- Brace counts can balance while the file is broken (two opposite errors cancel). Verify with a
  **running-depth scan**: depth never goes negative and is 0 at every column-0 label (internal goto
  labels may sit at depth 1). Write a small Python checker for this as your first act, run it on
  every `.scr` you touch, and paste its output into your notes.
- Files are ASCII with the line endings they already have. Do not reformat or re-indent existing
  code; keep diffs minimal.
- No `waittill pain` - use `waittill damage` or an `events.scr` subscription.
- `wait` / `waitframe` are forbidden in or before `coop_mod/main.scr::main` (the whole init runs in
  one frame). New init hooks called from there must return in the same frame and `thread` anything
  that waits.
- `moveto` / `move` silently do nothing on a `script_model` - step the origin each tick.
- `spawn <class> key "value" ...` with inline key/values is fine (190+ working uses).
- Per-player state lives in `self.flags["coop_*"]`. `$player` is 1-indexed; `$player.size` is the
  connected count. Players can leave mid-loop: check `!= NULL` after every wait.
- The mod runs with `g_gametype 2`. Coop code is gated by `level.gametype != 0`. On a few player-vs-
  player arenas `inCoopMode` is true too - reinforcements must not run there (find how existing
  coop features exclude MP arenas and copy it).
- Cvars read in scripts must be seeded in `coop_mod/cfg/coop_defaults.cfg` (find the file and follow
  its conventions); do not rely on unset cvars.
- Every script file that waits on the coop framework calls
  `waitthread coop_mod/main.scr::waitForMainScript` first.
- Debug prints follow the existing pattern (`level.cMTE_coop_<file>`); add one for the new file.

## The work, in priority order

### A. Officer and reinforcements rework (the main job)

The full audit, the approved design, the build order S1..S6 and the user's answers are in the
second half of this document ("Officer and reinforcements: audit and design"). The coordinator note
at its top records what the user approved, including the radio addition: a destroyable radio, and
after the officer dies ordinary troops keep calling backup (with German radio chatter if an alias
for it already exists in the mod) until the radio is destroyed.

That document refers to local files and tools you do not have (`docs/TRAPS.md`, `.wolf/buglog.json`,
harness copies, G: paths). Ignore those references; everything you need about the existing code is
in this repository, chiefly `coop_mod/officer.scr`, `coop_mod/aihandler.scr`, `coop_mod/events.scr`
and the map scripts.

Build S1, then S2, then S3 and so on, in order. Depth beats breadth: a careful S1-S3 is worth more
than six thin steps. Stop and write up rather than rush the later steps.

### B. Forced sandstorm on the SAS rescue mission

The user's request, verbatim: "in the SAS rescue mission, when you pick up the explosives and the
first coop smoke grenade and the alarm triggers, can we force an extreme sandstorm every time, it
adds to the atmosphere a lot, should continue through end of the mission. After you place the
explosives on the gate door you should get a hint "Tutorial: Sandstorms, Blizzards and
Thunderstorms make visibility more difficult, tread carefully.""

- First identify the map. It is one of the North Africa mission-1 maps (`m1l*`). Find the script
  that has the explosives pickup, the coop smoke-grenade pickup, the alarm and the gate door, and
  say in your notes which map it is and the lines that prove it. If two maps fit, say so and do
  not guess.
- Read `coop_mod/weather.scr` to learn how weather is chosen and how a map or event can force a
  type and intensity. Use the existing forcing mechanism if there is one; if there is none, add the
  smallest possible hook and describe it.
- The storm starts at that moment, every run, and holds until the mission ends (it must survive
  the weather system's own timers and must not carry over to the next map).
- The hint shows once per player, after the explosives are placed on the gate. Copy how existing
  one-time tutorial hints are shown and remembered.
- This item is NOT behind `coop_reinfSmart`; give it its own switch `coop_m1StormForce`, default 1.

### C. "Give all weapons" key does nothing (diagnosis by reading)

In v1.10.22 the developer's key `bind K "append name ,gax"` does nothing on their own listen
server. The path is: the player's name change carries a comma command -> `coop_mod/player.scr`
(the name-command dispatch; `gax` is index 17) -> `coop_mod/developer.scr::give_all_weapons` ->
`global/giveall.scr`. Read that whole path and list every gate that could make it silently do
nothing for the host (dev cvar, host check, admin check, alive/spawned check, a rate limit, a name
length limit, anything recently changed around the name bus). Rank the candidates and say what one
console check would tell them apart. Fix it only if the cause is certain from the code alone.

## Final report

End with: the branch name; the list of commits with one line each; the depth-scan output; what is
unproven; and any question the user must answer. No claims of "works" - nothing here was run.

---

