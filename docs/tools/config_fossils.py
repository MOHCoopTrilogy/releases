#!/usr/bin/env python3
"""
Find CONFIG FOSSILS: archived coop_* values in a player's saved config that no longer match
the value the build actually ships.

WHY THIS EXISTS (2026-08-23). Three fossils turned up by accident in one week, each of which
had silently defeated a shipped decision:

  coop_idleBolt      archived 1, default 0  -> a feature the user asked us to REMOVE on 08-21
                                               was still running on their machine
  coop_lowAmmoTell   archived 1, default 0  -> retired feature, still on
  coop_sprintMult    archived 1.9, default 1.3 -> never shipped at 1.9; and because it is a
                                               SERVER cvar, the host's fossil applied to their
                                               friend too, which is what "sprint is too fast" was

The mechanism is TRAPS T7: `Cvar_Get` on an existing cvar keeps the saved value and updates only
the reset string, and coop_defaults.cfg execs BEFORE the saved config so it cannot override one
either. A default change therefore reaches nobody who has already played. The person most exposed
is whoever tunes the most - i.e. the only tester - so they are effectively play-testing a
configuration that no other player has.

    python docs/tools/config_fossils.py [path-to-omconfig.cfg]

Reports every archived coop_* whose value differs from the engine default, splitting them into
SERVER cvars (which affect everyone on that host) and client ones.
"""
import io
import os
import re
import sys

DEV = r'C:\mohaa-coop-dev'
DEFAULT_CFG = r'G:\mohaa-gl2\home\maintt\configs\omconfig.cfg'

# Cvar_Get("name", "default", flags) - capture name + default. fgame = server, cgame = client.
CVAR_RE = re.compile(r'Cvar_Get\(\s*"(coop_[A-Za-z0-9_]+)"\s*,\s*"([^"]*)"', re.I)
SETA_RE = re.compile(r'^\s*seta\s+(coop_[A-Za-z0-9_]+)\s+"?([^"\r\n]*?)"?\s*$', re.I | re.M)


def scan_engine():
    """name -> (default, scope) from the engine source."""
    out = {}
    for sub, scope in (('code/fgame', 'SERVER'), ('code/cgame', 'client')):
        root = os.path.join(DEV, 'openmohaa-hzm', sub)
        if not os.path.isdir(root):
            continue
        for fn in os.listdir(root):
            if not fn.endswith(('.cpp', '.c')):
                continue
            try:
                t = io.open(os.path.join(root, fn), encoding='utf-8', errors='replace').read()
            except OSError:
                continue
            for name, dflt in CVAR_RE.findall(t):
                # first registration wins; fgame scanned first so server scope sticks
                out.setdefault(name, (dflt, scope))
    return out


def scan_autoexec():
    """Values shipped by autoexec.cfg - which EXECS LAST and therefore beats everything.

    [2026-08-23] This tool originally scanned only the saved config and concluded that
    coop_sprintMult 1.9, coop_goreWounds 0 and coop_aiProneChance 45 were user fossils. They were
    not: autoexec.cfg shipped all three. Reporting them as fossils sent me to change engine defaults
    that could never win, and to tell the user their saved config was at fault when our own file
    was. A tool that names the wrong culprit is worse than no tool.
    """
    p = os.path.join(DEV, 'hzm-mohaa-coop-mod', 'autoexec.cfg')
    if not os.path.exists(p):
        return {}
    t = io.open(p, encoding='utf-8', errors='replace').read()
    return {n: v for n, v in SETA_RE.findall(t)}


def scan_defaults_cfg():
    """Values seeded by coop_defaults.cfg, which execs BEFORE the saved config."""
    p = os.path.join(DEV, 'hzm-mohaa-coop-mod', 'coop_defaults.cfg')
    if not os.path.exists(p):
        return {}
    t = io.open(p, encoding='utf-8', errors='replace').read()
    return {n: v for n, v in SETA_RE.findall(t)}


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main():
    cfg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CFG
    if not os.path.exists(cfg):
        print('no such config: %s' % cfg)
        return 1
    engine = scan_engine()
    seeded = scan_defaults_cfg()
    autoexec = scan_autoexec()
    saved = dict(SETA_RE.findall(io.open(cfg, encoding='utf-8', errors='replace').read()))

    rows = []
    shipped = []
    for name, val in sorted(saved.items()):
        if name not in engine:
            continue
        dflt, scope = engine[name]
        a, b = num(val), num(dflt)
        same = (abs(a - b) < 1e-9) if (a is not None and b is not None) else (val.strip() == dflt.strip())
        # autoexec.cfg execs LAST and wins outright, so a value it ships is a SHIPPED DECISION,
        # not a fossil in the player's config. Report those separately rather than blaming them.
        if name in autoexec:
            shipped.append((scope, name, autoexec[name], dflt))
            continue
        if not same:
            rows.append((scope, name, val, dflt, seeded.get(name)))

    print('config : %s' % cfg)
    print('engine : %d coop_* cvars registered | saved: %d | seeded by coop_defaults.cfg: %d'
          % (len(engine), len(saved), len(seeded)))
    print()
    for scope in ('SERVER', 'client'):
        mine = [r for r in rows if r[0] == scope]
        if not mine:
            continue
        note = ' - these apply to EVERYONE on your host' if scope == 'SERVER' else ''
        print('== %s cvars diverging from the shipped default (%d)%s' % (scope, len(mine), note))
        print('   %-30s %-12s %-12s %s' % ('cvar', 'yours', 'ships', 'also seeded in coop_defaults.cfg?'))
        for _, name, val, dflt, seed in mine:
            print('   %-30s %-12s %-12s %s' % (name, val, dflt, seed if seed is not None else '-'))
        print()
    if shipped:
        print('== SHIPPED BY autoexec.cfg (%d) - these beat the engine default AND the saved
   config, because autoexec execs last. Changing a Cvar_Get default cannot move them.'
              % len(shipped))
        print('   %-30s %-12s %s' % ('cvar', 'autoexec', 'engine default'))
        for scope, name, val, dflt in shipped:
            print('   %-30s %-12s %s' % (name, val, dflt))
        print()
    if not rows:
        print('no fossils - every archived coop_* matches what the build ships.')
    else:
        print('A row with no coop_defaults.cfg entry is a value NOBODY ELSE HAS. A SERVER row is one')
        print('your co-op partners have been playing with too, without choosing it.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
