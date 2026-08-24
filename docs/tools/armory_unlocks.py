#!/usr/bin/env python3
"""
ARMORY UNLOCK AUDIT - every gun, helmet and uniform in the armory, and the exact thing that
unlocks it.

WHY THIS EXISTS (2026-08-23). The user reported that armory items say they unlock "through
challenges or rank" without naming WHICH challenge or WHICH rank. Two questions follow, and
neither could be answered by reading the scripts by hand:

  1. Is the requirement KNOWABLE at all - does every gated item actually have a source? A gated
     item with no challenge and no rank granting it is PERMANENTLY UNOBTAINABLE, and nothing in
     the game would ever say so. That is a silent defect of exactly the shape this project keeps
     paying for.
  2. What IS the specific requirement, so the UI can print it instead of a shrug?

This is a derived inventory, so per .wolf/OPENWOLF.md it is GENERATED, never hand-written.

    python docs/tools/armory_unlocks.py           # summary + problems only
    python docs/tools/armory_unlocks.py --full    # every item with its requirement
    python docs/tools/armory_unlocks.py --text    # emit the per-item requirement STRINGS,
                                                  # ready to feed the in-game lock caption

THE MODEL, as read out of the scripts (not assumed):
  guns      loadoutroster.scr   local.r["give"] = "<tik>"   gated unless one of 4 free starters
                                (loadoutpick.scr::loadout_isUnlocked)
  helmets   helmet.scr          coop_helmetTik[N]           gated iff listed in coop_cosmeticGatedTok
  uniforms  helmet.scr          coop_armorySkins[N]         token = models/player/<skin>.tik, same gate
  sources   xp.scr              coop_xp_rankUnlock[R][..]   -> "Reach rank R"
            challenges.scr      chal_def(..., <reward tik>) -> that challenge's title + description

IMPORTANT SEMANTIC, easy to get backwards: cosmetic_gatedBuild is an ALLOW-LIST of things that
REQUIRE unlocking. A cosmetic that is NOT in that set is free to everyone - even if a challenge
reward points at it. So "challenge exists" does not imply "item is gated", and the audit reports
those two facts separately.
"""
import io
import os
import re
import sys

MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'
CO = os.path.join(MOD, 'coop_mod')

# loadoutpick.scr::loadout_isUnlocked - hardcoded free starters
FREE_GUNS = {
    'models/weapons/m1_garand.tik',
    'models/weapons/thompsonsmg.tik',
    'models/weapons/colt45.tik',
    'models/weapons/m2frag_grenade_sp_start.tik',
}


def rd(name):
    p = os.path.join(CO, name)
    if not os.path.exists(p):
        return ''
    return io.open(p, encoding='utf-8', errors='replace').read()


def strip_comments(t):
    """Drop // line comments so a commented-out definition is not counted as live."""
    return '\n'.join(line.split('//')[0] for line in t.splitlines())


