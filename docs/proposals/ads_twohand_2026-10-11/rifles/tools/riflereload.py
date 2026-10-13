"""Aimed full reload of a rifle to the 2026-10-12 standard, from the gun's own HIP technique.

Hands: hold_bake - both hands keep the retail hip clip's hand-to-gun relation frame by frame (its own contact with the
bolt, the clip, the magazine), blended from / to the aim grip at the two ends; arms by IK; the camera never moves.
Gun: NOT keyed frame by frame. The shooter's intent is a short list of HOLDS (5 numbers each, camera frame: drop u,
roll deg + = top to the right, pitch deg + = muzzle down, side u + = left, back u + = toward the eye; rotation about
the butt in the shoulder):
    'bolt'  off the cheek along the sight line, canted to the working hand - the bolt is worked on the sights
    'low'   the rifle brought DOWN under the centre box, action turned up to the eye - a clip / magazine is worked there
and gunphys (tools/gunphys.py, a rifle class) is the mass on a damped spring that FOLLOWS those holds (it lags, and
settles after each move) and answers every stroke of the action with an impulse at the frame the gun's own clip makes
it. The result goes in as hold_bake's `dip` (pivot = the butt).

    cd rifles/assets; python ../tools/riflereload.py kar98 [--set low.drop=6 ...] [--scale 4]
"""
import sys, os, json, argparse, hashlib, copy
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import boltphys as BP           # RIFLE class + rb_* actions (and the shared gunphys)
gunphys = BP.gunphys
T = BP.T
_c = os.getcwd(); os.chdir(T)
import hold_bake as H
os.chdir(_c)
R = H.R
CTL = BP.CTL

gunphys.ACTIONS.update({
    'clip_set':  ((2.0, -6.0, 3.0, 0.0, 0.0), 2.0),      # the charger set into its guide from above
    'clip_push': ((9.0, -5.0, 9.0, 0.0, -1.0), 3.0),     # five rounds thumbed down against the magazine spring: the rifle is pushed down
    'mag_out_r': ((-3.0, 0.0, -8.0, 0.0, 0.0), 3.0),     # a box magazine pulled out below: the rifle lifts as the weight leaves
    'mag_in_r':  ((-10.0, 0.0, 14.0, 0.0, 0.6), 2.5),    # ...and rocked / pushed home from below
    # the trip to the pouch (no hand in view for most of a second): the right shoulder goes down and back with the
    # reaching arm and comes up again with the clip - the rifle, held by the left hand alone, follows the body
    'body_reach': ((1.6, 9.0, 3.0, -0.8, 0.6), 5.0),
    'body_back':  ((-1.4, -7.0, -2.5, 0.6, -0.5), 5.0),
    # the working hand lets go of the rifle (bolt knob / charger): what it was pressing down springs back
    'hand_off':   ((-1.6, -8.0, -2.0, 0.3, 0.0), 2.0),
    # the hand at the pouch, out of sight: the flap pulled open / the charger pulled free knocks through the shoulder
    'pouch_tug':  ((1.2, 5.0, 2.2, -0.5, 0.5), 2.0),
})

