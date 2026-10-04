"""samples.py - the sample tiles.

    python tools/samples.py sources   # copy each chosen raw frame into ../sources/ (jpg q95) + SOURCES.json provenance
    python tools/samples.py crops     # ../samples/qa/crops.jpg - card (c, s) and print (c, s) boxes on each source
    python tools/samples.py cards     # per layout c (ui_menuCenter 1) and s (default stretch, 16:9):
                                      #   ../samples/full/<id>_card_<l>_1024.jpg, ../samples/game/<id>_<l>.jpg (512, shipped),
                                      #   ../samples/full/<id>_print_<l>_1024x768.jpg (war-room print)

Sources are real game frames only: in-engine screenshots (G:\\mohaa-loadart runs, or this proposal's own staging run under
G:\\mohaa-tileart) and retail stills read straight out of the retail paks. Nothing is generated.
Samples marked pending=True wait for the staging run (docs/proposals/mission_tile_art_2026-09-29/staging/).
"""
import io
import json
import os
import sys
import zipfile

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)
SRC = os.path.join(PROP, "sources")
sys.path.insert(0, HERE)

RUNS = r"G:\mohaa-loadart\runs"
STAGE = r"G:\mohaa-tileart\runs"
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"

SPECS = {
    "aa1_m1l2a": dict(bsp="m1l2a", raw=RUNS + r"\scout\m1l2a\sc_m1l2a_4_180.jpg",
                      how="in-engine: loadart scout pass, m1l2a position 4, yaw 180 (2026-09-28, 1920x1080, HUD off, no chat line in frame)",
                      crop=(700, 20, 1740, 836), pcrop_s=(469, 20, 1920, 836), key=0.30),   # y <= 836: the player's rifle stays out
    "bt2_e1l3": dict(bsp="e1l3", raw=RUNS + r"\scout\e1l3\sc_e1l3_4_000.jpg",
                     how="in-engine: loadart scout pass, e1l3 position 4, yaw 0",
                     # every box keeps x >= 650 (eagle-marked crates stay out) and y <= 736 (the vehicle hood stays out)
                     crop=(650, 60, 1470, 703), crop_s=(650, 0, 1920, 720), pcrop_c=(650, 60, 1470, 675),
                     pcrop_s=(650, 20, 1920, 720), key=0.42),
    "brief_t2": dict(bsp="briefing/briefingt2", raw=("mainta/pak1.pk3", "textures/mohmenu/Slideshow/Bastogne/E.jpg"),
                     how="retail still: Spearhead's own Bastogne slideshow (mainta/pak1.pk3 textures/mohmenu/Slideshow/Bastogne/E.jpg, "
                         "500x375, a wartime photograph: soldiers holding the BASTOGNE town sign). Cropped inside its burned-in vignette.",
                     crop=(34, 22, 460, 356), max_aspect=1.36, key=0.45),
    # ---- re-staged in this proposal's own run, 2026-09-29 12:20-12:27 (staging/run.log, G:\mohaa-tileart\runs) ----
    # Every box starts below y 80: the engine still printed "UnnamedSoldier#8240 has joined the Allies" at y ~58.
    "aa2_m5l2a": dict(bsp="m5l2a", raw=STAGE + r"\m5l2a\kt_r520_000.tga",
                      how="in-engine staged: the level's OWN King Tiger (vehicle_german_kingtigertank, vehicles//kingtank.tik, "
                          "targetname playertank, 3068 -4128 360 in the retail BSP) where the level places it; camera 520 u off, low",
                      crop=(497, 330, 1453, 1080), crop_s=(328, 330, 1622, 1080), pcrop_c=(475, 330, 1475, 1080),
                      pcrop_s=(308, 330, 1641, 1080), key=0.40),   # to y 1080: tracks, ground contact and shadow in frame
    "sh1_t2l1": dict(bsp="t2l1", raw=STAGE + r"\t2l1\bs_y+0_02.tga",
                     how="in-engine staged: the loadart Bastogne road camera, no smoke-sprite emitters; frame 02: GIs firing on "
                         "German infantry advancing beside the Panzer IV (frame +12_07 was rejected: a GI lined up with a corpse)",
                     crop=(686, 380, 1515, 1030), crop_s=(540, 380, 1661, 1030), pcrop_c=(667, 380, 1534, 1030),
                     pcrop_s=(523, 380, 1679, 1030), key=0.50),
    "bt1_e1l1": dict(bsp="e1l1", raw=STAGE + r"\e1l1\ks_y+35_01.tga",
                     how="in-engine staged: the level's own disabled Sherman (thrown track on the sand) in the dust-hazed camp; "
                         "no spawned props. Every box stays above the ride truck's wheel (y <= 690) and right of the pole (x >= 560)",
                     # tight on the tank (x 925-1335, y 475-675); the thin line above the tent is the level's smoke wisp
                     crop=(905, 330, 1364, 690), crop_s=(824, 330, 1445, 690), pcrop_c=(895, 330, 1375, 690),
                     pcrop_s=(815, 330, 1455, 690), key=0.42),
    "brief_e2": dict(bsp="briefing/briefinge2", raw=STAGE + r"\e2l1\gl_r650_270.tga",
                     how="in-engine: e2l1's own opening - glider troops braced beside a jeep inside the CG-4A before the Sicily "
                         "landing (the coop intro binds the player in the glider). Boxes keep out the jeep's bumper serial (y <= 1030) "
                         "and the console line (y >= 90); the pilot frame was rejected (his shoulder patch renders as a blob)",
                     crop=(580, 90, 1779, 1030), crop_s=(520, 150, 1920, 962), pcrop_c=(553, 90, 1806, 1030),
                     pcrop_s=(520, 160, 1920, 948), key=0.40),   # _s: x >= 520 keeps the wall's stain decal out
    # ---- still pending ----
    "sh2_t3l2": dict(bsp="t3l2", pending=True, raw=STAGE + r"\t3l2\bf_y+20_00.tga",
                     how="FAILED QA twice: the spawned Soviet pair (nodes 1127/1130) stand fused and idle in every frame of both "
                         "cameras. Next pass: film the level's own scripted bridge defence (objective 3) instead of spawned actors"),
}


