#!/bin/bash
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py wait alarmplace
cd docs/proposals/alarm_counterattack_2026-10-15/tools
for m in m6l3b t1l2 t2l1 t3l1 e3l1 e3l2; do timeout 200 python ap_cz.py cz$m $m; done
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py release alarmplace
python docs/tools/harness_turn.py wait alarmplace
cd docs/proposals/alarm_counterattack_2026-10-15/tools
for m in e3l1 e3l2 m1l1 m2l1 m3l2 m4l1 m4l2 t1l1 t3l1; do timeout 200 python ap_shots.py v2$m $m; done
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py release alarmplace
echo BATCHDONE
