"""recipes_keyed.py - hand-keyed reload recipes for keyclip.py (reload authenticity phase B polish).

Hand rotation specs: ('from', clip, frame, side, tag) = that clip frame's hand-to-gun rotation (a real artist's hand
orientation for that kind of grip), optionally followed by a small gun-frame euler tweak; a plain (x, y, z) euler =
relative to the hand's idle grip. Gun frame: x fwd, y right, z down, game units.
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import beltsched as BS

TOP = ('from', 'viewmodel/coop_dp28/dp28_reload.skc', 27, 'L', 'tag_weapon_right')       # palm down on top of a receiver
KNOB_R = ('from', 'viewmodel/rifle/kar98_rechamber.skc', 18, 'R', 'tag_weapon_left')     # right hand on a right-side knob
# right hand on the belt guns' charging handle: euler tweak on its idle grip, chosen by a joint-limit search over 27
# candidates (rsearch: 0 wrist / pronation violations, contacts held, no forearm across the view); the kar98 knob
# grip it replaced turned the palm up and flipped the forearm 30-40 deg a frame (user: 'hands bending all weird')
BELT_KNOB = {'m1919': (40.0, 30.0, -30.0), 'mg42': (-40.0, 30.0, 0.0)}   # wrap grip (rb7 review)
BELT_ROT = {}    # per-gun hand-on-belt euler tweak (joint QA)
BELT_AWAY = (0.0, -30.0, 0.0)   # relaxed wrist while the hand is below the view with the belt (joint QA: MG42 dev -32 -> in range)


def belt_recipe(g, knob_rot=None, ret=18, belt_rot=None, away_rot=None):
    S = BS.GUNS[g]
    KR = knob_rot or BELT_KNOB.get(g, KNOB_R)
    br = belt_rot if belt_rot is not None else BELT_ROT.get(g)
    TB = tuple(list(TOP) + [tuple(br)]) if br else TOP     # hand on the belt
    away_rot = away_rot if away_rot is not None else BELT_AWAY
    TA = tuple(list(TOP) + [tuple(away_rot)]) if away_rot else TB   # relaxed while it is below the view
    lat = np.array(S['latch']); belt = np.array(S['belt_pt']); knob = np.array(S['handle_knob'])
    cov = lambda f, p: BS.cover_point(g, f, p)
    hdl = lambda f, p: BS.handle_point(g, f, p)
    c = dict(S['cover']); keys = S['cover']
    c_open0, c_lift, c_open1 = keys[1][0], keys[2][0], keys[3][0]   # lifted by the hand to c_lift, flicked on up
    c_shut0, c_shut1 = keys[4][0], keys[5][0]          # cover pressed shut
    p0, p1 = S['prop']
    edge = (lat[0] + 0.3, 0.0, lat[2] + 0.2)            # the cover's rear edge, where the fingers hook it
    mid = (S['hinge'][0] - 5.0, 0.0, S['cover_box'][2][0] - 0.3)   # cover top, 5 u behind the hinge (in reach when open)
    L = [('L', 'idle', 0), ('L', 'idle', max(1, c_open0 - 13)),                 # stays on the fore-end until it moves
         ('L', c_open0 - 5, 'index', tuple(lat + [-0.6, 0, -1.2]), TOP),            # approach above the latch
         ('L', c_open0 - 2, 'index', tuple(lat), TOP),                             # finger on the latch
         ('L', c_open0, 'index', tuple(lat + [0.5, 0, 0.15]), TOP),                # press it forward (deliberate)
         ('L', 'follow', c_open0 + 1, c_lift, 'wrap', ('part', 'cover', edge), TOP),    # lift the cover (deliberate)
         ('L', c_lift + 2, 'wrap', tuple(cov(c_lift, edge) + [1.0, -0.8, -0.8]), TOP),     # flick it on up, short follow-through (rb4: a 2.2 u one threw the hand into the top of the view)
         ('L', p0 - 2, 'pinch', tuple(belt + [0, -1.2, -1.0]), TB),               # reach to the belt end
         ('L', p0, 'pinch', tuple(belt), TB),                                     # take the belt end
         ('L', p0 + 4, 'pinch', tuple(belt + [-0.5, -5.0, 1.0]), TB),             # strip it out to the left
         ('L', p0 + 8, 'pinch', tuple(belt + [-2.0, -10.0, 9.0]), TA),            # down out of view (new belt)
         ('L', p0 + 12, 'pinch', tuple(belt + [-2.0, -10.0, 9.5]), TA),
         ('L', p0 + 17, 'pinch', tuple(belt + [-0.5, -5.0, -0.8]), TB),           # bring the new belt up from the left
         ('L', p0 + 21, 'pinch', tuple(belt + [0, -1.0, -0.4]), TB),              # lay it on the feed tray
         ('L', p0 + 23, 'pinch', tuple(belt), TB),                                # seat the first round on the stop
         ('L', p1, 'pinch', tuple(belt), TB),
         ('L', c_shut0 - 2, 'palm', tuple(cov(c_shut0, mid) + [0, 0, -1.0]), TOP),  # hand onto the open cover
         ('L', 'follow', c_shut0, c_shut1, 'palm', ('part', 'cover', mid), TOP),   # press it shut (deliberate)
         ('L', c_shut1 + 1, 'palm', tuple(np.array(mid) + [0, 0, 0.35]), TOP),     # slap home (quick)
         ('L', c_shut1 + 3, 'palm', tuple(np.array(mid) + [0, 0, -0.5]), TOP),     # follow-through off the cover
         ('L', c_shut1 + 7, 'palm', tuple(np.array(mid) + [2.0, -5.0, 4.0]), TOP), # back down the left side, under the view
         ('L', 'idle', c_shut1 + ret)]
    LF = [('L', 0, 'idle'), ('L', c_open0 - 6, 'open'), ('L', c_open0 - 2, 'pinch'), ('L', c_open0 + 2, 'wrap'),
          ('L', c_lift, 'wrap'), ('L', c_lift + 2, 'open'), ('L', p0 - 2, 'open'), ('L', p0, 'pinch'),
          ('L', p1, 'pinch'), ('L', p1 + 1, 'open'), ('L', c_shut1 + 3, 'open'), ('L', c_shut1 + ret, 'idle')]
    # right hand: the charging handle on the right, pulled by the knob, released under spring
    hk = S['handle']
    pulls = [(hk[i][0], hk[i + 1][0]) for i in range(len(hk) - 1) if hk[i][1] == 0.0 and hk[i + 1][1] < 0]
    Rk = [('R', 'idle', 0), ('R', 'idle', pulls[0][0] - 14)]     # on the grip until it goes for the handle (14 frames: the wrist turns over unhurried)
    RF = [('R', 0, 'idle'), ('R', pulls[0][0] - 14, 'idle')]
    # the hand GRIPS the handle (fingers wrapped round it, rb7 review: an open pinch read as pointing at it), stays
    # curled between pulls (pull, let it slam home, take it again), and is back on the grip 3 frames before the clip
    # ends (rb7: the return ran past the clip end and the arm snapped to the idle)
    HE = 'wrap'
    Rk.append(('R', 'turn', pulls[0][0] - 9, HE, KR))      # wrist turns over on the grip first, out of view
    RF.append(('R', pulls[0][0] - 9, 'open'))
    for i, (a, b) in enumerate(pulls):
        Rk += [('R', a - 3, HE, tuple(knob + [0.6, 1.2, 0]), KR) if i == 0 else ('R', a - 1, HE, tuple(knob + [0.2, 0.5, 0]), KR),
               ('R', 'follow', a, b + 1, HE, ('part', 'handle', tuple(knob)), KR),  # pull back (quick)
               ('R', b + 2, HE, tuple(hdl(b, knob) + [-0.2, 0.6, 0]), KR)]          # let it fly
    RF += [('R', pulls[0][0] - 4, 'open'), ('R', pulls[0][0] - 1, 'wrap'), ('R', pulls[-1][1] + 1, 'wrap'),
           ('R', pulls[-1][1] + 4, 'open')]
    last = pulls[-1][1]
    if g == 'mg42':   # the MG42 handle is pushed forward by hand, not sprung: ride it forward too
        a, b = pulls[0]
        Rk = [('R', 'idle', 0), ('R', 'idle', a - 14), ('R', 'turn', a - 9, HE, KR),
              ('R', a - 3, HE, tuple(knob + [0.6, 1.2, 0]), KR),
              ('R', 'follow', a, b + 5, HE, ('part', 'handle', tuple(knob)), KR),
              ('R', b + 7, HE, tuple(knob + [0.4, 1.4, 0]), KR)]
        RF = [('R', 0, 'idle'), ('R', a - 14, 'idle'), ('R', a - 9, 'open'), ('R', a - 1, 'wrap'), ('R', b + 5, 'wrap'), ('R', b + 8, 'open')]
        last = b + 5
    ret_r = min(last + 16, 97 - 3)
    Rk.append(('R', 'idle', ret_r)); RF.append(('R', ret_r, 'idle'))
    contacts = [('L', c_open0 - 2, c_open0, 'index', tuple(lat), 'latch'),
                ('L', c_open0 + 1, c_lift, 'wrap', ('part', 'cover', edge), 'cover lift'),
                ('L', p0, p0, 'pinch', tuple(belt), 'belt taken'), ('L', p0 + 23, p1, 'pinch', tuple(belt), 'belt seated'),
                ('L', c_shut0, c_shut1, 'palm', ('part', 'cover', mid), 'cover shut')]
    for a, b in pulls:
        contacts.append(('R', a, b, HE, ('part', 'handle', tuple(knob)), 'charging handle %d' % a))
    moving = {'cover open (hand)': (cov, list(range(c_open0 + 1, c_lift + 1)), edge),
              'cover shut': (cov, list(range(c_shut0, c_shut1 + 1)), mid)}
    for a, b in pulls:
        moving['handle pull %d' % a] = (hdl, list(range(a + 1, b + 1)), tuple(knob))
    # the gun comes forward, down and rolls its top toward the left hand while the top is worked (view-blocking search:
    # (+3, -3, +4) u, roll -35 deg keeps both forearms out of the central 25 deg of the view, contacts held), half that
    # while the belt is handled
    gp, gr = (3.0, -3.0, 3.0 if g == 'm1919' else 4.0), (-35.0, 0.0, 0.0)   # m1919 3 u lower is as clear; mg42 needs 4
    hp, hr = tuple(np.array(gp) * 0.6), tuple(np.array(gr) * 0.5)
    gun_keys = [(max(2, c_open0 - 2), gp, gr), (c_open1 + 4, gp, gr), (p0 + 2, hp, hr), (p1, hp, hr),
                (c_shut0 - 4, gp, gr), (c_shut1 + 4, gp, gr)]
    # secondary motion: the gun gives under the slap that shuts the cover and settles, jolts as the bolt slams home
    # after each pull, and nods as the belt is seated (keyclip gun_fx: damped kicks, gun frame u / deg)
    fx = [(c_shut1, (0.0, 0.0, 0.5), (1.0, 0.0, 0.0)), (p0 + 23, (0.0, 0.15, 0.2), (0.0, 0.0, 0.0))]
    for a, b in pulls:
        fx += [(a + 1, (-0.25, 0.0, 0.0), (0.0, 0.0, 0.0)), (b + 2, (0.35, 0.0, 0.1), (0.5, 0.0, 0.0))]
    return dict(template='viewmodel/coop_dp28/dp28_reload.skc', idle='viewmodel/mg/barpose.skc',
                hands=L + Rk, fingers=LF + RF, parts={'cover': cov, 'handle': hdl},
                tagL=[(p0, p0, p1)], contacts=contacts, moving=moving,
                gun=gun_keys, gun_fx=fx)


RECIPES = {'m1919': belt_recipe('m1919'), 'mg42': belt_recipe('mg42')}


# ================================================================ magazine-swap guns ================================
import swapsched as SS   # noqa: E402
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src_clips') + os.sep   # the pre-polish clips
P38_RACK = ('from', 'viewmodel/pistol/reload_p38.skc', 57, 'L', 'tag_weapon_right')   # left hand over a slide's rear


def swap_hands(g, part, out_dir, grip_rot, eff='wrap', lift=None, twist=0.0, away=(-1.0, 0.0, 12.0), hold_to=None,
               away_rot=None):
    """left hand: approach (anticipation) -> take hold (fingers curl) -> off along the guides / post (deliberate)
    -> away below the view -> the full one back up -> on (turned to lock if twist) -> seated -> a smack home (quick)
    -> follow-through off -> idle. The hand is STATIC on the part from 2 frames before the prop appears to 2 frames
    after the gun hides its part, and again around the show / removal (overlap rule), so the prop never jumps.
    hold_to: keep holding the gun by the part until that frame (e.g. while the other hand cocks)."""
    S = SS.GUNS[g]
    p0, p1 = S['prop']
    g0, s0 = p0 - 2, p1 - 2
    P = np.array(part, float); D = np.array(out_dir, float)
    first = P + (np.array(lift, float) if lift is not None else D * 0.3)
    awayp = P + D * 1.2 + np.array(away, float)
    rot = lambda deg: tuple(list(grip_rot) + [(0.0, 0.0, deg)]) if deg else grip_rot
    arot = tuple(list(grip_rot) + [tuple(away_rot)]) if away_rot else rot(twist)   # the hand relaxes while it is away
    span = s0 - (p0 + 2)
    t = lambda x: p0 + 2 + int(round(span * x))
    k = [('L', 'idle', 0), ('L', 'idle', max(1, g0 - 14)),
         ('L', g0 - 4, eff, tuple(P + D * 0.25 + np.array([0.0, 0.0, 0.8])), grip_rot),   # approach from below-out
         ('L', g0, eff, tuple(P), grip_rot), ('L', p0 + 2, eff, tuple(P), grip_rot),
         ('L', t(0.17), eff, tuple(first), grip_rot),
         ('L', t(0.30), eff, tuple(P + D if lift is None else first + D), grip_rot),
         ('L', t(0.46), eff, tuple(awayp), arot),
         ('L', t(0.54), eff, tuple(awayp + np.array([0.4, 0.0, 0.5])), arot),
         ('L', t(0.72), eff, tuple(P + D if lift is None else first + D), rot(twist)),
         ('L', t(0.86), eff, tuple(first), rot(twist * 0.7)),
         ('L', s0, eff, tuple(P), grip_rot), ('L', p1, eff, tuple(P), grip_rot)]
    hold = hold_to or p1
    k += [('L', p1 + 2, eff, tuple(P + np.array([0.0, 0.0, -0.3]) - D * 0.03), grip_rot),   # smack home (quick)
          ('L', p1 + 4, eff, tuple(P), grip_rot)]
    if hold > p1 + 4:
        k.append(('L', hold, eff, tuple(P), grip_rot))
    k += [('L', hold + 3, eff, tuple(P + D * 0.25 + np.array([0.0, 0.0, 1.2])), grip_rot),   # off, follow-through
          ('L', 'idle', hold + 12)]
    f = [('L', 0, 'idle'), ('L', g0 - 5, 'open'), ('L', g0, 'wrap'), ('L', hold + 1, 'wrap'), ('L', hold + 4, 'open'),
         ('L', hold + 12, 'idle')]
    contacts = [('L', g0, p0 + 2, eff, tuple(P), 'part taken'), ('L', s0, p1, eff, tuple(P), 'part seated')]
    return k, f, contacts, [(p0, p0, p1)]


def knob_hands(side, g, frames, rot, eff='pinch', approach=(0.0, -1.0, -1.5), back=None, idle_from=None):
    """a hand on a cocking knob: approach, on it at frames[0] (the part still), follow it while it moves to frames[1],
    let go at frames[1]+1 (it flies home under spring, or stays back), clear of it, back to idle"""
    a, b = frames
    kn = lambda f, p: SS.knob_point(g, f, p)
    K0 = np.array(SS.GUNS[g]['knob'])
    k = [(side, 'idle', 0), (side, 'idle', max(1, a - 12)), (side, a - 4, eff, tuple(kn(a, K0) + approach), rot),
         (side, 'follow', a, b, eff, ('part', 'knob', tuple(K0)), rot),
         (side, b + 2, eff, tuple(kn(b, K0) + np.array(approach) * 0.8), rot),
         (side, 'idle', b + 11)]
    f = [(side, 0, 'idle'), (side, max(1, a - 8), 'idle'), (side, a - 4, 'open'), (side, a, 'pinch'), (side, b, 'pinch'), (side, b + 2, 'open'),
         (side, b + 11, 'idle')]
    con = [(side, a, b, eff, ('part', 'knob', tuple(K0)), 'knob')]
    mov = {'knob %s f%d-%d' % (side, a, b): (kn, list(range(a, b + 1)), tuple(K0))}
    return k, f, con, mov


def drum_recipe(g, template, idle, part, out_dir, grip_rot, gun, knob=None, knob_side='L', knob_rot=None,
                hold_to=None, gun_fx=None, **kw):
    k, f, con, tag = swap_hands(g, part, out_dir, grip_rot, hold_to=hold_to, **kw)
    parts, mov = {}, {}
    if knob:
        kk, kf, kc, km = knob_hands(knob_side, g, knob, knob_rot)
        if knob_side == 'L':      # the knob comes first: the same hand then goes on to the drum
            k = [x for x in k if not (x[1] == 'idle' and x[2] == 0)] + [x for x in kk if x[1] != 'idle' or x[2] == 0]
            k = [x for x in k if not (x[1] == 'idle' and 0 < x[2] < knob[1] + 4)]
            f = [x for x in f if x[1] > knob[1] + 3] + [x for x in kf if x[1] <= knob[1] + 2]
        else:
            k += kk; f += kf
        con += kc; mov.update(km); parts['knob'] = lambda fr, p: SS.knob_point(g, fr, p)
    p1 = SS.GUNS[g]['prop'][1]
    fx = list(gun_fx or [])
    fx.append((p1 + 2, tuple(-0.04 * np.array(out_dir, float) + np.array([0.0, 0.0, 0.1])), (0.8, 0.0, 0.0)))  # smacked home
    if knob:   # the knob let go: the bolt slams (MP18) / the hand's tug settles (Thompson)
        fx.append((knob[1] + 2, (0.3 if knob_side == 'R' else -0.15, 0.0, 0.05), (0.4, 0.0, 0.0)))
    return dict(template=template, idle=idle, hands=k, fingers=f, parts=parts, tagL=tag, contacts=con, moving=mov,
                gun=gun, gun_fx=fx)


TOMMY_DRUM = ('from', SRC + 'tommydrum_reload.skc', 10, 'L', 'tag_weapon_right')   # pre-polish drum grip (reviewed)
# the gun rolls its top toward the left hand for the knob (view search: 3 frames with the forearm in the central 25 deg,
# retail's own Thompson cock has 12), then turns its left side out for the drum
_tg = [(6, (1.0, -1.0, 2.0), (-25.0, 0.0, 0.0)), (16, (1.0, -1.0, 2.0), (-25.0, 0.0, 0.0)),
       (22, (0.5, 0.0, -0.5), (8.0, 0.0, 0.0)), (66, (0.5, 0.0, -0.5), (8.0, 0.0, 0.0))]
_tg28 = [(6, (0.5, 0.0, -0.5), (8.0, 0.0, 0.0)), (66, (0.5, 0.0, -0.5), (8.0, 0.0, 0.0))]
RECIPES['tommy50'] = drum_recipe('tommy50', 'viewmodel/smg/reload_tommy_stand.skc', 'viewmodel/smg/idle_tommy_stand.skc',
                                 (7.4, -1.1, -0.1), (0.0, -10.0, 0.0), TOMMY_DRUM, _tg, knob=(11, 16), knob_side='L',
                                 knob_rot=TOP, away_rot=(0.0, -30.0, 0.0))   # relaxed wrist while away (joint QA)
RECIPES['tommy1928'] = drum_recipe('tommy1928', 'viewmodel/smg/reload_tommy_stand.skc',
                                   'viewmodel/smg/idle_tommy_stand.skc', (7.4, -1.1, -0.1), (0.0, -10.0, 0.0),
                                   TOMMY_DRUM, _tg28, away_rot=(0.0, -30.0, 0.0))
MP18_DRUM = ('from', SRC + 'mp18_reload.skc', 10, 'L', 'tag_weapon_right')
def mp18_recipe(knob_rot=(0.0, 0.0, 0.0)):
    """MP18: the right hand leaves the grip, hooks the right-side cocking handle (palm in, as it holds the grip, so the
    fingers - not an open palm - are what the eye sees on the handle), pulls it back and lets it fly"""
    return drum_recipe('mp18', 'viewmodel/MP40/reload_mp40_stand.skc', 'viewmodel/mp40/mp40_stand_idle.skc',
                       (13.8, -11.3, -5.2), (0.0, -8.0, 0.0), MP18_DRUM,
                       [(4, (0.0, 1.0, -1.0), (-10.0, 0.0, 0.0)), (62, (0.0, 1.0, -1.0), (-10.0, 0.0, 0.0))],
                       knob=(52, 57), knob_side='R', knob_rot=knob_rot, hold_to=60, away_rot=(0.0, -30.0, 0.0))


RECIPES['mp18'] = mp18_recipe()
RECIPES['lewis'] = drum_recipe('lewis', 'viewmodel/coop_dp28/dp28_reload.skc', 'viewmodel/mg/barpose.skc',
                               (13.5, 1.6, -3.9), (-1.0, -9.0, 0.0), TOP,
                               [(6, (3.0, -3.0, 1.5), (-25.0, 0.0, 0.0)), (70, (3.0, -3.0, 1.5), (-25.0, 0.0, 0.0))],   # rb7: 3 u down hid the pan; 1.5 keeps the view clear
                               lift=(0.0, 0.0, -3.0), twist=-20.0)


# ---------------------------------------------------------------- Mauser C96 stripper clip --------------------------
def c96_recipe(rot=TOP, gun=((0.0, -1.0, 2.5), (-35.0, 0.0, 0.0))):
    """bolt ears pulled back f13-18 and let go f23 (the ADS agent's bolt bone is to be keyed to these frames); the full
    clip rides the hand into the guides (prop on tag_weapon_left f28-41, sits on the gun f41-44); the thumb strips the
    rounds down f42-44; the empty clip is taken f47, pulled up out of the guides and tossed f47-56."""
    ears = np.array((0.6, -0.75, -4.5)); spine = np.array((4.8, -0.6, -6.7)); rnd = np.array((5.6, -0.55, -6.5))
    k = [('L', 'idle', 0),
         ('L', 10, 'pinch', tuple(ears + [0.0, -0.8, -1.2]), rot),
         ('L', 13, 'pinch', tuple(ears), rot),                      # take the bolt ears
         ('L', 18, 'pinch', tuple(ears + [-1.6, 0, 0]), rot),       # draw the bolt back (quick)
         ('L', 20, 'pinch', tuple(ears + [-1.6, 0, 0]), rot),       # it holds open on the follower
         ('L', 23, 'pinch', tuple(ears + [-1.8, -1.5, -1.2]), rot), # let go, up and off
         ('L', 27, 'pinch', tuple(spine + [-3.0, -6.0, 10.0]), rot),  # down to the pouch, below the view
         ('L', 29, 'pinch', tuple(spine + [-3.0, -6.0, 10.3]), rot),  # clip taken
         ('L', 35, 'pinch', tuple(spine + [-0.6, -2.5, -2.5]), rot),  # up and over the open action
         ('L', 39, 'pinch', tuple(spine + [0, 0, -1.0]), rot),      # lined up over the guides
         ('L', 41, 'pinch', tuple(spine), rot),                     # into the guides
         ('L', 42, 'thumb', tuple(rnd), rot),                       # thumb onto the top round
         ('L', 44, 'thumb', tuple(rnd + [0, 0, 1.8]), rot),         # press the rounds down (deliberate)
         ('L', 45, 'thumb', tuple(rnd + [0, 0, 1.6]), rot),
         ('L', 47, 'pinch', tuple(spine), rot),                     # take the empty clip
         ('L', 50, 'pinch', tuple(spine + [0, 0, -2.8]), rot),      # pull it up out of the guides (quick)
         ('L', 56, 'pinch', tuple(spine + [-1.0, -8.0, 3.0]), rot), # flick it away to the left
         ('L', 58, 'pinch', tuple(spine + [-1.5, -9.5, 5.0]), rot), # follow-through
         ('L', 'idle', 68)]
    f = [('L', 0, 'idle'), ('L', 8, 'open'), ('L', 13, 'pinch'), ('L', 21, 'pinch'), ('L', 23, 'open'),
         ('L', 27, 'open'), ('L', 29, 'pinch'), ('L', 47, 'pinch'), ('L', 56, 'pinch'), ('L', 57, 'open'), ('L', 68, 'idle')]
    return dict(template='viewmodel/pistol/reload_p38.skc', idle='viewmodel/pistol/coltpose.skc', hands=k, fingers=f,
                parts={}, tagL=[(41, 28, 41), (47, 47, 56)],
                contacts=[('L', 13, 13, 'pinch', tuple(ears), 'bolt ears'),
                          ('L', 41, 41, 'pinch', tuple(spine), 'clip in the guides'),
                          ('L', 42, 42, 'thumb', tuple(rnd), 'thumb on the rounds'),
                          ('L', 47, 47, 'pinch', tuple(spine), 'empty clip taken')],
                moving={},
                gun=[(5, gun[0], gun[1]), (60, gun[0], gun[1])],
                # the thumb's push on the rounds dips the pistol; the bolt slams home as the empty clip comes out
                gun_fx=[(43, (0.0, 0.0, 0.3), (0.0, 0.0, 0.0)), (50, (0.25, 0.0, 0.05), (0.6, 0.0, 0.0))])


RECIPES['c96'] = c96_recipe()