def collect():
    helmet = strip_comments(rd('helmet.scr'))
    roster = strip_comments(rd('loadoutroster.scr'))
    xp = strip_comments(rd('xp.scr'))
    chal = strip_comments(rd('challenges.scr'))

    helmets = {}
    for m in re.finditer(r'coop_helmetName\[(\d+)\]\s*=\s*"([^"]*)"', helmet):
        helmets.setdefault(int(m.group(1)), ['', ''])[0] = m.group(2)
    for m in re.finditer(r'coop_helmetTik\[(\d+)\]\s*=\s*"([^"]*)"', helmet):
        helmets.setdefault(int(m.group(1)), ['', ''])[1] = m.group(2)

    skins = {}
    for m in re.finditer(r'coop_armorySkins\[(\d+)\]\s*=\s*"([^"]*)"', helmet):
        skins[int(m.group(1))] = m.group(2)

    # loadoutroster.scr writes give BEFORE name inside each `case` block:
    #     local.r["give"] = "models/weapons/kar98.tik"
    #     local.r["name"] = "KAR98K"
    # so latching the name and emitting on give pairs every token with the PREVIOUS gun's name -
    # which made the audit claim the M1 Garand (a free starter) needed rank 1. Latch the give and
    # emit on the name instead. The generated .scr was never affected because it keys on the token,
    # but a wrong label in an audit is how a real finding gets dismissed as noise.
    guns = []
    pending = None
    for line in roster.splitlines():
        m = re.search(r'r\["give"\]\s*=\s*"([^"]+)"', line)
        if m:
            pending = m.group(1)
            continue
        m = re.search(r'r\["name"\]\s*=\s*"([^"]*)"', line)
        if m and pending:
            guns.append((m.group(1), pending))
            pending = None

    # [bug-2080] Gloves are the third cosmetic family and live in their own file. Their tokens are
    # bare ids (glv_*), not tik paths, because a glove is a shader index on a surface the model
    # already has rather than a file to load.
    gl = strip_comments(rd('gloves.scr'))
    gloves = {}
    for m in re.finditer(r'coop_gloveName\[(\d+)\]\s*=\s*"([^"]*)"', gl):
        gloves.setdefault(int(m.group(1)), ['', ''])[0] = m.group(2)
    for m in re.finditer(r'coop_gloveTok\[(\d+)\]\s*=\s*"([^"]*)"', gl):
        gloves.setdefault(int(m.group(1)), ['', ''])[1] = m.group(2)

    gated = set(re.findall(r'coop_cosmeticGatedTok\["([^"]+)"\]\s*=\s*1', helmet))

    src = {}
    # NOTE the greedy .* on the second subscript. xp.scr writes rank grants TWO ways:
    #   coop_xp_rankUnlock[1][0]                              = "..."
    #   coop_xp_rankUnlock[3][ level.coop_xp_rankUnlockCnt[3] ] = "..."
    # The second form contains a nested ']', so a [^\]]* class silently misses every uniform
    # granted that way - which is all 16 of them, and they then read as UNOBTAINABLE. Caught by
    # noticing the tool's own output contradicted xp.scr, not by the tool. Greedy .* to the last
    # ']' before the '=' handles both.
    for m in re.finditer(r'coop_xp_rankUnlock\[(\d+)\]\[.*\]\s*=\s*"([^"]+)"', xp):
        src.setdefault(m.group(2), []).append('Reach rank %s' % m.group(1))

    # chal_def <id> <cat> <title> <desc> <stat> <target> <reward>
    for line in chal.splitlines():
        if 'chal_def' not in line:
            continue
        q = re.findall(r'"([^"]*)"', line)
        if len(q) < 5:
            continue
        cid, title, desc = q[0], q[2], q[3]
        # The reward is the last quoted field, but chal_def's `stat` is also quoted, so a challenge
        # with NO reward would otherwise have its stat read as one. A reward is either an asset path
        # (contains '/') or one of the non-asset token families. glv_ was added with the glove row
        # and its absence here made all three challenge-gated gloves read as UNOBTAINABLE - caught
        # by this tool contradicting challenges.scr, which is what it is for.
        rw = q[-1]
        reward = rw if ('/' in rw or rw.startswith(('glv_', 'perk_', 'finish_'))) else ''
        if reward:
            src.setdefault(reward, []).append('%s - %s  [%s]' % (title, desc, cid))

    return helmets, skins, guns, gated, src, gloves


