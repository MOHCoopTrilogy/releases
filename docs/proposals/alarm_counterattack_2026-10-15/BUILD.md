# Alarm + counter-attack BUILD log (design: DESIGN.md)

## HANDOVER (keep current after every step)
- Worktree: C:\mohaa-coop-dev\hzm-mod-alarm, branch alarm-next (from combo-1.10.29). Harness: tools/cn_run.py <label> <map> (private client G:/mohaa-hudfeed2, see cnlib.py); driver tools/cn_drv.scr.
- Scope (coordinator, user "let me worry about the cap"): all 8 DESIGN build steps, incl. per-map alarm placements for the first batch. m3l1a (Omaha) is dropped from the 12-map list (hard rule: no Omaha).
- DONE: steps 1-3 counter-attack (coop_mod/coop_counter.scr, hook in missioncomplete.scr, cvars seeded in autoexec.cfg, default OFF).
- NEXT: step 4 alarm module (coop_mod/alarm.scr) on m4l3 via global/alarmer.scr hooks, then 5 generator + m1l1, 6 rollout (11 maps, no m3l1a), 7 stealth regression, 8 defaults stay 0 (playtest by user).

## Steps
1. Counter skeleton: DONE. Proof m1l1 (40 s window): `COUNTER start`, 3 waves of 4 (players=1), `COUNTER end`, then the normal debrief ran.
2. Waves/sizes/cap: DONE. counter_wavesize 1,2,3,4,5,8 -> 4,4,6,6,8,8; cap 6 test: wave1 4, wave2 trimmed to 2, wave3 skipped (cap 6 alive 6); 0 script errors; map transitioned to m1l2a after the debrief.
3. Exclusions: DONE. counter_denied list (22 maps, audited from each map's mission-end call site; reasons in the file header), plus stealth/disguise/noCounter/maptest/lobby/briefing/mp, and a restart guard (nextlevel == same map, e.g. m5l3 failure reload, or "void"). Gate table run on 30 names: 12 allowed (m1l1 m4l1 m1l2a m2l1 m3l2 m5l1a m6l3b t1l2 t2l1 t3l1 e3l1 e3l2), 18 denied/lobby/briefing; stealth flag -> "stealth"; coop_counter 0 -> "off". Real fire on m4l1 (second map). m2l2a real boot not possible in the harness (player never spawned); denied by name + stealth flag instead.
