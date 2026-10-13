r"""Shotgun: FIRING BREAKS OFF THE RELOAD (user 2026-10-12: "break off the reload") - a patch for coop_mod/player_Torso.st.

Retail: `RELOAD_SHOTGUN_END : +ATTACK_PRIMARY HAS_AMMO_IN_CLIP "mainhand" !RELOAD` in the loop state. RELOAD is the
weapon's "wants to go on reloading" latch (set by CHECK_CONTINUE's `reload`, cleared by clip_add): the press only
counted in the part of each loop AFTER the shell was counted, never during the start, and it is an edge - a press that
came too early was simply lost (run hj13: two presses, the reload ran to the full tube both times, no shot). And
nothing fired afterwards unless the trigger was still down.

STAGE 1 (the revolvers' recipe, pistol lane tools/patch_breakfire.py):
  RELOAD_SHOTGUN (start) and RELOAD_SHOTGUN_SINGLE:  +ATTACK_PRIMARY with a round in the gun -> RELOAD_SHOTGUN_BREAK_END
  RELOAD_SHOTGUN_BREAK_END   = the end row as it is (the gun comes back up; the pump when it was empty - cgame), with the
                               latch dropped (`donereloading`), then
  RELOAD_SHOTGUN_BREAK_FIRE  -> the OWED SHOT (aimed or hip attack state) when a round is in, else STAND
An empty gun cannot break off before its first shell is in (HAS_AMMO_IN_CLIP).

STAGE 2 (fifth agent, 2026-10-13: 1.18 s from the press to the shot was the whole end row - too slow when a round is
already chambered and nothing has to be pumped):
  The state machine has no memory, so "the reload began with rounds in the gun" is carried by WHICH states run:
  RELOAD_SHOTGUN : ANIMDONE_TORSO with a round in the gun (no shell has been counted yet in the start state, so that
  is the gun's state when the reload began) -> RELOAD_SHOTGUN_SINGLE_CH / RELOAD_SHOTGUN_CHECK_CONTINUE_CH, copies of
  the loop pair whose break-off goes to
  RELOAD_SHOTGUN_BREAK_QUICK = torso row `shotgun_reload_break` (0.37 s: hand back to the forend, no pump; row added to
                               anims_shotgun.txt by stage_sgreload.py), latch dropped, then RELOAD_SHOTGUN_BREAK_FIRE.
                               It sends `viewmodelanim reload_end` TWICE: the client sees the change counter step by
                               two and plays the hands row `<row>_break` (+ `_ads`) - cgame apply_sgbreak.py. A client
                               without that cgame plays its normal end row and is cut by the shot.
  A reload that began EMPTY keeps stage 1 (the pump has to be worked: RELOAD_SHOTGUN_BREAK_END, 1.2 s).
  The normal, uninterrupted reload is not retimed: same rows, same lengths, in both chains.

    python patch_sgbreak.py <tree>      (<tree>/coop_mod/player_Torso.st; idempotent; upgrades a stage-1 file)
The state file is shared by every lane: this is a PATCH, apply it to the final tree - do not copy the lane's staged file.
"""
import io, os, re, sys
p = os.path.join(sys.argv[1], 'coop_mod', 'player_Torso.st')
s = io.open(p, encoding='latin-1', newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
TAG = '// HZM coop [heavy lane 2026-10-13, patch_sgbreak.py]'


def state(name):
    m = re.search(r'(?m)^state %s[ \t]*\r?\n\{' % name, s)
    assert m, name
    e = s.index(nl + '}', m.end())
    return m.start(), e + len(nl) + 1


done = []
if 'RELOAD_SHOTGUN_BREAK_END' not in s:
    # 1. the loop: the early-out no longer waits for the latch, and goes to the break states
    a, b = state('RELOAD_SHOTGUN_SINGLE')
    blk = s[a:b]
    old = re.search(r'(?m)^[ \t]*RELOAD_SHOTGUN_END[ \t]*:[ \t]*\+ATTACK_PRIMARY HAS_AMMO_IN_CLIP "mainhand" !RELOAD[^\r\n]*', blk)
    assert old
    blk = blk[:old.start()] + '\t\tRELOAD_SHOTGUN_BREAK_END\t: +ATTACK_PRIMARY HAS_AMMO_IN_CLIP "mainhand"\t' + TAG + ' the trigger breaks the reload off at any point of the loop' + blk[old.end():]
    s = s[:a] + blk + s[b:]
    # 2. the start: the same, when rounds are in the gun
    a, b = state('RELOAD_SHOTGUN')
    blk = s[a:b]
    k = re.search(r'(?m)^[ \t]*RELOAD_SHOTGUN_SINGLE[ \t]*:[ \t]*ANIMDONE_TORSO[^\r\n]*', blk)
    assert k
    blk = blk[:k.start()] + '\t\tRELOAD_SHOTGUN_BREAK_END\t: +ATTACK_PRIMARY HAS_AMMO_IN_CLIP "mainhand"\t' + TAG + nl + blk[k.start():]
    s = s[:a] + blk + s[b:]
    # 3. the two new states, after RELOAD_SHOTGUN_END
    a, b = state('RELOAD_SHOTGUN_END')
    new = nl.join([
        '', '',
        TAG + ' the reload broken off by the trigger: the end row (the gun comes back up; cgame racks it only if it was',
        '// empty), the "go on reloading" latch dropped, then the owed shot',
        'state RELOAD_SHOTGUN_BREAK_END',
        '{',
        '\tmovetype legs',
        '\tentrycommands',
        '\t{',
        '\t\tweaponcommand mainhand donereloading',
        '\t\tviewmodelanim reload_end',
        '\t}',
        '\taction',
        '\t{',
        '\t\tshotgun_reload_end\t: default',
        '\t}',
        '\tstates',
        '\t{',
        '\t\tSTAND\t: KILLED',
        '\t\tRELOAD_INTERUPTED\t: NEW_WEAPON',
        '\t\tRELOAD_SHOTGUN_BREAK_FIRE\t: ANIMDONE_TORSO',
        '\t}',
        '}',
        '',
        'state RELOAD_SHOTGUN_BREAK_FIRE',
        '{',
        '\tmovetype legs',
        '\taction',
        '\t{',
        '\t\tnone\t: default',
        '\t}',
        '\tstates',
        '\t{',
        '\t\tSTAND\t: KILLED',
        '\t\tATTACK_SHOTGUN_PRIMARY_AIM\t: COOP_ADS HAS_AMMO_IN_CLIP "mainhand"',
        '\t\tATTACK_SHOTGUN_PRIMARY\t: HAS_AMMO_IN_CLIP "mainhand"',
        '\t\tSTAND\t: default',
        '\t}',
        '}'])
    s = s[:b] + new + s[b:]
    done.append('stage 1')

if 'RELOAD_SHOTGUN_BREAK_QUICK' not in s:
    TAG2 = TAG + ' [quick break-off]'
    # 4. the start state: a round is in the gun = it is chambered -> the quick break, and the chambered loop chain
    a, b = state('RELOAD_SHOTGUN')
    blk = s[a:b]
    assert blk.count('RELOAD_SHOTGUN_BREAK_END') == 1
    blk = blk.replace('RELOAD_SHOTGUN_BREAK_END', 'RELOAD_SHOTGUN_BREAK_QUICK')
    k = re.search(r'(?m)^[ \t]*RELOAD_SHOTGUN_SINGLE[ \t]*:[ \t]*ANIMDONE_TORSO[^\r\n]*', blk)
    assert k
    blk = (blk[:k.start()] + '\t\tRELOAD_SHOTGUN_SINGLE_CH\t: ANIMDONE_TORSO HAS_AMMO_IN_CLIP "mainhand"\t' + TAG2
           + ' rounds were in the gun when the reload began: the chambered chain' + nl + blk[k.start():])
    s = s[:a] + blk + s[b:]
    # 5. copies of the loop pair for the chambered chain (same rows, same timing; only the break-off target differs)
    a, b = state('RELOAD_SHOTGUN_SINGLE')
    single = s[a:b]
    assert single.count('RELOAD_SHOTGUN_BREAK_END') == 1 and single.count('RELOAD_SHOTGUN_CHECK_CONTINUE') == 1
    single = (single.replace('state RELOAD_SHOTGUN_SINGLE', 'state RELOAD_SHOTGUN_SINGLE_CH')
              .replace('RELOAD_SHOTGUN_BREAK_END', 'RELOAD_SHOTGUN_BREAK_QUICK')
              .replace('RELOAD_SHOTGUN_CHECK_CONTINUE', 'RELOAD_SHOTGUN_CHECK_CONTINUE_CH'))
    a, b = state('RELOAD_SHOTGUN_CHECK_CONTINUE')
    chk = s[a:b]
    assert len(re.findall(r'RELOAD_SHOTGUN_SINGLE\b', chk)) == 1
    chk = (chk.replace('state RELOAD_SHOTGUN_CHECK_CONTINUE', 'state RELOAD_SHOTGUN_CHECK_CONTINUE_CH')
           .replace('RELOAD_SHOTGUN_SINGLE', 'RELOAD_SHOTGUN_SINGLE_CH'))
    quick = nl.join([
        'state RELOAD_SHOTGUN_BREAK_QUICK',
        '{',
        '\tmovetype legs',
        '\tentrycommands',
        '\t{',
        '\t\tweaponcommand mainhand donereloading',
        '\t\tviewmodelanim reload_end',
        '\t\tviewmodelanim reload_end 1\t// the second one is the signal: the change counter steps by two = the quick break row',
        '\t}',
        '\taction',
        '\t{',
        '\t\tshotgun_reload_break\t: default',
        '\t}',
        '\tstates',
        '\t{',
        '\t\tSTAND\t: KILLED',
        '\t\tRELOAD_INTERUPTED\t: NEW_WEAPON',
        '\t\tRELOAD_SHOTGUN_BREAK_FIRE\t: ANIMDONE_TORSO',
        '\t}',
        '}'])
    a, b = state('RELOAD_SHOTGUN_BREAK_FIRE')
    new = nl.join([
        '', '',
        TAG2 + ' a reload that began with rounds in the gun (one is chambered): the same loop, and the trigger',
        '// breaks it off through a SHORT end (hand back to the forend, no pump) - about 0.45 s from the press to the shot',
        single, '', chk, '', quick])
    s = s[:b] + new + s[b:]
    done.append('stage 2')

if not done:
    print('already patched'); sys.exit(0)
assert 'state ATTACK_SHOTGUN_PRIMARY_AIM' in s and 'state ATTACK_SHOTGUN_PRIMARY' in s
for n_ in ('RELOAD_SHOTGUN_SINGLE_CH', 'RELOAD_SHOTGUN_CHECK_CONTINUE_CH', 'RELOAD_SHOTGUN_BREAK_QUICK', 'RELOAD_SHOTGUN_BREAK_END', 'RELOAD_SHOTGUN_BREAK_FIRE'):
    assert len(re.findall(r'(?m)^state %s[ \t]*\r?$' % n_, s)) == 1, n_
# brace depth must be 0 at every `state` line (a broken state file leaves the player without a torso state machine)
d = 0
for ln in s.split(nl):
    t = ln.split('//')[0]
    if t.startswith('state '):
        assert d == 0, ln
    d += t.count('{') - t.count('}')
    assert d >= 0, ln
assert d == 0
io.open(p, 'w', encoding='latin-1', newline='').write(s)
print('patched', p, '+'.join(done))
