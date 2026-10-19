#!/bin/bash
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py wait alarmplace-carry11
cd docs/proposals/alarm_counterattack_2026-10-15/tools
timeout 800 python ap_carry.py c11 m4l1 m4l2 0
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py release alarmplace-carry11
echo BATCHDONE
