"""v1.10.68 bring-your-own-disc: the co-op map select lists converted Frontline / European Assault missions ONLY when
their local pak is present (coop_flHave_1_1 / coop_eaHave_1_11, raised by the marker cfg inside the pak; autoexec.cfg).

  python patch_coopstart.py <mod dir>        (idempotent: replaces its own block)

Why a patch and not make_mpui.py: on 2026-11-09 docs/proposals/mpui_2026-11-02/make_mpui.py no longer reproduces the
shipped ui/coop_start.urc (147 lines drift: later attic / chrono edits landed in the mod only), so re-running it would
revert other work (it also rewrites H:/hzm_work/mpui/ship). This adds one self-contained block after
`include "ui/coop_maps.inc"`; whoever brings make_mpui.py back in sync must carry this block (or call this patch).

What it adds, all declared after the generic tiles (later = drawn on top and hit first):
  * a YOUR OWN DISCS selector in the MISSION header row (right side; the column header text is left-aligned), shown only
    when a mission is present. It sets ui_coopCamp 14 and execs ui/coop_start/byo.cfg, which blanks the 11 generic
    tiles (no art, no command - so nothing invisible is clickable) and names the board;
  * one dedicated tile per known mission (own plate + two text lines + its own Button), gated
    `ui_coopCamp==14 coop_<game>Have_<level>`. Without the pak every one of these widgets is disabled: the screen is
    exactly the v1.10.67 screen.
"""
import re
import sys

BEGIN = "// [byo68] begin: YOUR OWN DISCS (bring-your-own-disc missions, shown only when converted on this PC)"
END = "// [byo68] end"
PLATE = "0.14 0.10 0.06 0.94"
BEIGE = "0.90 0.84 0.66 1.00"
RUST = "0.42 0.22 0.06 1.00"
AMBER = "0.98 0.78 0.28 1.00"
CLEAR = "0.00 0.00 0.00 0.00"
GLOW = "textures/mohmenu/hzm_theme/mpui_glow"
TILE_H = "textures/mohmenu/hzm_theme/mpui_tileframe"

# (key, map, gate cvar, line 1, line 2, line 3, board title)
MISSIONS = [
    ("Fl11", "coop_fl_1_1", "coop_flHave_1_1", "SEALED", "ORDERS", "St. Mathieu 1944", "Your own discs - Frontline"),
    ("Ea111", "coop_ea_1_11", "coop_eaHave_1_11", "THEIR DYING", "BREATH", "Stalingrad 1943", "Your own discs - European Assault"),
]
TX, TY, TS, TG = 186, 92, 82, 6


def w(kind, name, rect, **kv):
    out = ["resource", kind, "{"]
    if "title" in kv:
        out.append('title "%s"' % kv.pop("title"))
    out += ['name "%s"' % name, "rect %d %d %d %d" % rect]
    out.append("fgcolor %s" % kv.pop("fg", "1.00 1.00 1.00 1.00"))
    out.append("bgcolor %s" % kv.pop("bg", CLEAR))
    out.append('borderstyle "%s"' % kv.pop("border", "NONE"))
    for k in ("hovershader", "font", "textalign", "clicksound", "stuffcommand", "enabledcvar"):
        if k in kv:
            v = kv.pop(k)
            out.append(("%s %s" if k in ("font", "textalign") else '%s "%s"') % (k, v))
    assert not kv, kv
    return out + ["}"]


def block():
    L = [BEGIN]
    # selector: one per mission, the first present one wins (enabledcvar is AND-only, so later ones exclude earlier)
    sel = (344, 66, 110, 18)
    excl = ""
    for key, m, gate, *_rest, board in MISSIONS:
        g = (gate + " " + excl).strip()
        L += w("Label", "byoSelPlate" + key, sel, bg=PLATE, border="3D_BORDER", enabledcvar=g)
        L += w("Label", "byoSelLit" + key, (sel[0] + 4, sel[1] + sel[3] - 3, sel[2] - 8, 2), bg=AMBER,
               enabledcvar=g + " ui_coopCamp==14")
        L += w("Button", "byoSel" + key, sel, title="YOUR OWN DISCS", fg=BEIGE, hovershader=GLOW, font="verdana-12",
               textalign="center", clicksound="sound/menu/apply.wav",
               stuffcommand="set ui_coopCamp 14;exec ui/coop_start/byo.cfg;set ui_dmmap %s;seta coop_mapcmd map %s" % (m, m),
               enabledcvar=g)
        excl = (excl + " !" + gate).strip()
    # one tile per mission, in its own slot (tile i of the 3 x 4 grid)
    for i, (key, m, gate, l1, l2, l3, board) in enumerate(MISSIONS):
        r, c = divmod(i, 3)
        x, y = TX + c * (TS + TG), TY + r * (TS + TG)
        g = "ui_coopCamp==14 " + gate
        L += w("Label", "byoTile" + key, (x, y, TS, TS), bg=PLATE, border="3D_BORDER", enabledcvar=g)
        L += w("Label", "byoTileA" + key, (x + 2, y + 14, TS - 4, 18), title=l1, fg=BEIGE, font="facfont-20",
               textalign="center", enabledcvar=g)
        L += w("Label", "byoTileB" + key, (x + 2, y + 32, TS - 4, 18), title=l2, fg=BEIGE, font="facfont-20",
               textalign="center", enabledcvar=g)
        L += w("Label", "byoTileC" + key, (x + 2, y + 58, TS - 4, 14), title=l3, fg=AMBER, font="verdana-12",
               textalign="center", enabledcvar=g)
        L += w("Button", "byoTileBtn" + key, (x, y, TS, TS), hovershader=TILE_H, font="facfont-20", textalign="center",
               clicksound="sound/menu/apply.wav",
               stuffcommand="set ui_dmmap %s;seta coop_mapcmd map %s" % (m, m), enabledcvar=g)
    L.append(END)
    return L


def main(mod):
    p = mod + "/ui/coop_start.urc"
    s = open(p, "rb").read().decode("latin-1")
    nl = "\r\n" if "\r\n" in s else "\n"
    s = s.replace("\r\n", "\n")
    s = re.sub(r"(?s)\n" + re.escape(BEGIN) + r".*?" + re.escape(END), "", s)
    anchor = 'include "ui/coop_maps.inc"'
    assert s.count(anchor) == 1
    s = s.replace(anchor, anchor + "\n" + "\n".join(block()))
    open(p, "wb").write(s.replace("\n", nl).encode("latin-1"))
    print("patched", p)


if __name__ == "__main__":
    main(sys.argv[1])
