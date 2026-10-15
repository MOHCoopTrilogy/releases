#!/bin/bash
# usage: batch_scout.sh map1 map2 ...   (each: boot, auto-place, prove the chain)
cd /c/mohaa-coop-dev/docs/proposals/alarm_counterattack_2026-10-15/tools
export CNFILES=coop_mod/alarm.scr,coop_mod/alarmpoints.scr,coop_mod/coop_counter.scr,coop_mod/main.scr,coop_mod/missioncomplete.scr
for m in "$@"; do
  timeout 800 python -I cn_scout.py sc_$m $m > logs/sc_$m.out 2>&1
  echo "done $m" >> logs/batch.log
done
echo "batch finished" >> logs/batch.log
