"""coverage_status.json after the server-side fix and the ship cut (runs pa21, pa23, pa24, ded pa21b; 2026-10-13).
    python covupd_f.py        idempotent"""
import json
P = r'C:\mohaa-coop-dev\docs\proposals\ads_twohand_2026-10-11\tools\coverage_status.json'
d = json.load(open(P))
TAG = 'server rows as released'


def T(stem):
    return 'models/weapons/%s.tik' % stem


SRV = ('; SERVER SIDE FIXED (2026-10-13, bug-3782): `reload` / `fire` are the released clips again, the long clips play on the cgame\'s own clock '
       '(ads-next e8e199be, coop_vmGunClipClock); dedicated server pa21b: fire row, reload row, refill, next shot, ammo = released; aimed run pa21 '
       'loaded / emptied %s %%, clips run to their end (GUNCLOCK trace), fire / switch during the reload traced')
for g, fig in (('welrod', '0.0 / 0.0'), ('tt33', '0.0 / 0.1'), ('tt33silenced', '0.0 / 0.0')):
    e = d[T(g)]
    q = e.get('qa', '').split('; DO NOT SHIP')[0].split('; SERVER SIDE FIXED')[0]
    e['qa'] = q + SRV % fig
    ru = e.setdefault('rule', {})
    if 'pa21' not in ru.get('run', ''):
        ru['run'] = 'pa21 (stand, server rows as released), ' + ru.get('run', '')
# stances measured in pa23 (emptied reload, sway envelope, dry-pose rule)
ST = dict(tt33='0.0, 0.1, 0.3, 0.3', colt45_coltpa='0.1, 0.0, 1.2, 0.2', p38silenced='0.1, 0.2, 0.4, 0.3', p38='0.1, 0.1, 0.3, 0.3',
          colt_silenced='0.1, 0.0, 2.4, 0.2')
for g, fig in ST.items():
    e = d[T(g)]
    if 'pa23' not in e.get('qa', ''):
        e['qa'] = e.get('qa', '') + '; emptied reload beyond the sway envelope per stance (pa23: crouch, prone, lean L, lean R): %s %%' % fig
        if g == 'colt_silenced':
            e['qa'] += ' - lean L 2.4 % in 7 frames = the last shot\'s muzzle smoke drifting through the box, no hand in it, gun as in its dry pose (frames looked at)'
        ru = e.setdefault('rule', {})
        ru['run'] = 'pa23 (stances, sway envelope), ' + ru.get('run', '')
# PPK: its own emptied row
e = d[T('ppk')]
if 'pa23' not in e.get('qa', ''):
    e['qa'] = (e.get('qa', '').split('; on target NO')[0]
               + '; OWN EMPTIED ROW (2026-10-13): coopr_walther_ppk_reload_empty_ads = the Colt clip baked with the support thumb lower (PB_THUMB 0.15); '
                 'emptied reload beyond the sway envelope, run pa23: stand 0.1, crouch 0.1, prone 0.1, lean L 0.3, lean R 0.2 % (was 1.4 / 2.3 / 2.7 / 2.3 / 0.5); '
                 'thumb sweep not looked at up close')
    ru = e.setdefault('rule', {})
    ru['target'] = 'yes'
    ru['run'] = 'pa23 (stand + stances, own emptied row), ' + ru.get('run', '')
# the dry-pose rule is the default now: pa20 re-read
DRY = dict(it_w_beretta='0.2, 0.1, 0.5, 0.1', berettasilenced='0.1, 0.0, 0.5, 0.2', colt45='0.1, 0.1, 0.3, 0.2', welrod='0.5, 0.3, 0.3, 0.2',
           tt33silenced='0.6, 0.0, 0.4, 0.2', nambu='0.0, 0.1, 0.3, 0.3', lugerp08='0.1, 0.1, 0.3, 0.3', lugerp08silenced='0.1, 0.1, 0.4, 0.3')
for g, fig in DRY.items():
    e = d[T(g)]
    if 'dry-pose rule' not in e.get('qa', ''):
        e['qa'] = e.get('qa', '') + '; pa20 re-read with the dry-pose rule as the default (crouch, prone, lean L, lean R): %s %%' % fig
# held out of the ship cut
for g, why in (('mauser_c96', 'stripper clip unfinished'), ('m10_revolver', 'another player always sees six chamber heads (by the code, not run)')):
    e = d[T(g)]
    if 'SHIP CUT' not in e.get('qa', ''):
        e['qa'] = e.get('qa', '') + '; HELD OUT of the SHIP CUT 2026-10-13 (%s): ships as released (run pa24)' % why
json.dump(d, open(P, 'w'), indent=1)
print('coverage_status.json updated')
