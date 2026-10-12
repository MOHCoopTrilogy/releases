#!/usr/bin/env python3
"""gen_vram_panel.py - the VIDEO MEMORY readout on the Options > Video panel (ui/video options.urc).

User, 2026-10-12: "Video panel only. put it somewhere creatively". The panel is the retail instrument board, so the
readout is an instrument on that board, not a strip bolted to it. Two looks are generated so the user can choose:

  A  "gauge"   the big dead dial in the middle of the board (the retail monitor-calibration tube) becomes a meter:
               24 lamps on a 270 degree arc light up for this game / after Apply / other programs, a red marker sits
               at the Windows limit, and three short lines read out inside the tube
  B  "tag"     the decorative DANGER plate becomes a stencilled supply tag: a belt of 20 rounds fills the same way,
               with the same three lines under it

    python gen_vram_panel.py stage A|B <dir>   write <dir>/ui/video options.urc + <dir>/textures/hud/vram/* (test overlay)
    python gen_vram_panel.py apply A|B         write the block into the mod tree's menu + the art (the chosen look)
    python gen_vram_panel.py remove            take the block out of the mod tree's menu again
    python gen_vram_panel.py check             the tree's block matches what this generator would write (or none is there)

How it works. The gl2 renderer (renderergl2/tr_hzm_vram.c) publishes read-only cvars; the block is only Labels:
  r_vramShow                 1 while the feature is on and the game's own number is known -> the whole block shows;
                             0 (dormant, an older engine) -> nothing of it is drawn and the board is the retail one
  r_vramBarGame/Pending/All  0-100 of the bar's scale; a lamp of threshold T is a Label gated `cvar>=T`
  r_vramBarBudget            where the Windows limit sits (0 = not known: no marker)
  r_vramHot                  1 near the limit: the game's lamps turn rust
  r_vramShortGame/Other/Limit  the three lines, ready to print ("GAME 1.3 GB", "OTHER 3.9 GB", "LIMIT 14.9 GB";
                             what is not known is said or left empty by the renderer, never guessed here)
Every lamp is its own small texture, drawn where it sits: nothing is scaled along the bar, so it is as sharp at
640x480 as at 4K. textures/hud/vram/mark is the renderer's "the block is on screen" texture (it polls only while that
was drawn) - one transparent Label of the block uses it, and nothing else may.

ui/video options.urc is hand-maintained; this tool owns only the lines between its BEGIN / END markers, placed just
before the menu's `end.`. All art is drawn here (PIL), flat shapes only - no text is baked into a texture.
"""
import io
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
URC = os.path.join(MOD, "ui", "video options.urc")
TEX = "textures/hud/vram/"
BEGIN = "// >>> BEGIN gen_vram_panel.py - generated, do not hand-edit (python docs/tools/gen_vram_panel.py apply A|B)"
END = "// <<< END gen_vram_panel.py"
SHOW = "r_vramShow"

AMBER = (250, 184, 51)
PALE = (255, 232, 170)
STEEL = (150, 156, 150)
RUST = (226, 74, 30)
RED = (235, 40, 28)
UNLIT_A = (52, 50, 46)


def tga(im):
    """PIL RGBA image -> uncompressed 32-bit TGA, bottom-up (the engine's loaders ignore the top-down bit)"""
    im = im.convert("RGBA")
    w, h = im.size
    out = bytearray([0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, w & 255, w >> 8, h & 255, h >> 8, 32, 8])
    px = im.load()
    for y in range(h - 1, -1, -1):
        for x in range(w):
            r, g, b, a = px[x, y]
            out += bytes((b, g, r, a))
    return bytes(out)


def _pil():
    from PIL import Image, ImageDraw, ImageFilter   # noqa: F401 (tool-time only)
    return Image, ImageDraw, ImageFilter


