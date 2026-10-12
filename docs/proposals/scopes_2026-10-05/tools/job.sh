#!/bin/sh
# job.sh <command...> - ONE game run: heavy lock + test slot "hudfeed" around it; both given back on any exit
S="C:/Users/curry/AppData/Local/Temp/claude/C--mohaa-coop-dev/7ee3b4ee-deea-4563-b7bc-c7746a82f4e9/scratchpad"
sh "$S/heavy_lock.sh" acquire scopes
cleanup() {
  if [ "$(cat "$S/test_slot.txt")" = "hudfeed" ] && [ -f "$S/scopes/slot_mine" ]; then printf free > "$S/test_slot.txt"; fi
  rm -f "$S/scopes/slot_mine"
  sh "$S/heavy_lock.sh" release scopes
}
trap cleanup EXIT
while [ "$(cat "$S/test_slot.txt")" != "free" ]; do sleep 5; done
printf hudfeed > "$S/test_slot.txt"
touch "$S/scopes/slot_mine"
"$@"
echo "job rc=$?"