_CLIPS = {}
PIVOT = -22.0       # hold_bake dip pivot: 22 u BEHIND the eye along the sight line = the butt in the shoulder
GUNS = {
    'kar98': dict(
        gun='kar98', hip='viewmodel/rifle/kar98_reload.skc', charge='viewmodel/kar_stand00.skc', offhand=(1, 100),
        out='viewmodel/rifle/kar98_reload_ads.skc', enter=6, exit=8,
        # retail timeline (30 fps): knob lifted 8-9, bolt back 14-15, hand to the pouch 21-33, clip on the gun 43,
        # pushed 53-54 (charger) and 62-63 (rounds), bolt forward 78-79 (the charger is thrown out), down 82-84,
        # hand back on the grip 93-99
        # 2026-10-12 on target: 'bolt' / 'close' = boltphys.HOLD (the receiver eased 1.25 u down with the front sight
        # held on the target, canted to the hand) - the bolt is opened and closed there; only 'low' leaves the target
        # USER DECISION (variant A): the bolt is opened and closed with the rifle LOCKED on the sights
        # 2026-10-12 (coordinator, after the rb15 playback): the FULL reload is worked JUST UNDER THE CENTRE BOX from
        # its first stroke to its last - the rifle comes down first, the bolt is opened there, the charger thumbed in,
        # the bolt closed, and only then does the rifle come back up to the exact aim. Locked on the sights (rb15) the
        # full stroke of the reload clip brought the bolt to 1.1 u from the eye for 0.45 s at each end (boltnear.py:
        # bolt bbox 33-39 % of the screen) and the hand crossed the box (2.9 %); and 'low' sat so low (drop 4.3 u,
        # muzzle 3 deg down) that the action was at the bottom edge of the frame and the loading could not be seen.
        holds=dict(bolt=dict(drop=1.9, roll=7.0, pitch=0.6, side=0.3, back=-3.2),
                   # LOW: the muzzle swung down about the butt (which stays in the shoulder, so the left arm still
                   # reaches the fore-end): the open action comes under the centre box, its top turned to the eye
                   # LOW: the butt dropped from the shoulder toward the armpit, the rifle a little forward and turned to
                   # the working hand: the open action sits under the centre box with its top to the eye (a muzzle-down
                   # swing about the butt put it below the frame: v2), the charger is thumbed in there
                   low=dict(drop=2.5, roll=13.0, pitch=1.2, side=0.7, back=-3.2),
                   # the trip to the pouch: the right shoulder goes down and back with the reaching arm - the rifle,
                   # on the left hand alone, sags to that side and comes up again as the hand returns with the clip
                   reach=dict(drop=3.9, roll=25.0, pitch=2.8, side=-0.7, back=-2.2),
                   # the thumb presses the five rounds down against the magazine spring: the rifle is pressed down with
                   # them (and the hand over the charger stays under the centre box: 5.9 % at the 'low' height)
                   push=dict(drop=3.5, roll=13.0, pitch=1.6, side=0.7, back=-3.2),
                   # the bolt is shoved home while the rifle is still on its way up
                   close=dict(drop=1.9, roll=8.0, pitch=0.6, side=0.3, back=-3.2),
                   # run rb21: with a shallow 'down' (0.9 u) the rifle canted and went forward while still in the box - its own
                   # body read 2-6 % beyond the settled aim for 0.18 s at each end. Straight down / straight up, aligned,
                   # the whole way under the box; the cant and the reach forward only below it
                   down=dict(drop=1.9, roll=0.0, pitch=0.6, side=0.0, back=-0.6)),
        # 'down' = the bolt hold's drop and muzzle dip alone: the rifle leaves and re-enters the aim downward first
        pose=[(0, None), (5, 'down'), (10, 'bolt'), (16, 'bolt'), (21, 'low'), (27, 'reach'), (37, 'push'), (56, 'push'), (63, 'low'),
              (71, 'close'), (85, 'close'), (91, 'down'), (98, None), (101, None)],
        # the bolt strokes are worked with key_bolt's grip (one wrapped grip from retail frame 12, rolled under and
        # swung right of the knob so the hand body stays under the sight line), carried by the gun's own bolt bone
        # 2026-10-13 (rule 3: hands GRIP the control): the grasp is the bolt cycle's closed fist round the knob
        # (kar98_rechamber frame 12, as boltphys / key_bolt carry it), not this clip's own open cupped hand; the knob
        # sits IN the curl of the fingers (off 0.3 right / 0.1 down: under the box there is no rim to stay clear of)
        bolt=dict(anim='reload', gref=12, roll=35.0, yaw=-40.0, off=(0.0, 0.3, 0.1), spans=[(7, 18), (71, 85)],
                  src=dict(hip='viewmodel/rifle/kar98_rechamber.skc', frame=12, offhand=(1, 44), anim='rechamber')),
        # prop_from 8: the hand-over to the off hand at frame 1 is FADED by the cgame from the main-hand tag; with the
        # prop's value on that tag from frame 1 the rifle started the reload with a 0.1 s jump to the left (run ra6)
        prop_until=51, prop_from=8,
        # THE RIGHT HAND (2026-10-13, rb23 judged: open hand at the knob, flat hand over the receiver, no charger seen):
        #   19-45  retail: off the knob, down to the pouch, up with the charger (the server's prop rides this hand,
        #          drawn 27-45) and into the guides at 43 (the gun's own rounds + charger appear there)
        #   46-53  THE THUMB ON THE ROUNDS: the retail hand of frame 48 (thumb tip on the top round) turned 40 deg about
        #          that thumb tip - the wrist comes down beside the stock instead of lying flat over the receiver, the
        #          four fingers curled (finger_add) - and it goes DOWN with the stack in two pushes (46-48, 49-51);
        #          chargerclip.py sinks the gun's rounds by the same numbers
        #   55-63  the empty charger is plucked off (thumb back to its top, up out of the guide) and flicked away to the
        #          right and down - never upward through the centre (the retail hand threw it up past the lens)
        rhand=dict(aim=[(0, 3), (97, 101)], rel=[(19, 45)], way={5: (-0.8, 2.2, 2.6)},      # the reach to the knob dips under the sight line (run ra5: 3-5 % for two frames)
                   keys=dict([(f, dict(pivot=(48, 'Bip01 R Finger02', (22.0, 0.0, 0.0)), gun_add=(0.0, 0.0, z)))
                              for f, z in {46: 0.0, 47: 0.9, 48: 1.5, 49: 1.5, 50: 2.3, 51: 3.0, 52: 3.0, 53: 3.0}.items()] +
                             [(f, dict(pivot=(48, 'Bip01 R Finger02', (22.0, 0.0, 0.0)), gun_add=v))
                              for f, v in {55: (-1.2, 0.0, 0.3), 57: (-1.4, 0.8, -0.5), 59: (-2.0, 4.5, 1.5), 61: (-3.0, 8.0, 4.5),
                                           63: (-4.0, 10.0, 7.0)}.items()])),
        rc=dict(finger_add=dict([('Bip01 R Finger%s rot' % j, [(44, 0.0), (47, d), (63, d), (68, 0.0)])
                                 for j, d in {'1': 50, '11': 60, '2': 50, '21': 60, '3': 50, '31': 60, '4': 50, '41': 60}.items()] +
                                # the pluck: the thumb closes on the charger against the curled fingers (straight, it read as a pointing thumb: rb49)
                                [('Bip01 R Finger01 rot', [(53, 0.0), (56, 30.0), (63, 30.0), (68, 0.0)]),
                                 ('Bip01 R Finger02 rot', [(53, 0.0), (56, 40.0), (63, 40.0), (68, 0.0)])])),
        support=[(0, 1), (3, 1), (6, 0), (92, 0), (98, 1)],
        # multipliers are on top of --scale (2.5, the bolt cycle's): the clip events keep their first strength (x4)
        # the pouch (23-35): the shoulder goes down with the reaching arm, the hand tugs the pouch open (27) and pulls
        # the charger free (31) - two small knocks through the body - and comes up again
        events=[(8, 'rb_up'), (14, 'rb_back'), (15, 'rb_stop'), (19, 'hand_off'), (23, 'body_reach', 2.0), (27, 'pouch_tug', 1.0),
                (31, 'pouch_tug', 1.3), (35, 'body_back', 2.0),
                (43, 'clip_set', 2.0), (46, 'clip_push', 2.0), (49, 'clip_push', 2.2), (54, 'hand_off', 0.6), (58, 'hand_off', 0.5),
                (78, 'rb_fwd'), (82, 'rb_down'), (95, 'rb_grip')]),
    # MOSIN-NAGANT (92-frame hands clip, gun clip 76 frames: knob up 9-10, bolt back 13-15, forward + down 73-75).
    # Retail: hand to the pouch 20-36, the charger (the server's prop enfield_clip1.tik on tag_weapon_right, torso
    # frames 30-53) into the guides 46-48, the thumb on the rounds 48-52 and down 2.9 u at 53-54, then the hand flies UP
    # 5 u (56-60, throwing a charger the server has already removed) and comes back to shove the bolt home.
    # Aimed: the Kar98's plan and holds. The charger is PINNED in the guides from 46 and goes down under the thumb in two
    # pushes (49-50, 52-53); no empty charger exists as a model (the prop is one piece, removed at 53), so there is no
    # flick - the hand goes from the push to the bolt knob.
    'mosin': dict(
        gun='mosin_nagant_rifle', hip='viewmodel/mosin_nagant/mosin_nagant_reload.skc', charge='viewmodel/kar_stand00.skc', offhand=(1, 91),
        out='viewmodel/mosin_nagant/mosin_reload_ads.skc', enter=6, exit=8,
        holds=dict(bolt=dict(drop=1.9, roll=7.0, pitch=0.6, side=0.3, back=-3.2),
                   low=dict(drop=2.5, roll=13.0, pitch=1.2, side=0.7, back=-3.2),
                   reach=dict(drop=3.9, roll=25.0, pitch=2.8, side=-0.7, back=-2.2),
                   push=dict(drop=3.5, roll=13.0, pitch=1.6, side=0.7, back=-3.2),
                   close=dict(drop=1.9, roll=8.0, pitch=0.6, side=0.3, back=-3.2),
                   down=dict(drop=1.9, roll=0.0, pitch=0.6, side=0.0, back=-0.6)),
        pose=[(0, None), (5, 'down'), (9, 'bolt'), (16, 'bolt'), (21, 'low'), (27, 'reach'), (38, 'push'), (56, 'push'), (62, 'low'),
              (67, 'close'), (77, 'close'), (83, 'down'), (89, None), (91, None)],
        bolt=dict(anim='reload', gref=12, roll=35.0, yaw=-40.0, off=(0.0, 0.3, 0.1), spans=[(8, 17), (67, 77)],
                  src=dict(hip='viewmodel/rifle/kar98_rechamber.skc', frame=12, offhand=(1, 44), anim='rechamber', tik='models/weapons/kar98.tik')),
        prop_until=47, prop_from=8,
        prop_pin={'at': 48, 'from': 46, 'until': 62, 'blend': 3, 'sink': {48: 0.0, 49: 0.9, 50: 1.5, 51: 1.5, 52: 2.3, 53: 2.9}},
        rhand=dict(aim=[(0, 3), (88, 91)], rel=[(19, 45)], way={5: (-0.8, 2.2, 2.6)},
                   keys=dict([(f, dict(pivot=(50, 'Bip01 R Finger02', (48.0, 0.0, 0.0)), gun_add=(0.0, 0.0, z)))
                              for f, z in {48: 0.0, 49: 0.9, 50: 1.5, 51: 1.5, 52: 2.3, 53: 2.9, 54: 2.9, 56: 2.9}.items()] +
                             [(60, dict(pivot=(50, 'Bip01 R Finger02', (48.0, 0.0, 0.0)), gun_add=(-2.0, 3.0, 3.5)))])),
        rc=dict(finger_add=dict([('Bip01 R Finger%s rot' % j, [(46, 0.0), (49, d), (58, d), (64, 0.0)])
                                 for j, d in {'1': 50, '11': 60, '2': 50, '21': 60, '3': 50, '31': 60, '4': 50, '41': 60}.items()])),
        support=[(0, 1), (3, 1), (6, 0), (83, 0), (89, 1)],
        events=[(9, 'rb_up'), (13, 'rb_back'), (15, 'rb_stop'), (19, 'hand_off'), (23, 'body_reach', 2.0), (27, 'pouch_tug', 1.0),
                (31, 'pouch_tug', 1.3), (35, 'body_back', 2.0),
                (46, 'clip_set', 2.0), (49, 'clip_push', 2.0), (52, 'clip_push', 2.2), (58, 'hand_off', 0.6),
                (73, 'rb_fwd'), (75, 'rb_down'), (86, 'rb_grip')]),
    # LEE-ENFIELD (116-frame hands clip, gun clip 100 frames: knob up 4-5, bolt back 10-11, forward + down 94-99; ten
    # rounds = TWO chargers). Retail: hand to the pouch 20-36 and up with both chargers at 38-44 (the server's props:
    # enfield_clip2.tik rigid on the right HAND 30-53, enfield_clip1.tik on tag_weapon_right 30-80), first charger
    # thumbed in 48-54, the hand up 5 u (57-63), second charger set 69-78 and pushed 81-84, to the bolt 90-99.
    'enfield': dict(
        gun='lee_enfield', hip='viewmodel/enfield/enfield_reload.skc', charge='viewmodel/kar_stand00.skc', offhand=(1, 115),
        out='viewmodel/enfield/enfield_reload_ads.skc', enter=6, exit=8,
        holds=dict(bolt=dict(drop=1.9, roll=7.0, pitch=0.6, side=0.3, back=-3.2),
                   low=dict(drop=2.5, roll=13.0, pitch=1.2, side=0.7, back=-3.2),
                   reach=dict(drop=3.9, roll=25.0, pitch=2.8, side=-0.7, back=-2.2),
                   push=dict(drop=3.5, roll=13.0, pitch=1.6, side=0.7, back=-3.2),
                   close=dict(drop=1.9, roll=8.0, pitch=0.6, side=0.3, back=-3.2),
                   down=dict(drop=1.9, roll=0.0, pitch=0.6, side=0.0, back=-0.6)),
        pose=[(0, None), (5, 'down'), (9, 'bolt'), (16, 'bolt'), (21, 'low'), (27, 'reach'), (38, 'push'), (85, 'push'), (89, 'low'),
              (92, 'close'), (101, 'close'), (107, 'down'), (113, None), (115, None)],
        # gun anim reload_ads_loaded = the aim-only clip of chargerclip.py: knob up 8-9, bolt back 14-15 (released: 4-5, 10-11)
        bolt=dict(anim='reload_ads_loaded', gref=13, roll=35.0, yaw=-40.0, off=(0.0, 0.3, 0.1), spans=[(7, 17), (91, 101)],
                  src=dict(hip='viewmodel/rifle/kar98_rechamber.skc', frame=12, offhand=(1, 44), anim='rechamber', tik='models/weapons/kar98.tik')),
        # TWO CHARGERS, each as on the Mosin (run rb55, the retail hand kept: a big hand laid over the receiver, the
        # loading at the bottom edge of the frame, no charger seen going down). The server's prop on tag_weapon_right
        # (enfield_clip1.tik, 30-80) is what is seen both times: stood in the guides and thumbed down 46-55, hidden
        # in the receiver while the hand goes down out of the frame (it returns to the hand there, 57), brought up as
        # the second charger 66-69, stood in the guides and thumbed down 71-79.
        prop_until=70, prop_from=8,
        prop_pin=[{'at': 48, 'from': 46, 'until': 56, 'blend': 3, 'sink': {48: 0.0, 49: 0.9, 50: 1.5, 51: 1.5, 52: 2.3, 53: 2.9}},
                  {'at': 72, 'from': 69, 'until': 90, 'blend': 3, 'sink': {72: 0.0, 73: 0.9, 74: 1.5, 75: 1.5, 76: 2.3, 77: 2.9}}],
        rhand=dict(aim=[(0, 3), (112, 115)], rel=[(19, 45), (65, 69)], way={5: (-0.8, 2.2, 2.6)},
                   # the retail hand comes DOWN onto the action with the second charger (from its 5 u fly-up): kept under the box
                   add={65: (0, 2.0, 4.2), 66: (0, 1.8, 3.6), 67: (0, 1.4, 2.8), 68: (0, 0.9, 1.8), 69: (0, 0.4, 0.8)},
                   keys=dict([(f, dict(pivot=(50, 'Bip01 R Finger02', (48.0, 0.0, 0.0)), gun_add=(0.0, 0.0, z)))
                              for f, z in {48: 0.0, 49: 0.9, 50: 1.5, 51: 1.5, 52: 2.3, 53: 2.9, 54: 2.9, 55: 2.9}.items()] +
                             [(58, dict(pivot=(50, 'Bip01 R Finger02', (48.0, 0.0, 0.0)), gun_add=(-2.0, 5.0, 6.0))),
                              (61, dict(pivot=(50, 'Bip01 R Finger02', (48.0, 0.0, 0.0)), gun_add=(-2.0, 5.0, 6.0)))] +
                             [(f, dict(pivot=(75, 'Bip01 R Finger02', (48.0, 0.0, 0.0)), gun_add=(0.0, 0.0, z)))
                              for f, z in {72: 0.0, 73: 0.9, 74: 1.5, 75: 1.5, 76: 2.3, 77: 2.9, 78: 2.9, 80: 2.9}.items()] +
                             [(85, dict(pivot=(75, 'Bip01 R Finger02', (48.0, 0.0, 0.0)), gun_add=(-2.0, 3.0, 3.5)))])),
        # the four fingers curled while the thumb presses a charger down (straight, the retail hand reads as pointing)
        rc=dict(finger_add=dict([('Bip01 R Finger%s rot' % j, [(46, 0.0), (48, d), (60, d), (64, 0.0), (69, 0.0), (72, d), (84, d), (88, 0.0)])
                                 for j, d in {'1': 50, '11': 60, '2': 50, '21': 60, '3': 50, '31': 60, '4': 50, '41': 60}.items()])),
        support=[(0, 1), (3, 1), (6, 0), (107, 0), (113, 1)],
        events=[(8, 'rb_up'), (14, 'rb_back'), (15, 'rb_stop'), (19, 'hand_off'), (23, 'body_reach', 2.0), (27, 'pouch_tug', 1.0),
                (31, 'pouch_tug', 1.3), (35, 'body_back', 2.0),
                (46, 'clip_set', 2.0), (49, 'clip_push', 2.0), (52, 'clip_push', 2.2), (56, 'hand_off', 0.6),
                (70, 'clip_set', 2.0), (73, 'clip_push', 2.0), (76, 'clip_push', 2.2), (82, 'hand_off', 0.6),
                (95, 'rb_fwd'), (98, 'rb_down'), (110, 'rb_grip')]),
    # SPRINGFIELD M1903, iron sights. The game loads it ONE ROUND AT A TIME (torso state RELOAD_SPRINGFIELD: start,
    # one `reload_single` loop per round, end - the hip technique; no charger in this game), so the aimed reload is
    # three clips too. Hip clips: start 49 frames (knob up 8-9, bolt back 13-15, hand to the pouch from 19), loop 28
    # frames (the server's round prop springfield_clip_reload.tik on tag_weapon_right, drawn frames 0-5, removed and
    # counted at 8; retail: the hand is still on its way up from the pouch then - the round is at the action at 7-8),
    # end 32 frames (hand on the knob 4-8, bolt forward 8-10, knob down 11-15, grip 22-26).
    # Aimed: the rifle comes down under the centre box in `start` and stays in the loading hold through every loop.
    # THE LOOP IS RE-TIMED so the round is SEEN going in: frame 0 = the retail hand of frame 4 (already up beside the
    # action with the round), round on the action at 3, thumbed down 4-6, away to the pouch 12-21, up again by 27.
    # `start` therefore ends, and `end` begins, with the hand coming up (the loop's retail frame 3).
    'springfield': dict(
        gun='springfield_unscoped', hip='viewmodel/rifle/springfield_reload_start.skc', charge='viewmodel/sprng_stand00.skc', offhand=(1, 48),
        out='viewmodel/rifle/springfield_reload_ads.skc', enter=6, exit=0, chain='start',
        holds=dict(bolt=dict(drop=1.9, roll=7.0, pitch=0.6, side=0.3, back=-3.2),
                   low=dict(drop=2.5, roll=13.0, pitch=1.2, side=0.7, back=-3.2),
                   reach=dict(drop=3.9, roll=25.0, pitch=2.8, side=-0.7, back=-2.2),
                   push=dict(drop=2.4, roll=16.0, pitch=1.1, side=0.9, back=-3.2),
                   down=dict(drop=1.9, roll=0.0, pitch=0.6, side=0.0, back=-0.6)),
        pose=[(0, None), (5, 'down'), (9, 'bolt'), (16, 'bolt'), (21, 'low'), (26, 'reach'), (43, 'push'), (48, 'push')],
        bolt=dict(anim='reload', gref=13, roll=35.0, yaw=-40.0, off=(0.0, 0.3, 0.1), spans=[(7, 17)],
                  src=dict(hip='viewmodel/rifle/kar98_rechamber.skc', frame=12, offhand=(1, 44), anim='rechamber', tik='models/weapons/kar98.tik')),
        rhand=dict(aim=[(0, 3)], rel=[(19, 38)], way={5: (-0.8, 2.2, 2.6)},
                   keys={45: dict(clip=('viewmodel/rifle/springfield_reload_fill.skc', 2)),
                         48: dict(clip=('viewmodel/rifle/springfield_reload_fill.skc', 3))}),
        support=[(0, 1), (3, 1), (6, 0), (48, 0)],
        events=[(8, 'rb_up'), (14, 'rb_back'), (15, 'rb_stop'), (19, 'hand_off'), (23, 'body_reach', 2.0), (27, 'pouch_tug', 1.0),
                (31, 'pouch_tug', 1.3), (40, 'body_back', 2.0)]),
    'springfield_single': dict(
        gun='springfield_unscoped', hip='viewmodel/rifle/springfield_reload_fill.skc', charge='viewmodel/sprng_stand00.skc', offhand=(0, 27),
        out='viewmodel/rifle/springfield_reload_single_ads.skc', enter=0, exit=0, chain='loop',
        holds=dict(push=dict(drop=2.4, roll=16.0, pitch=1.1, side=0.9, back=-3.2)),
        pose=[(0, 'push'), (27, 'push')],
        # the round rides the hand as the retail art has it (tag_map: clip frame -> retail frame of the prop tag)
        rc=dict(free_tag=True, tag_map={0: 4, 1: 5, 2: 6, 3: 7, 4: 8, 6: 8, 8: 10, 10: 14, 12: 16, 14: 18, 17: 22, 21: 26, 24: 2, 27: 3}),
        rhand=dict(aim=[], rel=[], keys={0: dict(rel=4), 1: dict(rel=5), 2: dict(rel=6), 3: dict(rel=7),
                                         4: dict(rel=8, gun_add=(0.0, 0.0, 0.5)), 5: dict(rel=8, gun_add=(0.0, 0.0, 1.0)),
                                         6: dict(rel=8, gun_add=(0.0, 0.0, 1.0)), 8: dict(rel=10, gun_add=(0.0, 1.0, 1.5)),
                                         10: dict(rel=14, gun_add=(0.0, 1.5, 2.5)), 12: dict(rel=16), 14: dict(rel=18),
                                         17: dict(rel=22), 21: dict(rel=26), 24: dict(rel=2), 27: dict(rel=3)}),
        support=[(0, 0), (27, 0)],
        events=[(3, 'clip_set', 1.2), (5, 'clip_push', 1.6), (8, 'hand_off', 0.5), (15, 'body_reach', 0.8), (22, 'body_back', 0.8)]),
    'springfield_end': dict(
        gun='springfield_unscoped', hip='viewmodel/rifle/springfield_reload_end.skc', charge='viewmodel/sprng_stand00.skc', offhand=(0, 30),
        out='viewmodel/rifle/springfield_reload_end_ads.skc', enter=0, exit=8, chain='end',
        holds=dict(push=dict(drop=2.4, roll=16.0, pitch=1.1, side=0.9, back=-3.2),
                   close=dict(drop=1.9, roll=8.0, pitch=0.6, side=0.3, back=-3.2),
                   down=dict(drop=1.9, roll=0.0, pitch=0.6, side=0.0, back=-0.6)),
        pose=[(0, 'push'), (5, 'close'), (15, 'close'), (20, 'down'), (26, None), (31, None)],
        bolt=dict(anim='reload_end', gref=6, roll=35.0, yaw=-40.0, off=(0.0, 0.3, 0.1), spans=[(5, 15)],
                  src=dict(hip='viewmodel/rifle/kar98_rechamber.skc', frame=12, offhand=(1, 44), anim='rechamber', tik='models/weapons/kar98.tik')),
        rhand=dict(aim=[(26, 31)], rel=[], keys={0: dict(clip=('viewmodel/rifle/springfield_reload_fill.skc', 3))}),
        support=[(0, 0), (20, 0), (26, 1)],
        events=[(9, 'rb_fwd'), (12, 'rb_down'), (24, 'rb_grip')]),
    # M1 GARAND (hands vm_riflereload.skc, 61 frames = 2.03 s; gun clip 60 frames). Retail: the hand is away at the
    # pouch 8-20, comes up with the en-bloc clip at 24 (the server's prop garand_clip_reload.tik on tag_weapon_right,
    # torso frames 4-42), holds it on the open action 26-33 (the gun's OWN clip surface material8 is drawn 28-48, in the
    # same place), thumbs it down 2.8 u at 34-35 (gun bone `gun clip`), snatches the thumb away 38-42, lays the hand on
    # the operating-rod handle 46-48 and rides it forward as the bolt closes 49-52, grip at 56. No bolt work at the
    # start (the bolt stays back; an emptied Garand is already locked open, `idle_empty`, and has pinged on its last
    # shot - `fire_empty`, untouched).
    # Aimed: rifle down under the centre box at once, the pouch trip with the body's reach, the clip stood on the
    # action (prop PINNED in the gun's frame so the turned hand does not turn it; it sinks with the gun's own clip),
    # the thumb presses it down with the wrist beside the stock and comes clear to the right, the retail hand on the
    # operating-rod handle runs forward with the bolt, back to the aim.
    'garand': dict(
        gun='garand', hip='viewmodel/rifle/vm_riflereload.skc', charge='viewmodel/grnd_stand00.skc', offhand=(1, 57),
        out='viewmodel/rifle/coop_garand_reload_ads.skc', enter=5, exit=5,
        holds=dict(reach=dict(drop=3.9, roll=25.0, pitch=2.8, side=-0.7, back=-2.2),
                   push=dict(drop=3.5, roll=13.0, pitch=1.6, side=0.7, back=-3.2),
                   close=dict(drop=2.2, roll=9.0, pitch=0.8, side=0.4, back=-3.2),
                   down=dict(drop=1.9, roll=0.0, pitch=0.6, side=0.0, back=-0.6)),
        pose=[(0, None), (4, 'down'), (9, 'reach'), (19, 'reach'), (25, 'push'), (40, 'push'), (45, 'close'), (52, 'close'),
              (56, 'down'), (59, None), (60, None)],
        prop_until=27, prop_from=6,
        prop_pin={'at': 30, 'from': 26, 'until': 44, 'blend': 2, 'sink': {33: 0.0, 34: 1.42, 35: 2.83}},
        rhand=dict(aim=[(0, 2), (58, 60)], rel=[(4, 26), (44, 54)],
                   keys=dict([(f, dict(pivot=(30, 'Bip01 R Finger02', (20.0, 0.0, 0.0)), gun_add=(0.0, 0.0, z)))
                              for f, z in {28: 0.0, 33: 0.0, 34: 1.42, 35: 2.83, 37: 2.83}.items()] +
                             # THUMB CLEAR: out from under the bolt's path, to the right and back, before the hand goes to the handle
                             [(40, dict(pivot=(30, 'Bip01 R Finger02', (20.0, 0.0, 0.0)), gun_add=(-1.0, 3.0, 2.0)))])),
        # fingers curled while the thumb presses, and kept half closed on the operating-rod handle (the retail hand there
        # is an open hand with spread fingers)
        rc=dict(finger_add=dict([('Bip01 R Finger%s rot' % j, [(26, 0.0), (28, d), (40, d), (44, 0.6 * d), (53, 0.6 * d), (56, 0.0)])
                                 for j, d in {'1': 50, '11': 60, '2': 50, '21': 60, '3': 50, '31': 60, '4': 50, '41': 60}.items()])),
        support=[(0, 1), (2, 1), (4, 0), (54, 0), (58, 1)],
        events=[(3, 'hand_off'), (7, 'body_reach', 2.0), (13, 'pouch_tug', 1.2), (19, 'body_back', 2.0),
                (27, 'clip_set', 2.0), (34, 'clip_push', 3.0), (39, 'hand_off', 0.8), (46, 'rb_grip', 0.6),
                (50, 'rb_fwd', 1.2), (52, 'rb_stop', 1.0), (57, 'rb_grip')]),
}


