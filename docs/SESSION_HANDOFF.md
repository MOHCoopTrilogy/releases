# SESSION HANDOFF — 2026-08-09 (early hours)

Read this, then `docs/SOURCE_OF_TRUTH.md`.

---

## 0. State right now

Everything below is **deployed** (`build.ps1`, last run 01:20). Still local only — **v1.2.3 is
what is public**. No game process should be running; the last one was killed at 02:00.

**Two things are confirmed fixed and verified live. One is fixed but unconfirmed. One is open.**

---

## 1. m2l2a stealth route — the long hunt

Six instrumented playtests. The route kept failing for **four independent reasons**, each of which
fully explained the symptom on its own, which is why fixing any one of them changed nothing visible.

| # | Cause | Status |
|---|---|---|
| 1 | `aihandler::attackPlayer` forces attacks on a disguised player; 3 of its 4 callers never checked | **VERIFIED** — every `AGGRO` is now followed by `AGGRO BLOCKED` |
| 2 | `ai_alarm_alerted` rings the alarm on a disguised player, via an engine callback the guard cannot see | **VERIFIED** — `ALARMTRIP BLOCKED` |
| 3 | Carrying the **papers** counted as being armed, so the disguise cleared ~18s in | **VERIFIED** — `eng_is=1 mod_is=1` now holds |
| 4 | Count-scaling **clones**, squad go-loud and morale berserk call raw `attackplayer` | **DEPLOYED, UNCONFIRMED** |

Bugs 1615–1618. The single most useful measurement was:

```
STEALTHWATCH eng_is=1 eng_has=1 mod_is=1 attackers=0 -> 7 -> 9 -> 15  alarm=0
```

Both disguise flags correct, no alarm, and the attacker count still climbing — which is what finally
pointed past the disguise system entirely and at `coop_spawnReplica`, where every clone is created
with `forceactivate` + `attackplayer` **hardcoded**. The user's own observation nailed it: *"the first
two guards don't immediately try to shoot me but the others barge in."* The first two are the
disguise-aware ones; the rest are clones.

That is also why **it works in singleplayer**: clone-spawning, the squad brain and the morale system
are coop-only additions, and none of them ever asked whether the player was disguised.

**Verify #4 first next session.** One short m2l2a run: take the papers, wait ~20 s, watch
`STEALTHWATCH … attackers=`. It should stay at or near **0** instead of climbing to 15.

### Design rules the user set, which the fixes honour
- Papers can be shown **whenever they like** — that was the point of #3.
- The alarm **must still fire** once cover is genuinely blown. Guarded only while disguised + no alarm.
- Enemies should otherwise behave as they do in vanilla when disguised.

---

## 2. Also fixed and verified this session

- **Enigma is visible** (bug-1610/1611). The shader was never the problem the log implied — the pk3
  was stamped one minute *after* the client quit, so the complaint was about a build that predated
  it. Its `enigmatext` stage also needed `cull none` + `alphaFunc GE128` + `depthwrite`, copied from
  retail's `static_enigmatext` (the texture is 32-bit with a real alpha channel).
- **Enigma facing** — BSP ships `angle 270` and the machine opened away from the player. Flipped to
  90, tunable live via **`coop_enigmaYaw`** (use 360, not 0). *Not yet eyeballed.*
- **Objectives 4/5** now read "Escape the U-Boat." / "Eliminate the enemies and Exfiltrate."
- **Sink cutscene** — water bursts were positioned at the *sinking* hull origin, so they chased her
  underwater. Now pinned to the waterline with a port/starboard throw, cadence ramps 0.45 s → ~2 s,
  plus surface columns down both sides while she is still afloat. *Not yet seen.*
- **`level.coop_ambEnt` name collision** (bug-1612) — one name owned by two subsystems. Broke the
  m1l2b telephone gag from the day it shipped. Registry renamed `coop_ambByAlias`.
- **m2l2b `level waittill spawn`** (bug-1613) — replaced with the `replace.scr::waitTillSpawn` shim.

---

## 3. Blueprints — narrowed to one line, not yet fixed

`BP think started` prints, the loop never runs. Staged checkpoints located it exactly:

```
BP g0 → BP g1 → BP g2 → BP END at owner-guard
```

**`local.owner` is NIL/NULL inside `coop_bp_think`, while `local.ent` and `local.n` both bind.**
Param 2 — and only param 2 — fails to arrive, and it is the only one that is a *player* entity.

Ruled out on the way (don't re-chase these): `level.coop_mapname` is a perfectly good `"m2l2a"`
(confirmed by rcon — it reaches `g_scoreboardpic` and `coop_prevMap` intact), `vector_length` is used
723×, `isAlive` 944×.

**Suggested fix:** stop passing the player entity. Pass the **entnum** (a number, proven to bind) and
resolve it out of `$player` inside the loop each tick.

⚠️ **Watch the probe syntax.** `println( "x" ) end` on one line makes MOHAA swallow the `end` **as a
second println argument** — it printed `owner-guardend` and the thread kept running. Put `end` on its
own line. That is a genuine parse trap and cost a misread.

---

## 4. Overnight autotest — 80% built, deliberately NOT left running

`stealth_autotest.ps1` + `autotest_rcon.py`, results to `autotest_results/`. It has a clean oracle
needing no human judgement: `attackers>0` while `mod_is=1 alarm=0` is a regression.

**It launches, spawns the player and captures the right log slice.** Four harness defects were found
and fixed (bug-1619): bare `ui_startdmmap` instead of `start_server.cfg`; minimized window defeating
the spawn click; deleting `qconsole.log` between runs (the engine does not recreate it); and then a
byte offset that broke because the engine **truncates** the log on launch.

**What still doesn't work:** the papers and uniform are **USE pickups**, and driving that with rcon
`setviewpos` + a synthetic `F` keypress did not reliably collect them. Without the pickup there is no
disguise and no guards, so every run scores `SETUP-FAIL`.

It was left **off** on purpose — a harness that always reports SETUP-FAIL would run the machine all
night for nothing.

**Recommended next step:** drive the pickup from **script**, not synthetic input — a
`coop_selftest`-style thread that force-grants the disguise and walks the player past guard origins
(54 of them are in `map_entities/m2l2a_entities.txt`). The existing `coop_selftest_*.scr` files are
the pattern. Only the spawn itself genuinely needs a real click; everything after it can be in-script.

---

## 5. Before any release

- **Remove the two TEMP debug lines from `autoexec.cfg`** (`set coop_aggroDebug 1`, `set coop_bpDebug 1`).
  They are marked TEMP with the reason inline. `coop_aggroDebug` is chatty — several lines a second.
- The guards default **ON**; `coop_stealthNoAggro 0` disables them without a rebuild.
- Blueprint staged checkpoints (`BP g0/g1/g2/g3`) are unconditional prints — gate or remove them.
- 23 other map scripts still hold a raw `level waittill spawn` (bug-1614). Per TRAPS T3 the rule is
  **do not bulk-replace** — the runtime log is the oracle, fix each as it is played.
