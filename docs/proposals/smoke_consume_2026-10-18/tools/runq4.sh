#!/bin/bash
cd "$(dirname "$0")"
until grep -q ALLDONE3 runq3.out 2>/dev/null; do sleep 10; done
while [ -n "$(tasklist | grep -i -E 'openmohaa|omohaaded')" ]; do sleep 8; done
SMBOTS=1 timeout 1100 python sm_sess.py new_drops3 m3l2 drops > run_new_drops3.out 2>&1
echo ALLDONE4
