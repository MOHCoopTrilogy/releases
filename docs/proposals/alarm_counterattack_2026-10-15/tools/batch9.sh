#!/bin/bash
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py wait alarmplace-r2
cd docs/proposals/alarm_counterattack_2026-10-15/tools
timeout 400 python ap_ring.py r1 e3l2
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py release alarmplace-r2
echo BATCHDONE
