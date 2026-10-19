#!/usr/bin/env python3
"""patch_done_gate.py - one-shot, idempotent patch: the Armory DONE button refuses to close while a LOCKED item is selected.
    python patch_done_gate.py <mod_tree>          (the mod worktree, e.g. C:\\mohaa-coop-dev\\hzm-mod-donegate)

User 2026-10-15: "when in the loadout, if you try to hit 'Done' and you have selected [locked] equipment, a message appears
'Equipment Pre-Requisite Not Met' and doesn't let you hit Done unless you have only unlocked equipment."

Why it is built this way (cfg cannot branch; ui/coop_loadout.urc cannot run script):
  * DONE now runs `exec ui/loadout/done.cfg`.  done.cfg preloads the verdict `coop_loDnFin = exec donego.cfg`, runs one VERDICT cvar per
    source (each is a command: either a no-op or "set coop_loDnFin exec donebad.cfg ; set coop_loDnM2 <item> ; set coop_loDnM3 <need>"),
    then runs coop_loDnFin.  donego = the old close (popmenu / ,w0x bus token / fit unbind); donebad = show the banner, beep, stay open.
  * Uniform / helmet / glove: the PARKED page is a selection the server never hears about (locked pages send nothing), so the verdict
    is baked into every page cfg (coop_loDnS / coop_loDnH / coop_loDnG).  A gated page bakes "bad"; the row's uok.cfg (the server's
    push for an EARNED page, run by the page's `vstr coop_lo*LkA<NN>`) resets it to a no-op, exactly like it opens the padlock.
  * Guns / finishes / variants: the server owns them (loadoutpick.scr::loadout_doneGateExport) and pushes coop_loDnSv
    (+ coop_loDnSvA/B text) whenever the picture changes.  Server-HELD uniform/helmet/glove picks are deliberately NOT checked: the player never sees them (the row shows the parked page), the spawn path heals a locked one (helmet.scr helmet_apply 'locked-heal'), and blocking DONE on an invisible item would be unfixable.  Server-side refusal (loadout_set / finish / cosmetic gates) is untouched: safety net.
  * The banner is a few widgets at the end of ui/coop_loadout.urc (the file is checksum-locked: re-lock it, see check_mp_isolation.py).
"""
import io, os, re, sys

CR, LF = chr(13), chr(10)
CRLF = CR + LF


def rd(p):
    return io.open(p, encoding="latin-1", newline="").read()


def wr(p, s):
    io.open(p, "w", encoding="latin-1", newline="").write(s)


def crlf(s):
    return s.replace(CRLF, LF).replace(LF, CRLF)


ROWS = {
    "skin": dict(dn="coop_loDnS", pre="s", label="Uniform", nm="coop_loCharNm"),
    "helm": dict(dn="coop_loDnH", pre="h", label="Helmet", nm="coop_loHelmNm"),
    "glove": dict(dn="coop_loDnG", pre="g", label="Gloves", nm="coop_loGloveNm"),
}
NOP = "set coop_loDnNop 0"


def clean(t):
    t = t.replace('"', "'").replace(";", ",").replace("//", "/ /").replace("%", " pct")
    return " ".join(t.split())


def cvarval(s, name):
    m = re.search(r'^set %s "([^"\r\n]*)"' % name, s, re.M)
    return m.group(1) if m else ""


def patch_page(path, row):
    r = ROWS[row]
    s = rd(path)
    if r["dn"] in s:
        return "skip"
    lines = s.split(CRLF)
    idx = [i for i, l in enumerate(lines) if re.match(r"set coop_loCosLk [01]\s*$", l)]
    if len(idx) != 1:
        return "NOLK"
    i = idx[0]
    gated = lines[i].strip().endswith("1")
    hasv = any(re.match(r"vstr coop_lo\w+LkA\d+\s*$", l) for l in lines)
    if gated and not hasv:
        return "MISMATCH"
    # (s14 / s55 bake CosLk 0 AND carry a vstr LkA line: the server does not gate them, so the baked 0 wins - a free page)
    if gated:
        nm = clean(cvarval(s, r["nm"]))
        req2 = cvarval(s, "coop_loCosReq2")
        req3 = cvarval(s, "coop_loCosReq3")
        if req3.lower().startswith("not equipped"):
            req3 = ""
        need = clean((req2 + " " + req3).strip() or cvarval(s, "coop_loCosReq") or "Not unlocked yet")
        val = ("set coop_loDnFin exec ui/loadout/donebad.cfg ; set coop_loDnM2 %s: %s ; set coop_loDnM3 %s" % (r["label"], nm, need))
    else:
        val = NOP
    lines.insert(i, 'set %s "%s"' % (r["dn"], val))
    wr(path, CRLF.join(lines))
    return "gated" if gated else "free"


