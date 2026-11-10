"""Emit one challenge per (GUN, FINISH) on a per-gun kill ladder - the coop half of the per-gun finish unlocks.

WHY THIS EXISTS (user 2026-10-19): weapon FINISHES (gold, chrome, blued, bloody, woodland, winter, desert) used to
unlock ACCOUNT-WIDE from one global challenge each (fin_gold = 250 kills with anything, fin_blued = 150 headshots ...)
plus "master this gun" (the gun's base wpn_ challenge). So one challenge handed you gold on every gun you had mastered.
The ask: every gun earns its own finishes with kills WITH THAT GUN, starting at 25 and climbing per tier.

It follows variant_challenges.py (the per-gun MODEL-variant ladder) exactly: same chal_def, same per-gun kill stat
(wpn_<wid>, written by challenges.scr::chal_ai_killed), so NO new stat writer exists - only new thresholds on stats
that are already counted. Variants (fid 8+) keep their own accelerating curve and sit AFTER the finishes (a variant
starts at 3x the gun's base target, a finish at 25).

THE LADDER (7 finishes per gun, easy -> hard; the order is the prestige order, GOLD last):
    standard   BLUED 25 / WOODLAND 50 / WINTER 100 / DESERT 175 / CHROME 250 / BLOODY 350 / GOLD 500
    slow       launchers (base target <= 15 kills): 25 / 40 / 60 / 90 / 125 / 175 / 250
The Thompson keeps its existing GOLD challenge (wpn_thompson_gold, 250 kills): its ladder is
BLUED 25 / WOODLAND 50 / WINTER 100 / DESERT 175 / GOLD 250 (existing cid) / CHROME 350 / BLOODY 500.

[v1.10.68 finishes2] The SECOND finish set (fids 40+: paint / camo coats, Airborne 101st and the layered finishes) extends the same
per-gun ladder: its rungs are in docs/tools/finishes2.tsv (rung / slow), interleaved between the seven above so the ladder keeps
climbing evenly to the 750 cap (standard: 75 BATTLE-WORN, 125 AIRBORNE ... 750 PARADE). Same stat, same chal_def, cid
fin_<wid>_<key>; a gun gets a rung only for a finish it really has (coop_skinGive[give][fid] in loadoutskins.scr).

ONE SET PER WID, not per tik: g43 + coop_g43_irons, fg42 + coop_fg42_irons, shotgun + coop_dbshotgun, kar98 +
kar98_mortar all resolve to the same wid through challenges.scr::chal_widFromModel (parsed from the script here, so
this generator can never disagree with the kill-stat writer about which gun a model is).

Rebuild:  python docs/tools/finish_challenges.py --emit        (writes coop_mod/finchal_gen.scr)
Check:    python docs/tools/finish_challenges.py --check       (regenerate in memory + byte-compare; exit 1 = drift)
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.environ.get("HZM_MOD") or os.path.join(ROOT, "hzm-mohaa-coop-mod")
SKINS = os.path.join(MOD, "coop_mod", "loadoutskins.scr")
CHALS = os.path.join(MOD, "coop_mod", "challenges.scr")
OUT = os.path.join(MOD, "coop_mod", "finchal_gen.scr")
ROSTER_TSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loadout_weapons.tsv")

# fid -> (key used in the cid, SR/chip label). Same numbering as loadoutskins.scr coop_skinFinStat / the armory strip.
FINISHES = {1: ("gold", "GOLD"), 2: ("chrome", "CHROME"), 3: ("blued", "BLUED"), 4: ("bloody", "BLOODY"),
            5: ("woodland", "WOODLAND"), 6: ("winter", "WINTER"), 7: ("desert", "DESERT")}
ORDER = [3, 5, 6, 7, 2, 4, 1]                       # easy -> hard
ORDER_THOMPSON = [3, 5, 6, 7, 1, 2, 4]              # gold sits at the existing 250
LADDER = [25, 50, 100, 175, 250, 350, 500]
LADDER_SLOW = [25, 40, 60, 90, 125, 175, 250]
SLOW_BASE = 15                                      # a gun whose own base challenge asks <= this many kills (bazooka, schreck, PIAT)
# wid -> an EXISTING challenge that already is this gun's finish challenge (not generated twice)
EXISTING = {("thompson", 1): "wpn_thompson_gold"}
# wids with no base wpn_ challenge to read a display name from
GUN_NAME = {"fg42": "FG 42", "carbine": "M1 Carbine", "lewis": "Lewis Gun",   # [v1.10.65 camo] + two stats with no base challenge
            "bren": "Bren", "mp28": "MP 28", "panzerfaust": "Panzerfaust"}    # [newguns 2026-11-09] no base wpn_ challenge either
SLOW_WIDS = {"panzerfaust"}                         # [newguns] single-shot launcher: the rocket ladder
# [v1.10.68 finishes2] the second set, from the shared table (fid -> key, label; its own rungs)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import finishes2 as _F2  # noqa: E402
FS2 = {r["fid"]: r for r in _F2.table()}
for _f, _r in FS2.items():
    FINISHES[_f] = (_r["key"], _r["name"])


def read(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def wid_chain(chal_src):
    """[(token, wid)] in the order chal_widFromModel tests them (first match wins)."""
    m = re.search(r"(?ms)^chal_widFromModel local\.m:\{(.*?)^\}end", chal_src)
    assert m, "chal_widFromModel not found in challenges.scr"
    return re.findall(r'containsText local\.m "([^"]+)" 0 \)\s*\)?\s*\{ local\.wid = "([^"]+)" \}', m.group(1))


def wid_of(chain, model):
    m = model.lower()
    for tok, wid in chain:
        if tok.lower() in m:
            return wid
    return ""


def load():
    skins = read(SKINS)
    chal = read(CHALS)
    chain = wid_chain(chal)
    assert len(chain) > 40, "wid chain parse found only %d tokens" % len(chain)
    give = re.findall(r'level\.coop_skinGive\["([^"]+)"\]\[(\d+)\]\s*=\s*"([^"]+)"', skins)
    fins = {}
    for g, f, p in give:
        if int(f) <= 7 or int(f) in FS2:
            fins.setdefault(g, set()).add(int(f))
    base = {}
    for cid, desc, stat, tgt in re.findall(
            r'chal_def\s+"(wpn_[^"]+)"\s+"[^"]*"\s+"[^"]*"\s+"([^"]*)"\s+"([^"]*)"\s+(\d+)\s+"[^"]*"', chal):
        base[cid] = (desc, stat, int(tgt))
    wids = {}
    for g in sorted(fins):
        w = wid_of(chain, g)
        if not w:
            continue                        # binoculars / mine detectors / smoke / dbno pistol: no kill stat, not a gun
        e = wids.setdefault(w, {"wid": w, "guns": [], "fids": set()})
        e["guns"].append(g)
        e["fids"] |= fins[g]
    rows = []
    for w in sorted(wids):
        e = wids[w]
        b = base.get("wpn_" + w)
        btgt = b[2] if b else 50
        name = GUN_NAME.get(w)
        if not name and b:
            mm = re.search(r"kills with the (.+)$", b[0])
            name = mm.group(1).strip() if mm else None
        if not name:
            name = w.replace("_", " ").title()
        name = name.replace('"', "'")
        ladder = LADDER_SLOW if (btgt <= SLOW_BASE or w in SLOW_WIDS) else LADDER
        order = ORDER_THOMPSON if w == "thompson" else ORDER
        tiers = {}
        for fid, tgt in zip(order, ladder):
            if fid in e["fids"]:
                tiers[fid] = tgt
        for fid, r2 in FS2.items():                 # [v1.10.68 finishes2] interleaved rungs (finishes2.tsv)
            if fid in e["fids"]:
                tiers[fid] = r2["slow"] if btgt <= SLOW_BASE else r2["rung"]
        rows.append({"wid": w, "name": name, "stat": "wpn_" + w, "btgt": btgt, "guns": sorted(e["guns"]), "tiers": tiers})
    return rows, chain


def cid_for(wid, fid):
    return EXISTING.get((wid, fid)) or "fin_%s_%s" % (wid, FINISHES[fid][0])


def emit(rows):
    L = []
    L.append("//=========================================================================")
    L.append("// GENERATED by docs/tools/finish_challenges.py --emit   DO NOT EDIT BY HAND")
    L.append("//=========================================================================")
    L.append("// One challenge per (GUN, FINISH): kills WITH THAT GUN unlock that finish for that gun.")
    L.append("// Rides each gun's EXISTING kill stat (wpn_<wid>, challenges.scr::chal_ai_killed), so no")
    L.append("// new stat writer exists. loadoutpick.scr::loadout_finOpen reads level.coop_finCid.")
    L.append("//=========================================================================")
    L.append("")
    L.append("main:{")
    L.append("\tif( level.coop_finChalBuilt == 1 ){ end }")
    L.append("\tlevel.coop_finChalBuilt = 1")
    L.append("")
    for r in rows:
        L.append("\t//---- %s (%s) ----" % (r["name"], r["wid"]))
        L.append('\tlevel.coop_finGunName["%s"] = "%s"' % (r["wid"], r["name"]))
        for fid in sorted(r["tiers"], key=lambda f: (f in FS2, r["tiers"][f])):
            tgt = r["tiers"][fid]
            cid = cid_for(r["wid"], fid)
            key, lab = FINISHES[fid]
            L.append('\tlevel.coop_finCid["%s"][%d] = "%s"' % (r["wid"], fid, cid))
            if (r["wid"], fid) in EXISTING:
                continue
            title = ("%s %s" % (r["name"], lab.title()))[:46]
            desc = ("Get %d kills with the %s to unlock the %s finish" % (tgt, r["name"], lab))[:118]
            L.append('\twaitthread coop_mod/challenges.scr::chal_def "%s" "finishes" "%s" "%s" "%s" %d ""'
                     % (cid, title, desc, r["stat"], tgt))
            L.append('\tlevel.coop_finIs["%s"] = 1' % cid)
        L.append("")
    L.append("}end")
    L.append("")
    return "\n".join(L)


def build_text():
    rows, _ = load()
    txt = emit(rows)
    bad = [c for c in txt if ord(c) > 127]
    assert not bad, "non-ASCII in generated .scr is a parse killer: %r" % bad[:5]
    return rows, txt


def main():
    rows, txt = build_text()
    n_ch = sum(1 for r in rows for f in r["tiers"] if (r["wid"], f) not in EXISTING)
    print("finish ladders: %d guns (wids), %d finishes, %d new challenges (+%d existing reused)"
          % (len(rows), sum(len(r["tiers"]) for r in rows), n_ch, len(EXISTING)))
    data = txt.replace("\n", "\r\n").encode("ascii")
    if "--emit" in sys.argv:
        io.open(OUT, "wb").write(data)
        print("wrote %s" % OUT)
        return 0
    if "--check" in sys.argv:
        cur = io.open(OUT, "rb").read() if os.path.exists(OUT) else b""
        if cur != data:
            print("DRIFT - run: python docs/tools/finish_challenges.py --emit")
            return 1
        print("EXACT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