def build_rows(helmets, skins, guns, gated, src, gloves):
    rows = []   # (section, display, token, gated, [requirements])
    for name, tik in guns:
        if tik in FREE_GUNS:
            rows.append(('GUN', name, tik, False, ['Free starter']))
        else:
            rows.append(('GUN', name, tik, True, src.get(tik, [])))
    for i in sorted(helmets):
        disp, tok = helmets[i]
        if tok in ('std', 'none', ''):
            rows.append(('HELMET', disp, tok, False, ['Always available']))
        elif tok in gated:
            rows.append(('HELMET', disp, tok, True, src.get(tok, [])))
        else:
            rows.append(('HELMET', disp, tok, False, ['UNGATED - free to everyone']))
    for i in sorted(skins):
        base = skins[i]
        tok = 'models/player/%s.tik' % base
        if tok in gated:
            rows.append(('UNIFORM', base, tok, True, src.get(tok, [])))
        else:
            rows.append(('UNIFORM', base, tok, False, ['UNGATED - free to everyone']))
    # [bug-2080] GLOVES, the third cosmetic family. Their tokens are bare ids (glv_*) rather than
    # tik paths, because a glove is a shader index on a surface the model already has, not a file.
    for i in sorted(gloves):
        disp, tok = gloves[i]
        if not tok:
            continue
        if tok in gated:
            rows.append(('GLOVE', disp, tok, True, src.get(tok, [])))
        else:
            rows.append(('GLOVE', disp, tok, False, ['Free starter']))
    return rows


def sanitise(s):
    """Make a requirement string safe to paste into a .scr string literal.

    MOHAA parse killers are unforgiving and kill the WHOLE file silently (docs/TRAPS.md): a single
    em-dash or stray double quote in a challenge title would take down the entire generated script
    and with it the armory. Challenge titles are authored prose, so they genuinely contain both.
    """
    s = s.replace('"', "'")
    s = s.replace('—', '-').replace('–', '-').replace('’', "'")
    s = ''.join(c for c in s if 32 <= ord(c) < 127)
    return ' '.join(s.split())


def requirement_text(reqs):
    """One short player-facing line. Rank first when available - it is concrete and short."""
    if not reqs:
        return 'Not currently obtainable'
    ranks = [r for r in reqs if r.startswith('Reach rank ')]
    chals = [r for r in reqs if not r.startswith('Reach rank ')]
    if ranks:
        out = ranks[0]
        if chals:
            out += ', or challenge: ' + chals[0].split(' - ')[0]
    else:
        c = chals[0]
        title = c.split(' - ')[0]
        desc = c.split(' - ', 1)[1].rsplit('  [', 1)[0] if ' - ' in c else ''
        out = 'Challenge: %s - %s' % (title, desc)
    extra = len(reqs) - 1
    if extra > 0 and not (ranks and chals and extra == 1):
        out += ' (+%d other way%s)' % (extra, '' if extra == 1 else 's')
    # 80 chars: loadout_deny prefixes "Armory: <gun name> is LOCKED - ", and the whole thing goes
    # through a single iprint line. Long enough to name a challenge and its condition, short enough
    # to stay one readable line on screen.
    return sanitise(out)[:80]


def emit_scr(rows, path):
    """Write the generated requirement table the game reads for its lock captions."""
    lines = []
    lines.append('//=========================================================================')
    lines.append('// GENERATED by docs/tools/armory_unlocks.py --emit   DO NOT EDIT BY HAND')
    lines.append('//=========================================================================')
    lines.append('// The armory used to tell players a locked item was earned "via challenges/ranks"')
    lines.append('// without naming which one (user report, 2026-08-23). The requirement was always')
    lines.append('// knowable - it is just spread across challenges.scr rewards and xp.scr rank grants -')
    lines.append('// so this table is swept out of those two files rather than written by hand, which')
    lines.append('// means it cannot drift away from the thing it describes.')
    lines.append('//')
    lines.append('// Rebuild:  python docs/tools/armory_unlocks.py --emit')
    lines.append('//=========================================================================')
    lines.append('')
    lines.append('main:{')
    lines.append('\tif( level.coop_unlockReqBuilt == 1 ){ end }')
    lines.append('\tlevel.coop_unlockReqBuilt = 1')
    n = 0
    for sec, disp, tok, g, reqs in rows:
        if not g:
            continue
        lines.append('\tlevel.coop_unlockReq["%s"] = "%s"' % (tok, requirement_text(reqs)))
        n += 1
    lines.append('}end')
    lines.append('')
    body = '\n'.join(lines)
    io.open(path, 'w', encoding='ascii', errors='replace', newline='\n').write(body)
    return n


