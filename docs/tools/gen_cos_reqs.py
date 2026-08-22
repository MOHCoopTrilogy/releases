#!/usr/bin/env python3
"""
Rewrite the armory cosmetic hover text with the REAL unlock path.

[user 2026-08-21] "Some of the weapons, uniforms, and helmets in the armory say 'Earn via
rank or challenge' instead of specifically stating what challenge or rank unlocks it."

Every skin/helmet hover cfg shipped the same generic placeholder, while the authoritative
mapping already exists in code twice over:
  - challenges.scr: chal_def's 7th argument is the reward asset (the same field
    UNLOCKABLES.md is generated from)
  - xp.scr: level.coop_xp_rankUnlock[rank][i] = asset, with coop_xp_rankName[] for display

This derives the hover from those tables, so it can never drift. Unmatched cosmetics keep a
fallback line and are COUNTED loudly - silence is how the placeholder shipped in the first
place.
"""
import io, os, re, glob, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD  = os.path.join(ROOT, 'hzm-mohaa-coop-mod')

def read(p):
    return io.open(p, encoding='utf-8', errors='replace').read().replace('\r\n', '\n')

def unlock_map():
    """asset path (lowercase) -> human 'how to earn it' line."""
    out = {}
    src = read(os.path.join(MOD, 'coop_mod', 'challenges.scr'))
    pat = (r'chal_def\s+"([^"]+)"\s+"([^"]+)"\s+"([^"]*)"\s+"([^"]*)"'
           r'(?:\s+"([^"]*)"\s+(\S+)\s+"([^"]*)")?')
    for m in re.finditer(pat, src):
        reward = (m.group(7) or '').strip().lower()
        if reward.startswith('models/'):
            out[reward] = ('Challenge: %s' % m.group(3), m.group(4))
    xp = read(os.path.join(MOD, 'coop_mod', 'xp.scr'))
    names = dict(re.findall(r'coop_xp_rankName\[(\d+)\]\s*=\s*"([^"]+)"', xp))
    for m in re.finditer(r'coop_xp_rankUnlock\[(\d+)\]\[[^\]]*\]\s*=\s*"([^"]+)"', xp):
        rank, asset = m.group(1), m.group(2).strip().lower()
        # a challenge reward wins if both grant the same asset - it is the more specific story
        out.setdefault(asset, ('Rank: %s' % names.get(rank, 'rank ' + rank),
                               'Reach this rank to unlock'))
    return out

def main():
    um = unlock_map()
    print('  unlock table: %d assets (challenges + ranks)' % len(um))
    touched = matched = 0
    unmatched = []
    for pat, modkey in (('skin/s*.cfg', 'coop_loChar'), ('helm/h*.cfg', 'coop_loHelm')):
        for f in sorted(glob.glob(os.path.join(MOD, 'ui', 'loadout', pat))):
            d = read(f)
            mm = re.search(r'set %s\s+"([^"]+)"' % modkey, d)
            if not mm:
                continue
            tik = mm.group(1).strip().lower()
            # _nohat / variant suffixes: the unlock table stores the base tik
            base = re.sub(r'_(nohat|fps)\.tik$', '.tik', tik)
            hit = um.get(tik) or um.get(base)
            if not hit:
                if 'set coop_loCosReq2' in d:
                    unmatched.append(os.path.basename(f))
                continue
            line2, line3 = hit
            nd = re.sub(r'set coop_loCosReq2\s+"[^"]*"', 'set coop_loCosReq2 "%s"' % line2, d)
            nd = re.sub(r'set coop_loCosReq3\s+"[^"]*"', 'set coop_loCosReq3 "%s"' % line3, nd)
            if nd != d:
                io.open(f, 'w', encoding='utf-8', newline='\n').write(nd)
                touched += 1
            matched += 1
    print('  matched %d cosmetics to a real unlock path; rewrote %d cfgs' % (matched, touched))
    if unmatched:
        print('  UNMATCHED (kept generic text): %d' % len(unmatched))
        for u in unmatched[:10]:
            print('    ', u)
        if len(unmatched) > 10:
            print('     ... and %d more' % (len(unmatched) - 10))
    return 0

if __name__ == '__main__':
    sys.exit(main())
