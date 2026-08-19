#!/usr/bin/env python
"""ui_wiring_audit.py - does every UI wire terminate somewhere real?

The classes this catches, each of which shipped as a live bug at least once:
  1. EXEC CLOSURE   - every `exec ui/....cfg` (in cfgs, urcs, or script stufftext) must point
                      at a file that exists, with the exact case (Windows hides case drift;
                      a Linux dedicated server does not).
  2. VSTR CLOSURE   - every `vstr coop_lo*/coop_sr*/coop_ui*` must name a cvar that SOMETHING
                      assigns (set/seta in a cfg or urc, a stufftext in a script, or the
                      engine). An unassigned vstr is a dead button (the Fcmt8 near-miss).
  3. BUS AGREEMENT  - every name-append token index registered in variables.scr must have a
                      dispatch branch in player.scr, and every `append name ,xx` sent from the
                      UI must match a registered token. A sent-but-undispatched token is a
                      click that does nothing, silently.

Run from repo root. Exit 1 on any failure. Wired into build.ps1 as a deploy-blocking gate.
"""
import re, io, os, sys, glob

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
MOD  = os.path.join(ROOT, "hzm-mohaa-coop-mod")
fail = []

def read(p):
    t = io.open(p, encoding="latin-1").read()
    if p.endswith(".scr"):
        t = re.sub(r"//[^\n]*", "", t)   # a vstr named in a comment is documentation, not a wire
    return t

# ---------- gather sources ----------
cfgs = glob.glob(os.path.join(MOD, "ui", "**", "*.cfg"), recursive=True)
urcs = glob.glob(os.path.join(MOD, "ui", "**", "*.urc"), recursive=True)
scrs = glob.glob(os.path.join(MOD, "coop_mod", "*.scr"))
cl   = os.path.join(ROOT, "openmohaa-hzm", "code")

# real files, exact case, relative to mod root with forward slashes
real = set()
for p in glob.glob(os.path.join(MOD, "ui", "**", "*"), recursive=True):
    if os.path.isfile(p):
        real.add(os.path.relpath(p, MOD).replace(os.sep, "/"))
real_lower = {r.lower(): r for r in real}

# ---------- 1. exec closure ----------
exec_rx = re.compile(r'exec\s+(ui/[^\s";)]+\.cfg)', re.I)
refs = {}
for p in cfgs + urcs + scrs:
    for m in exec_rx.finditer(read(p)):
        if "<" in m.group(1):          # documentation placeholder in a comment, not a reference
            continue
        refs.setdefault(m.group(1), set()).add(os.path.relpath(p, MOD))
# engine-side execs (stufftext filters, lazy loads)
for p in glob.glob(os.path.join(cl, "**", "*.c*"), recursive=True):
    try:
        t = read(p)
    except Exception:
        continue
    if "ui/" in t:
        for m in exec_rx.finditer(t):
            refs.setdefault(m.group(1), set()).add("engine:" + os.path.basename(p))
for tgt, srcs in sorted(refs.items()):
    if tgt in real:
        continue
    hit = real_lower.get(tgt.lower())
    if hit:
        fail.append("CASE DRIFT: %s (real file: %s) <- %s" % (tgt, hit, ", ".join(sorted(srcs)[:2])))
    else:
        fail.append("MISSING CFG: %s <- %s" % (tgt, ", ".join(sorted(srcs)[:2])))

# ---------- 2. vstr closure (our namespaces only) ----------
vstr_rx = re.compile(r'vstr\s+(coop_(?:lo|sr|ui)\w*)', re.I)
setters = set()
set_rx = re.compile(r'\bseta?\s+(coop_\w+)', re.I)
for p in cfgs + urcs:
    for m in set_rx.finditer(read(p)):
        setters.add(m.group(1).lower())
for p in scrs:
    t = read(p)
    for m in re.finditer(r'"seta?\s+(coop_\w+)', t):          # stufftext ( "seta coop_x ...
        setters.add(m.group(1).lower())
    for m in re.finditer(r'"\s*seta?\s+"?\s*\+?\s*"?(coop_\w+)"?\s*\+', t):  # concat forms
        setters.add(m.group(1).lower())
    # stufftext ( "set coop_loMvPN_s" + local.slot ... -> treat prefix as wildcard setter
    for m in re.finditer(r'"seta?\s+(coop_\w+?)"\s*\+', t):
        setters.add(m.group(1).lower() + "*")
for p in glob.glob(os.path.join(cl, "**", "*.c*"), recursive=True):
    try:
        t = read(p)
    except Exception:
        continue
    for m in re.finditer(r'Cvar_(?:Set2?|Get)\(\s*(?:va\(\s*)?"(coop_\w+)', t):
        setters.add(m.group(1).lower())
        if "%d" in t[m.end():m.end()+8] or "%s" in t[m.end():m.end()+8]:
            setters.add(m.group(1).lower() + "*")
prefixes = tuple(s[:-1] for s in setters if s.endswith("*"))
used = {}
for p in cfgs + urcs + scrs:
    t = read(p)
    for m in vstr_rx.finditer(t):
        tail = t[m.end():m.end() + 3]
        if tail.startswith('"') and "+" in t[m.end():m.end() + 6]:
            continue                   # dynamic name built by concatenation - prefix, not a literal
        used.setdefault(m.group(1).lower(), set()).add(os.path.relpath(p, MOD))
for cv, srcs in sorted(used.items()):
    if cv in setters or cv.startswith(prefixes):
        continue
    fail.append("DEAD VSTR: %s never assigned anywhere <- %s" % (cv, ", ".join(sorted(srcs)[:2])))

# ---------- 3. name-bus agreement ----------
vscr = read(os.path.join(MOD, "coop_mod", "variables.scr"))
pscr = read(os.path.join(MOD, "coop_mod", "player.scr"))
reg = {}   # index -> token
for m in re.finditer(r'local\.command\["(\d+)"\]\s*=\s*"\s*(,\S+)"', vscr):
    reg[int(m.group(1))] = m.group(2)
dispatched = {int(m.group(1)) for m in re.finditer(r'arrayIndex\s*==\s*(\d+)', pscr)}
for i, tok in sorted(reg.items()):
    if i not in dispatched:
        fail.append("BUS TOKEN %d (%s) registered in variables.scr but has NO dispatch branch in player.scr" % (i, tok))
sent = set()
for p in cfgs + urcs:
    for m in re.finditer(r'append name (,[A-Za-z0-9]+)', read(p)):
        sent.add(m.group(1))
regtoks = sorted(reg.values(), key=len, reverse=True)
for tok in sorted(sent):
    if not any(tok.startswith(rt) for rt in regtoks):
        fail.append("UNREGISTERED TOKEN sent from UI: append name %s" % tok)

print("wiring audit: %d exec refs, %d vstr names, %d bus tokens registered, %d sent from UI"
      % (len(refs), len(used), len(reg), len(sent)))
if fail:
    print("\n%d WIRING FAILURES:" % len(fail))
    for f in fail:
        print("  " + f)
sys.exit(1 if fail else 0)
