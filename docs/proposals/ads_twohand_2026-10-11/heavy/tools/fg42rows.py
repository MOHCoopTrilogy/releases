"""FG 42, both guns, all finishes: the staged weapon tiks with the charging handle and the client-side reload rows.

  * the 8 FG 42 Irons tiks (fg42tik.py writes them from the mod tree; this patches its output), and
  * the 8 SCOPED FG 42 tiks (FG42.tik + 7 finishes) = the mod tree's own, with ONLY these changes:
        skelmodel coop_fg42.skd (the retail mesh + the handle, fg42handle.py)
Both families:
  * `surface coop_handle shader coop_fg42_sight` (dark steel on every finish)
  * new rows the SERVER never plays (cgame shows them instead of `reload`, cg_modelanim.c):
        reload_empty       coop_reload_empty.skc   hip, the gun was EMPTY: the handle hauled back and let go (+ the bolt sound there)
        reload_ads_empty   coop_reload_empty.skc   the same, aimed
        reload_ads_loaded  fg42.skc                aimed, rounds left: nothing moves
  * the `reload` row keeps its clip (fg42.skc, 91 frames = the server's 3.0 s) and its server commands; its client
    block loses `30 sound fg42_snd_bolt`: with rounds left no handle is worked (the emptied rows play it at the pull).

    python fg42rows.py            (runs fg42tik.py first; prints one line per tik)
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fg42tik as FT
import fg42bake as FB
PULL = FB.T_EMPTY['pull'][0]
BLOCK = ['\t// HZM coop [ads heavy rows] FG 42: rows only the cgame shows. An EMPTY gun gets the charging handle (bone coop_chg)',
         '\t// hauled back and let go by the firing hand; with rounds left the bolt is cocked and nothing moves.',
         '\treload_empty\tcoop_reload_empty.skc', '\t{', '\t\tclient', '\t\t{', '\t\t\tentry sound fg42_snd_reload', '\t\t\t%d sound fg42_snd_bolt' % PULL, '\t\t}', '\t}',
         '\treload_ads_empty\tcoop_reload_empty.skc', '\t{', '\t\tclient', '\t\t{', '\t\t\tentry sound fg42_snd_reload', '\t\t\t%d sound fg42_snd_bolt' % PULL, '\t\t}', '\t}',
         '\treload_ads_loaded\tfg42.skc', '\t{', '\t\tclient', '\t\t{', '\t\t\tentry sound fg42_snd_reload', '\t\t}', '\t}',
         '\t// HZM coop [ads heavy rows end]']


def patch(t, name, scoped):
    nl = '\r\n' if '\r\n' in t else '\n'
    assert 'coop_handle' not in t and 'reload_empty' not in t, name + ': already patched'
    if scoped:
        t, n = re.subn(r'skelmodel\s+fg42\.skd', 'skelmodel coop_fg42.skd', t); assert n == 1, name
    # the handle's surface line after the last `surface` line of the setup block
    setup_end = t.index('}', t.index('setup'))
    ms = list(re.finditer(r'\n([ \t]*)surface[ \t]+\S+[^\n]*', t[:setup_end]))
    assert ms, name
    m = ms[-1]
    t = t[:m.end()] + '\n' + m.group(1) + 'surface coop_handle shader coop_fg42_sight\t// HZM coop [ads heavy] the charging handle (fg42handle.py)' + t[m.end():]
    m = re.search(r'(?m)^[ \t]*reload[ \t]+fg42\.skc[^\n]*\n', t); assert m, name + ': reload row'
    t = t[:m.start()] + nl.join(BLOCK) + nl + t[m.start():]
    t, n = re.subn(r'\n[ \t]*30[ \t]+sound[ \t]+fg42_snd_bolt[^\n]*', '\n\t\t\t// HZM coop [ads heavy] the bolt sound moved to the emptied rows (reload_empty / reload_ads_empty): rounds left = no handle work', t)
    assert n == 1, name + ': bolt sound'
    t = t.replace('\r\n', '\n').replace('\n', nl)
    d = 0
    for ln in re.sub(r'//[^\n]*', '', t).splitlines():
        d += ln.count('{') - ln.count('}')
        assert d >= 0, name
    assert d == 0, name
    return t


def main():
    FT.main()
    for src, fin in FT.SRC:
        out = 'coop_fg42_irons%s.tik' % (('_' + fin) if fin else '')
        p = os.path.join(FT.OUT, out)
        t = patch(open(p, 'rb').read().decode('latin-1'), out, False)
        open(p, 'wb').write(t.encode('latin-1'))
        print('irons ', out, 'handle surface + rows')
        t = patch(open(os.path.join(FT.MOD, src), 'rb').read().decode('latin-1'), src, True)
        open(os.path.join(FT.OUT, src), 'wb').write(t.encode('latin-1'))
        print('scoped', src, 'skelmodel coop_fg42.skd + handle surface + rows')


if __name__ == '__main__':
    main()
