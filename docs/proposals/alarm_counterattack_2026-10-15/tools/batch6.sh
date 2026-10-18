#!/bin/bash
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py wait alarmplace
cd docs/proposals/alarm_counterattack_2026-10-15/tools
rm -rf runs/flow_*
timeout 420 python ap_flow.py f2 e3l2
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py release alarmplace
echo BATCHDONE
