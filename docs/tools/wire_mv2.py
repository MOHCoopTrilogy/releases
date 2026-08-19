# PRESERVED 2026-08-19 from session scratchpad - the model-variant wiring generator
# (chains + tables + reqmv). Credits in variant labels per user: pack-level for certain
# provenance (MOH:PA ports, WW1 Extended); author-level pending research.
"""Model variants v2: multiple variants per gun, VARIANT button cycles.

fid map: 0 = standard, 1-7 = finishes, 8-13 = this gun's model variants in list order.
The client's VARIANT button always sends fid 8 = "cycle": the server steps to the next variant
the gun has (wrapping to standard after the last). fids 9-13 arrive only from the join-time
resend replay, which the server re-writes after every successful apply so a rejoin lands on the
exact variant that was picked, not one step past it.
"""
import io
import re

MOD = "hzm-mohaa-coop-mod/"
UI = MOD + "ui/loadout/"

# per-gun ordered variant lists: (base stem, [(key, LABEL), ...]) -> fids 8, 9, 10...
MV = [
    ("thompsonsmg",  [("tommy28", "THOMPSON (M1928)"), ("tommy1928d", "THOMPSON (1928 TOMMY)"),
                      ("tommy27a1", "THOMPSON (27A1 COMMANDO)"), ("m1a1dk", "M1A1 REMODEL")], "wpn_thompson_e"),
    ("mp40",         [("mp40r2", "MP40 (REACTIVATED)"), ("mp18", "MP18 (WW1 EXT)")], "wpn_mp40_e"),
    ("bar",          [("pabar", "BAR (PACIFIC) (MOH:PA)"), ("bar1918", "BAR M1918 (WWI) (WW1 EXT)"),
                      ("bar1918a", "M1918 CLASSIC"), ("bar1918a1", "M1918A1"),
                      ("bar1918a2", "M1918A2")], "wpn_bar_e"),
    ("m1_garand",    [("pagarand", "M1 GARAND (PACIFIC) (MOH:PA)")], "wpn_garand_e"),
    ("mp44",         [("mp44strap", "STG 44 (STRAPPED)")], "wpn_stg44_e"),
    ("colt45",       [("coltpa", "COLT 45 (PACIFIC) (MOH:PA)"), ("colt1911w", "M1911 (WWI) (WW1 EXT)"),
                      ("covert", "M1911 COVERT"), ("drbond", "1911 CLASSIC"),
                      ("bloodyeic", "M1911 BLOODY EIC")], "wpn_colt_e"),
    ("enfield",      [("p14", "P14 ENFIELD (WW1 EXT)")], "wpn_enfield_e"),
    # G98 is HOSTED under the G43 (family grouping, user request) but its BODY is the Kar98's -
    # "a bolt action should remain a bolt action". The explicit path points at the kar98-derived
    # tik; its name strips to "Mauser KAR 98K", so hands, bolt-cycle anims and ADS are the Kar98's.
    ("G43",          [("g98", "GEWEHR 98 (BOLT) (WW1 EXT)", "models/weapons/kar98_g98.tik")], "wpn_g43_e"),
    ("KAR98sniper",  [("g98scope", "G98 SCOPED (WW1 EXT)")], "wpn_kar98sniper_e"),
    ("springfield",  [("smlescope", "SMLE SCOPED (WW1 EXT)"), ("m1903", "M1903 SPRINGFIELD (WW1 EXT)")], "wpn_springfield_e"),
    ("mauser_c96",   [("c96trench", "C96 (TRENCH) (WW1 EXT)")], "wpn_c96_e"),
    ("shotgun",      [("authwinch", "AUTHENTIC WOOD")], "wpn_shotgun_e"),
]


def rd(p):
    raw = io.open(p, "rb").read()
    return raw.decode("latin-1"), ("\r\n" if b"\r\n" in raw else "\n")


def wr(p, s):
    io.open(p, "wb").write(s.encode("latin-1"))


