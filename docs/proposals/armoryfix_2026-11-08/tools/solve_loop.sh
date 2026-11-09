#!/bin/sh
# solve_loop.sh <mode> <first round> <last round>: render + solve until no jobs remain
m=$1; r=$2
while [ $r -le $3 ]; do
  n=$(python -c "import json;print(len(json.load(open('jobs_${m}_$r.json'))))")
  [ "$n" = "0" ] && break
  python fit_render.py run $m jobs_${m}_$r.json hf_${m}_$r > /dev/null 2>&1
  HF_MODE=$m python armory_fit.py solve H:/hzm_work/wpnviewer/runs/hf_${m}_$r jobs_${m}_$((r+1)).json | head -1
  r=$((r+1))
done
echo "$m loop done at round $r"
