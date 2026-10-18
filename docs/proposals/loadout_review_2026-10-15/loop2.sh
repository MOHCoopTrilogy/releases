#!/bin/bash
# loop2.sh <first> <last> <ids> : probe3 on a subset -> one fair-queue turn -> refine3 T
cd /c/mohaa-coop-dev/docs/proposals/loadout_review_2026-10-15
for n in $(seq $1 $2); do
  python fit3.py probe3 j.json $3 >/dev/null && mv j.json fit3_jobs_r$n.json
  ./runloop.sh r$n >/dev/null 2>&1
  python fit3.py refine3 r$n T 2>&1 | head -2
done
echo LOOPDONE
