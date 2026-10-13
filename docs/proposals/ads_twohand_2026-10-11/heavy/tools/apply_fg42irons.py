r"""cgame patch (ads-heavy-next worktree, cgame only) for the iron-sight FG 42 ("FG 42 Irons", coop_fg42_irons*.tik,
tools/fg42irons.py / fg42tik.py) - the rifle lane's G 43 Irons wiring, for this gun:

  1. hands prefix: "FG 42 Irons" -> WPREFIX_FG42 (the scoped gun's hands rows)
  2. aim tune donor: "FG 42 Irons" -> "StG 44" (as the scoped FG 42)
  3. the per-weapon row override `coopr_<weapon key>_<suffix>` also covers `charge` (the aim pose) - the same line the
     pistol / rifle lanes carry on ads-next / ads-rifle-next, so the irons gun gets an aim pose of its own
     (row coopr_fg_42_irons_charge) and the scoped FG 42 keeps none
  4. the 8 sight rows: heavy/sights_override.json key fg42_irons (`"new": true`) -> code/cgame/cg_adssights.h, in the
     generator's row format (rifles/tools/patch_sights_row.py `row`)
The scope table (cg_hzmscope.c "FG 42") is NOT touched: the new base name does not match it.

    python apply_fg42irons.py <worktree>     (idempotent)
"""
import sys, os, re, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..', 'rifles', 'tools')))
import patch_sights_row as PS
W = sys.argv[1]


def patch(rel, pairs, mark):
    p = os.path.join(W, rel)
    s = open(p, encoding='utf-8', newline='').read()
    if mark in s:
        print(rel, 'already patched'); return
    nl = '\r\n' if '\r\n' in s else '\n'
    for a, b in pairs:
        a = a.replace('\n', nl); b = b.replace('\n', nl)
        assert s.count(a) == 1, (rel, a[:60], s.count(a))
        s = s.replace(a, b)
    open(p, 'w', encoding='utf-8', newline='').write(s)
    print(rel, 'patched')


patch('code/cgame/cg_viewmodelanim.c', [
    ('        if (!Q_stricmp(szWeaponName, "FG 42")) {\n',
     '        // HZM coop [fg42 irons 2026-10-13] "FG 42 Irons" = the FG 42 without its scope (coop_fg42_irons*.tik): the same hands\n'
     '        if (!Q_stricmp(szWeaponName, "FG 42") || !Q_stricmp(szWeaponName, "FG 42 Irons")) {\n'),
    ('        if (cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD || cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD_SINGLE\n'
     '            || cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD_END) {\n'
     '            CoopPerWeaponReloadAnim(',
     '        if (cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD || cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD_SINGLE\n'
     '            || cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD_END || cgi.anim->g_iLastVMAnim == VM_ANIM_CHARGE) {\n'
     '            CoopPerWeaponReloadAnim('),
], '"FG 42 Irons"')
patch('code/cgame/cg_modelanim.c', [
    ('    {"FG 42",         "StG 44"          }, // shoulder-fired automatic rifle\n',
     '    {"FG 42",         "StG 44"          }, // shoulder-fired automatic rifle\n'
     '    {"FG 42 Irons",   "StG 44"          }, // [fg42 irons 2026-10-13] the FG 42 without its scope: iron-sight aim\n'),
], '"FG 42 Irons"')
# sight rows
h = os.path.join(W, 'code/cgame/cg_adssights.h')
ov = json.load(open(os.path.join(HERE, '..', 'sights_override.json')))
txt = open(h, encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in txt else '\n'
lines = txt.split(nl)
n = 0
for key, o in ov.items():
    if not o.get('new'):
        continue
    for tik, name in sorted(o['tiks'].items()):
        new = PS.row(tik, name, o, key)
        at = [i for i, ln in enumerate(lines) if PS.ROW.match(ln) and PS.ROW.match(ln).group(1).lower() == tik.lower()]
        if at:
            if lines[at[0]] != new:
                lines[at[0]] = new; n += 1
            continue
        rows = [i for i, ln in enumerate(lines) if PS.ROW.match(ln)]
        pos = next((i for i in rows if PS.ROW.match(lines[i]).group(1).lower() > tik.lower()), rows[-1] + 1)
        lines.insert(pos, new); n += 1
if n:
    open(h, 'w', encoding='utf-8', newline='').write(nl.join(lines))
print('cg_adssights.h: %d row(s) written' % n)
