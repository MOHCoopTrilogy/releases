# Live Operations - build record (v1.10.71 lane, 2026-11-10)

The plan is `PLAN.md`; this is what was built and how to rebuild it. Status: **SHIPPED-UNVERIFIED** until merged and
played by the user (harness-verified on a private client, below).

## Pieces

| Piece | Where | Generated? |
|---|---|---|
| Contract pool, layout pass, reference roll, all textures, urc widgets, tables | `gen_ops.py` (this folder) | the generator |
| Location evidence | `ops_locations.json` | authored |
| NEW GAME wall + flat chooser | `ui/hzm_newgame3d.urc`, `ui/hzm_ngflat.urc` (+ `textures/menu/hzm_ops_*`) | yes, via `make_ng3campaigns.py` |
| Engine: board, card, deploy, return | `code/client/cl_hzm_ops.cpp` + `cl_hzm_ops_table.h` (exe only) | table yes |
| In the match | `coop_mod/mp_ops.scr` (MP-owned) + `mp_ops_table.scr` (generated) + one seam each in `mp.scr`, `mp_bots.scr`, `mp_hardcore.scr`, `mp_weather.scr` | table yes |
| Sweep / client harness | `tools/ops_sweep.py`, `tools/liveops_test.py` | - |

## Rebuild (order matters)

```
python -P -E ../sp3camp_2026-11-08/warmap.py all <ne> H:/hzm_work/liveops-warmap   # tags from missions.json
python -P -E gen_ops.py check  --sheet H:/hzm_work/liveops-warmap                # layout problems = build failure
python -P -E gen_ops.py engine <engine checkout>                                 # cl_hzm_ops_table.h
python -P -E gen_ops.py mp     <mod checkout>                                    # coop_mod/mp_ops_table.scr
python ../sp3camp_2026-11-08/make_ng3campaigns.py --mod <mod checkout> --sheet H:/hzm_work/liveops-warmap
```
The `hzm_ng3c_*` / `hzm_ops_*` textures are gitignored: run the last step in the checkout `build.ps1` packs from.
The exe and the mod pak ship TOGETHER (the menu's `hzm_ops` command and `ui_ops*` cvars live in the exe).

## Decisions taken while building
- **No arm cfgs, no engine MP hook.** The engine sets only `ui_*`/engine cvars and the contract (`ui_opsGo*`); `mp_ops.scr`
  reads them while `ui_opsLive` is 1 and overrides mode/preset/fill/hardcore/weather in level state. `check_mp_isolation`
  passes with no new allowance (22/22, selftest 91 mutations).
- **Stateless schedule.** Each exclusion group's time is cut into 11-minute windows, at most one contract per window
  (90 %, 5-8 min). 24 h census: mean 4.2 live, one empty minute a day.
- **Tag nudges on the widened wall:** only bt3 moves (-> 46.6, 13.8, the Adriatic head) to clear the Bologna loop. bt2 needed a
  move only while Malta was in the pool; with Malta pruned it stays where v1.10.70 put it. bt1 stays.
- **Pool after the 300 s sweep:** TDM Remagen, Stalingrad, Algiers, Brest, Monte Cassino, Bologna; OBJ Bologna, Palermo,
  Bizerte Festung, The Hunt, V2 Facility, The Bridge. Dropped for no fighting: Malta, Berlin (TDM), Omaha (OBJ).
- **Approx pins moved** for clearance: The Hunt -> 49.05/-1.45; "Somewhere in France" -> 45.6/2.5 (Auvergne) with a smaller
  area loop, between the BASTOGNE tag and the printed FRANCE.
- **OBJ result** = the engine's `allieswin`/`axiswin`/`draw` level event (the `g_temp*score` cvars are not readable after the
  restart). Bots are held until the player has joined, so the round he plays is the first.
