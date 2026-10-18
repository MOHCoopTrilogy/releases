#!/bin/bash
# zone shots for the first six maps + alarm placements part 1 (one turn, <= 15 min of game time)
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py wait alarmplace
cd docs/proposals/alarm_counterattack_2026-10-15/tools
for m in $@; do
  case $m in cz*) timeout 200 python ap_cz.py ${m} ${m#cz};; ap*) timeout 200 python ap_shots.py v2${m#ap} ${m#ap};; esac
done
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py release alarmplace
echo BATCHDONE