# --- resolve gives (roster spelling), tile ids, base display names; assert everything ----------
tsv = io.open("docs/tools/loadout_weapons.tsv", encoding="utf-8").read()
chal = io.open(MOD + "coop_mod/challenges.scr", encoding="latin-1").read()
roster = io.open(MOD + "coop_mod/loadoutroster.scr", encoding="latin-1").read()
rgives = {g.lower(): g for g in re.findall(r'coop_loRosterGive\[\d+\] = "([^"]+)"', roster)}

resolved = []   # (give, tile, elite, basename, [(fid, key, label, variantpath), ...])
for stem, variants, elite in MV:
    give = rgives.get("models/weapons/%s.tik" % stem.lower())
    assert give, "no roster give for %s" % stem
    m = re.search(r"(?m)^(\d+)\t" + re.escape(give), tsv)
    assert m, "no tsv row for %s" % give
    tile = m.group(1)
    assert ('"%s"' % elite) in chal, "elite %s missing" % elite
    base_name = re.search(r'(?mi)^\s*name\s+"([^"]+)"',
                          io.open(MOD + "models/weapons/%s.tik" % stem, encoding="latin-1").read()).group(1)
    vlist = []
    for i, v in enumerate(variants):
        key, label = v[0], v[1]
        vpath = v[2] if len(v) > 2 else "models/weapons/%s_%s.tik" % (stem, key)
        import os
        assert os.path.exists(MOD + vpath), "variant tik missing: " + vpath
        vlist.append((8 + i, key, label, vpath))
    resolved.append((give, tile, elite, base_name, vlist))
    print("  %-34s tile %-3s %-22s %d variant(s)" % (give, tile, elite, len(vlist)))

# --- 1. regenerate the MV block in loadoutskins.scr wholesale -----------------------------------
p = MOD + "coop_mod/loadoutskins.scr"
txt, nl = rd(p)
m = re.search(r"(?ms)^\t//\[user [0-9-]+\] MODEL VARIANTS.*?(?=^\}end)", txt)
assert m, "MV block not found"
B = []
B.append("\t//[user 2026-08-18] MODEL VARIANTS v2 - fids 8..N per gun, in cycle order. The VARIANT")
B.append("\t//button sends 8 = CYCLE; the server steps through these and wraps to standard. Unlock")
B.append("\t//for ALL of a gun's variants = that gun's ELITE challenge (coop_skinMvElite). Names are")
B.append("\t//per fid; MvMax bounds the cycle; the ByElite/Pseudo maps feed the announce pipeline.")
for give, tile, elite, base_name, vlist in resolved:
    for fid, key, label, vpath in vlist:
        B.append('\tlevel.coop_skinGive["%s"][%d] = "%s"' % (give, fid, vpath))
        B.append('\tlevel.coop_skinMvName["%s"][%d] = "%s"' % (give, fid, label))
    B.append('\tlevel.coop_skinMvMax["%s"] = %d' % (give, vlist[-1][0]))
    B.append('\tlevel.coop_skinMvElite["%s"] = "%s"' % (give, elite))
    B.append('\tlevel.coop_skinMvByElite["%s"] = "%s MODEL VARIANTS"' % (elite, base_name.upper()))
    B.append('\tlevel.coop_skinMvPseudo["mv_%s"] = "%s MODEL VARIANTS"' % (elite, base_name.upper()))
txt = txt[:m.start()] + nl.join(B) + nl + txt[m.end():]
wr(p, txt)
print("loadoutskins.scr: MV v2 block - %d guns, %d variants"
      % (len(resolved), sum(len(v[4]) for v in resolved)))

