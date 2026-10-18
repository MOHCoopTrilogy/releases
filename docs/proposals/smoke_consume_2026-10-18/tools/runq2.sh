#!/bin/bash
cd "$(dirname "$0")"
run() {
  while [ -n "$(tasklist | grep -i -E 'openmohaa|omohaaded')" ]; do sleep 8; done
  SMREF="$4" timeout 1100 python sm_sess.py "$1" "$2" "$3" > "run_$1.out" 2>&1
  echo "done $1"
}
run new_binoc2 m3l2 binoc ""
run new_drops2 m3l2 drops ""
echo ALLDONE2
