r"""Shotgun: FIRING BREAKS OFF THE RELOAD (user 2026-10-12: "break off the reload") - a patch for coop_mod/player_Torso.st.

Retail: `RELOAD_SHOTGUN_END : +ATTACK_PRIMARY HAS_AMMO_IN_CLIP "mainhand" !RELOAD` in the loop state. RELOAD is the
weapon's "wants to go on reloading" latch (set by CHECK_CONTINUE's `reload`, cleared by clip_add): the press only
counted in the part of each loop AFTER the shell was counted, never during the start, and it is an edge - a press that
came too early was simply lost (run hj13: two presses, the reload ran to the full tube both times, no shot). And
nothing fired afterwards unless the trigger was still down.

Now (the revolvers' recipe, pistol lane tools/patch_breakfire.py):
  RELOAD_SHOTGUN (start) and RELOAD_SHOTGUN_SINGLE:  +ATTACK_PRIMARY with a round in the gun -> RELOAD_SHOTGUN_BREAK_END
  RELOAD_SHOTGUN_BREAK_END   = the end row as it is (the gun comes back up; the pump when it was empty - cgame), with the
                               latch dropped (`donereloading`), then
  RELOAD_SHOTGUN_BREAK_FIRE  -> the OWED SHOT (aimed or hip attack state) when a round is in, else STAND
An empty gun cannot break off before its first shell is in (HAS_AMMO_IN_CLIP).

    python patch_sgbreak.py <tree>      (<tree>/coop_mod/player_Torso.st; idempotent)
The state file is shared by every lane: this is a PATCH, apply it to the final tree - do not copy the lane's staged file.
"""
import io, os, re, sys
p = os.path.join(sys.argv[1], 'coop_mod', 'player_Torso.st')
s = io.open(p, encoding='latin-1', newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
if 'RELOAD_SHOTGUN_BREAK_END' in s:
    print('already patched'); sys.exit(0)
TAG = '// HZM coop [heavy lane 2026-10-13, patch_sgbreak.py]'


def state(name):
    m = re.search(r'(?m)^state %s[ \t]*\r?\n\{' % name, s)
    assert m, name
    e = s.index(nl + '}', m.end())
    return m.start(), e + len(nl) + 1


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
assert 'state ATTACK_SHOTGUN_PRIMARY_AIM' in s and 'state ATTACK_SHOTGUN_PRIMARY' in s
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
print('patched', p)
