#!/bin/bash
# waits for the heavy.lock protocol, then takes BEFORE stills (in-game gl2) of the ice and the pens water. Log: chain_before.log
cd "$(dirname "$0")"
L=/c/Users/curry/AppData/Local/Temp/claude/heavy.lock
log(){ echo "$(date +%H:%M:%S) $*" >> chain_before.log; }
while true; do
  while [ -f $L ] && [ -z "$(find $L -mmin +40 2>/dev/null)" ]; do sleep 20; done
  log "lock free; 3 min gap"; sleep 180
  [ -f $L ] && { log "retaken, waiting again"; continue; }
  if python -c "import sys;sys.path.insert(0,r'C:\mohaa-coop-dev\docs\tools');import harness_guard as h;sys.exit(1 if h.classify() else 0)"; then break; fi
  log "a game is running, waiting"; sleep 60
done
echo "ice1025-before $(date +%Y-%m-%dT%H:%M:%S%:z) 4 in-game BEFORE sessions via ice_ingame.py (<=30min)" > $L
log "took lock"
python /c/mohaa-coop-dev/docs/tools/harness_turn.py wait ice1025 >> chain_before.log 2>&1
for job in "m6l2a a0,a9" "m6l2b b13,b4" "m2l2a pa0,pa9" "m2l2b pb0,pbcut1,pbfin"; do
  set -- $job; log "run $1 $2"
  python ice_ingame.py $1 $2 --tag before >> chain_before.log 2>&1 || log "FAILED $1"
done
python /c/mohaa-coop-dev/docs/tools/harness_turn.py release ice1025 >> chain_before.log 2>&1
rm -f $L; log "released lock; done"; touch chain_before.done
