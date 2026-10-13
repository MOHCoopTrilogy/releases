"""APPEND-ONLY staging of new per-weapon rows in the lane's fps_anims_smg.txt (coordinator 2026-10-13: the MP40-family rows
of this file are being shipped from here - they may not be reordered or rewritten; stage_rows.py REGENERATES the file
from the released fixes-pak copy, which the integration now changes underneath, so it moves those rows: do not run it
any more for a new gun).

    cd smg/assets;  python ../tools/append_rows.py <weapon key> "<block title>"
Takes the rows named coopr_<weapon key>_* from tools/rows_extra.json ('add': [row, clip, crossblend, base row]) and puts
them in ONE titled block before the closing brace of the file as it is in git HEAD; a row that is already in the file is
left where it is (its clip is checked to be the same). Every other byte of the file stays as it was.
"""
import sys, os, json, re, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.normpath(os.path.join(HERE, '..', 'assets', 'models', 'player', 'base', 'fps_anims_smg.txt'))
REL = 'docs/proposals/ads_twohand_2026-10-11/smg/assets/models/player/base/fps_anims_smg.txt'


def main():
    key, title = sys.argv[1], sys.argv[2]
    head = subprocess.run(['git', 'show', 'HEAD:' + REL], capture_output=True, cwd=os.path.dirname(P)).stdout
    cur = open(P, 'rb').read()
    base = cur if '--keep' in sys.argv else head          # --keep: add to the working file (a second gun before a commit)
    s = base.decode('latin-1')
    nl = '\r\n' if '\r\n' in s else '\n'
    ex = json.load(open(os.path.join(HERE, 'rows_extra.json')))
    rows = [r for r in ex['add'] if r[0].startswith('coopr_%s_' % key)]
    assert rows, 'no rows for %s in rows_extra.json' % key
    have = dict(re.findall(r'(?m)^[ \t]+(\S+)[ \t]+(\S+\.skc)', s))
    new = []
    for r in rows:
        if r[0] in have:
            assert have[r[0]].lower() == r[1].lower(), ('row is in the file with another clip', r[0], have[r[0]], r[1])
            continue
        new.append('\t%s\t\t%s\t\tcrossblend %s\t// HZM coop [ads-smg] staged' % (r[0], r[1], r[2]))
    if not new:
        print('nothing to add for', key); return
    k = s.rstrip().rfind('}')
    assert k > 0
    block = '\t//===================== ads-smg lane: %s =====================' % title + nl + nl.join(new) + nl
    out = s[:k] + block + s[k:]
    open(P, 'wb').write(out.encode('latin-1'))
    print('appended %d rows for %s in one block before the closing brace (base = %s)' % (len(new), key, 'the working file' if '--keep' in sys.argv else 'git HEAD'))


if __name__ == '__main__':
    main()
