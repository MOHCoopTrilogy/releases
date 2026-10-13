"""bug-3736: the tik rows the SERVER reads go back to the released clips (idempotent source patch of p12.py / welrod.py).

    python patch_srvrows.py
p12.py     TT-33 / silenced TT-33: no padded `reload` (pad=True dropped) - `reload` stays tt33_reload.skc (7 frames)
welrod.py  `reload` stays welrod_pistol_reload.skc (1 frame), `fire` stays welrod_pistol_fire.skc (1 frame);
           the 73-frame still clip is only the client row reload_ads_loaded
The long clips play on the cgame's own clock (ads-next, coop_vmGunClipClock).
"""
import os, re
HERE = os.path.dirname(os.path.abspath(__file__))


def sub(fn, pairs):
    p = os.path.join(HERE, fn)
    s = open(p, encoding='utf-8').read()
    o = s
    for a, b in pairs:
        if b in s and a not in s:
            continue                                    # already applied
        assert a in s, (fn, a[:60])
        s = s.replace(a, b)
    if s != o:
        open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print(fn, 'patched' if s != o else 'unchanged')


sub('p12.py', [
    ("travel=['tt33_fire.skc', 'tt33_reload.skc'], pad=True),",
     "travel=['tt33_fire.skc', 'tt33_reload.skc']),   # no pad (bug-3736): `reload` is the server's row and stays as released"),
])
sub('welrod.py', [
    ("        s = p12.patch_tik(stem, s, {k: clips[k] for k in ('reload', 'reload_ads_loaded', 'reload_ads_empty')},",
     "        s = p12.patch_tik(stem, s, {k: clips[k] for k in ('reload_ads_loaded', 'reload_ads_empty')},      # `reload` = the server's row: as released (bug-3736)"),
    ("             + blk + '%sfire%s%s\\n' % (mm.group(1), mm.group(2), clips['fire']) + s[mm.end():])",
     "             + blk + s[mm.start():mm.end()] + s[mm.end():])                                  # `fire` = the server's row: as released (bug-3736)"),
    ("    clips = dict(fire=gun_clip(root, 'coop_welrod_fire_hip.skc', 26, None, tmpl), fire_ads=",
     "    clips = dict(fire_ads="),
])
