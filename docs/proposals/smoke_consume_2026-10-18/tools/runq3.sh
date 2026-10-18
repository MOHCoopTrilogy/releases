#!/bin/bash
cd "$(dirname "$0")"
until grep -q ALLDONE2 runq2.out 2>/dev/null; do sleep 10; done
while [ -n "$(tasklist | grep -i -E 'openmohaa|omohaaded')" ]; do sleep 8; done
timeout 900 python sm_sess.py new_binoc3 m3l2 binoc > run_new_binoc3.out 2>&1
echo ALLDONE3
