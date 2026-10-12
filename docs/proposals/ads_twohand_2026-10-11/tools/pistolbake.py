"""Aimed reloads of the MAGAZINE pistols on the two-handed aim - the user's rules of 2026-10-12:

  1. ON TARGET ("you reload without losing your target"): the gun stays in the aim, the centre of the screen stays
     clear, the work happens low - the support hand leaves downward and comes back from below.
  2. THE GUN REACTS, by physics ("weighty, weapon should move realistically based on physics"): no gun key is set by
     hand. The gun's motion is gunphys.py's damped spring driven by the events of the clip - the support hand leaving
     (the muzzle sags, the hold softens), the magazine dropping, the push that seats the new one, the support hand
     landing, the slide stop pressed, the slide slamming forward.
  3. THE ACTION WORKS ("functioning slides ... with whichever arm makes sense"): an EMPTY gun has its slide locked back
     and the support thumb presses the slide stop as the hand returns to the grip; the slide runs forward the frame
     the thumb is down (pistolgun.py's `reload_ads_empty` gun clip). A gun with a round chambered has no slide action
     (`reload_ads_loaded`). Two hand clips: <prefix>_reload_ads and <prefix>_reload_empty_ads.

The firing hand keeps its aim grip (fixed_right). The support hand is keyed (left_path): grip -> down and out to the
pouch -> under the magazine well with the retail hand-to-gun relation of the retail hand-over frame -> push -> up the
left side of the grip -> grip. First and last frame = the aim pose exactly. The spec (events per gun) is pistolgun.GUNS.

    cd stage; python ../pistolbake.py <gun|all> .          env PB_STRENGTH (default 1.0)
"""
import sys, os, json, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import revbake as RB
import gunphys
import pistolgun
H = RB.H; R = RB.R
GUNS = pistolgun.GUNS

STRENGTH = float(os.environ.get('PB_STRENGTH', '1.0'))
POUCH = (5.0, 9.0, -15.0)              # camera frame (fwd, left, up): the belt, well under the frame


def events(g, empty):
    t = g['t']
    if g.get('rack'):                       # hand-cycled: magazine in, then the rack - pulled back, slammed forward
        r = g['rack']
        return [(t['rel'], 'mag_release'), (t['out'][0], 'mag_out'), (t['seat'][1] - 1, 'mag_seat'),
                (r['pull'][0], 'slide_back'), (r['fwd'][1] - 1, 'slide_fwd'), (r['on'] - 4, 'hand_on')]
    ev = [(t['rel'], 'mag_release'), (t['out'][0], 'mag_out'), (t['seat'][1] - 1, 'mag_seat'), (t['on'][1] - 4, 'hand_on')]
    if empty:
        ev += [(t['press'], 'thumb_press'), (t['fwd'][1] - 1, 'slide_fwd')]
    return ev


