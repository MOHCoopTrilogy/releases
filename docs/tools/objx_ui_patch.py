#!/usr/bin/env python
"""objx_ui_patch.py - one-shot, idempotent patch: side-objective HUD lines 3..5 (objectives-next, 2026-10-18).

Edits two CLIENT files in the mod checkout (binary mode, CRLF kept, every replace asserted):
  ui/coop_objectives/obj_setup.cfg   seeds coop_so3..so5 (+d/s/a) next to coop_so1/so2
  ui/coop_objectives.urc             a header "Additional Objectives:" (y=426) and three rows (y=446/466/486, same widgets as rows 1-2),
                                     the pinned-challenge block moved down 80 px, the canvas 512 -> 592

    python docs/tools/objx_ui_patch.py <mod checkout>        (default hzm-mohaa-coop-mod)
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "hzm-mohaa-coop-mod")
SHIFT = 80


def rd(p):
    with open(p, "rb") as f:
        return f.read()


def wr(p, b):
    with open(p, "wb") as f:
        f.write(b)


def patch_cfg():
    p = os.path.join(MOD, "ui", "coop_objectives", "obj_setup.cfg")
    d = rd(p)
    if b"coop_so3d" in d:
        print("cfg: already patched")
        return
    anchor = b'seta coop_so2a "0";\r\n'
    assert d.count(anchor) == 1
    add = b""
    for n in (3, 4, 5):
        add += ('seta coop_so%d "";\r\nseta coop_so%dd "0";\r\nseta coop_so%ds "0";\r\nseta coop_so%da "0";\r\n' % (n, n, n, n)).encode()
    wr(p, d.replace(anchor, anchor + add))
    print("cfg: patched")


def row(n, y):
    t = (
        "//--- Secondary line %(n)d (objx) ---\r\n"
        "resource\r\nWidget\r\n{\r\nname \"coop_MiObjSec%(n)dBg\"\r\nrect 10 %(y)d 550 20\r\nbgcolor 0.2 0.2 0.2 0.8\r\nborderstyle \"NONE\"\r\nenabledcvar \"coop_so%(n)dd\"\r\n}\r\n"
        "resource\r\nCheckBox\r\n{\r\nname \"coop_MiObjSec%(n)dCheck\"\r\nrect 10 %(y)d 24 16\r\nfgcolor 1.00 1.00 1.00 1.00\r\nbgcolor 0 0 0 0\r\nborderstyle \"RAISED\"\r\nlinkcvar \"coop_so%(n)ds\"\r\n"
        "checked_shader \"textures/OBJECTIVES/filledbox.tga\"\r\nunchecked_shader \"textures/OBJECTIVES/emptybox.tga\"\r\nenabledcvar \"coop_so%(n)dd\"\r\n}\r\n"
        "resource\r\nLabel\r\n{\r\ntitle \"Objective\"\r\nname \"coop_MiObjSec%(n)dcomplete\"\r\nrect 36 %(y)d 640 16\r\nfgcolor 1 1 1 0.5\r\nbgcolor 0 0 0 0\r\nborderstyle \"NONE\"\r\nfont courier-16\r\ntextalign left\r\nenabledcvar \"coop_so%(n)dd\"\r\nlinkcvar \"coop_so%(n)d\"\r\n}\r\n"
        "resource\r\nLabel\r\n{\r\ntitle \"Objective\"\r\nname \"coop_MiObjSec%(n)dactive\"\r\nrect 36 %(y)d 640 16\r\nfgcolor 1 1 1 1\r\nbgcolor 0 0 0 0\r\nborderstyle \"NONE\"\r\nfont courier-16\r\ntextalign left\r\nenabledcvar \"coop_so%(n)da\"\r\nlinkcvar \"coop_so%(n)d\"\r\n}\r\n"
    ) % {"n": n, "y": y}
    return t.encode()


HDR = (b"resource\r\nLabel\r\n{\r\ntitle \"Additional Objectives:\"\r\nname \"coop_MiObjAddHdr\"\r\nrect 10 426 640 16\r\nfgcolor 0.8 0.9 1.0 1\r\n"
       b"bgcolor 0 0 0 0\r\nborderstyle \"NONE\"\r\nfont courier-16\r\ntextalign left\r\nenabledcvar \"coop_so3d\"\r\n}\r\n")


def patch_urc():
    p = os.path.join(MOD, "ui", "coop_objectives.urc")
    d = rd(p)
    if b"coop_MiObjSec3Bg" in d:
        print("urc: already patched")
        return
    assert d.count(b"\r\n") == d.count(b"\n")
    assert d.count(b"menu \"coop_objectives\" 640 512 ") == 1
    d = d.replace(b"menu \"coop_objectives\" 640 512 ", b"menu \"coop_objectives\" 640 %d " % (512 + SHIFT))
    # the pinned block: everything from its banner to the end
    marker = b"/////////////////////////////////////////////////////////////\r\n//PINNED CHALLENGES"
    assert d.count(marker) == 1
    i = d.find(marker)
    head, tail = d[:i], d[i:]
    n_rect = len(re.findall(rb"rect (\d+) (\d+) (\d+) (\d+)", tail))
    assert n_rect == 16, n_rect
    tail = re.sub(rb"rect (\d+) (\d+) (\d+) (\d+)", lambda m: b"rect %s %d %s %s" % (m.group(1), int(m.group(2)) + SHIFT, m.group(3), m.group(4)), tail)
    hdr = HDR
    new = hdr + row(3, 446) + row(4, 466) + row(5, 486)
    wr(p, head + new + tail)
    print("urc: patched (header + %d rows, pinned block +%d px)" % (3, SHIFT))


patch_cfg()
patch_urc()
