for m in m1l2a m1l2b m1l3a m1l3b; do
  python -c "
import sys;sys.path.insert(0,'C:/mohaa-coop-dev/docs/tools')
import harness_guard as hg;r=hg.user_game_running();sys.exit(1 if r else 0)" || { echo "user playing - stop"; break; }
  timeout 280 python propscan.py $m
done