def spec(name, empty):
    g = GUNS[name]
    t = g['t']
    n = R.load(R.ANIM + H.fps_rows()[g['row']]).numFrames - 1
    ph = gunphys.simulate(n + 1, 1 / 30.0, g['cls'],
                          support=[(0, 1), (t['off'][0], 1), (t['off'][1], 0)] + ([(g['rack']['on'] - 6, 0), (g['rack']['on'], 1)] if g.get('rack')
                                                                                  else [(t['on'][0], 0), (t['on'][1], 1)]),
                          mag=[(0, 1), (t['out'][0], 1), (t['out'][1], 0), (t['seat'][0], 0), (t['seat'][1], 1)],
                          events=events(g, empty), strength=STRENGTH,
                          pose=pistolgun.rack_pose(g['rack']['pull'], g['rack']['fwd'], n) if g.get('rack') else None)
    a0, a1 = t['off']
    s0, s1 = t['seat']
    o0, o1 = t['on']
    rack = g.get('rack')
    if rack:
        o1 = rack['on']
    hold = g['rel']                         # retail frame: the hand holds the new magazine just under the well
    magup = pistolgun.gun_facts(name)['magup']
    UP = dict(rel=hold, gun_add=magup, fing=hold)           # the same hand pushed up the well by the magazine's travel
    AIM = dict(aim=1, fing='aim')
    lp = {0: AIM, a0: AIM,
          a0 + 3: dict(aim=1, cam_add=(-0.4, 1.3, -1.2), fing=('mix', hold, 0.5)),       # the fingers come off the firing hand
          a1 + 2: dict(aim=1, cam_add=(-1.5, 3.5, -6.5), fing=hold),
          a1 + 6: dict(cam=POUCH, rot='aim', fing=hold), s0 - 7: dict(cam=POUCH, rot='aim', fing=hold),
          s0 - 2: dict(rel=hold, fing=hold), s0: dict(rel=hold, fing=hold)}
    for f in range(s1, o0 + 1):                                                           # the palm stays on the magazine as the gun gives
        lp[f] = UP
    lp[o0 + 4] = dict(aim=1, cam_add=(-0.6, 1.5, -1.8), fing=('mix', hold, 0.5))          # up the left side of the grip
    if rack:                                 # ... and on up to the slide: the shared rack, then down onto the grip
        import json as _j
        trav = _j.load(open(os.path.join(HERE, 'slide_%s.json' % name)))['travel']
        lp.update(pistolgun.rack_hand(name, rack['reach'], rack['pull'], rack['fwd'], trav, ('mix', hold, 0.3), fing_open='pose'))
    for f in range(o1, n + 1):
        lp[f] = AIM
    # the magazine prop (server: on tag_weapon_left from frame 0 to the hand-over frame) sits in the keyed hand as the
    # retail hand holds it at frame `hold`; the retail hand-over to the gun is timed for the retail hand, so it is off
    kw = dict(gun=g['sight'], charge=g['aim'], fixed_right=True, dip=ph['dip'], left_path=lp, weight=dict(on=False),
              handover=False, tag_map={0: 0, a1 + 2: a1 + 2, s0 - 7: hold, n: hold},
              elbow_vec={'R': (0.0, -1.0, -0.2), 'L': (0.0, 0.0, -1.0)})
    if g.get('park'):
        kw['tag_park'] = dict(tag='tag_weapon_left', ranges=[(0, a1 + 3), (s1, n)])
        kw['tag_map'] = {0: hold, n: hold}
    if empty and not rack:
        p = t['press']
        # the support thumb rides high as the hand closes on the grip and sweeps the slide stop down over p..p+2;
        # the slide starts forward on p+2 (pistolgun: fwd[0])
        kw['finger_add'] = {'Bip01 L Finger01 rot': [(o0 + 2, 0.0), (p - 3, -26.0), (p, -26.0), (p + 2, 7.0), (p + 6, 0.0)],
                            'Bip01 L Finger02 rot': [(o0 + 2, 0.0), (p - 3, -16.0), (p, -16.0), (p + 2, 5.0), (p + 6, 0.0)]}
    return kw, ph


def bake(name, root):
    g = GUNS[name]
    rep = {}
    for empty in (False, True):
        kw, ph = spec(name, empty)
        rc = H.auto_recipe(g['row'], **kw)
        H.RECIPES[g['row']] = rc
        sk, _ = H.bake(g['row'], RB.CTL)
        bts = R.skc_io.write(sk)
        out = '%s/%s_reload_%sads.skc' % (g['vdir'], name, 'empty_' if empty else '')
        dst = os.path.join(root, 'models', 'human', 'animation', out.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(bts)
        print(name, 'empty' if empty else 'loaded', '->', out, sk.numFrames, 'frames', hashlib.md5(bts).hexdigest()[:8])
        print('   ', ph['report'])
        rep['empty' if empty else 'loaded'] = dict(peak_deg=round(ph['peak_deg'], 2), settle_s=round(ph['settle_s'], 2))
    return rep


def rows_file():
    """rows_pistol_empty.txt: the <row>_empty (hip: the retail clip) and <row>_empty_ads rows for mkov's MKOV_EXTRA"""
    rows = H.fps_rows()
    L = ['\t//===================== HZM coop magazine pistols: reload of an EMPTY gun (cgame picks <row>_empty when the clip is 0) =====================']
    for name, g in GUNS.items():
        L.append('\t%s_empty\t\t\t%s\t\t\tcrossblend 0.3' % (g['row'], rows[g['row']]))
        L.append('\t%s_empty_ads\t\t%s/%s_reload_empty_ads.skc\t\tcrossblend 0.1' % (g['row'], g['vdir'], name))
    open(os.path.join(HERE, 'rows_pistol_empty.txt'), 'w', newline='\n').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    rep = {}
    for nm in (list(GUNS) if sys.argv[1] == 'all' else sys.argv[1].split(',')):
        rep[nm] = bake(nm, sys.argv[2])
    rows_file()
    p = os.path.join(HERE, 'pistolphys.json')
    d = json.load(open(p)) if os.path.isfile(p) else {}
    d.update(rep)
    json.dump(d, open(p, 'w'), indent=1, sort_keys=True)
