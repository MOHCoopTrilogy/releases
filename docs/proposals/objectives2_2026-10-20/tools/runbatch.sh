#!/bin/bash
# usage: runbatch.sh <runner.py> <label> [stages]   (waits for the fair-queue turn, runs ONE batch, releases)
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py wait objectives2
cd docs/proposals/objectives2_2026-10-20/tools
timeout 840 python "$@"
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py release objectives2
echo BATCHDONE
