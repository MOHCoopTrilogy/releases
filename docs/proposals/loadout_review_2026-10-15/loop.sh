#!/bin/bash
# loop.sh <firstRound> <lastRound> : probe3 -> harness -> refine3 per round
cd /c/mohaa-coop-dev/docs/proposals/loadout_review_2026-10-15
for n in $(seq $1 $2); do
  python fit3.py probe3 j.json >/dev/null && mv j.json fit3_jobs_r$n.json
  ./runloop.sh r$n >/dev/null 2>&1
  python fit3.py refine3 r$n T 2>&1 | head -1
done
echo LOOPDONE
