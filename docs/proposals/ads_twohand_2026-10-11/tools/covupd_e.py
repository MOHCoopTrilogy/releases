"""coverage_status.json after the sway-envelope re-measure (runs pa18 / pa19 / pa20; pistol lane 2026-10-13).
    python covupd_e.py [stances.json]     (stances.json = centrebox.py --json of the stance demos, keys <gun>@<stance>_empty)"""
import json, os, sys
P = r'C:\mohaa-coop-dev\docs\proposals\ads_twohand_2026-10-11\tools\coverage_status.json'
d = json.load(open(P))
ST = json.load(open(sys.argv[1])) if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]) else {}
SRUN = sorted(set(v.get('run', '') for v in ST.values()))


def T(stem):
    return 'models/weapons/%s.tik' % stem


def stance_note(g):
    r = ['%s %.1f' % (k.split('@')[1].replace('_empty', ''), v['xmax']) for k, v in sorted(ST.items()) if k.startswith(g + '@') and v.get('env')]
    return ('; emptied reload beyond the sway envelope per stance (%s): %s %%' % (' '.join(SRUN), ', '.join(r))) if r else ''


KEY = dict(beretta='it_w_beretta')
NO6 = dict(welrod='0.00 / 0.03', tt33silenced='0.01 / 0.14', berettasilenced='0.02 / 0.77', nambu='0.02 / 0.01', colt45='0.01 / 0.79', beretta='0.02 / 1.29')
ALL = dict(lugerp08='0.02 / 0.03', lugerp08silenced='0.02 / 0.02', mauser_c96='0.05 / 0.02', ppk='0.03 / 1.42', tt33='0.05 / 0.38',
           colt45_coltpa='0.07 / 0.93', colt_silenced='0.05 / 0.59', p38silenced='0.08 / 0.05', p38='0.07 / 0.85')
ALL.update(NO6)
for g, fig in ALL.items():
    e = d[T(KEY.get(g, g))]
    ru = e.setdefault('rule', {})
    if 'pa18' not in ru.get('run', ''):
        ru['run'] = 'pa18 (stand, sway envelope), ' + ru.get('run', '')
    if g in NO6:
        ru['target'] = 'yes'
        q = e.get('qa', '')
        q = q.split('; on target NO')[0]
        e['qa'] = q + '; on target (2026-10-13): against the settled aim\'s sway envelope, run pa18, loaded / emptied %s %% - the earlier 2-4 %% readings were the aim\'s own sway at another phase (bug: sway envelope)' % fig
    else:
        e['qa'] = e.get('qa', '') + ('' if 'sway envelope' in e.get('qa', '') else '; pa18 against the sway envelope: loaded / emptied %s %%' % fig)
    sn = stance_note(g)
    if sn and 'per stance' not in e['qa']:
        e['qa'] += sn
e = d[T('mauser_c96')]
if 'pa19' not in e['qa']:
    e['qa'] += ('; pa19 (2026-10-13, UNFINISHED): clip strip + eight rounds + bolt bar (2.0 u travel) + open port added to the mesh, the rounds go down and the strip is pulled and flicked - the hand does not travel with the rounds, the rounds read small; '
                'an existing prop pair (models/ammo/coop_c96_stripper_full / _empty + the server attach timeline) was found afterwards and is NOT used - decision open')
e = d[T('p38silenced')]
if 'filler' not in e['qa'] or 'dark middle slot' in e['qa']:
    e['qa'] = e['qa'].replace('; the open slide shows a dark middle slot', '') + '; pa19: steel block fills the open slide\'s rear slot (comes flush only as the slide goes back)'
for g in ('lugerp08', 'lugerp08silenced'):
    e = d[T(g)]
    if 'frame 5' not in e['qa']:
        e['qa'] = e['qa'].replace('open toggle in the centre box for 0.2 s before the gun is down', 'the emptied gun is under the box by frame 5 of the reload (pa19; was 7) - the open toggle stands in the box only in the dry gun\'s own aim and while it travels (0.13 s)')
e = d[T('ppk')]
e['rule']['target'] = 'no'
if 'OVER the bar' not in e['qa']:
    e['qa'] += '; on target NO (pa20): emptied reload OVER the bar in crouch / prone / lean L (2.3 / 2.7 / 2.3 %) at the support thumb\'s sweep (clip frame 51) - needs its own hands row with a lower thumb'
e = d[T('it_w_beretta')]
if 'lean R 3.4' not in e['qa']:
    e['qa'] += '; lean R 3.4 % = the emptied gun\'s own locked-back pose at the start of the window, no hand in the box (frames looked at); 0.11 % with the dry pose in the reference (centrebox.py --dry)'
json.dump(d, open(P, 'w'), indent=1, sort_keys=True)
print('coverage_status updated', len(ALL), 'guns; stance notes from', SRUN)
