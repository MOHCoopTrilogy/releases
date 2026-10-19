#!/bin/bash
# usage: runbatch.sh <runner.py> <label> [stages]   (waits for the fair-queue turn, runs ONE batch, releases)
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py wait objectives
cd docs/proposals/objectives_ch1-3_2026-10-18/tools
timeout 840 python "$@"
cd /c/mohaa-coop-dev
python docs/tools/harness_turn.py release objectives
echo BATCHDONE
