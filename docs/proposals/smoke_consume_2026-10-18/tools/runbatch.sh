#!/bin/bash
# ONE harness batch: wait for the shared turn, run binoc3 + drops3, release (even on failure)
cd "$(dirname "$0")"
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py wait smokec
cd docs/proposals/smoke_consume_2026-10-18/tools

timeout 600 python sm_sess.py new_drops4 m3l2 drops > run_new_drops4.out 2>&1
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py release smokec
echo BATCHDONE
