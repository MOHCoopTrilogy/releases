"""Hand-maintained script wiring for the new guns in the MOD worktree (the dbshotgun f58e211c recipe): roster case + id table,
the kill-stat token, the unlock challenge (appended LAST: the Service Record bakes one image per challenge index), the item
handler's class lists, giveall, the ubermode class table, and the heavy key-item list (rockets). Idempotent: every insertion
is keyed on a marker and skipped when present.
    python wire_scripts.py [--mod H:/hzm_work/newguns-mod] [guns ...]     (default: every gun in GUNS)
"""
import os, sys, re

MOD = sys.argv[sys.argv.index('--mod') + 1] if '--mod' in sys.argv else r"H:\hzm_work\newguns-mod"
TAG = '[newguns 2026-11-09]'
GUNS = {
    'bren': dict(id='82', tik='models/weapons/coop_bren.tik', name='BREN MK I', slot='p', ammo='mg', ammoN=120, cls='heavy', tab=3,
                 wid='bren', token='coop_bren', ihclass='mg', uber='mg', heavykey=False,
                 chal=('wpn_bren_v', 'support_weapons', 'Section Gun', 'Get 60 kills with the Vickers', 'wpn_vickers', 60)),
    'mp28': dict(id='83', tik='models/weapons/coop_bergmann.tik', name='MP 28', slot='p', ammo='smg', ammoN=160, cls='smg', tab=2,
                 wid='mp28', token='coop_bergmann', ihclass='smg', uber='smg', heavykey=False,
                 chal=('wpn_mp28_v', 'smgs', 'Before the MP40', 'Get 60 kills with the MP40', 'wpn_mp40', 60)),
    'panzerfaust': dict(id='84', tik='models/weapons/coop_panzerfaust.tik', name='PANZERFAUST 60', slot='p', ammo='heavy', ammoN=1,
                        cls='heavy', tab=3, wid='panzerfaust', token='coop_panzerfaust', ihclass='heavy', uber='heavy', heavykey=True,
                        chal=('wpn_panzerfaust_v', 'support_weapons', 'Faust', 'Get 10 kills with the Panzerschreck', 'wpn_panzerschreck', 10)),
}


def rw(rel, fn):
    p = os.path.join(MOD, *rel.split('/'))
    b = open(p, 'rb').read(); s = b.decode('latin-1')
    nl = '\r\n' if '\r\n' in s else '\n'
    s2 = fn(s, nl)
    if s2 != s:
        open(p, 'wb').write(s2.encode('latin-1'))
        print('  wrote', rel)


def once(s, marker, anchor, text, after=True):
    if marker in s:
        return s
    assert s.count(anchor) == 1, (anchor[:60], s.count(anchor))
    return s.replace(anchor, anchor + text if after else text + anchor)


def roster(g):
    def f(s, nl):
        blk = (nl + '\t\tcase "%s":\t//%s %s' % (g['id'], TAG, g['name']) + nl +
               '\t\t\tlocal.r["give"] = "%s"' % g['tik'] + nl + '\t\t\tlocal.r["name"] = "%s"' % g['name'] + nl +
               '\t\t\tlocal.r["slot"] = "%s"' % g['slot'] + nl + '\t\t\tlocal.r["ammo"] = "%s"' % g['ammo'] + nl +
               '\t\t\tlocal.r["ammoN"] = %d' % g['ammoN'] + nl + '\t\t\tlocal.r["class"] = "%s"' % g['cls'] + nl + '\t\t\tbreak')
        if 'case "%s":' % g['id'] not in s:
            m = re.search(r'(\t\tcase "75":.*?\t\t\tbreak)', s, re.S)
            # after the LAST case block of roster_get (the id table follows the switch)
            last = [mm for mm in re.finditer(r'\t\t\tbreak(\r?\n)\t\}\r?\n\}end local\.r', s)][0]
            s = s[:last.start() + len('\t\t\tbreak')] + blk + s[last.start() + len('\t\t\tbreak'):]
        n = int(re.search(r'level\.coop_loRosterN = (\d+)', s).group(1))
        if 'coop_loRosterGive[%d] = "%s"' % (n - 1, g['tik']) not in s and g['tik'] not in s.split('roster_ids:')[1]:
            s = s.replace('level.coop_loRosterN = %d' % n, 'level.coop_loRosterN = %d' % (n + 1), 1)
            last = list(re.finditer(r'\tlevel\.coop_loRosterTab\[%d\] = \d+' % (n - 1), s))[-1]
            add = (nl + '\tlevel.coop_loRosterId[%d] = "%s"\t//%s' % (n, g['id'], TAG) + nl +
                   '\tlevel.coop_loRosterGive[%d] = "%s"' % (n, g['tik']) + nl + '\tlevel.coop_loRosterTab[%d] = %d' % (n, g['tab']))
            s = s[:last.end()] + add + s[last.end():]
        return s
    rw('coop_mod/loadoutroster.scr', f)