def append_line(path, line, marker):
    s = rd(path)
    if marker in s:
        return False
    if not s.endswith(CRLF):
        s += CRLF
    wr(path, s + line + CRLF)
    return True


def sub_once(path, old, new, marker):
    s = rd(path)
    if marker in s:
        return False
    old, new = crlf(old), crlf(new)
    if s.count(old) != 1:
        raise SystemExit("anchor not unique/found in %s: %r (count %d)" % (path, old[:70], s.count(old)))
    wr(path, s.replace(old, new))
    return True


SERVER_FN = r'''//=========================================================================
//[done gate 2026-10-15] DONE REFUSES TO CLOSE ON A LOCKED SELECTION. Everything the SERVER holds as a pick (gun per slot, finish /
//variant per slot - the slot cards show them) is checked against the same unlock tests the tiles and the spawn path use; the
//first offender becomes a client verdict:
//  coop_loDnSv  = "set coop_loDnNop 0" (fine) | "exec ui/loadout/dnsv_bad.cfg" (ui/loadout/done.cfg runs it via vstr)
//  coop_loDnSvA = "set coop_loDnM2 <item>"   coop_loDnSvB = "set coop_loDnM3 <what unlocks it>"   (dnsv_bad.cfg runs both)
//Diff-only (flags coop_loDnLast; the menu-open token clears it so a fresh open always re-asserts).  The parked uniform / helmet /
//glove PAGE is client-only state and is checked client-side (page cfgs bake coop_loDnS/H/G); a server-held cosmetic is not (the spawn path heals it).  bug-758 wire rules: unquoted, no ';'.
//=========================================================================
loadout_doneGateExport local.player:{
	if(local.player == NULL){ end }
	if(local.player.flags["coop_loDnGen"] == NIL){ local.player.flags["coop_loDnGen"] = 0 }
	local.player.flags["coop_loDnGen"] = local.player.flags["coop_loDnGen"] + 1
	local.gen = local.player.flags["coop_loDnGen"]
	local.l2 = ""
	local.l3 = ""
	if(getcvar("coop_lockLoadout") != "0"){
		waitthread coop_mod/challenges.scr::chal_ensure local.player
		if(local.player == NULL){ end }
		if(local.player.flags["coop_loDnGen"] != local.gen){ end }	//superseded while chal_ensure waited
		waitthread coop_mod/loadoutskins.scr::skin_init
		for(local.sl = 1; local.sl <= 4; local.sl++){
			if(local.l2 != ""){ break }
			local.sid = local.player.flags["coop_loSlotId" + local.sl]
			if(local.sid == NIL || local.sid == ""){ continue }
			local.r = waitthread coop_mod/loadoutroster.scr::roster_get local.sid
			local.give = local.r["give"]
			if(local.give == NIL || local.give == ""){ continue }
			if(!(waitthread loadout_isUnlocked local.player local.give)){
				local.l2 = "Slot " + local.sl + ": " + local.r["name"]
				local.l3 = waitthread coop_mod/challenges.scr::chal_reqText local.give
				continue
			}
			local.fid = local.player.flags["coop_loFin" + local.sl]
			if(local.fid == NIL || local.fid == ""){ continue }
			local.fid = int(local.fid)
			if(local.fid < 1){ continue }
			if(local.fid >= 8){
				if(!(waitthread loadout_mvUnlocked local.player local.give local.fid)){
					local.l2 = "Slot " + local.sl + " variant: " + local.r["name"]
					local.l3 = "Variant not unlocked yet"
				}
			} else if(!(waitthread loadout_finUnlocked local.player local.fid)){
				local.l2 = "Slot " + local.sl + " finish: " + level.coop_skinFinName[local.fid]
				local.l3 = "Finish not unlocked yet"
			} else if(!(waitthread loadout_finMastered local.player local.give)){
				local.l2 = "Slot " + local.sl + " finish: " + level.coop_skinFinName[local.fid]
				local.l3 = "Master " + local.r["name"] + " first"
			}
		}
	}
	if(local.player == NULL){ end }
	if(local.player.flags["coop_loDnGen"] != local.gen){ end }
	local.key = local.l2 + "|" + local.l3
	if(local.player.flags["coop_loDnLast"] == local.key){ end }
	local.player.flags["coop_loDnLast"] = local.key
	if(local.l2 == ""){
		local.player stufftext "set coop_loDnSv set coop_loDnNop 0"
	} else {
		local.player stufftext ( "set coop_loDnSvA set coop_loDnM2 " + local.l2 )
		local.player stufftext ( "set coop_loDnSvB set coop_loDnM3 " + local.l3 )
		local.player stufftext "set coop_loDnSv exec ui/loadout/dnsv_bad.cfg"
	}
}end

'''

