# Alarm + counter-attack BUILD log (design: DESIGN.md)

## HANDOVER (keep current after every step)
- Worktree: C:\mohaa-coop-dev\hzm-mod-alarm, branch alarm-next (from combo-1.10.29). Harness: tools/cn_run.py <label> <map> (private client G:/mohaa-hudfeed2, see cnlib.py); driver tools/cn_drv.scr.
- Scope (coordinator, user "let me worry about the cap"): all 8 DESIGN build steps, incl. per-map alarm placements for the first batch. m3l1a (Omaha) is dropped from the 12-map list (hard rule: no Omaha).
- DONE: step 1 counter skeleton + waves (coop_mod/coop_counter.scr, hook in missioncomplete.scr, cvars seeded in autoexec.cfg, default OFF).
- NEXT: step 2 proof (sizes/cap), step 3 exclusions (counter_denied list from the ending audit), step 4 alarm module on m4l3, ...

## Steps
1. Counter skeleton: DONE. Proof m1l1 (40 s window): `COUNTER start`, 3 waves of 4 (players=1), `COUNTER end`, then the normal debrief ran.
