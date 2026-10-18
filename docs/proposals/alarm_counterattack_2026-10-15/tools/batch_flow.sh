#!/bin/bash
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py wait alarmplace
cd docs/proposals/alarm_counterattack_2026-10-15/tools
python ap_flow.py f1 e3l1
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py release alarmplace
echo BATCHDONE
