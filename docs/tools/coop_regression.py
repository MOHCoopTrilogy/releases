#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
coop_regression.py - the co-op regression gate.

WHY THIS EXISTS (2026-08-30)
----------------------------
Eleven self-test batteries ship in `hzm-mohaa-coop-mod/coop_mod/coop_selftest*.scr`
(121 labels, ~4,775 lines). Every one is inert behind its own cvar, and of the 43
harness cfgs on disk NOT ONE armed them - so the suite had never been run as a suite.

Standard-MP work touches shared code: sentient.cpp (the player-vs-player damage
clause), autoexec.cfg, the statemap, global/*.scr. Co-op is the shipping product.
This tool answers one question, cheaply and repeatably:

    "did anything about co-op change when I did that?"

WHY A DIFFER AND NOT AN ASSERTION ENGINE
----------------------------------------
The batteries print MEASUREMENTS (`^~^~^ ENTSTRESS done spawned=...`), not verdicts.
Their PASS criteria live in prose comments inside the scripts. Re-deriving 121
expectations here would produce a second source of truth that drifts from the first -
exactly the failure this project keeps paying for. So instead: capture a fingerprint
of a known-good co-op run, and diff subsequent runs against it. A diff cannot be
subtly wrong about what a battery is "supposed" to say.

WHAT IS IN THE FINGERPRINT
--------------------------
Per marker family (ENTSTRESS, ST_DBNO, RESPAWNKIT, ...):
  * how many lines it emitted
  * the set of KEYS it used (`spawned=`, `weap=`), not their values

Counts and key-sets are stable across identical runs; VALUES are not (entity numbers,
timings, RNG). Comparing values would produce noise that trains you to ignore the tool.
Script Errors are tracked separately and exactly, because there the count IS the signal.

USAGE
    exec coop_mod/cfg/coop_regression.cfg   in-game, start a coop map, let it settle
    python docs/tools/coop_regression.py --baseline    # store a known-good run
    python docs/tools/coop_regression.py --check       # diff the newest run vs baseline
    python docs/tools/coop_regression.py --show        # print the current fingerprint

Exit status for --check: 0 = matches baseline, 1 = co-op changed.
"""

import argparse
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASELINE = os.path.join(ROOT, "docs", "generated", "coop_regression_baseline.json")

# Every place a coop run can leave a log. Newest wins.
LOG_CANDIDATES = [
    os.path.join(os.environ.get("APPDATA", ""), "openmohaa", "maintt", "qconsole.log"),
    r"G:\mohaa-gl2\home\maintt\qconsole.log",
    os.path.join(ROOT, "server_home", "maintt", "qconsole.log"),
]

# A family is an ALL-CAPS token of 2+ chars terminated by whitespace/punctuation.
# The 2-char minimum and the terminator both matter: the engine also prints prose behind
# this prefix ("^~^~^ Add the following line...", "^~^~^ Warning: ..."), and a naive
# [A-Z][A-Z0-9_]* happily reads those as families "A" and "W", which would put engine
# chatter into the fingerprint and make every baseline noisy.
MARKER = re.compile(r"\^~\^~\^ ([A-Z0-9][A-Z0-9_]+)(?=[\s:=,.]|$)(.*)$")
KEY = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)=")
SCRIPT_ERROR = re.compile(r"Script Error|Could not find label|Expecting|ERR_DROP", re.I)


def newest_log(explicit=None):
    if explicit:
        if not os.path.exists(explicit):
            sys.exit("no such log: %s" % explicit)
        return explicit
    found = [p for p in LOG_CANDIDATES if p and os.path.exists(p)]
    if not found:
        sys.exit("no qconsole.log found. Looked in:\n  " + "\n  ".join(c for c in LOG_CANDIDATES if c))
    return max(found, key=os.path.getmtime)


TIMESTAMP = re.compile(r"^\[(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d)")


def _seconds(line):
    """Wall-clock seconds from a qconsole timestamp, or None."""
    m = TIMESTAMP.match(line)
    if not m:
        return None
    y, mo, d, h, mi, s = (int(x) for x in m.groups())
    return ((d * 24 + h) * 60 + mi) * 60 + s


def fingerprint(path, window=None):
    """(families, errors, meta) - counts and key-sets per marker family.

    `window` bounds the capture to N seconds after the FIRST marker line. Without it the
    fingerprint is not reproducible: families like SVFRAME, SQUAD and PRB tick on a timer,
    so their counts scale with how long the session happened to run, and every later check
    would report a diff for a session that merely lasted longer. Bounding the window makes
    counts comparable, which is the whole point of the tool.
    """
    fams = {}
    errors = {}
    total = 0
    t0 = None
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            total += 1
            if window is not None:
                t = _seconds(line)
                if t is not None:
                    if t0 is None and MARKER.search(line):
                        t0 = t
                    if t0 is not None and t - t0 > window:
                        break
            m = MARKER.search(line)
            if m:
                fam, rest = m.group(1), m.group(2)
                e = fams.setdefault(fam, {"lines": 0, "keys": set()})
                e["lines"] += 1
                e["keys"].update(KEY.findall(rest))
                continue
            if SCRIPT_ERROR.search(line):
                # normalise: strip entity numbers and addresses so the same defect
                # collapses to one row instead of N
                k = re.sub(r"\b\d+\b", "N", line.strip())[:160]
                errors[k] = errors.get(k, 0) + 1
    fams = {k: {"lines": v["lines"], "keys": sorted(v["keys"])} for k, v in fams.items()}
    meta = {"log": path, "logLines": total, "families": len(fams), "windowSec": window}
    return fams, errors, meta


def load_baseline():
    if not os.path.exists(BASELINE):
        sys.exit("no baseline yet - run with --baseline first (after a known-good coop run)")
    return json.load(io.open(BASELINE, encoding="utf-8"))


def cmd_baseline(args):
    path = newest_log(args.log)
    fams, errors, meta = fingerprint(path, args.window)
    if not fams:
        sys.exit("that log contains no ^~^~^ markers - did you exec coop_regression.cfg\n"
                 "and set developer 1 before starting the map?  log: %s" % path)
    os.makedirs(os.path.dirname(BASELINE), exist_ok=True)
    io.open(BASELINE, "w", encoding="utf-8").write(
        json.dumps({"meta": meta, "families": fams, "errors": errors}, indent=2, sort_keys=True))
    print("baseline written: %s" % BASELINE)
    print("  from      : %s (%d lines)" % (path, meta["logLines"]))
    print("  families  : %d" % len(fams))
    print("  errors    : %d distinct" % len(errors))


def cmd_show(args):
    fams, errors, meta = fingerprint(newest_log(args.log), args.window)
    print("log: %s (%d lines)" % (meta["log"], meta["logLines"]))
    for f in sorted(fams):
        print("  %-22s %4d lines  keys: %s" % (f, fams[f]["lines"], ",".join(fams[f]["keys"]) or "-"))
    if errors:
        print("\n  script errors:")
        for k, n in sorted(errors.items(), key=lambda x: -x[1]):
            print("    x%-4d %s" % (n, k))


def cmd_check(args):
    base = load_baseline()
    fams, errors, meta = fingerprint(newest_log(args.log), base["meta"].get("windowSec"))
    bf, be = base["families"], base.get("errors", {})
    problems = []

    for f in sorted(set(bf) | set(fams)):
        if f not in fams:
            problems.append("GONE      %-20s baseline emitted %d lines, this run emitted none"
                            % (f, bf[f]["lines"]))
        elif f not in bf:
            problems.append("NEW       %-20s %d lines (not in baseline)" % (f, fams[f]["lines"]))
        else:
            if fams[f]["lines"] != bf[f]["lines"]:
                problems.append("COUNT     %-20s %d -> %d lines"
                                % (f, bf[f]["lines"], fams[f]["lines"]))
            lost = set(bf[f]["keys"]) - set(fams[f]["keys"])
            gained = set(fams[f]["keys"]) - set(bf[f]["keys"])
            if lost:
                problems.append("KEYS-LOST %-20s %s" % (f, ",".join(sorted(lost))))
            if gained:
                problems.append("KEYS-NEW  %-20s %s" % (f, ",".join(sorted(gained))))

    for k in sorted(set(errors) | set(be)):
        b, n = be.get(k, 0), errors.get(k, 0)
        if n > b:
            problems.append("ERROR+    x%d (was x%d)  %s" % (n, b, k))

    print("baseline: %s" % base["meta"]["log"])
    print("this run: %s (%d lines)" % (meta["log"], meta["logLines"]))
    if not problems:
        print("\nOK - co-op fingerprint matches baseline (%d families, no new script errors)."
              % len(fams))
        return 0
    print("\nCO-OP CHANGED - %d difference(s):\n" % len(problems))
    for p in problems:
        print("  " + p)
    print("\nA difference is not automatically a regression - a deliberate coop change moves")
    print("these too. Read each one, and re-baseline once you have decided it is correct.")
    return 1


def main():
    ap = argparse.ArgumentParser(description="co-op regression gate: diff a run against a known-good baseline")
    ap.add_argument("--window", type=int, default=180,
                    help="seconds after the first marker to consider (default 180). --check reuses the BASELINE's window so the two are always comparable.")
    ap.add_argument("--log", help="explicit qconsole.log (default: newest of the known locations)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--baseline", action="store_true", help="store this run as the known-good baseline")
    g.add_argument("--check", action="store_true", help="diff this run against the baseline (exit 1 on change)")
    g.add_argument("--show", action="store_true", help="print this run's fingerprint")
    a = ap.parse_args()
    if a.baseline:
        return cmd_baseline(a) or 0
    if a.show:
        return cmd_show(a) or 0
    return cmd_check(a)


if __name__ == "__main__":
    sys.exit(main())
