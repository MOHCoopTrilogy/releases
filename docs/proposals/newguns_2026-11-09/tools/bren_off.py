"""v1.10.68 cut: the Bren is held back (BREN_SIGHTS.md). Switched OFF, nothing deleted:
  root  docs/tools/loadout_weapons.tsv   row 82 commented out ("#OFF ") -> Armory tile/pages, loadouts, lktabs, stats, viewer,
                                          the generated unlock roster all drop it
  mod   coop_mod/challenges.scr           the unlock challenge wpn_bren_v and the kill-stat token "coop_bren" -> wid "bren"
                                          commented out -> no Service Record row, no finish ladder (finish_challenges keys on the wid)
  mod   coop_mod/loadoutroster.scr        the hand-written case "82" commented out (armory_unlocks / unlock_audit read it)
Re-enable: run with `on` (strips the same markers). The finishes2 rows come from the staging build (fs2_ng.py drop/add)."""
import sys
ON = len(sys.argv) > 1 and sys.argv[1] == 'on'
MARK = b'//[OFF v1.10.68 Bren held, BREN_SIGHTS.md] '
import os
# [newguns2] the worktrees come from the environment (default: the newguns2 ones; v1.10.68 ran it on newguns / newguns-mod)
_ROOT = os.environ.get('HZM_NG_ROOT', r'C:\hzm-newguns2\root')
_MOD = os.environ.get('HZM_MOD', r'H:\hzm_work\newguns2-mod')
TSV = os.path.join(_ROOT, 'docs', 'tools', 'loadout_weapons.tsv')
CH = os.path.join(_MOD, 'coop_mod', 'challenges.scr')
RO = os.path.join(_MOD, 'coop_mod', 'loadoutroster.scr')


def edit(path, fn):
    b = open(path, 'rb').read()
    nl = b'\r\n' if b.count(b'\r\n') * 2 > b.count(b'\n') else b'\n'
    lines = b.split(nl)
    out = fn(lines)
    open(path, 'wb').write(nl.join(out))


def tsv(lines):
    n = 0
    out = []
    for l in lines:
        if not ON and l.startswith(b'82\tmodels/weapons/coop_bren.tik'):
            l = b'#OFF ' + l; n += 1
        elif ON and l.startswith(b'#OFF 82\t'):
            l = l[5:]; n += 1
        out.append(l)
    assert n == 1, n
    return out


def ch(lines):
    n = 0
    out = []
    for l in lines:
        s = l.lstrip(b'\t')
        if not ON and (s.startswith(b'waitthread chal_def "wpn_bren_v"') or b'local.m "coop_bren" 0 ){ local.wid = "bren" }' in l and not s.startswith(b'//')):
            # the token is renamed too: the generators' chal_def / containsText regexes do not skip // comments
            s = s.replace(b'chal_def "', b'chal_def_HELD "').replace(b'containsText local', b'containsText_HELD local')
            l = l[:len(l) - len(s)] + MARK + s; n += 1
        elif ON and MARK in l:
            l = l.replace(MARK, b'').replace(b'chal_def_HELD "', b'chal_def "').replace(b'containsText_HELD local', b'containsText local'); n += 1
        out.append(l)
    assert n == 2, n
    return out


def ro(lines):
    out = []
    n = 0
    i = 0
    while i < len(lines):
        l = lines[i]
        if not ON and l.strip().startswith(b'case "82":'):
            j = i
            while not lines[j].strip().startswith(b'break'):
                j += 1
            for k in range(i, j + 1):
                s = lines[k].lstrip(b'\t')
                out.append(lines[k][:len(lines[k]) - len(s)] + MARK + s); n += 1
            i = j + 1
            continue
        if ON and MARK in l:
            l = l.replace(MARK, b''); n += 1
        out.append(l)
        i += 1
    assert n == 8, n
    return out


edit(TSV, tsv)
edit(CH, ch)
edit(RO, ro)
print('Bren', 'ON' if ON else 'OFF')