# --- 2. loadout_finish v2: full-label rewrite ----------------------------------------------------
p = MOD + "coop_mod/loadoutpick.scr"
txt, nl = rd(p)
m = re.search(r"(?ms)^loadout_finish local\.player local\.slot local\.fid:\{.*?^\}end", txt)
assert m, "loadout_finish label"
NEW = """loadout_finish local.player local.slot local.fid:{
//=========================================================================
if(level.cMTE_coop_loadoutpick){if(!level.cMTE){level.cMTE=0}; level.cMTE++; println( "-#-#- thread loadoutpick/loadout_finish->"+level.cMTE+"" )}
	if(local.player == NULL){ end }
	if(local.fid == NIL || local.fid == ""){ end }
	local.fid = int(local.fid)
	if(local.fid < 0 || local.fid > 13){ end }
	waitthread coop_mod/loadoutskins.scr::skin_init

	// standard = clear; always allowed
	if(local.fid == 0){
		local.player.flags["coop_loFin" + local.slot] = 0
		local.player stufftext ( "seta coop_loS" + local.slot + "F 0" )
		local.player stufftext ( "seta coop_loFA" + local.slot + " append name ,f" + local.slot + "0" )
		local.player iprint "Standard"
		end
	}

	local.id = local.player.flags["coop_loSlotId" + local.slot]
	if(local.id == NIL){
		local.player stufftext "vstr coop_loDeny"
		local.player iprint "Pick a weapon for that slot first"
		end
	}
	local.r = waitthread coop_mod/loadoutroster.scr::roster_get local.id
	local.give = local.r["give"]

	//---------------- finishes (1-7): unchanged gates -------------------------------------------
	if(local.fid <= 7){
		local.variant = level.coop_skinGive[local.give][local.fid]
		if(local.variant == NIL || local.variant == ""){
			local.player stufftext "vstr coop_loDeny"
			local.player iprint ( "No " + level.coop_skinFinName[local.fid] + " finish for this weapon" )
			end
		}
		if(!(waitthread loadout_finUnlocked local.player local.fid)){
			local.player stufftext "vstr coop_loDeny"
			local.player iprint ( level.coop_skinFinName[local.fid] + " is locked - see CHALLENGES" )
			end
		}
		if(!(waitthread loadout_finMastered local.player local.give)){
			local.player stufftext "vstr coop_loDeny"
			local.player iprint "Master this weapon first (its kill challenge)"
			end
		}
		local.player.flags["coop_loFin" + local.slot] = local.fid
		local.player stufftext ( "seta coop_loS" + local.slot + "F " + local.fid )
		local.player stufftext ( "seta coop_loFA" + local.slot + " append name ,f" + local.slot + local.fid )
		local.player stufftext ( "set coop_loPrev " + local.variant )
		local.player stufftext "vstr coop_loOpenInspect"
		local.player iprint ( level.coop_skinFinName[local.fid] + " finish applied" )
		end
	}

	//---------------- model variants (8 = cycle, 9-13 = direct from the join replay) -------------
	local.max = level.coop_skinMvMax[local.give]
	if(local.max == NIL){
		local.player stufftext "vstr coop_loDeny"
		local.player iprint "No model variants for this weapon"
		end
	}
	// both gates are per-GUN, so check once whichever variant lands
	if(!(waitthread loadout_mvUnlocked local.player local.give)){
		local.player stufftext "vstr coop_loDeny"
		local.player iprint "Model variants unlock at this gun's ELITE challenge"
		end
	}
	if(!(waitthread loadout_finMastered local.player local.give)){
		local.player stufftext "vstr coop_loDeny"
		local.player iprint "Master this weapon first (its kill challenge)"
		end
	}

	local.cur = local.player.flags["coop_loFin" + local.slot]
	if(local.cur == NIL || local.cur < 8 || local.cur > local.max){ local.cur = 7 }
	if(local.fid == 8){
		// CYCLE: next existing variant after the current one; past the last -> standard
		local.next = local.cur + 1
		while(local.next <= local.max && (level.coop_skinGive[local.give][local.next] == NIL)){
			local.next++
		}
		if(local.next > local.max){
			// wrap to standard
			local.player.flags["coop_loFin" + local.slot] = 0
			local.player stufftext ( "seta coop_loS" + local.slot + "F 0" )
			local.player stufftext ( "seta coop_loFA" + local.slot + " append name ,f" + local.slot + "0" )
			local.player stufftext ( "set coop_loPrev " + local.give )
			local.player stufftext "vstr coop_loOpenInspect"
			local.player iprint "Standard model"
			end
		}
		local.fid = local.next
	}
	local.variant = level.coop_skinGive[local.give][local.fid]
	if(local.variant == NIL || local.variant == ""){ end }	// direct replay for a fid this gun lacks

	local.player.flags["coop_loFin" + local.slot] = local.fid
	local.player stufftext ( "seta coop_loS" + local.slot + "F " + local.fid )
	local.player stufftext ( "seta coop_loFA" + local.slot + " append name ,f" + local.slot + local.fid )
	local.player stufftext ( "set coop_loPrev " + local.variant )
	local.player stufftext "vstr coop_loOpenInspect"
	local.player iprint ( level.coop_skinMvName[local.give][local.fid] + " equipped" )
}end"""
txt = txt[:m.start()] + NEW.replace("\n", nl) + txt[m.end():]

