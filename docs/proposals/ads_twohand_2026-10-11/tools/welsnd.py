"""Welrod: a sound for the bolt (pistol lane, 2026-10-13 pm; follow-up cut - the Welrod tiks of the frozen cut are silent there).

The bolt is worked by hand after every aimed shot (`fire_ads`, pulled at frame 10 of 26) and at the end of an emptied
aimed reload (`reload_ads_empty`, pulled at frame 51). Nothing sounded. The sound is the WAV of the game's existing
alias `springfield_snd_bolt` (sound/weapons/foley/Spring_Bolt.wav - a turn-bolt being worked), cached by the Welrod's
own tik under its own alias so that it does not depend on that alias's per-map list, quieter and a little higher (a
small bolt):
    aliascache welrod_snd_bolt sound/weapons/foley/Spring_Bolt.wav soundparms 0.55 0.05 1.15 0.05 160 800 item loaded always maps "dm obj lib"
Client rows only (frame commands in the client blocks of client-shown rows): nothing the server reads changes.
NOT HEARD by anyone: the harness is muted. Checked = the tiks parse, the rows load, no sound error in the log.

    python welsnd.py <stage root>          idempotent; every welrod*.tik under models/weapons
"""
import sys, os, re, glob
ALIAS = 'welrod_snd_bolt'
LINE = '\t\taliascache %s sound/weapons/foley/Spring_Bolt.wav soundparms 0.55 0.05 1.15 0.05 160 800 item loaded always maps "dm obj lib"\n' % ALIAS
ROWS = {'fire_ads': 10, 'reload_ads_empty': 51}


def patch(s):
    if ALIAS in s:
        return s, False
    m = re.search(r'(?m)^[ \t]*aliascache[ \t]+P38_snd_reload_loaded[^\n]*\n', s)
    assert m, 'no aliascache anchor'
    s = s[:m.end()] + LINE + s[m.end():]
    for row, fr in ROWS.items():
        mr = re.search(r'(?m)^[ \t]*%s[ \t]+\S+\.skc[^\n]*\n' % row, s)
        assert mr, row
        mc = re.compile(r'(?m)^([ \t]*)client[ \t]*\n[ \t]*\{[ \t]*\n').search(s, mr.end())
        assert mc and mc.start() - mr.end() < 400, row
        s = s[:mc.end()] + '%s\t%d sound %s item\t// HZM coop [pistol lane 2026-10-13] the bolt is pulled here\n' % (mc.group(1), fr, ALIAS) + s[mc.end():]
    return s, True


def main(root):
    done = []
    for fn in sorted(glob.glob(os.path.join(root, 'models', 'weapons', 'welrod*.tik'))):
        raw = open(fn, 'rb').read().decode('latin-1')
        nl = '\r\n' if '\r\n' in raw else '\n'
        s, ch = patch(raw.replace('\r\n', '\n'))
        d = 0
        for ln in s.split('\n'):
            c = ln.split('//')[0]; d += c.count('{') - c.count('}')
            assert d >= 0, fn
        assert d == 0, fn
        if ch:
            open(fn, 'wb').write(s.replace('\n', nl).encode('latin-1'))
        done.append(os.path.basename(fn) + ('' if ch else ' (already)'))
    print('welrod bolt sound:', done)


if __name__ == '__main__':
    main(sys.argv[1])
