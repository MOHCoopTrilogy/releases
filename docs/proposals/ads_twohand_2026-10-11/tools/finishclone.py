"""Stage the FINISH tiks of a gun whose staged base tik was built by hand-made tools (S&W M10): a finish tik is the
base tik with other shader lines, name and rank - so the staged finish = the STAGED base with exactly the lines in
which the released finish differs from the released base.

    python finishclone.py <staged root> <base stem> [--dry]

Every differing released line must be found exactly once in the staged base (asserted), so a finish that differs in
something the staged base no longer has stops the run instead of being written wrong. Idempotent (always rebuilt from
the staged base).
"""
import sys, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import p12
FIN = ('bloody', 'blued', 'camo_desert', 'camo_winter', 'camo_woodland', 'chrome', 'gold')


def main():
    root, base = os.path.abspath(sys.argv[1]), sys.argv[2]
    dry = '--dry' in sys.argv
    stems = p12.tik_stems()
    real = {k.lower(): (v or k) for k, v in stems.items()}
    sb = open(os.path.join(root, 'models', 'weapons', base + '.tik'), 'rb').read().decode('latin-1')
    nl = '\r\n' if '\r\n' in sb else '\n'
    sl = sb.replace('\r\n', '\n').split('\n')
    rb = p12.rd('models/weapons/%s.tik' % real[base.lower()]).decode('latin-1').replace('\r\n', '\n').split('\n')
    done = []
    for f in FIN:
        st = '%s_%s' % (base.lower(), f)
        if st not in real:
            continue
        rf = p12.rd('models/weapons/%s.tik' % real[st]).decode('latin-1').replace('\r\n', '\n').split('\n')
        assert len(rf) == len(rb), (st, len(rf), len(rb))
        out = list(sl)
        n = 0
        for a, b in zip(rb, rf):
            if a == b:
                continue
            idx = [i for i, l in enumerate(sl) if l == a]
            assert len(idx) == 1, (st, a, len(idx))
            out[idx[0]] = b
            n += 1
        txt = '\n'.join(out)
        p12.depth_ok(txt, st)
        if not dry:
            p12.write_tik(root, real[st], txt, nl)
        done.append('%s (%d lines)' % (real[st], n))
    print('%s: %d finish tiks %s: %s' % (base, len(done), 'checked' if dry else 'written', ', '.join(done)))


if __name__ == '__main__':
    main()
