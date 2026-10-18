#!/bin/bash
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py wait alarmplace
cd docs/proposals/alarm_counterattack_2026-10-15/tools
for m in m1l1 m4l1 m1l2a m2l1 m3l2 m5l1a; do timeout 200 python ap_cz.py cz$m $m; done
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py release alarmplace
echo BATCHDONE
