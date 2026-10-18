#!/bin/bash
# runs the proof sessions one at a time, each only when no harness openmohaa/omohaaded process exists
cd "$(dirname "$0")"
run() {  # label map flow [SMREF]
  while [ -n "$(tasklist | grep -i -E 'openmohaa|omohaaded')" ]; do sleep 8; done
  SMREF="$4" timeout 900 python sm_sess.py "$1" "$2" "$3" > "run_$1.out" 2>&1
  echo "done $1"
}
run old2 m3l2 smoke coop-wip
run new_smoke m3l2 smoke ""
run new_unused m3l2 unused ""
run new_binoc m3l2 binoc ""
run new_drops m3l2 drops ""
echo ALLDONE