def challenges(g):
    def f(s, nl):
        anchor = '\tif( waitthread coop_mod/main.scr::containsText local.m "mauser_c96" 0 ){ local.wid = "c96" }'
        tok = '\tif( waitthread coop_mod/main.scr::containsText local.m "%s" 0 ){ local.wid = "%s" }\t//%s' % (g['token'], g['wid'], TAG)
        if tok not in s:
            # the new tokens go FIRST (ordered substring match; "coop_<gun>" contains no earlier token) and the old first line
            # becomes an else-if
            s = s.replace(anchor, tok + nl + anchor.replace('\tif(', '\telse if('), 1) if anchor in s else \
                s.replace('\tif( waitthread coop_mod/main.scr::containsText local.m "coop_', tok + nl + '\telse if( waitthread coop_mod/main.scr::containsText local.m "coop_', 1)
        c = g['chal']
        line = '\twaitthread chal_def "%s" "%s" "%s" "%s" "%s" %d "%s"\t//%s unlocks the %s' % (c[0], c[1], c[2], c[3], c[4], c[5], g['tik'], TAG, g['name'])
        if '"%s"' % c[0] not in s:
            anchor2 = 'waitthread chal_def "cc_seaside_stowaway"'
            i = s.index(anchor2); j = s.index(nl, i)
            s = s[:j] + nl + line + s[j:]
        return s
    rw('coop_mod/challenges.scr', f)


def itemhandler(g):
    def f(s, nl):
        if g['tik'] in s:
            return s
        # 1) getAmmoType-style class list: before the end("<class>") that closes the list holding the donor family
        fam = {'mg': 'models/weapons/uk_w_vickers.tik', 'smg': 'models/weapons/sten.tik', 'heavy': 'models/weapons/panzerschreck.tik'}[g['ihclass']]
        out = []
        for ln in s.split(nl):
            out.append(ln)
            if ln.strip() == 'case "%s":' % fam:
                out.append('\t\tcase "%s": //%s' % (g['tik'], TAG))
        return nl.join(out)
    rw('coop_mod/itemhandler.scr', f)


def giveall(g):
    def f(s, nl):
        if g['tik'].replace('models/', '') in s:
            return s
        anchor = 'weapon weapons/coop_dbshotgun.tik'
        i = s.index(anchor); j = s.index(nl, i)
        return s[:j] + nl + 'weapon %s\t//%s' % (g['tik'].replace('models/', ''), TAG) + s[j:]
    rw('global/giveall.scr', f)


def uber(g):
    def f(s, nl):
        if g['tik'] in s:
            return s
        anchor = '\tlocal.classes["models/weapons/coop_dbshotgun.tik"] = "shotgun"'
        i = s.index(anchor); j = s.index(nl, i)
        return s[:j] + nl + '\tlocal.classes["%s"] = "%s"\t//%s' % (g['tik'], g['uber'], TAG) + s[j:]
    rw('ubermode/get_player_weaponclass.scr', f)


def heavykey(g):
    if not g['heavykey']:
        return

    def f(s, nl):
        if g['tik'] in s:
            return s
        anchor = '\tlocal.m[3] = "models/weapons/Uk_W_Piat.tik"'
        i = s.index(anchor); j = s.index(nl, i)
        return s[:j] + nl + '\tlocal.m[4] = "%s"\t//%s a downed player drops the unfired tube' % (g['tik'], TAG) + s[j:]
    rw('coop_mod/keyitems.scr', f)


if __name__ == '__main__':
    names = [a for a in sys.argv[1:] if a in GUNS] or list(GUNS)
    for n in names:
        print(n)
        g = GUNS[n]
        for fn in (roster, challenges, itemhandler, giveall, uber, heavykey):
            fn(g)