# ------------------------------------------------------------------------------------------------ look A: gauge
A_C = (316.0, 149.5)       # centre of the dial on the 640x480 board (measured on an engine still)
A_N = 24
A_R = 47.5                 # lamp centre radius
A_CELL = 11                # lamp Label edge, virtual units
A_A0, A_SPAN = 155.0, 230.0   # first lamp lower left, clockwise over the top; the gap at the bottom holds the limit line


def a_angle(i):
    return A_A0 + (i + 0.5) * A_SPAN / A_N   # degrees, screen convention (0 = right, 90 = DOWN)


def a_lamp(color, i, glow):
    """one lamp, already turned to its place on the arc: a rounded bar, long side along the arc"""
    Image, ImageDraw, ImageFilter = _pil()
    S = 4
    im = Image.new("RGBA", (64 * S, 64 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    w, h = 22 * S, 40 * S   # radial thickness x tangential length before rotation (bar lies along +y)
    x0, y0 = (64 * S - w) // 2, (64 * S - h) // 2
    d.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=7 * S, fill=color + (255,))
    if glow:   # a lit lamp: a lighter core, so it reads as a light and not as a painted cell
        core = tuple(min(255, int(c + (255 - c) * 0.45)) for c in color)
        d.rounded_rectangle((x0 + 5 * S, y0 + 6 * S, x0 + w - 5 * S, y0 + h - 6 * S), radius=4 * S, fill=core + (255,))
    im = im.rotate(-a_angle(i), resample=Image.BICUBIC)   # PIL turns counter-clockwise; screen angles run clockwise
    return im.resize((64, 64), Image.LANCZOS)


def a_tick(i):
    """the limit marker: a red bar across the lamp ring, turned to lamp i's place"""
    Image, ImageDraw, _ = _pil()
    S = 4
    im = Image.new("RGBA", (64 * S, 64 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((6 * S, 28 * S, 58 * S, 36 * S), fill=RED + (255,))
    im = im.rotate(-a_angle(i), resample=Image.BICUBIC)
    return im.resize((64, 64), Image.LANCZOS)


def a_face():
    """the tube's face: a soft dark disc so the readout sits on an even black whatever the retail art does there"""
    Image, ImageDraw, ImageFilter = _pil()
    S = 2
    im = Image.new("RGBA", (256 * S, 256 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((6 * S, 6 * S, 250 * S, 250 * S), fill=(10, 10, 11, 255))
    im = im.filter(ImageFilter.GaussianBlur(2 * S))
    return im.resize((256, 256), Image.LANCZOS)


def art_a():
    out = {"mark.tga": tga(_pil()[0].new("RGBA", (4, 4), (0, 0, 0, 0))), "a_face.tga": tga(a_face())}
    for i in range(A_N):
        out["a_off_%02d.tga" % i] = tga(a_lamp(UNLIT_A, i, False))
        out["a_game_%02d.tga" % i] = tga(a_lamp(AMBER, i, True))
        out["a_hot_%02d.tga" % i] = tga(a_lamp(RUST, i, True))
        out["a_pend_%02d.tga" % i] = tga(a_lamp(PALE, i, True))
        out["a_other_%02d.tga" % i] = tga(a_lamp(STEEL, i, False))
        out["a_tick_%02d.tga" % i] = tga(a_tick(i))
    return out


# ------------------------------------------------------------------------------------------------ look B: tag
B_RECT = (418, 248, 96, 80)    # over the retail DANGER plate (420..511 x 250..325 on the 640x480 board)
B_N = 20
B_X0, B_Y, B_W, B_H = 426, 268, 80, 14    # the belt: 20 rounds on a 4-unit pitch (whole pixels at 640x480)


def b_plate():
    """an olive supply tag: flat paint, a darker edge, four rivets, light wear. No text."""
    Image, ImageDraw, ImageFilter = _pil()
    import random
    rnd = random.Random(1944)
    W, H = 384, 320
    im = Image.new("RGBA", (W, H), (74, 82, 58, 255))
    d = ImageDraw.Draw(im)
    for _ in range(2600):   # paint wear: tiny lighter / darker flecks
        x, y = rnd.randrange(W), rnd.randrange(H)
        k = rnd.choice((-14, -9, 8, 12))
        c = im.getpixel((x, y))
        d.point((x, y), fill=(max(0, min(255, c[0] + k)), max(0, min(255, c[1] + k)), max(0, min(255, c[2] + k)), 255))
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W - 1, H - 1), outline=(36, 40, 28, 255), width=6)
    d.rectangle((6, 6, W - 7, H - 7), outline=(104, 112, 84, 255), width=2)
    for cx, cy in ((22, 22), (W - 22, 22), (22, H - 22), (W - 22, H - 22)):
        d.ellipse((cx - 9, cy - 9, cx + 9, cy + 9), fill=(46, 50, 36, 255))
        d.ellipse((cx - 7, cy - 8, cx + 5, cy + 4), fill=(126, 132, 104, 255))
        d.ellipse((cx - 4, cy - 5, cx + 4, cy + 3), fill=(92, 98, 74, 255))
    # the belt's bed: a recessed dark strip where the rounds sit
    k = W / float(B_RECT[2])
    bx0, by0 = (B_X0 - B_RECT[0]) * k - 6, (B_Y - B_RECT[1]) * k - 5
    bx1, by1 = (B_X0 + B_W - B_RECT[0]) * k + 6, (B_Y + B_H - B_RECT[1]) * k + 5
    d.rounded_rectangle((bx0, by0, bx1, by1), radius=6, fill=(24, 26, 20, 255), outline=(40, 44, 32, 255), width=2)
    return im


def b_round(color, lit):
    """one round of the belt, standing: case, shoulder, bullet. `lit` rounds get a highlight down the case."""
    Image, ImageDraw, _ = _pil()
    S = 8
    W, H = 16 * S, 64 * S
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    dark = tuple(int(c * 0.55) for c in color)
    d.rounded_rectangle((2 * S, 24 * S, 14 * S, 62 * S), radius=2 * S, fill=color + (255,))            # case
    d.rectangle((2 * S, 57 * S, 14 * S, 62 * S), fill=dark + (255,))                                    # rim
    d.polygon(((2 * S, 26 * S), (14 * S, 26 * S), (11 * S, 16 * S), (5 * S, 16 * S)), fill=color + (255,))   # shoulder
    d.polygon(((5 * S, 17 * S), (11 * S, 17 * S), (8 * S, 2 * S)), fill=dark + (255,) if lit else color + (255,))   # bullet
    if lit:
        hi = tuple(min(255, int(c + (255 - c) * 0.5)) for c in color)
        d.rectangle((4 * S, 27 * S, 6 * S, 55 * S), fill=hi + (255,))
    return im.resize((16, 64), _pil()[0].LANCZOS)


def b_tick():
    Image, ImageDraw, _ = _pil()
    S = 8
    im = Image.new("RGBA", (16 * S, 16 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon(((1 * S, 1 * S), (15 * S, 1 * S), (8 * S, 15 * S)), fill=RED + (255,))
    return im.resize((16, 16), _pil()[0].LANCZOS)


def art_b():
    return {"mark.tga": tga(_pil()[0].new("RGBA", (4, 4), (0, 0, 0, 0))), "b_plate.tga": tga(b_plate()),
            "b_off.tga": tga(b_round((58, 56, 46), False)), "b_game.tga": tga(b_round((214, 160, 60), True)),
            "b_hot.tga": tga(b_round(RUST, True)), "b_pend.tga": tga(b_round(PALE, True)),
            "b_other.tga": tga(b_round(STEEL, False)), "b_tick.tga": tga(b_tick())}


# ------------------------------------------------------------------------------------------------ the block
def lab(name, rect, gate, shader=None, text=None, cvar=None, font="verdana-12", fg=(1, 1, 1, 1), align="center"):
    L = ["resource", "Label", "{", 'name "%s"' % name]
    if text is not None or cvar is not None:
        L.append("dontlocalize")
    if text is not None:
        L.append('title "%s"' % text)
    L += ["rect %d %d %d %d" % tuple(rect), "fgcolor %.2f %.2f %.2f %.2f" % tuple(fg), "bgcolor 0.00 0.00 0.00 0.00",
          'borderstyle "NONE"']
    if shader:
        L.append('shader "%s"' % (TEX + shader))
    if text is not None or cvar is not None:
        L += ['font "%s"' % font, "textalign " + align]
    if cvar:
        L.append('linkcvar "%s"' % cvar)
    L += ['enabledcvar "%s"' % gate, "}"]
    return L


def thresholds(n):
    """lamp i is lit when the bar value (0-100) reaches the middle of its slice; never below 1, so a small game
    share still lights the first lamp"""
    return [max(1, int(round((i + 0.5) * 100.0 / n))) for i in range(n)]


def lamps(prefix, n, rect_of, tex_of):
    """the gated Labels of one bar: unlit, other programs, after Apply, this game (amber / rust), limit marker"""
    L = []
    T = thresholds(n)
    for i in range(n):
        t = T[i]
        lo = 0 if i == 0 else int(round(i * 100.0 / n))
        hi = int(round((i + 1) * 100.0 / n))
        r = rect_of(i)
        L += lab("%sOff%02d" % (prefix, i), r, SHOW, tex_of("off", i))
        L += lab("%sOther%02d" % (prefix, i), r, "%s r_vramBarAll>=%d r_vramBarPending<%d r_vramBarGame<%d" % (SHOW, t, t, t), tex_of("other", i))
        L += lab("%sPend%02d" % (prefix, i), r, "%s r_vramBarPending>=%d r_vramBarGame<%d" % (SHOW, t, t), tex_of("pend", i))
        L += lab("%sGame%02d" % (prefix, i), r, "%s r_vramBarGame>=%d r_vramHot==0" % (SHOW, t), tex_of("game", i))
        L += lab("%sHot%02d" % (prefix, i), r, "%s r_vramBarGame>=%d r_vramHot==1" % (SHOW, t), tex_of("hot", i))
    for i in range(n):
        lo = int(round(i * 100.0 / n))
        hi = int(round((i + 1) * 100.0 / n))
        L += lab("%sTick%02d" % (prefix, i), rect_of(i, tick=True),
                 "%s r_vramBarBudget>%d r_vramBarBudget<=%d" % (SHOW, lo, hi), tex_of("tick", i))
    return L


def block_a():
    cx, cy = A_C

    def rect_of(i, tick=False):
        a = math.radians(a_angle(i))
        x, y = cx + A_R * math.cos(a), cy + A_R * math.sin(a)
        return (int(round(x - A_CELL / 2.0)), int(round(y - A_CELL / 2.0)), A_CELL, A_CELL)

    L = lab("vramMark", (0, 0, 1, 1), SHOW, "mark")
    L += lab("vramFace", (int(cx - 52), int(cy - 52), 104, 104), SHOW, "a_face")
    L += lamps("vramA", A_N, rect_of, lambda kind, i: "a_%s_%02d" % (kind, i))
    grey, amber, white = (0.66, 0.66, 0.62, 1), (1.0, 0.78, 0.28, 1), (0.93, 0.92, 0.86, 1)
    # line widths are the chords of the tube at that height, inside the lamp ring (LONGEST is checked against them)
    cool, hot, rust = SHOW + " r_vramHot==0", SHOW + " r_vramHot==1", (1.0, 0.42, 0.24, 1)
    L += lab("vramT1", (296, 116, 40, 12), cool, text="VIDEO", fg=grey)
    L += lab("vramT2", (291, 128, 50, 12), cool, text="MEMORY", fg=grey)
    L += lab("vramT1hot", (296, 116, 40, 12), hot, text="NEAR", fg=rust)
    L += lab("vramT2hot", (283, 128, 66, 12), hot, text="THE LIMIT", fg=rust)
    L += lab("vramGame", (276, 140, 80, 12), SHOW, cvar="r_vramShortGame", fg=amber)
    L += lab("vramOther", (277, 152, 78, 12), SHOW, cvar="r_vramShortOther", fg=white)
    L += lab("vramLimit", (280, 169, 72, 12), SHOW, cvar="r_vramShortLimit", fg=(1.0, 0.45, 0.36, 1))
    return L


def block_b():
    x, y, w, h = B_RECT
    step = B_W / float(B_N)

    def rect_of(i, tick=False):
        if tick:
            return (int(round(B_X0 + (i + 1) * step - 3)), B_Y - 5, 5, 4)
        return (int(round(B_X0 + i * step)), B_Y, 3, B_H)

    L = lab("vramMark", (0, 0, 1, 1), SHOW, "mark")
    L += lab("vramPlate", (x, y, w, h), SHOW, "b_plate")
    stencil, ink = (0.88, 0.86, 0.70, 1), (0.95, 0.93, 0.80, 1)
    L += lab("vramTitle", (x + 2, y + 3, w - 4, 12), SHOW + " r_vramHot==0", text="VIDEO MEMORY", fg=stencil)
    L += lab("vramTitleHot", (x + 2, y + 3, w - 4, 12), SHOW + " r_vramHot==1", text="NEAR THE LIMIT", fg=(1.0, 0.5, 0.3, 1))
    L += lamps("vramB", B_N, rect_of, lambda kind, i: "b_" + kind)
    L += lab("vramGame", (x + 6, y + 37, w - 10, 12), SHOW, cvar="r_vramShortGame", fg=(1.0, 0.82, 0.36, 1), align="left")
    L += lab("vramOther", (x + 6, y + 49, w - 10, 12), SHOW, cvar="r_vramShortOther", fg=ink, align="left")
    L += lab("vramLimit", (x + 6, y + 61, w - 10, 12), SHOW, cvar="r_vramShortLimit", fg=(1.0, 0.55, 0.42, 1), align="left")
    return L


LOOKS = {"A": (block_a, art_a), "B": (block_b, art_b)}
# the longest strings the renderer publishes into each line (tr_hzm_vram.c R_HzmVramPublish) and the width they get
# (one decimal below 10 GB, none from 10 GB up)
LONGEST = {"r_vramShortGame": "APPLY 9.9 GB", "r_vramShortOther": "OTHER 9.9 GB", "r_vramShortLimit": "LIMIT 9.9 GB"}


def strip(text):
    a, b = text.find(BEGIN), text.find(END)
    if a < 0 and b < 0:
        return text
    assert 0 <= a < b, "gen_vram_panel markers are damaged"
    e = text.index("\n", b) + 1
    return text[:a] + text[e:]


def splice(text, look):
    """the menu text with this look's block just before `end.` (text uses \\n; the caller keeps the file's own EOL)"""
    text = strip(text)
    k = text.rstrip().rfind("end.")
    assert k > 0 and text.rstrip().endswith("end."), "ui/video options.urc does not end in `end.`"
    blk = [BEGIN,
           "// VIDEO MEMORY readout, look %s. Drawn only while r_vramShow is 1 (gl2 renderer, tr_hzm_vram.c); with it 0 the" % look,
           "// board is the retail one. Lamp Labels are gated on 0-100 cvars; see docs/tools/gen_vram_panel.py."]
    blk += LOOKS[look][0]() + [END]
    return text[:k] + "\n".join(blk) + "\n" + text[k:]


def read_urc(path):
    b = io.open(path, "rb").read()
    crlf = b.count(b"\r\n") * 2 > b.count(b"\n")
    return b.decode("latin-1").replace("\r\n", "\n"), crlf


def write_urc(path, text, crlf):
    assert all(ord(c) < 128 for c in text[text.find(BEGIN):]) if BEGIN in text else True
    data = (text.replace("\n", "\r\n") if crlf else text).encode("latin-1")
    d = os.path.dirname(path)
    if not os.path.isdir(d):
        os.makedirs(d)
    io.open(path, "wb").write(data)


def gate(look, problems):
    """every Label inside the 640x480 canvas, names unique, and the longest published strings fit their Labels"""
    sys.path.insert(0, HERE)
    import gen_menu_fieldsettings as fs
    f = fs.Font("verdana-12")
    L = LOOKS[look][0]()
    names, cur = [], {}
    for ln in L + ["}"]:
        if ln == "{":
            cur = {}
        elif ln.startswith("name "):
            cur["name"] = ln.split('"')[1]
        elif ln.startswith("rect "):
            cur["rect"] = [int(v) for v in ln.split()[1:]]
        elif ln.startswith("title "):
            cur["title"] = ln.split('"')[1]
        elif ln.startswith("linkcvar "):
            cur["cvar"] = ln.split('"')[1]
        elif ln == "}" and cur:
            names.append(cur["name"])
            x, y, w, h = cur["rect"]
            if x < 0 or y < 0 or x + w > 640 or y + h > 480:
                problems.append("look %s: %s outside the canvas %s" % (look, cur["name"], cur["rect"]))
            s = cur.get("title") or LONGEST.get(cur.get("cvar", ""))
            if s and f.width(s) > w:
                problems.append("look %s: text too wide: %s %.0f > %d (%r)" % (look, cur["name"], f.width(s), w, s))
            if s and f.height > h + 0.5:
                problems.append("look %s: text too tall: %s" % (look, cur["name"]))
            cur = {}
    dup = sorted(set(n for n in names if names.count(n) > 1))
    if dup:
        problems.append("look %s: duplicate widget names %s" % (look, dup))
    return len(names)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode in ("stage", "apply"):
        look = sys.argv[2]
        problems = []
        n = gate(look, problems)
        if problems:
            print("\n".join(problems))
            return 1
        base = sys.argv[3] if mode == "stage" else MOD
        text, crlf = read_urc(URC)
        write_urc(os.path.join(base, "ui", "video options.urc"), splice(text, look), crlf)
        art = LOOKS[look][1]()
        d = os.path.join(base, TEX.replace("/", os.sep))
        if not os.path.isdir(d):
            os.makedirs(d)
        for name, data in sorted(art.items()):
            io.open(os.path.join(d, name), "wb").write(data)
        print("look %s: %d Labels, %d textures (%d bytes) -> %s" % (look, n, len(art), sum(len(v) for v in art.values()), base))
        return 0
    if mode == "remove":
        text, crlf = read_urc(URC)
        write_urc(URC, strip(text), crlf)
        print("block removed from", URC)
        return 0
    if mode == "check":
        text, _ = read_urc(URC)
        if BEGIN not in text:
            print("OK: no VIDEO MEMORY block in ui/video options.urc (no look applied)")
            return 0
        for look in sorted(LOOKS):
            if splice(text, look) == text:
                problems = []
                gate(look, problems)
                art = LOOKS[look][1]()
                for name, data in art.items():
                    p = os.path.join(MOD, TEX.replace("/", os.sep), name)
                    if not os.path.exists(p) or io.open(p, "rb").read() != data:
                        problems.append("DRIFT: %s%s missing or stale - run apply %s" % (TEX, name, look))
                print("\n".join(problems) if problems else "OK: look %s is applied and current" % look)
                return 1 if problems else 0
        print("DRIFT: the block in ui/video options.urc matches neither look - run apply A|B")
        return 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
