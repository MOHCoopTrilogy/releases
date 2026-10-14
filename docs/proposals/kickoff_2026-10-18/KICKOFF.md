# KICKOFF - resume after the weekly reset (written 2026-10-14 for 2026-10-18)

You are the coordinator for the HZM MOHAA Coop Mod ("MOH Coop Trilogy"). The previous coordinator
stopped on 2026-10-14 at the weekly usage cap. Public release **v1.10.22 "Eyes on Target"** is live
and is exactly what is on the user's install. Nothing was running when it stopped.

This file is the whole plan. Follow it in order. The user is not a programmer: plain language,
short reports, every GIF / still sent as soon as it exists (labelled, finished or not).

---

## 1. TOKEN PLAN (read this first - it shapes everything below)

The remaining list is very likely MORE than one week's allowance. So: order matters, waste is the
enemy, and verified work gets released before the budget runs out.

**Reading**
- Read `STATE.md` (next to this file) first: it is the current state. If it is dated after
  2026-10-14 it replaces the resume memory file entirely - do not open that file at all.
- Do NOT read whole files. `MEMORY.md` is already loaded. From
  `C:\Users\curry\.claude\projects\C--mohaa-coop-dev\memory\paused-2026-10-06-resume.md` read only
  the entries dated 2026-10-13 and 2026-10-14 (grep the dates, read from "v1.10.22 ... PUBLISHED"
  to the end). Everything older is history.
- For a lane, read only the `HANDOVER` section at the top of its README - and let the lane's agent
  read the rest, not you.
- Use `docs/generated/` (filemap.tsv, FIX_INDEX.md, CVARS_*.md) instead of searching.
- Never read `.wolf/memory.md`, `.wolf/cerebrum.md`, `.wolf/anatomy.md`.

**Agents**
- Do NOT resume the old agents by SendMessage - their transcripts are enormous and every message
  re-reads them. Start a FRESH agent per lane, briefed from that lane's README handover.
