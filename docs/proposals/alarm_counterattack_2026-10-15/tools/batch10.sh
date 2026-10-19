#!/bin/bash
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py wait alarmplace-carry
cd docs/proposals/alarm_counterattack_2026-10-15/tools
timeout 780 python ap_carry.py c1
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py release alarmplace-carry
echo BATCHDONE