def phys(g, n, ft, sc):
    z = (0.0,) * 5
    hv = lambda k: z if k is None else tuple(g['holds'][k][d] for d in gunphys.DOF)
    ev = [(e[0], e[1], (e[2] if len(e) > 2 else 1.0) * sc) for e in g['events']]
    ch = g.get('chain')
    if not ch:
        r = gunphys.simulate(n, ft, BP.RIFLE, support=g['support'], events=ev, pose=[(f, hv(k)) for f, k in g['pose']], fade=5)
        return r, ev
    # A ROUND-BY-ROUND reload is three clips the server strings together (start, one loop per round, end). The rifle
    # stays in its loading hold across the boundaries: `start` ends EXACTLY in the hold of its last pose key, `loop`
    # begins and ends in it (the strokes are a zero-ended excursion on top), `end` begins in it and returns to the aim.
    sm = lambda u: u * u * (3 - 2 * u)
    if ch == 'start':
        r = gunphys.simulate(n, ft, BP.RIFLE, support=g['support'], events=ev, pose=[(f, hv(k)) for f, k in g['pose']], fade=0)
        X = r['X'].copy(); Hh = np.array(hv(g['pose'][-1][1]), float)
        for f in range(n - 6, n):
            u = sm((f - (n - 6)) / 5.0)
            X[f] = (1 - u) * X[f] + u * Hh
    elif ch == 'loop':
        r = gunphys.simulate(n, ft, BP.RIFLE, support=g['support'], events=ev, pose=None, fade=5)
        X = r['X'] + np.array(hv(g['pose'][0][1]), float)
    else:
        pre = 40
        r = gunphys.simulate(n + pre, ft, BP.RIFLE, support=[(0, g['support'][0][1])] + [(f + pre, v) for f, v in g['support']],
                             events=[(e[0] + pre,) + tuple(e[1:]) for e in ev],
                             pose=[(0, hv(g['pose'][0][1]))] + [(f + pre, hv(k)) for f, k in g['pose']], fade=5)
        X = r['X'][pre:].copy(); Hh = np.array(hv(g['pose'][0][1]), float)
        for f in range(0, 4):
            u = sm(f / 4.0)
            X[f] = (1 - u) * Hh + u * X[f]
    r = dict(r, X=X, dip={f: tuple(float(v) for v in X[f]) for f in range(n)}, report='chain %s: %s' % (ch, r['report']))
    return r, ev


