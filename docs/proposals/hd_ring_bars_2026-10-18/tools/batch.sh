#!/bin/sh
# one harness turn: hd + old on a bright and a dark map (hd first, GIF frames come from the hd runs)
cd /c/mohaa-coop-dev/docs/proposals/hd_ring_bars_2026-10-18/tools
python /c/mohaa-coop-dev/docs/tools/harness_turn.py wait hdring
trap 'python /c/mohaa-coop-dev/docs/tools/harness_turn.py release hdring' EXIT
mkdir -p /g/mohaa-hdring-out
R=/g/mohaa-hdring-out
python hd_run.py hd_new_m3l2 --look hd --map m3l2 > $R/hd_new_m3l2.log 2>&1
python hd_run.py hd_old_m3l2 --look old --map m3l2 > $R/hd_old_m3l2.log 2>&1
python hd_run.py hd_new_m1l1 --look hd --map m1l1 --nogive > $R/hd_new_m1l1.log 2>&1
python hd_run.py hd_old_m1l1 --look old --map m1l1 --nogive > $R/hd_old_m1l1.log 2>&1
echo ok > $R/final.done