HOOK = "\tthread coop_mod/loadoutpick.scr::loadout_doneGateExport local.player\t//[done gate 2026-10-15] a pick changed: refresh the DONE verdict\r\n"

URC_BANNER = r'''
// [done gate 2026-10-15] "EQUIPMENT PRE-REQUISITE NOT MET" banner: shown by ui/loadout/donebad.cfg (set coop_loDnShow 1) when DONE is
// pressed with a LOCKED item selected; the menu stays open. Lines 2/3 are filled by the verdict cvars (coop_loDnM2 item, coop_loDnM3 need).
// Placed x258-474 so no rendermodel widget (slot thumbnails end at x252, big preview starts x478) can draw over it.
resource
Label
{
ordernumber 90
name "doneGateBg"
rect 258 196 216 78
fgcolor 1.00 1.00 1.00 1.00
bgcolor 0.07 0.05 0.05 0.98
borderstyle "3D_BORDER"
enabledcvar "coop_loDnShow"
}

resource
Label
{
ordernumber 91
name "doneGateT"
title "EQUIPMENT PRE-REQUISITE NOT MET"
rect 263 200 206 12
fgcolor 0.95 0.42 0.32 1.00
bgcolor 0.00 0.00 0.00 0.00
borderstyle "NONE"
font "verdana-12"
dontlocalize
textalign left
enabledcvar "coop_loDnShow"
}

resource
Label
{
ordernumber 91
name "doneGateM2"
rect 263 214 206 11
fgcolor 1.00 1.00 1.00 1.00
bgcolor 0.00 0.00 0.00 0.00
borderstyle "NONE"
font "verdana-12"
dontlocalize
textalign left
enabledcvar "coop_loDnShow"
linkcvar "coop_loDnM2"
}

resource
Label
{
ordernumber 91
name "doneGateM3"
rect 263 226 206 11
fgcolor 0.91 0.80 0.53 1.00
bgcolor 0.00 0.00 0.00 0.00
borderstyle "NONE"
font "verdana-12"
dontlocalize
textalign left
enabledcvar "coop_loDnShow"
linkcvar "coop_loDnM3"
}

resource
Label
{
ordernumber 91
name "doneGateHint"
title "Equip unlocked items only, then press DONE."
rect 263 240 206 11
fgcolor 0.60 0.58 0.54 1.00
bgcolor 0.00 0.00 0.00 0.00
borderstyle "NONE"
font "verdana-12"
dontlocalize
textalign left
enabledcvar "coop_loDnShow"
}

resource
Button
{
name "doneGateOk"
title "OK"
rect 402 255 66 14
fgcolor 0.85 0.83 0.78 1.00
bgcolor 0.10 0.11 0.14 0.94
borderstyle "3D_BORDER"
font "verdana-12"
clicksound "sound/menu/back.wav"
enabledcvar "coop_loDnShow"
stuffcommand "set coop_loDnShow 0"
}
'''


