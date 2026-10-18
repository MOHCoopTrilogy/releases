#!/bin/bash
# start the probe batch on the first harness copy whose slot is free (poll every 15 s, up to 12 min)
cd /c/mohaa-coop-dev
for i in $(seq 1 48); do
  o=$(python docs/tools/harness_guard.py status 2>&1 | grep -E "^HARNESS|^slot")
  for c in hudfeed4 hudfeed5 hudfeed2; do
    if ! echo "$o" | grep -q "mohaa-$c"; then
      echo "starting on $c"
      export MZ_CLIENT=$c
      cd docs/proposals/mortar_squads_2026-10-18/tools
      python mz_probe.py ${PROBE_LABEL:-p2} ${PROBE_MAPS:-m3l2 m1l3a m1l3b e1l1 e3l2 e3l4}
      echo "probe finished"
      exit 0
    fi
  done
  sleep 15
done
echo "no free client after 12 min"
