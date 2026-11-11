# bug-10899 - FG 42 crash (v1.10.73), fg42fix

Cause, fix and gate: see .wolf/buglog.json bug-10899 and tools/merge_anims_shared.py / apply_fg42fix.py /
docs/tools/check_anim_aliases.py.

## In-game results (private client G:/mohaa-fg42fix, release v1.10.73/74 exe + dlls, fix = an overlay with the merged
anims_shared.txt sorting last; tools/run_fg42.py)

| mode | fix | variants | reloads | state loop | 'unknown anim command' lines |
|---|---|---|---|---|---|
| co-op, Armory (w39 / fin1 / fin44 / w79 / fin6) | no | crash at the first FG 42 | - | Server crashed: possible infinite state loop | 41,756 |
| co-op, Armory | yes | FG 42, Gold, Splinter, Irons, Irons Winter | 20 | none | 0 |
| SP m1l2a, give (7: base, gold, winter, DAK, irons, irons bloody, irons Telo) | yes | 7 | 28 (magazine in hand, MAGS counting down) | none | 0 |
| MP dm/mohdm1, give (same 7) | yes | 7 | 28 | none | 0 |
| SP m1l2a | no | - | - | the client process exits during the map load, 8 of 8 tries (584 parse errors logged first) | 584 |

SP with the fix exited at load 2 of 8 tries at the same point (after SHADOWFIT W-BAKE) - a separate SP-load flake on
this client, not this bug. Evidence stills: evidence/*.jpg.

Harness traps found: a `*.pk3.off` in the homepath is STILL loaded as a pak (the first no-fix control silently had the fix);
SP/MP `give` needs `thereisnomonkey 1` (entity.cpp zeroes cheats on every cheat command otherwise); SP needs
`finishloadingscreen`; MP needs `join_team` + a spawn; `give all` for spare magazines.