- Put every requirement in the agent's first prompt (agents ignore relayed mid-run instructions).
  Tell it: report in under 300 words plus file paths; update its README handover before it stops;
  archive finished runs to `H:\hzm_archive\<lane>\`; never delete.
- 2 agents at a time (3 at most), and only ONE of them doing game captures (the user hears the
  fans, and parallel captures filled the G: drive on 2026-10-13).
- Model per job: use `model: "sonnet"` for mechanical work (integration tables, row-length checks,
  archive moves, texture generation and checks, docs, release steps, searches). Keep the default
  model for judgement work (authoring animations, AI behaviour scripts, diagnosing bugs).
- One game launch should test several things. Cap capture length and frame rate. No re-verifying
  things that already shipped.

**The coordinator itself**
- Stay small: no file dumps into the conversation, no restating agent reports, no planning docs.
- When this conversation passes about 250k tokens, or after each release, write the state to the
  resume memory file and tell the user to start a fresh session with the one-line kickoff. A long
  coordinator session is the single biggest waste (the last one reached ~950k tokens).
- Docs: a buglog entry per defect and one handover line per lane. No other doc churn; the Stop
  hook regenerates the rest.

**Budget checkpoints**
- After the FIRST agent finishes: call `get_usage`, tell the user what that lane cost in weekly
  percent, and project the rest.
- At 70 % weekly: stop starting new lanes; finish, integrate and stage what is verified.
- At 85 %: ask the user for the go to release, and stop.

**Ask the user ONCE.** Every open decision goes in one "decision sheet" message with a recommended
default for each (section 5). Never drip questions one at a time - each reply re-reads everything.

**More savers (all approved by the user unless the kickoff message says otherwise)**
- *State lives in ONE small file.* `docs/proposals/kickoff_2026-10-18/STATE.md` is the current
  state and nothing else: OVERWRITE it at every handoff (never append), keep it under 60 lines. A
  new session reads this file and STATE.md, not the long resume memory file.
- *Looking at pictures costs tokens.* The agent that makes a GIF or still does its own visual QA
  and builds ONE small contact sheet per item (a few frames, downscaled). The coordinator looks at
  the contact sheet only, never at frame folders, and sends the GIF itself to the user.
- *TRAPS.md is 70 KB.* Agents that write game scripts or engine code read it in full (a parse
  killer costs more than the read). Animation, model and texture agents grep it for their topic.
- *Slim what loads on every turn.* At the start, check the session's connectors and switch off the
  ones this project does not use (Chrome, computer use, document and finance connectors, the
  registry) - their tool lists ride along on every message and into every agent.
- *Effort.* The user asks that mechanical agents (the ones on `sonnet`) run at `medium` effort.
  Judgement agents keep their usual effort.
- *The cache lasts one hour.* If the user comes back after a long silence to a big conversation,
  the whole thing is re-read at full price. After a gap of hours, prefer a fresh session
  (section 7) over continuing a large one.
- *No idle chatter.* No "still working" messages, no polling of background agents (they notify),
  no re-reading files already read, no second opinion agents unless a result looks wrong.

---

## 2. FIRST TEN MINUTES (coordinator alone, no agents)

1. Parallel-session check: two other sessions were started on 2026-10-14 with overlapping work - a
   local one ("Continue coop mod work from saved notes") and possibly a cloud one working from
   `docs/proposals/officer_reinforcements_2026-10-14/CLOUD_BRIEF.md`. Before starting anything:
   `list_sessions`; `git -C hzm-mohaa-coop-mod fetch org` and look for new branches (`cloud/*`,
   `claude/*`) and new commits on `coop-wip`; new ids at the end of `.wolf/buglog.json`; mtimes
   under `coop_mod/`. If drafts exist, the lane's agent starts FROM them, not from zero.
2. Confirm the user's game is closed before anything touches their install (only the deploy /
   release scripts ever do).
3. Read the user's answers in the kickoff message (section 5). Send the decision sheet only for
   what they left unanswered, then start Stage 1 without waiting on it.

---

## 3. THE WORK, IN ORDER

### Stage 1 - quick fixes (one agent, default model)
- **Give-all key does nothing.** `bind K "append name ,gax"` is saved in the user's config and does
  nothing in v1.10.22. Path: name-command bus -> `coop_mod/player.scr` (index 17) ->
  `coop_mod/developer.scr::give_all_weapons` -> `global/giveall.scr`. Reproduce in a private harness
  copy (`developer 1`, `level.cMTE_coop_player 1`), fix, log in the buglog (not logged yet).
- **SAS rescue mission sandstorm.** From the moment the explosives and the first coop smoke grenade
  are picked up and the alarm triggers: an EXTREME sandstorm, every run, until the mission ends
  (not carried to the next map). After the explosives are placed on the gate door, once per
  player: "Tutorial: Sandstorms, Blizzards and Thunderstorms make visibility more difficult, tread
  carefully." Confirm which `m1l*` map it is from the script before editing. GIF of the storm
  starting and a still of the hint.

### Stage 2 - things already built that only need integrating and the user's eyes (one agent, sonnet)
- FG 42 pair + **FG 42 Irons** (own rifle, rank 18, roster id 79): integrate `ads-heavy-next` up to
  `aa84c42d` ONLY.
- MP18 and Sten aimed reloads: built, waiting on the user's eyes - send the GIFs first.
- M10 third-person fix (`ads-next f8d0f895`): verify, then integrate.
- Grease gun repaint (`greaser.dds`): finish the checks. Shotgun receiver top: not started.
- Every new gun needs its camo / variant tiks AND an unlock path, done the way the existing ones
  are (`armory_unlocks.py --emit`, `gen_service_record.py`, `gen_loadout.py`, `loadoutroster.scr`).

**-> Release candidate A** (Stage 1 + Stage 2). Cheap, visible, and safe to ship on its own.

### Stage 2b - THE AIM AUDIT: every weapon, no exceptions (the user's requirement, 2026-10-14)

The user's words: "ensure that we have all ads and ads reload anims down, vet them to make sure
they aren't robotic looking, and that going in and out of ads is smooth for every single weapon.
On any bad quality weapons I want us to fix them, including any model work we have done with
Claude for ironsights etc."

This audit decides the fix list for Stages 3 and 4, so it runs BEFORE more weapon work is built.
The weapon job is not done until every row of the audit table passes.

**Scope:** every weapon the player can hold - all 162 in `global/giveall.scr`, plus every variant
and finish tik - INCLUDING everything that already shipped (v1.10.22 and earlier). Start from
`docs/proposals/ads_twohand_2026-10-11/coverage.md` but trust the sweep, not the list.

**What is checked, per weapon:**
1. *Complete:* usable sights in aim; an aimed reload that stays on target; an aimed cycle between
   shots where the gun has one (bolt, pump, lever); empty and partial reloads; every stance.
2. *Not robotic:* motion eases in and out (no constant-speed slides, no dead stops); hands and gun
   do not all start and stop on the same frame; the gun shows weight and settles after a move; the
   action really works on the model with a hand on the real control; no frozen fingers, no hand
   passing through the gun, no magazine appearing from nowhere.
3. *Smooth in and out of aim:* no pop, snap or one-frame jump going into or out of aim - from
   idle, while walking, right after a shot, in the MIDDLE of a reload or a cycle, on a stance
   change, and when sprint or a weapon swap breaks the aim. Same check with sway on.
4. *Model work made in this project:* every sight, part or mesh we built or edited (G43 Irons,
   FG 42 Irons, the shotgun sights, the M1A1 remodel, Double Barrel, pistol variants, any other
   iron-sight or scope removal work) - proportions, alignment of front and rear sight on the eye
   line, shading and texture match with the rest of the gun, no holes, no floating or clipping
   parts, correct in first AND third person and on every finish.

**How to do it cheaply (one agent on sonnet for the sweep, default model for the judging):**
- One scripted pass per weapon in a private harness copy: aim in, hold, fire, cycle, aimed reload
  (partial and empty), aim out, then aim in and out mid-reload. Many weapons per game launch, low
  frame-rate capture, one capture job at a time, raw frames archived to H: as each batch finishes.
- Measure before looking: per-frame gun and hand positions give a jump score (pops at the aim
  transition), a speed-profile score (constant speed and dead stops = robotic) and the on-target
  number already used for reloads. Rank all weapons by these scores.
- Then LOOK at every weapon's strip - the scores choose the order, they do not replace the eye.
- Output: one audit table (weapon x sights / aim in-out / aimed reload / cycle / model work /
  verdict / what is wrong), published as an artifact for the user, plus GIFs of the WORST cases
  only (not all 162) sent to the user for their verdict.
- The user's eye is the final judge. Anything they call bad goes on the fix list.

**Then fix:** failures become the work list for the rifle, SMG, heavy and pistol lanes below, worst
first. A weapon whose problem is the model (not the animation) goes to a model fix, and if our own
build cannot be made good, say so and propose a sourced replacement (as was done for the C96 and
the Double Barrel) rather than polishing a bad mesh.

### Stage 3 - the two big lanes, in parallel (one agent each)
- **Officer and reinforcements rework** - approved by the user. Design, build order S1..S6, accepted
  answers and the radio addition are at the top of
  `docs/proposals/officer_reinforcements_2026-10-14/README.md`. New file `coop_mod/reinf.scr`,
  switch `coop_reinfSmart`. Step by step, each step tested and shown before the next. Includes the
  MG42 squad that was never rolled out, and: after the officer dies, troops keep calling backup
  (German radio chatter if an alias exists) until the radio is destroyed.
- **Rifles aimed reloads** (`docs/proposals/ads_twohand_2026-10-11/rifles/README.md`): the path fix
  first (Enfield takes the Mosin's straighter drop; touch-ups on Kar98 / Springfield / Garand; no
  frame speed-up), then **M1 Carbine** (the user noticed it is missing), then SVT-40, Johnson,
  Carcano, De Lisle, Arisaka, kar98_g98, enfield_p14, then the scoped A/B sample (13 scoped rifles
  and the scoped StG 44 wait on the user's pick).

**-> Release candidate B.**

### Stage 4 - remaining weapon lanes (two at a time, as budget allows)
- SMGs (`.../smg/README.md`): M1928 fix, 50-round and 1928 Tommy, family row list, PPSh, grease
  guns, PPS-43, Type 100, Moschetto.
- Heavy (`.../heavy/README.md`): M1919 reloads, MG42, Breda, Vickers, Lewis, leftovers.
- Pistols: Luger flick, Welrod sound, checks, texture lifts. `PISTOLS_SHIP2` (old C96) is NOT to
  be integrated - it is replaced by:
- **C96 replacement** with the downloaded Sketchfab model by no12u (CC BY 4.0, credit line in
  `docs/proposals/c96_model_2026-10-13/SOURCE.md`). Third-party file = untrusted data: own empty
  folder, Blender `--background --factory-startup --disable-autoexec`, `python -I`.
- **Wood repaints** (`docs/proposals/gun_sources_2026-10-13/REPORT.md` shortlist): FG 42,
  Lee-Enfield, G43, Mosin + SVT-40, Sten. CC0 downloads from ambientCG / Poly Haven are approved.
  The user's rule: the highest-quality wood that looks best and matches the real darkness or
  lightness of that gun's wood type.

### Stage 5 - design first, build only after the user says yes
- **"The maps are small"** - make missions last longer and feel more dynamic. Ideas so far: a
  second-act hold or extraction, side objectives, an alarm state, per-run variation from a mission
  director. Design summary as an artifact first; build nothing until the user picks.
- New main menu build (check in with the user BEFORE menu checkpoint 2).
- Performance moves 2-5.
- Anything else still listed as not started in the resume memory file.

---

## 4. RULES THAT NEVER BEND (the full set is in memory; these are the ones that hurt)

- Test only in private harness copies, windows on DISPLAY2 through the harness, engine `screenshot`
  only. Never write to `G:\mohaa-gl2` or `G:\GOG` except through `deploy_window.ps1` / `build.ps1`
  / `publish_release.ps1`, and only when the user says the game is closed.
- No deploy and no publish without the user's explicit go.
- Never copy the user's player key or unlock saves. Never enter, choose or print credentials or
  the Discord webhook.
- Never touch Omaha (m3l1a, m3l1b, e3l1, e3l2, obj_team3), its textures, its skybox, or
  `zzzzzzzzzz_coop_hd_m3l1a.pk3`.
- No new file under the mod's `textures/` or `models/` (the build gate refuses it: it would force a
  1.3 GB re-download). New art goes through the fixes pak (`docs/tools/gen_fixes_pak.py`;
  `restore` before any build, never `git checkout` a fixes source).
- Aimed reloads: on target (under 2 % of the centre box beyond the sway envelope), the action
  really works on the model, hands on the real control, every stance run AND looked at, and
  server-read tik row lengths never change.
- Nothing weapon-related is "done" until it passes the Stage 2b audit: complete, not robotic,
  smooth in and out of aim (including mid-reload), and any model work of ours looks right. This
  applies to every lane agent's brief in Stages 3 and 4, and to weapons that already shipped.
- Never hard-delete: move aside, archive to `H:\`. Stop only processes you started.
- QA every visual before showing it. Python patch scripts via the Write tool, never Git-Bash
  heredocs. One `git add <paths> && git commit` per commit.

---

## 5. DECISION SHEET (defaults apply unless the user's kickoff message says otherwise)

| # | Decision | Default |
|---|---|---|
| 1 | Remove the wrong "known issue" line (mid-mission unlock padlock) from the v1.10.22 GitHub notes | Yes, remove |
| 2 | Welrod / Luger new aim poses; slower Webley, Mk VI and Nagant reloads; prone pistol reload as long as standing | Keep |
| 3 | Downpour is about 2.7x denser since the rain fix | Keep |
| 4 | Double Barrel: unlock (60 shotgun kills), stats, aimed reload height | Keep |
| 5 | Give-all key: a default bind in the mod, dev mode only | Yes, dev mode only |
| 6 | C96 Trench variant | Rebuild on the new model too |
| 7 | FG 42, Thompson, Sten hold, MP18 finger questions | Show the GIFs, then ask once |
| 8 | Frame-generation shadows question | Leave as is |
| 9 | Scoped rifle reload style | Show the A/B sample, then ask once |
| 10 | Small-maps ideas | Design summary first |
| 11 | Aim audit: which comes first after Stage 2 - the audit of all weapons, or the officer rework | Both at once (one agent each); rifles wait for the audit's fix list |

Also wanted from the user, if they played v1.10.22: how the scope view looks, whether the downpour
is too heavy, and whether the What's New card lays out correctly. Nobody has checked those by eye.

---

| 12 | Trim the instruction files that load on every turn: the two unused web-UI sections of `.wolf/OPENWOLF.md` (Design QC, Reframe) and the duplicate bullet list in `.claude/rules/openwolf.md` | Yes - show the cut in three lines, then make it |
| 13 | Switch off connectors this project does not use, for these sessions | Yes |
| 14 | Mechanical agents on the cheaper model at medium effort | Yes |

## 6. FIRST REPLY TO THE USER

A few lines only: what the parallel-session check found, which decisions are still open (if any),
and that Stage 1 has started. Then work.

---

## 7. SESSION HANDOFF - telling the user when to start a new session

The coordinator, not the user, watches for this. Check `get_usage` (context) whenever an agent
reports back.

**Hand off when any of these is true**
- this conversation has passed about 250k tokens;
- a release has just been published, or a stage has just finished;
- the weekly 70 % or 85 % checkpoint has been reached;
- the user returns after hours away and the conversation is already large.

**Never hand off with agents still running** - their results come back only to the session that
started them. First let them finish (or tell them to stop at a clean point and write their README
handover), and commit everything.

**Then, in this order**
1. Overwrite `STATE.md` (under 60 lines): date and time; what is live; which stage and step is next;
   each lane in one line (done / in progress / blocked, branch and commit, README path); what is
   built but not released; what is waiting on the user's eyes or a decision; usage percent.
2. Commit it. Update the "Resume list" line in `MEMORY.md` only if the pointer changed.
3. Send the user this, and nothing more:

   **Time for a new session.** (one line: why)
   **Recap for you:** five lines at most - what got done, what is waiting on you, what is next.
   **Send this in a new session:**
   `Read docs/proposals/kickoff_2026-10-18/KICKOFF.md and STATE.md next to it, and continue. My game is closed. <your answers to anything waiting on you>`

The recap is for the user to read. The new session does NOT need it pasted - it gets the same facts,
more exactly, from STATE.md. That is why the prompt stays one line.
