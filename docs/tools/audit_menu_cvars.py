"""Audit every menu control against the code that is supposed to implement it.

[user 2026-08-21] "I also want to make sure the advanced graphics settings all function as
intended... if we removed settings for a bug reason that setting needs to be removed."

A menu control is a PROMISE. A checkbox that sets a cvar nothing reads is worse than a missing
checkbox: the player toggles it, sees no change, and concludes the whole options screen is fake.
This project has accumulated exactly that - settings whose implementation was reverted for a bug
while the control stayed on the sheet.

Checking this by eye does not work, because a cvar is almost never read through its own name. The
normal shape is:

    pFoo = cgi.Cvar_Get("coop_foo", "1", CVAR_ARCHIVE);   // the name appears ONCE, here
    ...
    if (pFoo->integer) { ... }                            // every actual READ is through pFoo

so grepping for the cvar name finds one hit and tells you nothing about whether it does anything.
This resolves the name to its cached pointer first, then counts DEREFERENCES of that pointer -
which is the thing that actually means "some code branches on this setting".

A control is reported DEAD when its cvar is registered but never dereferenced, or not registered
and not read by any script either. DEAD is the actionable state: either wire it up or take the
control off the sheet.

Usage:  python docs/tools/audit_menu_cvars.py [--menu <substr>]
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(ROOT, 'hzm-mohaa-coop-mod')
ENG = os.path.join(ROOT, 'openmohaa-hzm', 'code')

ONLY = None
if '--menu' in sys.argv:
    ONLY = sys.argv[sys.argv.index('--menu') + 1].lower()

# Menus that expose settings to the player. Anything else (loadout, objectives, service record)
# is a different kind of screen and is not a settings promise.
MENU_HINTS = ('coop_settings', 'coop_postfx', 'advanced_graphics', 'video options',
              'coop_audio', 'options_main', 'controls')


def read(p):
    try:
        return io.open(p, 'rb').read().decode('utf-8', 'replace')
    except Exception:
        return ''


def source_files():
    out = []
    for base, _dirs, files in os.walk(ENG):
        if 'thirdparty' in base or 'SDL2' in base:
            continue
        for f in files:
            if f.endswith(('.c', '.cpp', '.h')):
                out.append(os.path.join(base, f))
    return out


def script_files():
    out = []
    for base, _dirs, files in os.walk(MOD):
        if '.git' in base:
            continue
        for f in files:
            if f.endswith(('.scr', '.cfg')):
                out.append(os.path.join(base, f))
    return out


def build_index():
    """cvar name -> {'ptrs': set of cached pointer names, 'derefs': int, 'registered': bool}"""
    idx = {}
    # pFoo = <anything>Cvar_Get("name", ...)   /   Cvar_Get2, ri.Cvar_Get, cgi.Cvar_Get, gi.Cvar_Get
    reg = re.compile(r'(\w+)\s*=\s*[\w.\->]*Cvar_Get2?\s*\(\s*"([^"]+)"')
    # A registration with NO assignment - ri.Cvar_Get("r_desktopfullscreen", ...) - still creates the
    # cvar; it is then read by name through Cvar_VariableIntegerValue. Missing these reported a live
    # setting as dead.
    regbare = re.compile(r'Cvar_Get2?\s*\(\s*"([^"]+)"')
    blobs = {}
    for p in source_files():
        s = read(p)
        if 'Cvar_Get' not in s and 'Cvar_' not in s:
            continue
        blobs[p] = s
        for m in reg.finditer(s):
            ptr, name = m.group(1), m.group(2)
            e = idx.setdefault(name, {'ptrs': set(), 'derefs': 0, 'registered': False})
            e['registered'] = True
            if ptr not in ('r', 'ret', 'tmp'):
                e['ptrs'].add(ptr)
        for m in regbare.finditer(s):
            idx.setdefault(m.group(1), {'ptrs': set(), 'derefs': 0, 'registered': False})['registered'] = True
    # Count dereferences across EVERY source file, not just the ones that register a cvar.
    # Registration and use routinely live in different files: r_fastdlights is registered in
    # tr_init.c and read in tr_world.c/tr_backend.c, neither of which mentions the cvar API at all,
    # so scanning only registering files reported 5 real reads as zero and called the control dead.
    allsrc = '\n'.join(read(p) for p in source_files())
    for name, e in idx.items():
        for ptr in e['ptrs']:
            e['derefs'] += len(re.findall(r'\b' + re.escape(ptr) + r'\s*->\s*(?:integer|value|string)', allsrc))
        # direct-by-name reads also count (Cvar_VariableIntegerValue("name") etc.)
        e['derefs'] += len(re.findall(r'Cvar_Variable\w*\s*\(\s*"' + re.escape(name) + r'"', allsrc))
        # USERINFO cvars are never read through a pointer at all: the client ships them in its
        # userinfo string and the SERVER pulls them out by key. "fov" is exactly this - the video
        # slider sets it, G_ClientUserinfoChanged clamps it 80-160 and applies EV_Player_Fov - so
        # counting only Cvar_* reads called a working slider dead.
        e['derefs'] += len(re.findall(r'Info_ValueForKey\s*\([^;]{0,60}"' + re.escape(name) + r'"', allsrc))
    return idx


def script_index():
    """cvar -> how many times a SCRIPT reads it (getcvar) - script-side settings are legitimate."""
    hits = {}
    for p in script_files():
        s = read(p)
        for m in re.finditer(r'getcvar\s*\(?\s*"?([A-Za-z_][\w]*)', s):
            hits[m.group(1)] = hits.get(m.group(1), 0) + 1
        for m in re.finditer(r'\blevel\.\w+\s*=\s*getcvar\s+"?([\w]+)', s):
            hits[m.group(1)] = hits.get(m.group(1), 0) + 1
    return hits


def menu_controls(path):
    """(control-name, title, cvar) for every linkcvar/pulldown in one .urc"""
    s = read(path)
    out = []
    for block in re.split(r'\nresource\s*\n', s):
        cv = re.search(r'linkcvar\s+"([^"]+)"', block)
        if not cv:
            continue
        nm = re.search(r'\bname\s+"([^"]+)"', block)
        ti = re.search(r'\btitle\s+"([^"]+)"', block)
        rc = re.search(r'\brect\s+(-?\d+)\s+(-?\d+)', block)
        offscreen = bool(rc and (int(rc.group(1)) < -100 or int(rc.group(2)) < -100))
        # A pulldown whose entries carry their own command does the real work in that command
        # ("Borderless Window" -> set r_fullscreen 1; set r_desktopfullscreen 1). Its linkcvar is
        # only remembering which row is selected, so nothing is meant to read it.
        if re.search(r'addpopup\s+"[^"]*"\s+"[^"]*"\s+command', block):
            offscreen = True
        out.append((nm.group(1) if nm else '?', ti.group(1) if ti else '', cv.group(1), offscreen))
    return out


def main():
    idx = build_index()
    scr = script_index()

    menus = []
    for base, _d, files in os.walk(os.path.join(MOD, 'ui')):
        for f in files:
            if not f.endswith('.urc'):
                continue
            if not any(h in f.lower() for h in MENU_HINTS):
                continue
            if ONLY and ONLY not in f.lower():
                continue
            menus.append(os.path.join(base, f))

    ci = {k.lower(): v for k, v in idx.items()}   # case-folded view, see the lookup below
    dead, ok, offs = [], 0, 0
    for m in sorted(menus):
        ctrls = menu_controls(m)
        if not ctrls:
            continue
        print('\n=== %s ===' % os.path.basename(m))
        for nm, ti, cv, off in ctrls:
            # Cvar lookup is Q_stricmp (Cvar_FindVar, qcommon/cvar.c), so a menu may spell a cvar in
            # any case and still bind the real one - "r_texturemode" in the URC is the engine's
            # r_textureMode. Matching case-sensitively reported that working control as nonexistent.
            e = idx.get(cv) or idx.get(cv.lower()) or ci.get(cv.lower())
            sc = scr.get(cv, 0) or scr.get(cv.lower(), 0)
            if off:
                state, offs = 'offscreen', offs + 1
            elif e and e['derefs'] > 0:
                state, ok = 'OK  (%d reads)' % e['derefs'], ok + 1
            elif sc > 0:
                state, ok = 'OK  (script, %d reads)' % sc, ok + 1
            elif e and e['registered']:
                state = '** DEAD - registered, never read **'
                dead.append((os.path.basename(m), ti or nm, cv, 'registered but no code reads it'))
            else:
                state = '** DEAD - cvar does not exist **'
                dead.append((os.path.basename(m), ti or nm, cv, 'no registration, no script read'))
            print('  %-22s %-26s %-30s %s' % (nm, ('"%s"' % ti) if ti else '', cv, state))

    print('\n' + '=' * 78)
    print('%d working, %d offscreen/parked, %d DEAD' % (ok, offs, len(dead)))
    if dead:
        print('\nDEAD CONTROLS - wire them up or remove them from the sheet:')
        for mn, ti, cv, why in dead:
            print('  %-22s %-26s %-26s %s' % (mn, ti, cv, why))
    return 1 if dead else 0


sys.exit(main())
