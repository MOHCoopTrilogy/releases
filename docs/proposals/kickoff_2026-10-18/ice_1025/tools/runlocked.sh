#!/bin/bash
# runlocked.sh <label> <cmd...>   waits for heavy.lock OR heavy2.lock (atomic take), no user game, no heavy.priority; runs cmd; releases.
D=/c/Users/curry/AppData/Local/Temp/claude
LABEL=$1; shift
GOT=""
while [ -z "$GOT" ]; do
  if [ -f $D/heavy.priority ]; then sleep 10; continue; fi
  if python -c "import sys;sys.path.insert(0,r'C:\mohaa-coop-dev\docs\tools');import harness_guard as h;sys.exit(1 if h.user_game_running() else 0)"; then :; else sleep 20; continue; fi
  for L in $D/heavy.lock $D/heavy2.lock; do
    if [ -f $L ] && [ -n "$(find $L -mmin +40 2>/dev/null)" ]; then rm -f $L; fi
    ( set -o noclobber; echo "ice1025-$LABEL $(date +%Y-%m-%dT%H:%M:%S%:z) $* (<=30min)" > $L ) 2>/dev/null && { GOT=$L; break; }
  done
  [ -z "$GOT" ] && sleep 5
done
echo "$(date +%H:%M:%S) took $GOT"
python /c/mohaa-coop-dev/docs/tools/harness_turn.py wait ice1025
"$@"
echo "$(date +%H:%M:%S) cmd exit $?"
python /c/mohaa-coop-dev/docs/tools/harness_turn.py release ice1025
rm -f $GOT; echo "$(date +%H:%M:%S) released $GOT"