# finResolve: widen the fid bound comment path already handles 8; ensure lookup works for 9-13
m2 = re.search(r"(?ms)^loadout_finResolve local\.player local\.slot local\.give:\{.*?^\}end local\.variant", txt)
assert m2, "finResolve label"
seg = m2.group(0)
if "local.fid == 8){" in seg:
    seg2 = seg.replace("\tif(local.fid == 8){", "\tif(local.fid >= 8){", 1)
    txt = txt[:m2.start()] + seg2 + txt[m2.end():]
wr(p, txt)
print("loadoutpick.scr: loadout_finish v2 (cycle + direct) + finResolve bound")

# --- 3. p-pages: MV_HOSTS -> all 12 tile ids; reqmv per host ------------------------------------
p = "docs/tools/gen_loadout.py"
s = io.open(p, encoding="utf-8").read()
old = re.search(r"MV_HOSTS = \([^)]*\)", s)
assert old, "MV_HOSTS"
tiles = ", ".join('"%s"' % t for _, t, _, _, _ in sorted(resolved, key=lambda r: r[1]))
s = s[:old.start()] + "MV_HOSTS = (%s)" % tiles + s[old.end():]
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("gen_loadout.py: MV_HOSTS = 12 hosts")

N = "\r\n"
for give, tile, elite, base_name, vlist in resolved:
    em = re.search(r'"%s"[^\r\n]*?"([^"]+)"\s+"([^"]+)"\s+"[^"]*"\s+\d+' % elite, chal)
    req = "UNLOCK: %s" % (em.group(2) if em else "this gun's Elite challenge")
    labels = " / ".join(l for _, _, l, _ in vlist)
    wr(UI + "reqmv%s.cfg" % tile,
       'set coop_loReq "%s"' % labels[:120] + N + 'set coop_loReq2 "%s"' % req + N)
print("reqmv cfgs: 12 hosts, hover lists every variant")

# --- 3b. OFFLINE variant preview v2: PER-SLOT chains that archive the EXACT fid.
# v1 chains were slot-agnostic and archived nothing - a menu pick archived only ",fN8" (cycle
# once), so cycling to a gun's 2nd/3rd variant at the menu replayed as the 1st on join. Each
# chain entry now setas the slot's exact fid + resend recipe, so what you SEE at the menu is
# byte-for-byte what the join replay applies. The server additionally echoes the chain position
# after every live apply (loadout_finish), so rapid clicking can never desync client from server.
tsvname = {}
for line in tsv.splitlines():
    if line and not line.startswith("#"):
        f = line.split("	")
        if len(f) > 7:
            tsvname[f[0]] = f[7]
for give, tile, elite, base_name, vlist in resolved:
    n = len(vlist)
    for sl in (1, 2, 3, 4):
        for k in range(n + 1):
            nxt = (k + 1) % (n + 1)
            if k == 0:
                fid, prev_path, label = 0, give, tsvname.get(tile, base_name.upper())
            else:
                fid, _, label, prev_path = vlist[k - 1][0], None, vlist[k - 1][2], vlist[k - 1][3]
            body = ("// GENERATED - variant chain %d/%d, host %s, slot %d (exact-fid archive)" % (k, n, tile, sl) + N
                    + 'set coop_loPrev "%s"' % prev_path + N
                    + 'set coop_loNm "%s"' % label + N
                    + 'seta coop_loS%dF "%d"' % (sl, fid) + N
                    + 'seta coop_loFA%d "append name ,f%d%d"' % (sl, sl, fid) + N
                    + 'set coop_loMvPN_s%d "exec ui/loadout/mvp%s_%d_s%d.cfg"' % (sl, tile, nxt, sl) + N)
            wr(UI + "mvp%s_%d_s%d.cfg" % (tile, k, sl), body)
