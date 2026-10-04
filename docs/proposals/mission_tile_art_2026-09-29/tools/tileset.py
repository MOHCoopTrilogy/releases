"""tileset.py - AUTHORED picks for the full tile set: one entry per tile (key = the tile's bsp), read by build_set.py.

raw    the source: a path to a real in-engine frame, or (pak, member) of a retail still read straight from the paks
focus  (x0,y0,x1,y1) in source pixels: what MUST be in shot; every crop is fitted around it at its exact aspect
allow  (x0,y0,x1,y1) the region crops may use (keeps console lines, the ride vehicle, retail vignettes out)
max_aspect  a source narrower than the window is printed at this aspect on paper instead of being cropped harder
key    median luminance target of the finish (night ~0.30, snow ~0.52)
how    provenance + the QA note that justifies the pick
"""
import os

TA = r"G:\mohaa-tileart\runs"
LA = r"G:\mohaa-loadart\runs"
SLIDE = "mainta/pak1.pk3"
AAB = "main/Pak1.pk3"


def slide(camp, k):
    return (SLIDE, "textures/mohmenu/Slideshow/%s/%s.jpg" % (camp, k))


def aab(n):
    return (AAB, "textures/mohmenu/briefing/%s.tga" % n)


def FR(mp, frame, rt=False):
    """A scouted frame under TA: full_<mp>/<mp>_<frame>.jpg, or rt_<mp>/rt<mp>_<frame>.jpg for the retake run."""
    if rt:
        return os.path.join(TA, "rt_" + mp, "rt%s_%s.jpg" % (mp, frame))
    return os.path.join(TA, "full_" + mp, "%s_%s.jpg" % (mp, frame))


def S(mp, frame, focus, key, how, allow=(0, 80, 1920, 1080), rt=False, **kw):
    d = dict(raw=FR(mp, frame, rt), focus=focus, allow=allow, key=key, how="in-engine: " + how)
    d.update(kw)
    return d


