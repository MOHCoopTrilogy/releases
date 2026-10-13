"""Where can an AI be looked at without the map's own actors getting in the way? Per map: the player start and the
actors (classname ai_* / model human) by side, nearest first.   python mapents.py m4l1 m6l1a ..."""
import sys, os, re, struct
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
os.chdir(_c)
vfs = V.PR.vfs


def entities(name):
    raw = vfs.read('maps/%s.bsp' % name)
    ident, ver = struct.unpack('<4si', raw[:8])
    # MOHAA bsp (2015, version 17-21): header = ident, version, checksum, then lumps (offset, length); the entity lump is
    # found by content: the largest lump that starts with '{' and holds "classname"
    best = b''
    for k in range(8, 8 + 30 * 8, 4):
        try:
            off, ln = struct.unpack('<ii', raw[k:k + 8])
        except struct.error:
            break
        if 0 < off < len(raw) and 0 < ln <= len(raw) - off and raw[off:off + 1] == b'{' and b'"classname"' in raw[off:off + min(ln, 4000)]:
            if ln > len(best):
                best = raw[off:off + ln]
    out = []
    for blk in re.findall(r'\{([^{}]*)\}', best.decode('latin-1')):
        out.append(dict(re.findall(r'"([^"]*)"\s+"([^"]*)"', blk)))
    return out


for m in sys.argv[1:]:
    try:
        es = entities(m)
    except Exception as e:
        print(m, 'cannot read', e); continue
    st = [e for e in es if e.get('classname') == 'info_player_start']
    if not st:
        print(m, 'no player start,', len(es), 'entities'); continue
    o = [float(x) for x in st[0]['origin'].split()]
    acts = []
    for e in es:
        c = e.get('classname', '')
        if c.startswith('ai_') or 'human' in e.get('model', ''):
            p = [float(x) for x in e.get('origin', '0 0 0').split()]
            d = sum((a - b) ** 2 for a, b in zip(p, o)) ** 0.5
            side = 'ALLY' if ('allied' in c or 'american' in c or 'allied' in e.get('model', '') or 'american' in e.get('model', '')) else 'axis'
            acts.append((d, side, c or e.get('model'), e.get('targetname', '')))
    acts.sort()
    print('%s start %s angle %s | actors %d, allies %d | nearest: %s' % (
        m, st[0]['origin'], st[0].get('angle', '0'), len(acts), sum(1 for a in acts if a[1] == 'ALLY'),
        '; '.join('%s %s %.0f u %s' % (a[1], a[2], a[0], a[3]) for a in acts[:6])))
    al = [a for a in acts if a[1] == 'ALLY']
    if al:
        print('    allies:', '; '.join('%s %.0f u %s' % (a[2], a[0], a[3]) for a in al[:6]))