def main():
    full = '--full' in sys.argv
    text = '--text' in sys.argv
    emit = '--emit' in sys.argv

    helmets, skins, guns, gated, src, gloves = collect()
    rows = build_rows(helmets, skins, guns, gated, src, gloves)

    known = {r[2] for r in rows}
    # perk_ and finish_ are legitimate NON-ARMORY reward families (engine perks and the skin
    # finish strip), so they are not dead just because no armory page lists them.
    orphans = sorted(t for t in src
                     if t not in known and not t.startswith(('perk_', 'finish_')))
    unobtainable = [r for r in rows if r[3] and not r[4]]
    ungated = [r for r in rows if r[0] in ('HELMET', 'UNIFORM', 'GLOVE') and not r[3]
               and r[4] and r[4][0].startswith('UNGATED')]
    multi = [r for r in rows if r[3] and len(r[4]) > 1]

    if text:
        for sec, disp, tok, g, r in rows:
            if not g:
                continue
            print('%s\t%s\t%s' % (tok, disp, requirement_text(r)))
        return 0

    if emit:
        out = os.path.join(CO, 'unlockreq_gen.scr')
        n = emit_scr(rows, out)
        print('wrote %s  (%d gated items with a stated requirement)' % (out, n))
        if unobtainable:
            print('WARNING: %d gated item(s) have NO source and will read '
                  '"Not currently obtainable"' % len(unobtainable))
        return 0

    print('ARMORY UNLOCK AUDIT')
    print('  guns %d | helmets %d | uniforms %d | gloves %d | gated %d | sources %d'
          % (len(guns), len(helmets), len(skins), len(gloves), len(gated), len(src)))
    print()

    print('== UNOBTAINABLE - gated, but NOTHING grants it (%d)' % len(unobtainable))
    if unobtainable:
        for sec, disp, tok, _g, _r in unobtainable:
            print('   %-8s %-34s %s' % (sec, disp[:34], tok))
    else:
        print('   none - every gated item has at least one source.')
    print()

    print('== UNGATED COSMETICS - listed in the armory, gated by nothing (%d)' % len(ungated))
    for sec, disp, tok, _g, _r in ungated[:45]:
        note = ''
        if tok in src:
            note = '   <-- a challenge/rank points at it, but the gate list omits it'
        print('   %-8s %-34s %s%s' % (sec, disp[:34], tok, note))
    if len(ungated) > 45:
        print('   ... and %d more' % (len(ungated) - 45))
    print()

    print('== DEAD REWARDS - a source unlocks a token no armory page lists (%d)' % len(orphans))
    for t in orphans[:45]:
        print('   %-56s <- %s' % (t[:56], '; '.join(src[t])[:64]))
    if len(orphans) > 45:
        print('   ... and %d more' % (len(orphans) - 45))
    print()

    print('== MULTIPLE SOURCES - reachable more than one way (%d)' % len(multi))
    for sec, disp, tok, _g, r in multi[:20]:
        print('   %-8s %-26s %s' % (sec, disp[:26], ' | '.join(x[:46] for x in r)))
    print()

    if full:
        print('== FULL ITEM LIST')
        for sec in ('GUN', 'HELMET', 'UNIFORM', 'GLOVE'):
            print('-- %s' % sec)
            for s, disp, tok, g, r in rows:
                if s != sec:
                    continue
                req = r[0] if r else '*** NOTHING GRANTS THIS ***'
                print('   %-30s %-50s %s' % (disp[:30], tok[:50], req[:92]))
            print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