SPECS = {
    # ------------------------------------------------------------------ briefings: the campaign's own retail photos
    "briefing/briefing1": dict(raw=aab("portphoto"), focus=(20, 30, 492, 482), allow=(12, 12, 500, 500), max_aspect=1.36,
                               key=0.45, how="retail AA M1 briefing slide 'portphoto': the Arzew harbour from the heights"),
    "briefing/briefing2": dict(raw=aab("subdiving"), focus=(20, 30, 492, 482), allow=(12, 12, 500, 500), max_aspect=1.36,
                               key=0.45, how="retail AA M2 briefing slide 'subdiving': a U-boat at sea"),
    "briefing/briefing3": dict(raw=aab("higginsboat"), focus=(20, 30, 492, 482), allow=(12, 12, 500, 500), max_aspect=1.36,
                               key=0.42, how="retail AA M3 briefing slide 'higginsboat': troops in a landing craft"),
    "briefing/briefing4": dict(raw=aab("manorhouse"), focus=(20, 30, 492, 482), allow=(12, 12, 500, 500), max_aspect=1.36,
                               key=0.45, how="retail AA M4 briefing slide 'manorhouse': the manor house (the command post)"),
    "briefing/briefing5": dict(raw=aab("kingtiger"), focus=(20, 60, 492, 470), allow=(12, 12, 500, 500), max_aspect=1.36,
                               key=0.40, how="retail AA M5 briefing slide 'kingtiger': a King Tiger in the town"),
    "briefing/briefing6": dict(raw=aab("schmerzenaerial"), focus=(12, 12, 444, 332), allow=(6, 6, 450, 338), max_aspect=1.36,
                               key=0.45, how="retail AA M6 briefing slide 'schmerzenaerial': aerial recon photo of Fort Schmerzen"),
    "briefing/briefingt1": dict(raw=slide("Normandy", "C"), focus=(36, 28, 466, 368), allow=(30, 22, 472, 376), max_aspect=1.36,
                                key=0.50, how="retail SH Normandy slideshow still C: the paratroop drop (t1 opens with the jump)"),
    "briefing/briefingt2": dict(raw=slide("Bastogne", "E"), focus=(34, 22, 460, 356), allow=(30, 18, 470, 360), max_aspect=1.36,
                                key=0.45, how="retail SH Bastogne slideshow still E: soldiers holding the BASTOGNE town sign"),
    "briefing/briefingt3": dict(raw=slide("Berlin", "M"), focus=(26, 24, 474, 352), allow=(20, 18, 480, 358), max_aspect=1.36,
                                key=0.45, how="retail SH Berlin slideshow still M: a Soviet mortar crew (t3 fights beside the Red Army)"),
    "briefing/briefinge2": dict(raw=TA + r"\e2l1\gl_r650_270.tga", focus=(640, 280, 1760, 1000), allow=(250, 90, 1920, 1030),
                                key=0.40, how="in-engine: e2l1's own opening - glider troops beside a jeep inside the CG-4A"),
    # ------------------------------------------------------------------ levels already picked
    "m1l2a": dict(raw=LA + r"\scout\m1l2a\sc_m1l2a_4_180.jpg", focus=(800, 120, 1640, 780), allow=(460, 20, 1920, 836),
                  key=0.30, how="in-engine: the Arzew courtyard at night (loadart scout 4_180)"),
    "m5l2a": dict(raw=LA + r"\scout\m5l2a\sc_m5l2a_4_000.jpg", focus=(200, 250, 1800, 1000), allow=(0, 90, 1920, 1080),
                  key=0.42, how="in-engine: the destroyed village itself - rubble, gutted houses, the road (loadart scout 4_000)"),
    "e1l1": dict(raw=TA + r"\e1l1\pz_r600_000.tga", focus=(380, 300, 1380, 660), allow=(360, 80, 1920, 668),
                 key=0.45, how="in-engine: the level's own GIs along the barbed-wire wall, a Sherman down the track in the "
                                "dust haze; allow stops above the ride truck's wheel"),
    # ------------------------------------------------------------------ batch A/B (picked from the scouting pick sheets)
    "training": S("training", "s0tigertank_r450_300", (140, 300, 1260, 780), 0.42, "the training yard's own Tiger I among the sheds"),
    "m4l0": S("m4l0", "sc3_000", (300, 200, 1300, 800), 0.45, "the Normandy farm buildings on the hill, seen down the farm track"),
    "m1l1": S("m1l1", "st_270", (0, 80, 1500, 1080), 0.45, "the Rangers in the truck at the start of the level", allow=(0, 60, 1920, 1080)),
    "m1l2b": S("m1l2b", "s2obj_r300_120", (180, 250, 1200, 920), 0.32, "the motor pool's Opel truck with its hood up, a mechanic behind it"),
    "m1l3a": S("m1l3a", "sc0_090", (350, 130, 1050, 650), 0.28, "the night depot: truck, crates and lamp; cropped left of the jeep gun",
               crop_c=(0, 180, 890, 880), crop_s=(0, 290, 890, 807), pcrop_c=(0, 213, 890, 880), pcrop_s=(0, 330, 890, 831)),
    "m1l3b": S("m1l3b", "sthi_180", (0, 290, 890, 990), 0.28, "the airfield wall and gate, a truck of infantry firing; cropped clear of the jeep gun",
               crop_c=(0, 290, 890, 990), crop_s=(0, 180, 912, 710), pcrop_c=(0, 300, 890, 967), pcrop_s=(0, 190, 900, 696)),
    "m1l3c": S("m1l3c", "s4obj_r600_060", (400, 40, 1500, 900), 0.28, "the lighthouse lamp room and dome above the rocks", allow=(0, 0, 1920, 1080)),
    "m2l1": S("m2l1", "s2obj_r300_000", (450, 300, 1300, 780), 0.50, "German guards at the camp fence in the snow"),
    "m2l2a": S("m2l2a", "s2obj_r300_060", (350, 340, 1500, 1080), 0.32, "the Naxos laboratory: scientists at the blackboard"),
    "m2l2c": S("m2l2c", "sc0_090", (300, 200, 1920, 1080), 0.30, "the U-boat in its pen, seen from the dock"),
    "m2l3": S("m2l3", "s2obj_r600_180", (300, 200, 1800, 1000), 0.50, "a boxcar on the snowy siding of the rail yard, behind the fence (review 2026-10-04: the earlier pick showed uniformed figures of unclear side in the boxcar)"),
    "m3l1a": S("m3l1a", "s1obj_r300_240", (0, 80, 1920, 1080), 0.45, "GIs in the landing craft, ramp up"),
    "m3l2": S("m3l2", "s1panzeriveu_r450_300", (500, 250, 1500, 850), 0.35, "a Panzer in the sunken lane between the hedgerows"),
    "m4l1": S("m4l1", "sc0_000", (700, 280, 1500, 800), 0.30, "two figures meeting on the night path"),
    "m4l2": S("m4l2", "s2obj_r600_120", (0, 120, 1500, 900), 0.30, "the level's own Tiger I in the tank park beside the tents (bomb the Tigers)"),
    "m4l3": S("m4l3", "s4obj_r600_180", (100, 100, 1920, 1080), 0.38, "the manor's dining room, two Germans at the far door"),
    "m5l1a": S("m5l1a", "sthi_090", (0, 80, 1920, 1080), 0.45, "the village edge: half-timbered house, rubble slope, garden wall"),
    "m5l1b": S("m5l1b", "s0kingtank_r800_060", (450, 100, 1900, 760), 0.42, "the town hall with a King Tiger before it", allow=(0, 95, 1920, 1080)),
    "m5l2b": S("m5l2b", "s1tigertank_r450_060", (400, 250, 1500, 900), 0.42, "a Tiger I on the country road", allow=(0, 100, 1920, 1080)),
    "m6l1b": S("m6l1b", "s0obj_r600_240", (450, 350, 1500, 950), 0.32, "the anti-aircraft gun on the snowy bunker roof", allow=(0, 95, 1920, 1080)),
    "m6l1c": S("m6l1c", "sc2_180", (0, 80, 1920, 1080), 0.40, "the research bunker's yard: watchtower, fence, a guard"),
    "m6l2a": S("m6l2a", "s0radiomilit_r450_180", (0, 100, 1920, 1080), 0.35, "the radio station's huts and mast in the snow", allow=(0, 95, 1920, 1080)),
    "m6l2b": S("m6l2b", "s2obj_r600_240", (0, 100, 1920, 1080), 0.30, "the rail junction and signal tower", allow=(0, 95, 1920, 1080)),
    "m6l3a": S("m6l3a", "sc3_270", (0, 0, 1920, 1080), 0.30, "the fort's yard from above: train, fence, watchtower", allow=(0, 0, 1920, 1080)),
    "m6l3b": S("m6l3b", "sc1_090", (200, 0, 1500, 1080), 0.28, "a guard in the fort's timbered corridor", allow=(0, 0, 1920, 1080)),
    "m6l3c": S("m6l3c", "sc3_270", (0, 0, 1920, 1080), 0.28, "two soldiers running the long service corridor", allow=(0, 0, 1920, 1080)),
    "m6l3d": S("m6l3d", "s0obj_r300_180", (500, 200, 1900, 1000), 0.30, "the plant's pipe gallery and catwalks", allow=(0, 100, 1920, 1080)),
    "m6l3e": S("m6l3e", "s1obj_r600_300", (0, 60, 1920, 1080), 0.35, "the rail platform: boxcars, steps, the arch and a guard", allow=(0, 0, 1920, 1080)),
    # ------------------------------------------------------------------ 2026-10-04: AA retakes + re-picks (coordinator QA)
    # (later keys override the batch A/B entries above: m4l2, m4l3, m5l1a, m6l3e re-picked; e1l1 made stronger)
    "m2l2b": S("m2l2b", "s0uboat_r850_060", (450, 80, 1800, 950), 0.30, "the U-529 itself in its pen: hull, deck "
               "rail and conning tower, from the dock", rt=True),
    "m3l1b": S("m3l1b", "s115cmcannon_r450_060", (0, 150, 1920, 1080), 0.42, "the level's own casemated coastal gun "
               "(statweapons 15cm cannon) on its emplacement", rt=True),
    "m3l3": S("m3l3", "s1nebel2_r350_120", (500, 350, 1500, 950), 0.45, "the level's own Nebelwerfer (six-tube "
              "launcher on its carriage) inside the wire", rt=True),
    "m5l3": S("m5l3", "s0bridge_r1000_120", (0, 100, 1700, 1000), 0.40, "the stone bridge over the canal, a flak gun "
              "on it, the half-timbered town behind", rt=True),
    "m6l1a": S("m6l1a", "s120mmflak_r450_180", (270, 150, 1500, 1080), 0.46, "the level's own 20mm flak in its "
               "sandbag ring under camouflage net, crew in winter gear", rt=True),
    "m4l2": S("m4l2", "s4obj_r300_000", (650, 150, 1920, 1080), 0.30, "one of the Tiger I tanks to bomb (objective "
              "2), beside the tank-park tents"),
    "m4l3": S("m4l3", "s1officers_r260_120", (0, 200, 1300, 850), 0.38, "German officers at the command post's "
              "map tables", rt=True),
    "m5l1a": S("m5l1a", "s1obj_r600_060", (600, 100, 1600, 1000), 0.42, "the arched gate into the rest of the town "
               "(objective 2), rubble before it", allow=(560, 80, 1920, 1080)),
    "m6l3e": S("m6l3e", "s1rangers_r600_000", (0, 250, 1650, 1000), 0.34, "the escape train's boxcars at the "
               "fort's platform (Escape Fort Schmerzen)", allow=(0, 80, 1700, 1080), rt=True),
    # ------------------------------------------------------------------ batch C: Breakthrough
    "e1l1": S("e1l1", "sc2_090", (250, 120, 1380, 900), 0.40, "the level's own Shermans in the dust under the "
              "watchtower", allow=(0, 80, 1380, 1000)),
    "e1l2": S("e1l2", "sc3_090", (250, 300, 1700, 1080), 0.48, "a gun turret firing from its concrete emplacement "
              "in the pass"),
    "e1l3": S("e1l3", "s0canal_r900_180", (0, 150, 1920, 950), 0.45, "the canal: its rowboats, the lift-bridge "
              "towers and the quay houses"),
    "e2l1": S("e2l1", "sc2_180", (0, 80, 1700, 1000), 0.40, "a paratrooper hung up by his canopy on a pole beside the railway (checkpoint The Railway)"),
    "e2l2": S("e2l2", "s1oiltanker_r800_060", (0, 80, 1920, 1000), 0.30, "the airfield's fuel trucks under the "
              "refuelling canopy at night"),
    "e2l3": S("e2l3", "sc3_180", (200, 500, 1500, 1000), 0.42, "an Italian tank beside a farm cart at the edge of Gela"),
    "e3l1": S("e3l1", "s1shermanbas_r450_060", (500, 200, 1700, 900), 0.40, "a Sherman in the lane below the "
              "monastery hill"),
    "e3l2": S("e3l2", "sc0_270", (0, 200, 1800, 1000), 0.30, "the town square at night: field gun, sandbags, "
              "street lamps"),
    "e3l3": S("e3l3", "s0panzerwerf_r800_180", (300, 100, 1920, 1000), 0.35, "the level's railway gun on its "
              "flatcars at the siding"),
    "briefing/briefinge1": dict(raw=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sources",
                                                 "bt2_e1l3.jpg"),
                                focus=(650, 60, 1470, 703), allow=(650, 0, 1920, 720), key=0.42,
                                crop_c=(650, 60, 1470, 703), crop_s=(650, 0, 1920, 720), pcrop_c=(650, 60, 1470, 675),
                                pcrop_s=(650, 20, 1920, 720),
                                how="in-engine: Bizerte's Moorish horseshoe gate (e1l3, loadart scout 4_000; round-2 "
                                    "sample, QA'd: crates and vehicle hood boxed out)"),
    "briefing/briefinge3": S("e3l1", "sc1_270", (0, 150, 1920, 1080), 0.36, "the ruined town in the fog below "
                             "Monte Cassino"),
    # ------------------------------------------------------------------ batch C: Spearhead
    "t1l1": S("t1l1", "sc1_270", (0, 80, 1920, 700), 0.28, "the Norman farm buildings at night", allow=(0, 80, 1920, 760)),
    "t1l2": S("t1l2", "s2pflak88_r450_240", (450, 300, 1700, 1000), 0.28, "a German 88 and its crew at night "
              "(Locate and Destroy Artillery Emplacements)"),
    "t1l3": S("t1l3", "s0tigertankd_r800_060", (150, 300, 1300, 1000), 0.30, "the level's knocked-out Tiger on the "
              "night road, a fire burning behind it"),
    "t2l1": S("t2l1", "s0pz4_r420_120", (500, 300, 1900, 1050), 0.52, "the level's own Panzer IV in the snow, "
              "side-on"),
    "t2l3": S("t2l3", "sthi_180", (500, 300, 1700, 1050), 0.30, "the foxhole line in the snowy woods at night"),
    "t2l4": S("t2l4", "sc3_090", (300, 150, 1800, 1000), 0.30, "the snowed-in town at night: lit windows, the "
              "church spire"),
    "t3l1": S("t3l1", "s1panzerbrow_r800_000", (0, 150, 1920, 1000), 0.30, "Berlin in the rain: rubble and "
              "gutted apartment blocks"),
    # ------------------------------------------------------------------ ride levels (2026-10-04). Batch C never left the
    # opening ride. Retake C2 (ride release hook) freed e1l4 and t2l2; e3l4 (jeep .30cal) and t3l2 (T-34 driver) stayed
    # held, so those two remain PROVISIONAL: cropped clear of the ride (no weapon, no vehicle) from the level's own frames.
    "e1l4": S("e1l4", "s0ship_r1500_120", (0, 80, 1920, 1080), 0.28, "Bizerte harbour at night: the quay cranes, the "
              "ship's deck, crates on the dock (retake C2, ride released)",
              raw=os.path.join(TA, "r2_e1l4", "r2e1l4_s0ship_r1500_120.jpg")),
    "e3l4": S("e3l4", "sc2_090", (0, 150, 1400, 660), 0.32, "the mountain road at night: an overturned truck in the "
              "fog (PROVISIONAL)", allow=(0, 80, 1920, 670)),
    "t2l2": S("t2l2", "s0panzerwerf_r450_240", (650, 350, 1600, 1000), 0.50, "the level's own Panzerwerfer (rocket "
              "launcher on its halftrack) on the wooded mountain slope (retake C2, ride released)",
              raw=os.path.join(TA, "r2_t2l2", "r2t2l2_s0panzerwerf_r450_240.jpg")),
    "t3l2": S("t3l2", "s0tigerbase_r450_000", (560, 180, 1920, 590), 0.38, "a Berlin street of rubble below an "
              "apartment block, a ruined church beyond (PROVISIONAL)", allow=(0, 80, 1920, 570)),
}