print("per-slot exact-fid chains: %d cfgs" % sum((len(v[4]) + 1) * 4 for v in resolved))

# the table gains give->tile so the server can echo chain positions
p2 = MOD + "coop_mod/loadoutskins.scr"
t2, nl2 = rd(p2)
if "coop_skinMvTile" not in t2:
    add2 = ""
    for give, tile, elite, base_name, vlist in resolved:
        add2 += '	level.coop_skinMvTile["%s"] = "%s"' % (give, tile) + nl2
    assert t2.rstrip().endswith("}end")
    t2 = t2.rstrip()[:-4] + add2 + "}end" + nl2
    wr(p2, t2)
    print("loadoutskins: MvTile map")

# gen_loadout p-pages arm the four per-slot chain starts
g = io.open("docs/tools/gen_loadout.py", encoding="utf-8").read()
if "coop_loMvPN_s1" not in g:
    old = """    mv_pn = ("exec ui/loadout/mvp%s_1.cfg" % w["id"]) if w["id"] in MV_HOSTS else \"\""""
    old = old.replace("\\\"\\\"", '""')
    assert g.count(old) == 1, "mv_pn anchor"
    g = g.replace(old, """    mv_pn = ("vstr coop_loMvPN_s1") if w["id"] in MV_HOSTS else ""
    mv_pns = [("exec ui/loadout/mvp%s_1_s%d.cfg" % (w["id"], _sl)) if w["id"] in MV_HOSTS else ""
              for _sl in (1, 2, 3, 4)]""", 1)
    old2 = """        'set coop_loMvPN "%s"' % mv_pn,"""
    assert g.count(old2) == 1
    g = g.replace(old2, old2 + """
    ]
    L += ['set coop_loMvPN_s%d "%s"' % (_sl + 1, _v) for _sl, _v in enumerate(mv_pns)]
    L += [""", 1)
    io.open("docs/tools/gen_loadout.py", "w", encoding="utf-8", newline="\n").write(g)
    print("gen_loadout: per-slot chain arming")

# slot selectors point the live chain at their slot
for sl in (1, 2, 3, 4):
    fp = UI + "s%dsel.cfg" % sl
    ft, fnl = rd(fp)
    if "coop_loMvPN_s%d" % sl not in ft.split("coop_loMvPN_s%d " % sl)[0] or ('set coop_loMvPN "vstr coop_loMvPN_s%d"' % sl) not in ft:
        ft = ft.rstrip(fnl) + fnl + 'set coop_loMvPN "vstr coop_loMvPN_s%d"' % sl + fnl
        wr(fp, ft)
print("slot selectors bind the chain")

# --- 4. giveall: the 13 new variants -------------------------------------------------------------
p = MOD + "global/giveall.scr"
txt, nl = rd(p)
newtiks = ["mp44_mp44strap", "colt45_coltpa", "mp40_mp18", "enfield_p14", "springfield_m1903",
           "springfield_smlescope", "kar98_g98", "KAR98sniper_g98scope",
           "bar_bar1918", "colt45_colt1911w", "mauser_c96_c96trench", "thompsonsmg_m1a1dk", "colt45_covert", "colt45_drbond", "colt45_bloodyeic", "shotgun_authwinch", "bar_bar1918a", "bar_bar1918a1", "bar_bar1918a2",
           "thompsonsmg_tommy1928d", "thompsonsmg_tommy27a1"]
added = 0
anchor = "weapon weapons/m1_garand_pagarand.tik"
assert txt.count(anchor) == 1
add = anchor + nl
for t in newtiks:
    if ("weapons/%s.tik" % t) not in txt:
        add += "weapon weapons/%s.tik" % t + nl
        added += 1
txt = txt.replace(anchor + nl, add, 1)
wr(p, txt)
print("giveall: +%d variants" % added)
