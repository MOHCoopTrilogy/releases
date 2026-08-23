# Per-Map Coop Smoke Test

## How to load a map fast
- Console (`~`): `devmap <mapname>`  (sv_cheats is on; coop init runs via the map's main.scr).
  - If a map loads WITHOUT coop (no "***** Loaded *****", no loadout), use the in-game menu:
    Multiplayer -> HaZardModding Coop Mod -> pick map -> Apply.
- Map ids are the .bsp names, e.g. `devmap m1l1`, `devmap e1l1`, `devmap t1l2`.

## Per-map checklist (smoke test — ~1 min each)
1. **Loads clean** — no `Script Error` / parse-kill on load; reaches `(coop_mod/main.scr::main): ***** Loaded *****`.
2. **Player spawn + loadout** — you spawn, `waitForPlayer DONE`, weapons given (no stuck weapon-select).
3. **Officer spawns** — `OFFICER SPAWNED` at a sane spot (anchor log line shows position; officer not in a wall/floor/void).
4. **Playable** — you can move/fight and progress; map doesn't soft-lock on a scripted SP gate.

I (assistant) watch the monitor and flag each map's result from the log. Just load a map and play ~1 min; tell me the map name (or I'll see it in the log) and I'll record PASS / ISSUE below.

---

## Status legend: [ ] untested  [P] pass  [!] issue (see notes)

### AA m-series (integrated; m4l3 already PASS)
- [P] m4l3  — baseline, fully working
- [ ] m1l1   (anchor flagged for in-game capture)
- [ ] m1l2a
- [ ] m1l2b
- [ ] m1l3a  (no level script -> dynamic-anchor fallback)
- [ ] m1l3b
- [ ] m1l3c  (anchor flagged for in-game capture)
- [ ] m2l1
- [ ] m2l2a
- [ ] m2l2b
- [ ] m2l2c
- [ ] m2l3
- [ ] m3l1a
- [ ] m3l1b  (anchor flagged for in-game capture)
- [ ] m3l2   (no-wrapper anomaly — watch load closely)
- [ ] m3l3   (no level script -> dynamic-anchor fallback)
- [ ] m4l0
- [ ] m4l1
- [ ] m4l2
- [ ] m5l1a
- [ ] m5l1b
- [ ] m5l2a  (no level script -> dynamic-anchor fallback)
- [ ] m5l2b  (boss+paradrop reduced/off per Phase 1)
- [ ] m5l3   (wave mask reduced — no AT/dogs)
- [ ] m6l1a
- [ ] m6l1b  (no level script -> dynamic-anchor fallback)
- [ ] m6l1c
- [ ] m6l2a
- [ ] m6l2b
- [ ] m6l3a
- [ ] m6l3b
- [ ] m6l3c
- [ ] m6l3d
- [ ] m6l3e

### Spearhead e-series (integrated; e3l2/e3l3/e3l4 newly hooked)
- [ ] e1l1   (Afrika theater)
- [ ] e1l2   (Afrika theater)
- [ ] e1l3
- [ ] e1l4
- [ ] e2l1
- [ ] e2l2   (missing waitForPlayer — watch for player-less combat)
- [ ] e2l3   (checkpoint system)
- [ ] e3l1
- [ ] e3l2   (newly integrated)
- [ ] e3l3   (newly integrated; fixed pre-existing corruption)
- [ ] e3l4   (newly integrated; boss off — campaign end)

### Breakthrough t-series — on-foot (newly integrated)
- [ ] t1l2
- [ ] t1l3
- [ ] t2l1
- [ ] t2l3

### Breakthrough t-series — NOT integrated (expect vanilla / no officer)
- [skip] t1l1  (long plane/barn cinematic — needs surgery)
- [skip] t2l2  (halftrack-driven — needs surgery)
- [skip] t2l4  (player-kill death zones — needs surgery)
- [skip] t3l1  (tank waves — needs surgery)
- [skip] t3l2  (T-34 whole map + campaign end — needs surgery)

## Suggested order
1. A couple of integrated AA maps you haven't tried (m1l2a, m2l1, m3l1a) — confirm the rollout is neutral.
2. e-series, focusing on the newly-hooked e3l2/e3l3/e3l4.
3. On-foot t-series (t1l2, t1l3, t2l1, t2l3) — these are the riskiest (estimated anchors, fresh integration).
