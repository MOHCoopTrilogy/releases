"""sr_sim.py - Monte Carlo tally of surrenders over one map run, OLD rule vs NEW rule (a MODEL, not a game log).
Assumptions (stated, tunable): a map run has SQUADS squads; the last survivor of each squad is reached once;
squads fall every ~40 s with jitter; P_HURT = chance the lone survivor is below the hp gate when reached (most
Germans die in one or two hits); P_NEAR = a player is within 1000u; P_OFF = a live officer within 1500u."""
import random
SQUADS, P_HURT, P_NEAR, P_OFF, RUNS = 14, 0.25, 0.85, 0.20, 20000
def run(new):
    t, n, nxt, cnt = 0.0, 0, 0.0, 0
    for _ in range(SQUADS):
        t += random.uniform(20, 60)
        if not new:
            cnt += random.random() < 0.35; continue
        if cnt >= 3 or t < nxt: continue
        if random.random() > P_HURT or random.random() > P_NEAR or random.random() < P_OFF: continue
        if random.random() < 0.12: cnt += 1; nxt = t + 60
    return cnt
random.seed(7)
for name, new in (("OLD (35% per lone survivor, no cap)", 0), ("NEW (12% + hp/range/officer gates, cap 3, 60s cd)", 1)):
    r = [run(new) for _ in range(RUNS)]
    print("%-52s mean %.2f surrenders/run, P(>=1)=%.0f%%, max %d" % (name, sum(r)/RUNS, 100*sum(1 for x in r if x)/RUNS, max(r)))
