#!/bin/bash
# runloop.sh <run> : ONE fair-queue turn (harness_turn.py gunfit); inside it try harness pairs until one is not SlotBusy
cd /c/mohaa-coop-dev/docs/proposals/loadout_review_2026-10-15
R=$1; O=/c/Users/curry/AppData/Local/Temp/$R.out
python ../../tools/harness_turn.py wait gunfit
for P in 5,4 2,4 2,5 4,5 2,3 3,5; do
  HZPAIR=$P FITJOBS=$PWD/${JOBS:-fit3_jobs_$R.json} python -u ${PROG:-run_fit3.py} $R > $O 2>&1
  grep -q "fit screenshots" $O && break
  grep -q SlotBusy $O || break
done
python ../../tools/harness_turn.py release gunfit
grep -q "fit screenshots" $O && echo ok || echo FAILED
