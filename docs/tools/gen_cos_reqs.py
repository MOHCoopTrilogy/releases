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

# cosReq2/cosReq3 are 130px wide at verdana-12 (coop_loadout.urc). Measured against the overflow
# the user photographed, that is a little over 40 characters before the field clips. 40 is used so
# a slightly wide glyph run still lands inside, and the text is broken on WORD boundaries so a line
# never ends mid-word.
REQ_COLS = 40


def wrap2(text):
    """Split a condition across the two available lines, on word boundaries."""
    words = ' '.join((text or '').split()).split(' ')
    l1, l2 = '', ''
    for w in words:
        if not l1 or len(l1) + 1 + len(w) <= REQ_COLS:
            l1 = (l1 + ' ' + w).strip()
        elif not l2 or len(l2) + 1 + len(w) <= REQ_COLS:
            l2 = (l2 + ' ' + w).strip()
        else:
            # genuinely longer than two lines - say so rather than clipping mid-word silently
            if not l2.endswith('...'):
                l2 = (l2[:REQ_COLS - 3]).rstrip() + '...'
            break
    return l1, l2


def unlock_map():
    """asset path (lowercase) -> human 'how to earn it' line."""
    out = {}
    src = read(os.path.join(MOD, 'coop_mod', 'challenges.scr'))
    pat = (r'chal_def\s+"([^"]+)"\s+"([^"]+)"\s+"([^"]*)"\s+"([^"]*)"'
           r'(?:\s+"([^"]*)"\s+(\S+)\s+"([^"]*)")?')
    for m in re.finditer(pat, src):
        reward = (m.group(7) or '').strip().lower()
        if reward.startswith('models/'):
            # [user 2026-08-23] LINE 2 USED TO REPEAT THE TITLE. Line 1 (coop_loCosReq) already
            # reads "UNLOCK: <title> -", so spending line 2 on "Challenge: <title>" said the same
            # thing twice and left ONE 130px line for the actual condition - which then ran off the
            # end ("Save the trooper hanging from the power pole o"). Both lines now carry the
            # condition, word-wrapped, which roughly doubles the room and removes the duplication.
            out[reward] = wrap2(m.group(4))
    xp = read(os.path.join(MOD, 'coop_mod', 'xp.scr'))
    names = dict(re.findall(r'coop_xp_rankName\[(\d+)\]\s*=\s*"([^"]+)"', xp))
    # [user 2026-08-23] GREEDY .* ON THE SECOND SUBSCRIPT. xp.scr writes rank grants two ways:
    #   coop_xp_rankUnlock[1][0]                                = "..."
    #   coop_xp_rankUnlock[10][ level.coop_xp_rankUnlockCnt[10] ] = "..."
    # The second form contains a nested ']', so a [^\]]* class silently skips every uniform
    # granted that way - 16 of them - and they kept the generic "Earn via rank or challenge"
    # hover the user reported. This is the SAME defect that was found and fixed in
    # armory_unlocks.py earlier the same day; it existed independently in this file too.
    for m in re.finditer(r'coop_xp_rankUnlock\[(\d+)\]\[.*\]\s*=\s*"([^"]+)"', xp):
        rank, asset = m.group(1), m.group(2).strip().lower()
        # a challenge reward wins if both grant the same asset - it is the more specific story
        out.setdefault(asset, ('Reach the rank of', names.get(rank, 'rank ' + rank)))
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
