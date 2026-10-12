#!/bin/sh
# go.sh <session> <run_2h.py args...>   one harness run under the heavy lock + the test slot protocol
S="C:/Users/curry/AppData/Local/Temp/claude/C--mohaa-coop-dev/7ee3b4ee-deea-4563-b7bc-c7746a82f4e9/scratchpad"
SESS="$1"
sh "$S/heavy_lock.sh" acquire adsanim
# the slot must read free before we take it (another harness may still be finishing)
n=0
while [ "$(tr -d '\r\n ' < "$S/test_slot.txt")" != "free" ]; do
  sleep 10; n=$((n+1))
  if [ $n -gt 90 ]; then echo "slot never freed: $(cat "$S/test_slot.txt")"; sh "$S/heavy_lock.sh" release adsanim; exit 1; fi
done
printf 'adsbolt' > "$S/test_slot.txt"
python "$S/ads2h/run_2h.py" "$@" > "$S/ads2h/$SESS.out" 2>&1
rc=$?
# run_2h writes free itself; make sure of it even if python died before its finally
if [ "$(tr -d '\r\n ' < "$S/test_slot.txt")" = "adsbolt" ]; then printf 'free' > "$S/test_slot.txt"; fi
sh "$S/heavy_lock.sh" release adsanim
echo "run $SESS rc=$rc"
tail -5 "$S/ads2h/$SESS.out"