def right_path(g, hip):
    """hold_bake right_path: the aim grip at the ends, the retail hand-to-gun relation frame by frame in between, and
    on the bolt strokes one wrapped knob grip riding the gun's bolt bone (key_bolt's technique)"""
    import anahip, boltgrip
    V = H.V; B = H.B
    H.B = B
    rp = {}
    for a, b in g['rhand']['aim']:
        for f in range(a, b + 1):
            rp[f] = dict(aim=1)
    for f, add in g['rhand'].get('way', {}).items():      # reach waypoints: the aim grip moved in the gun frame (u: fwd, right, down)
        rp[f] = dict(aim=1, gun_add=add)
    rel_ = g['rhand']['rel']
    for a, b in ([rel_] if (rel_ and isinstance(rel_[0], int)) else rel_):
        for f in range(a, b + 1):
            rp[f] = dict(rel=f)
            if f in g['rhand'].get('add', {}):
                rp[f]['gun_add'] = g['rhand']['add'][f]
    lo_, hi_ = g['offhand']
    for f, sp in g['rhand'].get('keys', {}).items():      # hand-keyed frames (hold_bake _keyed specs), e.g. the thumb on the rounds
        sp = dict(sp)
        cl = sp.pop('clip', None)
        if cl:
            # (view clip under ANIM, frame): the hand-to-gun relation and the fingers of another clip's frame - the
            # hand at a chained clip's boundary is the neighbour clip's (the gun is on the off-hand tag in all of them)
            if cl[0] not in _CLIPS:
                _CLIPS[cl[0]] = R.load(R.ANIM + cl[0])
            Wc_ = R.evaluate(R.pose_dict(_CLIPS[cl[0]], cl[1]))
            sp['relT'] = Wc_['Bip01 R Hand'] @ R.inv(Wc_['tag_weapon_left' if lo_ >= 0 else 'tag_weapon_right'])
            sp.setdefault('fing', ('clip', cl[0], cl[1]))
        pv = sp.pop('pivot', None)
        if pv:
            # the retail hand of clip frame pv[0], TURNED about one of its own joints (pv[1], e.g. the thumb tip that
            # stays on the rounds) by pv[2] deg about the gun's x fwd / y right / z down axes: the same contact point,
            # the wrist and the hand's bulk somewhere else (beside the stock instead of over the receiver)
            Wk = R.evaluate(R.pose_dict(hip, pv[0]))
            Tg = Wk['tag_weapon_left' if lo_ <= pv[0] <= hi_ else 'tag_weapon_right']
            rel = Wk['Bip01 R Hand'] @ R.inv(Tg)
            kk = (Wk[pv[1]] @ R.inv(Tg))[3, 0:3]
            Rr = R.axis_angle_rows([1.0, 0, 0], pv[2][0]) @ R.axis_angle_rows([0, 1.0, 0], pv[2][1]) @ R.axis_angle_rows([0, 0, 1.0], pv[2][2])
            sp['relT'] = rel @ H.B.H(np.eye(3), -kk) @ H.B.H(Rr, np.zeros(3)) @ H.B.H(np.eye(3), kk)
            sp.setdefault('fing', pv[0])
        rp[f] = sp
    bo = g.get('bolt')
    if bo:
        lo, hi = g['offhand']
        tik = V.GUNTIK[g['gun']]
        Kn, kft = anahip.knob_traj(tik, bo['anim']); Ch, cft = boltgrip.chamber_traj(tik, bo['anim'])
        gi = lambda f, ft_, L: min(L - 1, int(round(f * hip.frameTime / ft_)))
        gr = bo['gref']
        src = bo.get('src')
        if src:
            # the grasp of ANOTHER clip (2026-10-13: the bolt cycle's closed fist round the knob - the reload clip's own
            # frame is an open, cupped hand beside the knob): hand-to-gun relation, knob point and bolt bone of that
            # clip's frame, carried by THIS reload's bolt bone
            shp = R.load(R.ANIM + src['hip'])
            sf = src['frame']; slo, shi = src['offhand']
            Ws = R.evaluate(R.pose_dict(shp, sf))
            rel = Ws['Bip01 R Hand'] @ R.inv(Ws['tag_weapon_left' if slo <= sf <= shi else 'tag_weapon_right'])
            stik = src.get('tik', tik)
            Ks, ksft = anahip.knob_traj(stik, src['anim']); Cs, csft = boltgrip.chamber_traj(stik, src['anim'])
            k = Ks[min(len(Ks) - 1, int(round(sf * shp.frameTime / ksft)))] / R.S
            Cref = Cs[min(len(Cs) - 1, int(round(sf * shp.frameTime / csft)))]
            fing = ('clip', src['hip'], sf)
            if stik != tik:
                # another RIFLE's grasp (key_bolt grip_src: the Kar98's wrapped fist on the Mosin / Enfield knob): the
                # hand keeps its place against the SOURCE knob and is carried over to this gun's knob at frame gref
                kt = Kn[gi(gr, kft, len(Kn))] / R.S
                rel = rel.copy(); rel[3, 0:3] += kt - k
                k = kt
                Cref = Ch[gi(gr, cft, len(Ch))]
        else:
            Wg = R.evaluate(R.pose_dict(hip, gr))
            rel = Wg['Bip01 R Hand'] @ R.inv(Wg['tag_weapon_left' if lo <= gr <= hi else 'tag_weapon_right'])
            k = Kn[gi(gr, kft, len(Kn))] / R.S
            Cref = Ch[gi(gr, cft, len(Ch))]
            fing = gr
        X = B.H(np.eye(3), -k) @ B.H(R.axis_angle_rows([1.0, 0, 0], bo['roll']) @ R.axis_angle_rows([0, 0, 1.0], bo['yaw']), np.zeros(3)) @ B.H(np.eye(3), k)
        relx = rel @ X
        rel_bolt0 = relx @ R.inv(Cref)

        def off_at(f):          # knob_off keyed per frame (boltphys): {frame: (x, y, z)} or one tuple
            o = bo.get('off')
            if o is None:
                return np.zeros(3)
            if isinstance(o, dict):
                ks = sorted(o)
                return np.array([H.K.pchip(ks, [o[q][i] for q in ks], f) for i in range(3)], float)
            return np.array(o, float)
        for a, b in bo['spans']:
            for f in range(a, b + 1):
                M = rel_bolt0 @ Ch[gi(f, cft, len(Ch))]
                M = M.copy(); M[3, 0:3] += off_at(f) / R.S
                rp[f] = dict(relT=M, fing=fing)
    return rp


