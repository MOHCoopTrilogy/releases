#!/usr/bin/env python3
"""ea_aiaudit - docs/tools/byoaudit/aiaudit.py for coop_ea_1_11, with one difference: a cursor clip whose rectangle
lies OUTSIDE the test display (the 1080p second screen our private client is on) is the user's own game clipping
its cursor while it has the foreground - theirs, not ours - so it is logged and ignored instead of ending the run.
Any other guard violation (a clip on our display, foreground, placement, capture) still stops the run at once.
Our code; logs it writes are local only.

  python ea_aiaudit.py <outdir> [mission|faceoff] [--minutes 24]
"""
import json
import os
import sys

BYO = os.environ.get("BYOAUDIT", r"C:\hzm-root-flpolish\docs\tools\byoaudit")
sys.path.insert(0, BYO)
os.environ.setdefault("BYO_CLIENT", r"G:\mohaa-ea")
# our own port block (flpolish uses 12470): on the shared default 12391 its clients joined our server (17:15, 2026-11-10)
os.environ.setdefault("BYO_SRVPORT", "12480")
import byoclient  # noqa: E402
import aiaudit    # noqa: E402

IGNORED = []


def _theirs(v):
    if v.get("kind") != "cursor_clip" or "rect" not in v:
        return False
    try:
        d = byoclient.hw.test_display()
    except Exception:
        return False
    l, t, r, b = d["rect"]
    x0, y0, x1, y1 = v["rect"]
    return x1 <= l or x0 >= r or y1 <= t or y0 >= b


def check(self):
    v = getattr(getattr(self.c, "watcher", None), "violations", None)
    if v:
        mine = [x for x in v if not _theirs(x)]
        for x in v:
            if _theirs(x) and x not in IGNORED:
                IGNORED.append(x)
        if mine:
            raise byoclient.GuardTrip(repr(mine[:3]))
        v.clear()
    if self.c is not None and self.c.proc.poll() is not None:
        raise RuntimeError("client exited")


byoclient.Client.check = check

if __name__ == "__main__":
    out = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "mission"
    mins = float(sys.argv[sys.argv.index("--minutes") + 1]) if "--minutes" in sys.argv else 24.0
    rep = aiaudit.run("coop_ea_1_11", out, mode, 1, "1", mins, "ea")
    rep["ignored_user_clips"] = len(IGNORED)
    json.dump(rep, open(os.path.join(out, "aiaudit.json"), "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in rep.items() if k not in ("idle_list", "spawn_lines")}, indent=1, default=str))
