"""coverage_status.json after list items D / E (run from tools/ after `coverage.py scan pa9 pa13 pa14 pa15 pa16`)"""
import json, os
P = r'C:\mohaa-coop-dev\docs\proposals\ads_twohand_2026-10-11\tools\coverage_status.json'
d = json.load(open(P))


def T(stem):
    return 'models/weapons/%s.tik' % stem


# the stance runs of D / E are EMPTIED reloads (tag stance <st>E): they are the reload entry of that stance
for k, e in d.items():
    r = e.get('reload')
    if isinstance(r, dict):
        for st in list(r):
            if st.endswith('E') and r[st].get('run', '').startswith('pa'):
                r[st[:-1]] = r.pop(st)
SEAT = dict(welrod='pa13', lugerp08='pa14', lugerp08silenced='pa13', mauser_c96='pa13', ppk='pa13', tt33='pa13', tt33silenced='pa13',
            colt45_coltpa='pa14', colt_silenced='pa14', berettasilenced='pa14', nambu='pa14', p38silenced='pa15', colt45='pa15', p38='pa15',
            it_w_beretta='pa15')
THUMB = 'support hand: magazine out / in below the screen edge; EMPTY: %s locked back, the support thumb sweeps the stop as the hand closes on the grip, it runs forward - shown; loaded: no action'
SP = {
    'welrod': dict(lowered=True, rule=('no', 'yes', 'yes', 'pa8 pa10 pa11 (stand), pa9 (stances), pa13 (seat)'),
                   action='BOLT ACTION by the support hand, after every aimed shot and at the end of an emptied reload: gun down under the centre box, hand over the rear, knob turned 55 deg, bolt pulled 2.0 u, run forward, turned shut - shown; loaded reload: no bolt work',
                   qa='pa11: GIFs decoded and looked at (cycle, loaded, emptied), stance sheet pa9 (crouch / prone / leans / braced) and seat sheet pa13 looked at; on target NO: loaded reload 0.6 / 2.8 / 1.3 % over three runs of the same clips; hip unchanged; aim pose new, not approved'),
    'lugerp08': dict(lowered=True, rule=('yes', 'yes', 'yes', 'pa10 (stand), pa9 (stances), pa14 (seat)'),
                     action='TOGGLE (two bones): up 50 deg while empty; emptied reload held under the centre box, support hand takes the knobs from above, pulls and lets go, it snaps shut - shown; loaded: magazine only',
                     qa='pa10: GIFs decoded and looked at, stance sheet pa9 and seat sheet pa14 looked at; open toggle in the centre box for 0.2 s before the gun is down; front link not articulated; aim pose new, not approved'),
    'lugerp08silenced': dict(lowered=True, rule=('yes', 'yes', 'yes', 'pa10 (stand), pa9 (stances), pa13 (seat)'), action='as the Luger P08 (same clips, own split mesh)',
                             qa='pa10: GIF decoded and looked at, stance sheet pa9 and seat sheet pa13 looked at'),
    'mauser_c96': dict(lowered=True, rule=('yes', 'yes', 'no', 'pa8 (stand), pa9 (stances), pa13 (seat)'),
                       action='own reload: gun straight down under the centre box, support hand strips a clip in from the top and lifts it out, bolt end forward as it leaves; loaded: the hand draws the bolt back first. NOT shown: the clip (no mesh - it is under the palm); only the bolt\'s rear end moves (0.42 u)',
                       qa='pa8: GIFs decoded and looked at, stance sheet pa9 and seat sheet pa13 looked at; lowered gun alone at the bottom of the frame for 0.35 s; Trench C96 not run'),
    'ppk': dict(rule=('yes', 'yes', 'yes', 'pa8 (stand), pa9 (stances), pa13 (seat)'), action=THUMB % 'slide', qa='pa8: GIF decoded and looked at, stance sheet pa9 and seat sheet pa13 looked at'),
    'tt33': dict(rule=('yes', 'yes', 'yes', 'pa8 (stand), pa9 (stances), pa13 (seat)'), action=THUMB % 'slide', qa='pa8: GIF decoded and looked at, stance sheet pa9 and seat sheet pa13 looked at; gun reload clip 7 -> 73 frames (server-side tik change, not tested on a dedicated server)'),
    'tt33silenced': dict(rule=('no', 'yes', 'yes', 'pa8 pa10 (stand), pa9 (stances), pa13 (seat)'), action=THUMB % 'slide', qa='pa10: GIF decoded and looked at, stance sheet pa9 and seat sheet pa13 looked at; on target NO: emptied 2.3 % in pa8, 1.8 % in pa10'),
    'colt45_coltpa': dict(rule=('yes', 'yes', 'yes', 'pa8 (stand), pa9 (stances), pa14 (seat)'), action=THUMB % 'slide', qa='pa8: GIF decoded and looked at, stance sheet pa9 and seat sheet pa14 looked at'),
    'colt_silenced': dict(rule=('yes', 'yes', 'yes', 'pa8 (stand), pa9 (stances), pa14 (seat)'), action=THUMB % 'slide', qa='pa8: GIF decoded and looked at, stance sheet pa9 and seat sheet pa14 looked at; the silencer never meets the support hand'),
    'berettasilenced': dict(rule=('no', 'yes', 'yes', 'pa8 pa10 (stand), pa9 (stances), pa14 (seat)'), action=THUMB % 'slide', qa='pa10: GIF decoded and looked at, stance sheet pa9 and seat sheet pa14 looked at; sheet gamma-lifted (readable); on target NO: emptied 1.7 % in pa8, 3.1 % in pa10'),
    'nambu': dict(rule=('no', 'yes', 'yes', 'pa8 pa10 pa11 (stand), pa9 (stances), pa14 (seat)'), action=THUMB % 'bolt (round knob, cut out onto a bone)', qa='pa11: GIF decoded and looked at, stance sheet pa9 and seat sheet pa14 looked at; sheet gamma-lifted in pa11; on target NO: loaded 1.4 / 3.1 / 2.2 % over three runs'),
    'p38silenced': dict(rule=('yes', 'yes', 'yes', 'pa8 pa10 pa11 (stand), pa9 (stances), pa15 (seat)'), action=THUMB % 'slide (cut out onto a bone)', qa='pa11: GIF decoded and looked at, stance sheet pa9 and seat sheet pa15 looked at; sheets gamma-lifted; the open slide shows a dark middle slot'),
    'colt45': dict(rule=('no', 'yes', 'yes', 'pa8 pa11 (stand), pa9 (stances), pa15 (seat); td8 / td9 before'), qa='pa11: GIF decoded and looked at, stance sheet pa9 and seat sheet pa15 looked at; seat push x0.6, thumb x0.45; on target NO: loaded 2.2 / 1.0 %, emptied 1.4 / 4.3 % over two runs of the same clips; pose approved by the user 2026-10-12 (th3)'),
    'p38': dict(rule=('yes', 'yes', 'yes', 'pa11 (stand), pa9 (stances), pa15 (seat)'), qa='pa11: GIF decoded and looked at, stance sheet pa9 and seat sheet pa15 looked at; breech block added in the slide\'s rear slot (no black gap); loaded 0.3 %, emptied 0.7 % (pa11), 1.8 / 2.8 % in pa8 before the filler'),
    'it_w_beretta': dict(rule=('no', 'yes', 'yes', 'pa8 pa10 pa11 (stand), pa9 (stances), pa15 (seat)'), qa='pa11: GIF decoded and looked at, stance sheet pa9 and seat sheet pa15 looked at; sheet gamma-lifted as .dds (readable); on target NO: loaded 2.1 / 0.9 / 2.0 %; emptied figure polluted by the 15-shot view walk (3.4 / 4.8 / 2.4 %)'),
}
for stem, v in SP.items():
    e = d.setdefault(T(stem), {})
    if v.get('lowered'):
        e['lowered'] = True
    r = v['rule']
    e['rule'] = dict(target=r[0], reacts=r[1], action=r[2], run=r[3])
    if 'action' in v:
        e['action'] = v['action']
    e['qa'] = v['qa']
    e.pop('note', None)
    st = e.get('reload')
    if isinstance(st, dict) and 'ride' in st:
        e['seat'] = dict(run=SEAT[stem], end=st['ride'].get('end'), dev=st['ride'].get('dev'))
m = d.setdefault(T('m10_revolver'), {})
m['qa'] = (m.get('qa', '') + ' / pa12: hip reload and both break-off states with the per-chamber heads looked at (fill one by one at the hip, a break-off closes on the heads that are in); third person not run - by the code another player always sees six heads').strip(' /')
json.dump(d, open(P, 'w'), indent=1, sort_keys=True)
for stem in SP:
    r = d[T(stem)].get('reload') or {}
    print('%-18s reload stances: %s' % (stem, ' '.join('%s(%s %s)' % (k, v.get('run'), 'ok' if v.get('ok') else 'FAIL dev %.1f end %.2f' % (v.get('dev', -1), v.get('end', -1))) for k, v in sorted(r.items()))))