def main():
    tree = sys.argv[1]
    ui = os.path.join(tree, "ui", "loadout")
    cm = os.path.join(tree, "coop_mod")
    stats = {}
    # ---- pages: bake the parked-page verdict
    for row in ROWS:
        d = os.path.join(ui, row)
        for fn in sorted(os.listdir(d)):
            if not re.match(r"^%s\d+\.cfg$" % ROWS[row]["pre"], fn):
                continue
            res = patch_page(os.path.join(d, fn), row)
            stats[(row, res)] = stats.get((row, res), 0) + 1
        # an EARNED page: the server's uok.cfg push also clears the verdict
        append_line(os.path.join(d, "uok.cfg"), 'set %s "%s"' % (ROWS[row]["dn"], NOP), ROWS[row]["dn"])
    append_line(os.path.join(ui, "helm", "hclear.cfg"), 'set coop_loDnH "%s"' % NOP, "coop_loDnH")
    print("pages:", sorted(stats.items()))
    bad = [k for k in stats if k[1] in ("NOLK", "MISMATCH")]
    if bad:
        raise SystemExit("unpatched pages: %r" % bad)
    # ---- cfgs
    wr(os.path.join(ui, "done.cfg"), crlf(
        "// [done gate 2026-10-15] the Armory DONE button (ui/coop_loadout.urc closeBtn: exec ui/loadout/done.cfg).\n"
        "// cfg cannot branch, so: preload the OK verdict, let each source (parked uniform / helmet / glove page, server-held picks)\n"
        "// overwrite it with the BAD one if it holds a locked item, then run whichever verdict is left.\n"
        'set coop_loDnShow 0\n'
        'set coop_loDnFin "exec ui/loadout/donego.cfg"\n'
        'vstr coop_loDnS\n'
        'vstr coop_loDnH\n'
        'vstr coop_loDnG\n'
        'vstr coop_loDnSv\n'
        'vstr coop_loDnFin\n'))
    wr(os.path.join(ui, "donego.cfg"), crlf(
        "// DONE with only unlocked equipment: the original close (it used to be the closeBtn stuffcommand itself).\n"
        "popmenu 0\n"
        "append name ,w0x\n"
        "exec ui/loadout/fitunbind.cfg\n"))
    wr(os.path.join(ui, "donebad.cfg"), crlf(
        "// DONE with a LOCKED item selected: show the EQUIPMENT PRE-REQUISITE NOT MET banner, beep, keep the menu open.\n"
        "set coop_loDnShow 1\n"
        "vstr coop_loDeny\n"))
    wr(os.path.join(ui, "dnsv_bad.cfg"), crlf(
        "// the server found a locked pick (gun / finish / variant / saved cosmetic): copy its text into the banner and arm the refusal.\n"
        'set coop_loDnFin "exec ui/loadout/donebad.cfg"\n'
        "vstr coop_loDnSvA\n"
        "vstr coop_loDnSvB\n"))
    # open: start from OK (offline armory has no server verdict); init: the three page rows
    sub_once(os.path.join(ui, "open.cfg"), "pushmenu coop_loadout\n",
             "// [done gate 2026-10-15] start the DONE verdict clean; the server re-asserts a locked pick right after the open token.\n"
             'set coop_loDnShow 0\nset coop_loDnNop 0\nset coop_loDnSv "set coop_loDnNop 0"\npushmenu coop_loadout\n', "coop_loDnSv")
    sub_once(os.path.join(ui, "init.cfg"), "set coop_loSel1 1\n",
             "// [done gate 2026-10-15] per-row DONE verdicts default to OK; the page replays at the end of this file re-arm a parked locked page.\n"
             'set coop_loDnShow 0\nset coop_loDnNop 0\nset coop_loDnS "set coop_loDnNop 0"\nset coop_loDnH "set coop_loDnNop 0"\n'
             'set coop_loDnG "set coop_loDnNop 0"\nset coop_loSel1 1\n', "coop_loDnShow")
    # ---- urc: DONE runs done.cfg + banner widgets
    urc = os.path.join(tree, "ui", "coop_loadout.urc")
    sub_once(urc, 'stuffcommand "popmenu 0 ; append name ,w0x ; exec ui/loadout/fitunbind.cfg"',
             'stuffcommand "exec ui/loadout/done.cfg"', "ui/loadout/done.cfg")
    s = rd(urc)
    if "doneGateBg" not in s:
        t = s.rstrip(CR + LF)
        if not t.endswith("end."):
            raise SystemExit("urc does not end with 'end.'")
        t = t[: -len("end.")].rstrip(CR + LF) + CRLF
        wr(urc, t + crlf(URC_BANNER) + CRLF + "end." + CRLF)
    # ---- server: verdict function + hooks
    lp = os.path.join(cm, "loadoutpick.scr")
    s = rd(lp)
    if "loadout_doneGateExport" not in s:
        anchor = crlf("//=========================================================================\n// Mastered = the gun's base per-weapon challenge is COMPLETE")
        if s.count(anchor) != 1:
            raise SystemExit("Mastered anchor not found")
        s = s.replace(anchor, crlf(SERVER_FN) + anchor)
        old = crlf('\tif(local.any == 1 && local.player != NULL){\n\t\tlocal.player stufftext "vstr coop_loMastApply"\n\t}\n}end')
        if s.count(old) != 1:
            raise SystemExit("slotLocksExport tail anchor not found")
        s = s.replace(old, old[: -len("}end")] + HOOK.rstrip(CRLF) + CRLF + "}end")
        old = crlf('\tif(local.data == "o"){\n\t\tthread loadout_ui_exportUnlocks local.player')
        if s.count(old) != 1:
            raise SystemExit("menuCtl o anchor not found")
        s = s.replace(old, crlf('\tif(local.data == "o"){\n\t\tlocal.player.flags["coop_loDnLast"] = NIL\t//[done gate 2026-10-15] a fresh open re-asserts the DONE verdict\n\t\tthread loadout_ui_exportUnlocks local.player'))
        wr(lp, s)
    print("OK")


if __name__ == "__main__":
    main()
