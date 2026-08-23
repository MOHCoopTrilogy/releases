# Callback-Registry Fix (Outstanding Item #5)

Stops the non-fatal `Could not find label 'coop_playerJust*'` console spam on the maps that do
not define the optional per-map callbacks, while preserving behavior on the maps that do define
them. Implemented per `hzm_coop_framework_guide.md` section 5 (opt-in registry checked in a guarded
dispatch helper).

Staged edits only. No pk3 rebuild, no launch. All changes under
`C:\mohaa-coop-dev\hzm-mohaa-coop-mod\`. ASCII / no BOM / no em-dash. Parens balanced; helper block
internally brace-balanced (the pre-existing raw `{`/`}` count mismatch in `main.scr` is from braces
inside comments/strings and is unchanged by this fix — the additive helper contributes 2 `{` and 2
`}`, net zero).

## 1. New helper in `coop_mod/main.scr`

Added immediately after the `startThread` function (before `getPlayerId`):

```
//=========================================================================
startMapCallback local.cb local.entity:{ //[207] opt-in guarded dispatch for optional per-map callbacks (stops missing-label spam)
//=========================================================================
	//[207] skip silently unless the current map opted in via level.coop_hasCallback[local.cb] = 1 in its main
	if( level.coop_hasCallback[ local.cb ] != 1 ){
		end
	}

	thread coop_mod/main.scr::startThread ( "maps/"+level.coop_mapname+".scr::"+local.cb ) local.entity
}end
```

Behavior: ends silently unless `level.coop_hasCallback[local.cb] == 1`; otherwise dispatches exactly
as the old call did (`startThread` -> `spawn trigger_once setthread maps/<map>.scr::<cb>` +
`doActivate`).

## 2. The four `coop_mod/player.scr` dispatch-site edits

All four now call `startMapCallback` instead of `startThread`:

| Site | Line | Callback | Before | After |
|------|------|----------|--------|-------|
| Respawn | 819 | coop_playerJustRespawned | `thread coop_mod/main.scr::startThread ( "maps/"+level.coop_mapname+".scr::coop_playerJustRespawned" ) (local.player)` | `thread coop_mod/main.scr::startMapCallback "coop_playerJustRespawned" (local.player)` |
| Spawn | 822 | coop_playerJustSpawned | `thread coop_mod/main.scr::startThread ( "maps/"+level.coop_mapname+".scr::coop_playerJustSpawned" ) (local.player)` | `thread coop_mod/main.scr::startMapCallback "coop_playerJustSpawned" (local.player)` |
| Death | 1071 | coop_playerJustDied | `thread coop_mod/main.scr::startThread ( "maps/"+level.coop_mapname+".scr::coop_playerJustDied" ) (local.player)` | `thread coop_mod/main.scr::startMapCallback "coop_playerJustDied" (local.player)` |
| Left | 129 | coop_playerJustLeft | `thread game.main::startThread ("maps/"+level.coop_mapname+".scr::"+"coop_playerJustLeft") $world` | `thread coop_mod/main.scr::startMapCallback "coop_playerJustLeft" $world` |

Note: the line-129 site previously used `game.main::startThread`; it now uses the same
`coop_mod/main.scr::startMapCallback` path as the others, preserving the `$world` activator.

## 3. Per-map opt-ins (backward-compat)

Every map that DEFINES at least one callback label got the matching opt-in line(s) inserted right
after its `waitthread coop_mod/main.scr::main` call. 25 maps define callbacks; all 25 were opted in.
Each map's opt-in set matches exactly the callbacks it defines (no misses, no extras). No callback
labels exist in any `maps/<map>/` subdirectory script.

| Map | Callbacks defined = opted-in |
|-----|------------------------------|
| e1l1 | Spawned, Left, Respawned |
| e1l2 | Spawned, Left, Respawned |
| e1l3 | Spawned, Left, Respawned |
| e1l4 | Spawned, Left, Respawned |
| e2l1 | Spawned, Left, Respawned |
| e2l2 | Spawned, Left, Respawned |
| e2l3 | Spawned, Left, Respawned |
| e3l1 | Spawned, Left, Respawned |
| e3l2 | Spawned, Left, Respawned |
| e3l3 | Spawned, Left, Respawned |
| e3l4 | Spawned, Left, Respawned |
| t1l2 | Spawned, Left, Respawned |
| t1l3 | Spawned, Left, Respawned |
| t2l1 | Spawned, Left, Respawned |
| t2l2 | Died, Left |
| t2l3 | Spawned, Left, Respawned |
| m1l1 | Spawned |
| m1l2b | Died |
| m1l3b | Respawned, Died, Left |
| M1L3a | Respawned, Died, Left |
| m2l3 | Spawned |
| m3l1a | Spawned |
| m4l3 | Spawned |
| M5L2A | Died |
| m6l3d | Spawned |

Opt-in line form (callback names quoted, value 1):

```
	//[207] opt-in to per-map optional callbacks (guarded dispatch)
	level.coop_hasCallback["coop_playerJustSpawned"] = 1
	level.coop_hasCallback["coop_playerJustLeft"] = 1
	level.coop_hasCallback["coop_playerJustRespawned"] = 1
```

## Notes

- Many e-series and t-series callback labels are empty stubs (`coop_playerJustSpawned: end`). They
  were opted in anyway so their pre-fix behavior (label found, no-op fires) is preserved exactly; the
  m-series labels (m1l1, m1l3b, M1L3a, m1l2b, m2l3, m3l1a, m4l3, M5L2A, m6l3d) and t2l2 carry real
  bodies and continue to fire.
- Files touched: `coop_mod/main.scr`, `coop_mod/player.scr`, and the 25 `maps/*.scr` listed above.
  No other framework file (officer.scr, maptest*.scr, spawn_clicker.ps1, etc.) was modified.
