"""Fair FIFO turn-taking for the shared test harnesses (G:\\mohaa-hudfeed*).

At most SLOTS games run at a time, each in its own harness copy. Agents take a ticket, wait until theirs is the
oldest live ticket, run ONE batch (max HOLD_MIN minutes), then release.

    python docs/tools/harness_turn.py wait <name>      # blocks until it is your turn
    python docs/tools/harness_turn.py release <name>   # always call when your batch ends
    python docs/tools/harness_turn.py status

Tickets older than HOLD_MIN (holder) or QUEUE_MAX_H (waiter, never polled) are stale
and skipped, so a crashed agent cannot block the queue.
"""
import os, sys, time, json

QDIR = r"C:\mohaa-coop-dev\.harness_queue"
SLOTS = 2              # games allowed at once (user 2026-10-18); each holder must use a different harness copy via harness_guard.py
HOLD_MIN = 15          # max minutes per turn
QUEUE_MAX_H = 6        # waiter ticket considered dead if not refreshed for this long
POLL_S = 5


def _tickets():
    out = []
    for f in os.listdir(QDIR):
        if not f.endswith(".json"):
            continue
        p = os.path.join(QDIR, f)
        try:
            with open(p, encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:
            continue
        d["_path"] = p
        out.append(d)
    out.sort(key=lambda d: d["ticket"])
    return out


def _live(d, now):
    if d.get("holding_since"):
        return now - d["holding_since"] < HOLD_MIN * 60
    return now - d.get("seen", d["ticket"]) < QUEUE_MAX_H * 3600


def _write(d):
    p = d.pop("_path", None) or os.path.join(QDIR, f"{d['ticket']:.6f}_{d['name']}.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(d, fh)
    d["_path"] = p


def wait(name):
    os.makedirs(QDIR, exist_ok=True)
    mine = next((d for d in _tickets() if d["name"] == name), None)
    if mine is None:
        mine = {"name": name, "ticket": time.time(), "seen": time.time()}
        _write(mine)
    while True:
        now = time.time()
        mine["seen"] = now
        _write(mine)
        live = [d for d in _tickets() if _live(d, now)]
        if name in [d["name"] for d in live[:SLOTS]]:
            mine["holding_since"] = now
            _write(mine)
            print(f"TURN {name}: go (max {HOLD_MIN} min, then release). Up to {SLOTS} games may run: use a harness copy whose harness_guard slot is FREE (hudfeed2/4/5); SlotBusy on one -> try the next.")
            return
        ahead = [d["name"] for d in live if d["ticket"] < mine["ticket"]]
        print(f"WAIT {name}: ahead={ahead}", flush=True)
        time.sleep(POLL_S)


def release(name):
    for d in _tickets():
        if d["name"] == name:
            os.replace(d["_path"], d["_path"] + ".done")
    print(f"RELEASED {name}")


def status():
    now = time.time()
    for d in _tickets():
        state = "HOLD" if d.get("holding_since") else "wait"
        print(f"{state} {d['name']} live={_live(d, now)} age={int(now - d['ticket'])}s")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"wait": lambda: wait(sys.argv[2]), "release": lambda: release(sys.argv[2]),
     "status": status}[cmd]()