def titles():
    return json.load(open(os.path.join(HERE, "titles.json"), encoding="utf-8"))["tiles"]


def src_path(i):
    return os.path.join(SRC, i + ".jpg")


def live():
    return [i for i, s in SPECS.items() if not s.get("pending")]


def read_raw(raw):
    if isinstance(raw, tuple):
        return Image.open(io.BytesIO(zipfile.ZipFile(os.path.join(GOG, raw[0])).read(raw[1]))).convert("RGB")
    return Image.open(raw).convert("RGB")


def do_sources():
    os.makedirs(SRC, exist_ok=True)
    prov = {}
    for i in live():
        s = SPECS[i]
        im = read_raw(s["raw"])
        im.save(src_path(i), quality=95, subsampling=0)
        frm = ("retail pak " + "/".join(s["raw"])) if isinstance(s["raw"], tuple) else s["raw"]
        prov[i] = {"bsp": s["bsp"], "from": frm, "how": s["how"], "size": im.size}
    json.dump(prov, open(os.path.join(SRC, "SOURCES.json"), "w"), indent=1)
    print("copied", len(prov))


def spec(i):
    s = dict(SPECS[i])
    s.update(src=src_path(i), title=titles()[s["bsp"]]["title"])
    return s


def do_crops():
    import tile_treat as T
    cells = []
    colors = {"card_c": (255, 0, 0), "card_s": (255, 160, 0), "print_c": (0, 200, 255), "print_s": (0, 255, 120)}
    for i in live():
        s = spec(i)
        im = Image.open(s["src"]).convert("RGB")
        d = ImageDraw.Draw(im)
        lw = max(2, im.width // 300)
        boxes = {"card_c": s["crop"],
                 "card_s": s.get("crop_s") or T.widest(s, min(1365 - 68, T.PHOTO_H * s.get("max_aspect", 99)) / T.PHOTO_H),
                 "print_c": s.get("pcrop_c") or T.widest(s, min(T.PRINT_ASPECT["c"], s.get("max_aspect", 99))),
                 "print_s": s.get("pcrop_s") or T.widest(s, min(T.PRINT_ASPECT["s"], s.get("max_aspect", 99)))}
        for k, b in boxes.items():
            d.rectangle(b, outline=colors[k], width=lw)
        im.thumbnail((960, 540))
        cells.append((i, im))
    S = Image.new("RGB", (1920, 560 * ((len(cells) + 1) // 2)), (20, 20, 20))
    dd = ImageDraw.Draw(S)
    for k, (i, im) in enumerate(cells):
        x, y = (k % 2) * 960, (k // 2) * 560
        S.paste(im, (x, y + 20))
        dd.text((x + 4, y + 4), i + "   red card_c  orange card_s  blue print_c  green print_s", fill=(255, 255, 0))
    S.save(os.path.join(PROP, "samples", "qa", "crops.jpg"), quality=88)
    print("crops sheet written")


def do_cards():
    import tile_treat as T
    for i in live():
        s = spec(i)
        for lay in ("c", "s"):
            c = T.card(s, lay)
            c.save(os.path.join(PROP, "samples", "full", "%s_card_%s_1024.jpg" % (i, lay)), quality=95, subsampling=0)
            T.game_texture(c, lay).save(os.path.join(PROP, "samples", "game", "%s_%s.jpg" % (i, lay)), quality=92, subsampling=0)
            T.print_photo(s, lay).save(os.path.join(PROP, "samples", "full", "%s_print_%s_1024x768.jpg" % (i, lay)),
                                       quality=95, subsampling=0)
        print("card", i, "-", s["title"])


if __name__ == "__main__":
    {"sources": do_sources, "crops": do_crops, "cards": do_cards}[sys.argv[1]]()
