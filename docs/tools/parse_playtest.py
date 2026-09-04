#!/usr/bin/env python
"""
parse_playtest.py - read a playtest qconsole.log and say what actually RAN.

WHY THIS EXISTS
    This project's most expensive recurring failure is the silent veto: a feature that is wired,
    plausible, and has never once executed. Reading the code cannot tell you which of the ~138
    Omaha labels fired; the log can, because most of them end in a `println("^~^~^ MARKER ...")`.
    This diffs the markers PRESENT IN THE SOURCE against the markers PRESENT IN THE LOG, so
    "absent" is a measured result rather than an impression.

TWO TRAPS IT ENCODES, each of which produced a wrong answer before it was written:

  1. `grep '^~^~^'` IS NOT A MOD-MARKER GREP. The ENGINE prints the same token for at least eleven
     warning families (Script Error, Not playing sound, Add the following line, Bad model name,
     TIKI_InitTiki, Animation duplicate channel, ...). A naive sweep invents phantom subsystems
     with names like "Add" and "Attack". A real mod marker is an ALL-CAPS token, so that is what
     this requires - and it prints the rejected tokens so the filter can never silently over-trim.

  2. SCRIPT MARKERS ARE DEVELOPER-GATED. ScriptThread::Println returns early when developer == 0
     (scriptthread.cpp:2869). On this install `developer 1` comes ONLY from PLAY-GL2.bat's command
     line: autoexec.cfg:39 is `seta developer 0` and autoexec execs LAST (common.c:1862), after
     configs/omconfig.cfg. So a log captured from any other launcher has NO mod markers at all,
     and every subsystem would read as "absent". This refuses to report if it cannot see evidence
     that developer was on.

USAGE
    python docs/tools/parse_playtest.py
    python docs/tools/parse_playtest.py --log <path> --map m3l1a
"""
import argparse, io, os, re, sys
from collections import Counter, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
DEFAULT_LOG = r"G:\mohaa-gl2\home\maintt\qconsole.log"

MARKER_RE = re.compile(r"\^~\^~\^\s+([A-Z][A-Z0-9_]{2,})\b")
SRC_MARKER_RE = re.compile(r'"\s*\^~\^~\^\s+([A-Z][A-Z0-9_]{2,})')


def read(path):
    with io.open(path, "r", encoding="latin-1", errors="replace") as fh:
        return fh.read()


def source_markers(mapname):
    """Every ALL-CAPS marker the map's own scripts can emit."""
    found = {}
    for rel in (
        os.path.join("maps", mapname + ".scr"),
        os.path.join("maps", mapname, "coopified.scr"),
        os.path.join("maps", mapname, "obstacles.scr"),
    ):
        p = os.path.join(MOD, rel)
        if not os.path.isfile(p):
            continue
        for i, line in enumerate(read(p).splitlines(), 1):
            for m in SRC_MARKER_RE.finditer(line):
                found.setdefault(m.group(1), (rel, i))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=DEFAULT_LOG)
    ap.add_argument("--map", default="m3l1a")
    args = ap.parse_args()

    if not os.path.isfile(args.log):
        print("no log at " + args.log)
        return 2
    text = read(args.log)
    lines = text.splitlines()
    print("log   : %s  (%s lines, %.1f MB)" % (args.log, format(len(lines), ","), os.path.getsize(args.log) / 1048576.0))

    # ---- trap 2: prove script println could reach the log at all -------------
    log_markers = Counter(MARKER_RE.findall(text))
    src = source_markers(args.map)
    seen_mod = sum(v for k, v in log_markers.items() if k in src)
    if not seen_mod:
        print("\n*** NO MOD MARKERS AT ALL. Do not read anything below as 'the feature did not run'.")
        print("*** Script println is developer-gated (scriptthread.cpp:2869) and autoexec.cfg:39 sets")
        print("*** `seta developer 0`. Launch via PLAY-GL2.bat, which passes +set developer 1.")
        return 1

    # ---- which subsystems ran ------------------------------------------------
    ran = OrderedDict()
    absent = OrderedDict()
    for name in sorted(src):
        n = log_markers.get(name, 0)
        (ran if n else absent)[name] = (n, src[name])

    print("\n=== SUBSYSTEMS THAT RAN (%d of %d markers defined for %s) ===" % (len(ran), len(src), args.map))
    for name, (n, where) in ran.items():
        print("  %-22s x%-5d  %s:%d" % (name, n, where[0], where[1]))

    print("\n=== DEFINED BUT NEVER EMITTED (%d) - each is a silent-veto candidate ===" % len(absent))
    for name, (_, where) in absent.items():
        print("  %-22s        %s:%d" % (name, where[0], where[1]))

    # engine tokens we deliberately ignore - printed so the filter cannot silently over-trim
    other = {k: v for k, v in log_markers.items() if k not in src}
    if other:
        print("\n=== non-mod ^~^~^ tokens seen (engine warnings; NOT subsystems) ===")
        print("  " + ", ".join("%s x%d" % (k, v) for k, v in sorted(other.items(), key=lambda kv: -kv[1])[:18]))

    # ---- this session's specific fixes --------------------------------------
    print("\n=== THIS SESSION'S FIXES ===")
    low = text.lower()

    n_lead = low.count("exp_leadin_0")
    print("  naval report (bug-2393)   : %d exp_leadin_* sound line(s)" % n_lead)
    print("      (needs s_show_sounds 1 to appear at all; 0 with it OFF proves nothing)")

    grill = len(re.findall(r"snd_step_grill needs an alias", text))
    print("  metal footsteps (bug-2394): %d 'snd_step_grill needs an alias' (was 4 pre-fix; expect 0)" % grill)

    cap = re.findall(r"(?i)(s_startsound:[^\n]*dfr_scripted_m3l1_\S+|openal: 2d[^\n]*dfr_scripted_m3l1_\S+)", text)
    print("  captain VO (bug-2395)     : %d probe line(s) for m3l1 dialogue" % len(cap))
    for c in cap[:12]:
        print("      " + c.strip()[:150])
    if not cap:
        print("      -> either voprobe.cfg was not exec'd BEFORE the map loaded, or the client never")
        print("         requested the sound. Those are different answers; re-run with the probe armed.")

    # ---- health --------------------------------------------------------------
    print("\n=== HEALTH ===")
    for label, pat in (
        ("Script Error", r"Script Error"),
        ("needs an alias", r"needs an alias"),
        ("Not playing sound (per-sfx cap 10)", r"Not playing sound"),
        ("Couldn't play (CHANNEL STARVATION)", r"Couldn't play"),
        ("missing precache", r"Add the following line"),
        ("not properly loaded (PARSE KILL)", r"not properly loaded"),
    ):
        print("  %-38s %d" % (label, len(re.findall(pat, text))))

    errs = Counter(re.findall(r"Script Error : ([^\n(]{0,70})", text))
    if errs:
        print("\n  script-error shapes:")
        for k, v in errs.most_common(10):
            print("    x%-4d %s" % (v, k.strip()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
