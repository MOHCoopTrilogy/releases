#!/bin/bash
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py wait alarmplace-r1
cd docs/proposals/alarm_counterattack_2026-10-15/tools
rm -rf runs/flow_*
timeout 420 python ap_flow.py f2 e3l2
for m in m1l1 m2l1; do rm -rf runs/ap_v2$m; timeout 200 python ap_shots.py v2$m $m; done
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py release alarmplace-r1
echo BATCHDONE
