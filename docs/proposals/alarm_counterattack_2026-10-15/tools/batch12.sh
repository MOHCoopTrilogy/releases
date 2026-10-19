#!/bin/bash
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py wait alarmplace-carry12
cd docs/proposals/alarm_counterattack_2026-10-15/tools
timeout 800 python ap_carry.py c12 e3l2 m1l1 0
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py release alarmplace-carry12
echo BATCHDONE