def bake(name, root, sc=2.5, sets=()):
    g = copy.deepcopy(GUNS[name])
    for kv in sets:
        k, v = kv.split('=')
        h, d = k.split('.')
        g['holds'][h][d] = float(v)
    hip = R.load(R.ANIM + g['hip'])
    n, ft = hip.numFrames, hip.frameTime
    r, ev = phys(g, n, ft, sc)
    rc = dict(gun=g['gun'], hip=g['hip'], charge=g['charge'], offhand=g['offhand'], enter=g['enter'], exit=g['exit'],
              slide={}, weight=dict(on=False), handover=False, dip=r['dip'], dip_pivot=PIVOT,
              free_tag=False)      # no ammo prop on a hand tag (the charger is part of the gun mesh): both tags stay on the gun
    if g.get('rhand'):
        rc['right_path'] = right_path(g, hip)
    rc.update(g.get('rc', {}))
    H.RECIPES['_r_' + name] = rc
    sk, _ = H.bake('_r_' + name, CTL)
    pu = g.get('prop_until')
    if pu:
        # the server attaches an ammo prop to the hand tag the gun is NOT on (kar98_clip_reload.tik on tag_weapon_right,
        # torso frames 0-50): up to there that tag keeps the hip art's value (the prop rides the hand); afterwards BOTH
        # tags are on the gun, so the hand-over back to the main hand at the end of the reload lands on the gun
        # whichever frame it arrives (run ra2: the gun swung out for 0.2 s after the clip)
        H.RECIPES['_r2_' + name] = dict(rc, free_tag=True)
        sk2, _ = H.bake('_r2_' + name, CTL)
        cm = R.chanmap(sk)
        other = 'tag_weapon_right' if g['offhand'][0] >= 0 else 'tag_weapon_left'
        for ch in (other + ' rot', other + ' pos'):
            for f in range(g.get('prop_from', 1), pu + 1):
                sk.V[f, cm[ch]] = sk2.V[f, cm[ch]]
        sk.values = [[[float(np.float32(x)) for x in sk.V[f, c]] for c in range(sk.numChannels)] for f in range(n)]
    for pp in ([g['prop_pin']] if isinstance(g.get('prop_pin'), dict) else (g.get('prop_pin') or [])):
        # THE CHARGER STANDS IN THE GUIDES (2026-10-13): the server's ammo prop hangs on the hand tag the gun is not on.
        # From `from` to `until` that tag is put where the retail art has it at frame `at` - in the GUN's frame (in the
        # charger guides) - instead of riding the hand, so the hand can be turned / the thumb pressed down without the
        # charger turning with it; `sink` {frame: u} lowers it with the thumb (the rounds go into the magazine; the
        # prop is ONE model, charger and rounds - the server removes it at its own frame)
        lo, hi = g['offhand']
        other = 'tag_weapon_right' if lo >= 0 else 'tag_weapon_left'
        hand = 'Bip01 R Hand' if other.endswith('right') else 'Bip01 L Hand'
        Wr = R.evaluate(R.pose_dict(hip, pp['at']))
        P0 = Wr[other] @ R.inv(Wr['tag_weapon_left' if lo <= pp['at'] <= hi else 'tag_weapon_right'])
        cm = R.chanmap(sk)
        sink = pp.get('sink', {0: 0.0})
        ks = sorted(sink)
        a, b = pp['from'], pp['until']
        for f in range(a, b + 1):
            Wf = R.evaluate(R.pose_dict(sk, f))
            Gf = Wf['tag_weapon_left' if lo <= f <= hi else 'tag_weapon_right']
            d = float(np.interp(f, ks, [sink[k_] for k_ in ks]))
            P = P0.copy(); P[3, 2] += d / R.S
            tl = P @ Gf @ R.inv(Wf[hand])
            q = R.rows_to_quat(tl[0:3, 0:3]); pos = tl[3, 0:3]
            wb = min(1.0, (f - a + 1) / float(pp.get('blend', 2)))          # eased over from the hand-carried value
            q0 = np.array(sk.V[f, cm[other + ' rot']], float); p0 = np.array(sk.V[f, cm[other + ' pos']], float)
            sk.V[f, cm[other + ' rot']] = R.qslerp(q0, q, wb)
            sk.V[f, cm[other + ' pos']] = np.array([*((1 - wb) * p0[0:3] + wb * pos), 0.0])
    if g.get('prop_pin'):
        sk.values = [[[float(np.float32(x)) for x in sk.V[f, c]] for c in range(sk.numChannels)] for f in range(n)]
    bts = R.skc_io.write(sk)
    dst = os.path.join(root, 'models', 'human', 'animation', g['out'].replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(bts)
    print(name, '->', g['out'], n, 'frames x %.4f s' % ft, hashlib.md5(bts).hexdigest()[:8])
    print('   ', r['report'])
    json.dump(dict(gun=name, holds=g['holds'], pose=g['pose'], scale=sc, events=[list(e) for e in ev], cls=BP.RIFLE,
                   report=r['report'], md5=hashlib.md5(bts).hexdigest()), open(dst[:-4] + '_phys.json', 'w'), indent=1)
    return dst


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('--root', default='.'); ap.add_argument('--set', action='append', default=[])
    ap.add_argument('--scale', type=float, default=2.5)
    a = ap.parse_args()
    for nm in a.gun.split(','):
        bake(nm, a.root, a.scale, a.set)
