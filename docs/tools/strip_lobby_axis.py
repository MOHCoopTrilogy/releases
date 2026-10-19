"""strip_lobby_axis.py - remove BSP-baked AXIS actors from the coop lobby maps (bug-429 recipe, bug-2959).

The co_lobbyN.bsp lobbies are copies of campaign BSPs. The engine spawns every ai_* entity baked into a BSP's entity
lump at map load, and the lobby scripts never run the original map script - so the source mission's German soldiers
stand in (and on co_lobby8, shoot at) the lobby. bug-429 fixed co_lobby4 by hand; co_lobby2/3/7/8 were never done.

Recipe (bug-429, proven): overwrite each matching { ... } entity block with the same number of spaces. File length
and the entity-lump length stay identical (no header / lump-offset surgery) and the entity parser skips whitespace.

Stripped: classname ai_german_* / ai_italian_*, info_aispawnpoint, and ai_actor whose model is axis (german / ital /
sc_ax_). Kept: worldspawn, spawns, triggers, props, and every allied actor (bug-429 kept co_lobby4's friendly).

    python docs/tools/strip_lobby_axis.py check          # report only; exit 1 if any lobby still bakes axis actors
    python docs/tools/strip_lobby_axis.py apply          # strip in place (idempotent; backups under _lobby_bsp_backup/)
"""
import os, re, sys, shutil, hashlib

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'hzm-mohaa-coop-mod', 'maps')
BACKUP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '_lobby_bsp_backup')
AXIS_MODEL = re.compile(r'german|/ital|_ital_|sc_ax_|axis', re.I)


def entity_span(d):
    w = d.find(b'"worldspawn"')
    if w < 0:
        raise ValueError('no worldspawn')
    return d.rfind(b'{', 0, w), d.find(b'\x00', w)


def blocks(d, s, e):
    i = s
    while True:
        a = d.find(b'{', i, e)
        if a < 0:
            return
        b = d.find(b'}', a, e)
        yield a, b + 1
        i = b + 1


def is_axis(kv):
    c = kv.get('classname', '')
    m = kv.get('model', '')
    if c.startswith('ai_german') or c.startswith('ai_italian'):
        return True
    if c == 'info_aispawnpoint':
        return True
    if c == 'ai_actor' and AXIS_MODEL.search(m):
        return True
    return False


def scan(path):
    d = bytearray(open(path, 'rb').read())
    s, e = entity_span(d)
    hits = []
    for a, b in blocks(d, s, e):
        kv = {k.decode('latin-1'): v.decode('latin-1') for k, v in re.findall(rb'"([^"]*)"\s+"([^"]*)"', bytes(d[a:b]))}
        if is_axis(kv):
            hits.append((a, b, kv))
    return d, s, e, hits


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'check'
    lobbies = sorted(f for f in os.listdir(ROOT) if re.match(r'co_lobby\d+\.bsp$', f, re.I))
    dirty = 0
    for f in lobbies:
        p = os.path.join(ROOT, f)
        d, s, e, hits = scan(p)
        names = sorted({h[2].get('targetname', '') for h in hits} - {''})
        print('%-14s axis blocks %3d  targetnames %s' % (f, len(hits), ', '.join(names[:12]) + (' ...' if len(names) > 12 else '')))
        if not hits:
            continue
        dirty += 1
        if mode != 'apply':
            continue
        os.makedirs(BACKUP, exist_ok=True)
        bk = os.path.join(BACKUP, f + '.' + hashlib.md5(bytes(d)).hexdigest()[:10])
        if not os.path.exists(bk):
            shutil.copy2(p, bk)
        n0 = len(d)
        for a, b, _ in hits:
            d[a:b] = b' ' * (b - a)
        assert len(d) == n0
        s2, e2 = entity_span(d)
        assert (s2, e2) == (s, e)
        open(p, 'wb').write(bytes(d))
        _, _, _, left = scan(p)
        assert not left, (f, len(left))
        print('   stripped -> %s (backup %s)' % (f, os.path.basename(bk)))
    if mode == 'check' and dirty:
        sys.exit(1)


if __name__ == '__main__':
    main()
