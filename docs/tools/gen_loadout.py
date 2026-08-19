#!/usr/bin/env python
"""Generate the armory picker's per-weapon pages under hzm-mohaa-coop-mod/ui/loadout/.

WHY THIS EXISTS
The original generator (gen_loadout3.py) was lost - it is one of the entries under "Tooling lost"
in docs/OPEN.md - which left 349 hand-unmaintainable files and made adding a weapon to the armory
impossible. Every gun imported since (C96, Johnson M1941, DP-28, Panzerfaust, S&W M10) is missing
from the picker for that reason alone.

This is a reconstruction, and it is only trustworthy because of `check`: it regenerates every file
in memory and byte-compares against what is on disk. Reproducing all 69 existing weapons exactly
is the evidence that the format is understood well enough to extend it.

    python docs/tools/gen_loadout.py extract   # re-derive the table from the live files
    python docs/tools/gen_loadout.py check     # regenerate in memory + byte-compare (exit 1 = drift)
    python docs/tools/gen_loadout.py build     # write the files

THE DATA
docs/tools/loadout_weapons.tsv is the source of truth. Adding a weapon to the armory is one row.
Columns are described in its header. The preview transform (xfm) is hand-dialled per gun the same
way the ADS table is - `extract` preserves whatever is there, and a new row starts from a sane
default that the user then tunes in-game.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UI = os.path.join(ROOT, "hzm-mohaa-coop-mod", "ui", "loadout")
TSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loadout_weapons.tsv")

COLS = ["id", "tik", "give", "xfm", "charanim", "cls", "tab", "name", "cd", "b0", "b1", "b2", "b3",
        "clip", "clipn", "recoil", "slots", "req1", "req2"]

# The server-side unlock roster. Absent from it, a weapon draws in the grid and does nothing
# when clicked - no commit command, no padlock, no unlock text.
ROSTER = os.path.join(ROOT, "hzm-mohaa-coop-mod", "coop_mod", "loadoutroster.scr")

# The class token in the wNN_sN "unreg" / "who" lines is INDEPENDENT of the hold pose, which the
# first reconstruction got wrong: weapon 12 uses coop_hold_rifle but belongs to the sniper class,
# so a sniper holds a rifle pose and still gates on unreg_sniper.cfg. It is its own column.


def _read(p):
    return io.open(p, "r", encoding="latin-1", newline="").read()


# ---------------------------------------------------------------- render ---------------------
def preview(w):
    """pNN.cfg - the inspect page. 24 set lines, fixed order."""
    slots = w["slots"]
    cmds = []
    for s in "1234":
        cmds.append('"exec ui/loadout/w%s_s%s.cfg"' % (w["id"], s) if s in slots
                    else '"vstr coop_loDeny"')
    # [user 2026-08-18] finish strip, fid 8: the generic VARIANT button lights up only while a
    # gun with an imported model variant is previewed. Host tile ids are pinned here; the actual
    # variant + its unlock live in loadoutskins.scr, keyed on the give path.
    MV_HOSTS = ("01", "03", "04", "05", "07", "08", "09", "12", "13", "14", "23", "24", "26", "36", "37", "44", "45", "46", "48", "50", "53", "55", "74")
    mv_on = "1" if w["id"] in MV_HOSTS else "0"
    mv_req = ("exec ui/loadout/reqmv%s.cfg" % w["id"]) if w["id"] in MV_HOSTS else "exec ui/loadout/reqclear.cfg"
    # [user 2026-08-18] deep-trace F5(viewer): this used to hard-code the ACTIVE pointer to
    # slot 1 on every variant-host page - a tile inspect on any other slot cross-wired the
    # VARIANT button into slot 1's ring and CORRUPTED slot 1's archived finish. The pointer is
    # owned solely by s<n>sel.cfg (set per slot click); pages only arm the per-slot rings.
    mv_pn = None
    mv_pns = [("exec ui/loadout/mvp%s_1_s%d.cfg" % (w["id"], _sl)) if w["id"] in MV_HOSTS else ""
              for _sl in (1, 2, 3, 4)]

    # [user 2026-08-18] OFFLINE finish previews: variants had a client-side preview chain and
    # finishes did not - so from the main menu a finish click changed nothing visible (the server
    # confirm is what swaps the preview, and there is no server there). Every page arms
    # coop_loFinP1..7 at its gun's finish tiks where they exist; the fin cfgs vstr them locally.
    import os as _os
    _stem = _os.path.splitext(_os.path.basename(w["tik"]))[0]
    _fk = ["gold", "chrome", "blued", "bloody", "camo_woodland", "camo_winter", "camo_desert"]
    finp = []
    for _i, _k in enumerate(_fk):
        _vt = _os.path.join(ROOT, "hzm-mohaa-coop-mod", "models", "weapons", "%s_%s.tik" % (_stem, _k))
        finp.append("exec ui/loadout/finp%s_%d.cfg" % (w["id"], _i + 1) if _os.path.exists(_vt) else "")
    L = [
        'set coop_loMvOn %s' % mv_on,
        'set coop_loMvReqCur "%s"' % mv_req,

    ]
    L += ['set coop_loMvPN_s%d "%s"' % (_sl + 1, _v) for _sl, _v in enumerate(mv_pns)]
    L += [
    ]
    L += ['set coop_loFinP%d "%s"' % (_i + 1, _v) for _i, _v in enumerate(finp)]
    L += [
        'set coop_loPrev "%s"' % w["tik"],
        'set coop_loXfmW "%s"' % w["xfm"],
        'set coop_loPrevId "%s"' % w["id"],
        'set coop_loCharAnim "%s"' % w["charanim"],
    ]
    L += ["set coop_loPvC%d 0" % i for i in range(6)]
    L += [
        "set coop_loPvG39 0",
        'set coop_loNm "%s"' % w["name"],
        'set coop_loCd "%s"' % w["cd"],
        'set coop_loB0 "textures/hud/coop_bf%s"' % w["b0"],
        'set coop_loB1 "textures/hud/coop_bf%s"' % w["b1"],
        'set coop_loB2 "textures/hud/coop_bf%s"' % w["b2"],
        'set coop_loB3 "textures/hud/coop_bf%s"' % w["b3"],
        'set coop_loClip "textures/hud/clip/clip_%s"' % w["clip"],
        'set coop_loClipN "%s"' % w["clipn"],
        'set coop_loRecoil "textures/hud/recoil/rec_%s"' % w["recoil"],
        "set coop_loC1 %s" % cmds[0],
        "set coop_loC2 %s" % cmds[1],
        "set coop_loC3 %s" % cmds[2],
        "set coop_loC4 %s" % cmds[3],
    ]
    return "\n".join(L) + "\n"


def slotfile(w, s):
    """wNN_sN.cfg - assign this weapon into slot N."""
    # Slots 1 and 2 are the class-REGISTERED primary slots and carry the unreg/who gating pair.
    # Slots 3 (sidearm) and 4 (heavy) carry none of it - they are not class-gated, so those four
    # lines are absent entirely rather than present-and-empty.
    cls = w["cls"]
    gated = s in ("1", "2") and cls
    L = []
    if gated:
        L += ["vstr coop_loUnregP%s" % s, "vstr coop_loWho_%s" % cls]
    L += [
        'seta coop_lo%s "%s"' % (s, w["id"]),
        'seta coop_loN%s "%s"' % (s, w["name"]),
        'seta coop_loS%s "%s"' % (s, w["tik"]),
        'seta coop_loA%s "append name ,w%s%s"' % (s, s, w["id"]),
        'set coop_loXfmT%s "%s"' % (s, w["xfm"]),
        "vstr coop_loA%s" % s,
    ]
    # [user 2026-08-18] "if I click sidearm he's still holding primary 1" - every slot commit now
    # registers ITS gun's inspect page, so the slot cards can drive the 3D soldier's held weapon
    # (s<N>sel.cfg replays coop_loInspectS<N>). OpenInspect stays for the server-confirm path.
    L.append('seta coop_loInspectS%s "exec ui/loadout/p%s.cfg"' % (s, w["id"]))
    # [user 2026-08-18] deep-trace F11: a NEW gun in the slot starts STANDARD - clear the
    # archived finish chip + replay recipe with the commit (client half; the server NILs its flag).
    L.append('seta coop_loS%sF "0"' % s)
    L.append('seta coop_loFA%s ""' % s)
    if s == "1":
        L.append('seta coop_loOpenInspect "exec ui/loadout/p%s.cfg"' % w["id"])
    if gated:
        L += [
            'seta coop_loUnregP%s "exec ui/loadout/unreg_%s.cfg"' % (s, cls),
            'seta coop_loWho_%s "exec ui/loadout/clrP%s.cfg"' % (cls, s),
        ]
    return "\n".join(L) + "\n"


def tile(w):
    """tNN.cfg - what the grid tile runs when clicked."""
    return ("// GENERATED - inspect + LOCK-GATED equip-into-active-slot "
            "(coop_loCmt<id> = commit or deny)\n"
            "exec ui/loadout/p%s.cfg\n"
            "vstr coop_loCmt%s\n" % (w["id"], w["id"]))


def req(w):
    """reqNN.cfg - the hover unlock line. Absent entirely for weapons unlocked from the start."""
    if not w["req1"]:
        return None
    return ('set coop_loReq "%s"\n'
            'set coop_loReq2 "%s"\n' % (w["req1"], w["req2"]))


def roster(rows):
    """The body of loadoutroster.scr::roster_ids - what the server iterates to push unlocks."""
    L = ["roster_ids:{",
         "\tif( level.coop_loRosterN != NIL ){ end }",
         "\tlevel.coop_loRosterN = %d" % len(rows)]
    for i, w in enumerate(rows):
        # An empty column renders "level.coop_loRosterTab[N] = " with nothing after the "=". That
        # is a parse killer and it takes ALL of loadoutroster.scr with it: the parser reads the
        # NEXT statement as the missing value and then dies on that statement's own "=", so the
        # error is reported against a line that is perfectly correct (bug-1908). In game the only
        # symptoms were a NIL loadout, default weapons and no padlocks. Fail loudly here instead.
        for col in ("id", "tab"):
            if str(w.get(col, "")).strip() == "":
                raise SystemExit(
                    "gen_loadout: weapon %s has an empty '%s' column - that would emit an "
                    "assignment with no value and kill the whole script"
                    % (w.get("name") or w.get("id"), col))
        L += ['\tlevel.coop_loRosterId[%d] = "%s"' % (i, w["id"]),
              '\tlevel.coop_loRosterGive[%d] = "%s"' % (i, w["give"] or w["tik"]),
              "\tlevel.coop_loRosterTab[%d] = %s" % (i, w["tab"])]
    L.append("}end")
    return "\n".join(L)


def splice_roster(rows, text):
    """Replace only the roster_ids label, leaving the rest of the file untouched."""
    m = re.search(r"(?ms)^roster_ids:\{.*?^\}end", text)
    assert m, "roster_ids label not found"
    nl = "\r\n" if "\r\n" in text else "\n"
    return text[:m.start()] + roster(rows).replace("\n", nl) + text[m.end():]


def render_all(rows):
    out = {}
    for w in rows:
        out["p%s.cfg" % w["id"]] = preview(w)
        # offline finish-preview stubs (only where the finish tik exists for this gun) - the
        # main-menu armory has no server to swap the preview, so the fin cfgs vstr these locally
        _stem2 = os.path.splitext(os.path.basename(w["tik"]))[0]
        for _i, (_k, _lab) in enumerate([("gold", "GOLD"), ("chrome", "CHROME"),
                                         ("blued", "BLUED"), ("bloody", "BLOODY"),
                                         ("camo_woodland", "WOODLAND"), ("camo_winter", "WINTER"),
                                         ("camo_desert", "DESERT")]):
            _vt = os.path.join(ROOT, "hzm-mohaa-coop-mod", "models", "weapons",
                               "%s_%s.tik" % (_stem2, _k))
            if os.path.exists(_vt):
                out["finp%s_%d.cfg" % (w["id"], _i + 1)] = (
                    'set coop_loPrev "models/weapons/%s_%s.tik"\n' % (_stem2, _k)
                    + 'set coop_loNm "%s (%s)"\n' % (w["name"], _lab))
        out["t%s.cfg" % w["id"]] = tile(w)
        for s in w["slots"]:
            out["w%s_s%s.cfg" % (w["id"], s)] = slotfile(w, s)
        r = req(w)
        if r is not None:
            out["req%s.cfg" % w["id"]] = r
    return out


# ---------------------------------------------------------------- extract --------------------
def extract():
    rows = []
    for fn in sorted(os.listdir(UI)):
        m = re.match(r"p(\d+)\.cfg$", fn)
        if not m:
            continue
        wid = m.group(1)
        t = _read(os.path.join(UI, fn))

        def g(key, pat=r'"([^"]*)"'):
            mm = re.search(r"(?m)^set %s\s+%s" % (re.escape(key), pat), t)
            return mm.group(1) if mm else ""

        slots = ""
        for s in "1234":
            if ("w%s_s%s.cfg" % (wid, s)) in t:
                slots += s
        cls = ""
        for s in "1234":
            sp = os.path.join(UI, "w%s_s%s.cfg" % (wid, s))
            if os.path.exists(sp):
                cm = re.search(r"(?m)^vstr coop_loWho_(\w+)", _read(sp))
                if cm:
                    cls = cm.group(1)
                    break

        rt_ = _read(ROSTER)
        tm = re.search(r'coop_loRosterId\[(\d+)\] = "%s"' % wid, rt_)
        tab = ""
        give = ""
        if tm:
            tb = re.search(r"coop_loRosterTab\[%s\] = (\d+)" % tm.group(1), rt_)
            tab = tb.group(1) if tb else ""
            gv = re.search(r'coop_loRosterGive\[%s\] = "([^"]+)"' % tm.group(1), rt_)
            give = gv.group(1) if gv else ""

        rq = os.path.join(UI, "req%s.cfg" % wid)
        r1 = r2 = ""
        if os.path.exists(rq):
            rt = _read(rq)
            m1 = re.search(r'(?m)^set coop_loReq\s+"([^"]*)"', rt)
            m2 = re.search(r'(?m)^set coop_loReq2\s+"([^"]*)"', rt)
            r1, r2 = (m1.group(1) if m1 else ""), (m2.group(1) if m2 else "")
        rows.append({
            "id": wid, "tik": g("coop_loPrev"), "give": give, "xfm": g("coop_loXfmW"),
            "charanim": g("coop_loCharAnim"), "cls": cls, "tab": tab,
            "name": g("coop_loNm"), "cd": g("coop_loCd"),
            "b0": g("coop_loB0").rsplit("coop_bf", 1)[-1],
            "b1": g("coop_loB1").rsplit("coop_bf", 1)[-1],
            "b2": g("coop_loB2").rsplit("coop_bf", 1)[-1],
            "b3": g("coop_loB3").rsplit("coop_bf", 1)[-1],
            "clip": g("coop_loClip").rsplit("clip_", 1)[-1],
            "clipn": g("coop_loClipN"),
            "recoil": g("coop_loRecoil").rsplit("rec_", 1)[-1],
            "slots": slots, "req1": r1, "req2": r2,
        })
    hdr = ("# Armory weapon table - the source of truth for ui/loadout/. One row = one weapon in\n"
           "# the picker. Regenerate the pages with: python docs/tools/gen_loadout.py build\n"
           "#\n"
           "# id       two-digit page id, also the tile number in ui/coop_loadout.urc\n"
           "# tik      weapon model handed to the preview and to the slot\n"
           "# xfm      preview transform, HAND-DIALLED per gun (x y z scale pitch yaw roll)\n"
           "# charanim coop_hold_* pose used by the preview\n"
           "# name     grid + slot label, upper case\n"
           "# cd       caliber / action / capacity line\n"
           "# b0..b3   the four stat bars, as the coop_bfN texture number\n"
           "# clip     clip_<n> texture; clipn the printed round count\n"
           "# recoil   rec_<id> recoil curve texture\n"
           "# slots    which inventory slots accept it: 1,2 primary  3 pistol  4 heavy\n"
           "# req1/2   hover unlock text, split over two lines. Empty = unlocked from the start.\n"
           + "\t".join(COLS) + "\n")
    body = "".join("\t".join(w[c] for c in COLS) + "\n" for w in rows)
    io.open(TSV, "w", encoding="utf-8", newline="\n").write(hdr + body)
    return rows


def load():
    rows = []
    for line in io.open(TSV, encoding="utf-8"):
        if line.startswith("#") or line.startswith("id\t") or not line.strip():
            continue
        v = line.rstrip("\n").split("\t")
        rows.append(dict(zip(COLS, v + [""] * (len(COLS) - len(v)))))
    return rows


# ---------------------------------------------------------------- modes ----------------------
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "extract":
        rows = extract()
        print("extracted %d weapons -> %s" % (len(rows), os.path.relpath(TSV, ROOT)))
        return 0

    rows = load()
    files = render_all(rows)

    if mode == "build":
        for name, text in sorted(files.items()):
            io.open(os.path.join(UI, name), "w", encoding="latin-1", newline="").write(text)
        # Compute BEFORE opening for write. open(..., "w") truncates immediately, and the
        # argument is evaluated after - so reading the file inside the write call reads the empty
        # file it just destroyed, and any failure leaves nothing behind. That emptied
        # loadoutroster.scr once already.
        new_roster = splice_roster(rows, _read(ROSTER))
        io.open(ROSTER, "w", encoding="latin-1", newline="").write(new_roster)
        print("wrote %d files + the unlock roster, for %d weapons" % (len(files), len(rows)))
        return 0

    bad, missing = [], []
    for name, text in sorted(files.items()):
        p = os.path.join(UI, name)
        if not os.path.exists(p):
            missing.append(name)
        elif _read(p) != text:
            bad.append(name)
    rtext = _read(ROSTER)
    roster_ok = splice_roster(rows, rtext) == rtext

    orphan = [f for f in os.listdir(UI)
              if re.match(r"(p|t|req)\d+\.cfg$|w\d+_s\d\.cfg$", f) and f not in files]
    print("%d weapons -> %d generated files" % (len(rows), len(files)))
    print("  byte-identical : %d" % (len(files) - len(bad) - len(missing)))
    if bad:
        print("  DIFFERENT      : %d  %s" % (len(bad), bad[:8]))
    if missing:
        print("  MISSING        : %d  %s" % (len(missing), missing[:8]))
    if orphan:
        print("  on disk only   : %d  %s" % (len(orphan), orphan[:8]))
    print("  unlock roster  : %s" % ("in sync" if roster_ok else "OUT OF SYNC - weapons will not equip"))
    ok = not bad and not missing and not orphan and roster_ok
    print("  -> %s" % ("EXACT REPRODUCTION" if ok else "MISMATCH - format not fully understood"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
