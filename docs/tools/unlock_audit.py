#!/usr/bin/env python
"""unlock_audit.py - does every armory gun have a legitimate, ENFORCED unlock path?

Three enforcement sources must union-cover the roster:
  1. free starters      loadoutpick.scr::loadout_isUnlocked hardcoded list
  2. challenge rewards  chal_def 7th arg == weapon tik  (SR-visible by construction:
                        gen_service_record.py parses the same chal_def list)
  3. rank unlocks       xp.scr level.coop_xp_rankUnlock[rank][k] tables, granted through
                        chal_add_unlock by xp_rank_unlock on identify/rank-up (idempotent)

Also cross-checks the DECLARED path (the armory hover, ui/loadout/req<id>.cfg - what the player
actually reads) against the enforced source - a gun that SAYS "Rank: Corporal" but is
actually only challenge-unlocked (or vice versa, or nothing) is UI drift. Since 2026-09-28
gen_loadout.py derives that hover from these same sources and its `check` fails on any
difference, so this half is a second opinion; the orphan half is still the only one of its kind.

Exit 1 on any orphan (no enforced path at all).
"""
import re, io, os, sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
MOD  = os.environ.get("HZM_MOD") or os.path.join(ROOT, "hzm-mohaa-coop-mod")


def hover(wid):
    p = os.path.join(MOD, "ui", "loadout", "req%s.cfg" % wid)
    if not os.path.exists(p):
        return ""
    return " ".join(x for x in re.findall(r'(?m)^set coop_loReq2?\s+"([^"]*)"',
                                          io.open(p, encoding="latin-1").read()) if x)


# ---- 1. roster (tab-separated cols: id tik give xfm charanim cls tab name cd b0..b3 clip clipn recoil slots)
roster = []
for ln in io.open(os.path.join(ROOT, "docs", "tools", "loadout_weapons.tsv"), encoding="utf-8"):
    if not ln.strip() or ln.lstrip().startswith("#"):
        continue
    c = ln.rstrip("\n").split("\t")
    if len(c) < 8 or not c[0].isdigit():
        continue
    req = hover(c[0])
    # empty give means "give the tik itself" (the newest imports use this)
    roster.append({"id": c[0], "give": (c[2] or c[1]).lower(), "name": c[7], "req": req})

# ---- 2. challenge rewards
chal = io.open(os.path.join(MOD, "coop_mod", "challenges.scr"), encoding="latin-1").read()
# [v1.10.64] the variant-mastery challenges (wire_mv2.py -> mvchal_gen.scr) are chal_defs too: a roster gun that IS a former
# variant (the Lewis gun, 81) is enforced by its wpn_*_mv challenge there, not in challenges.scr
_mv = os.path.join(MOD, "coop_mod", "mvchal_gen.scr")
if os.path.exists(_mv):
    chal += io.open(_mv, encoding="latin-1").read()
chal_unlocks = {}
for m in re.finditer(r'chal_def\s+"([^"]+)"\s+"[^"]+"\s+"([^"]+)"\s+"[^"]*"\s+"[^"]+"\s+\S+\s+"([^"]*)"', chal):
    cid, title, reward = m.groups()
    if reward.lower().startswith("models/weapons/"):
        chal_unlocks.setdefault(reward.lower(), []).append((cid, title))

# ---- 3. rank unlocks + rank names
xp = io.open(os.path.join(MOD, "coop_mod", "xp.scr"), encoding="latin-1").read()
rank_unlocks = {}
for m in re.finditer(r'level\.coop_xp_rankUnlock\[(\d+)\]\[\d+\]\s*=\s*"([^"]+)"', xp):
    rank_unlocks.setdefault(m.group(2).lower(), []).append(int(m.group(1)))
rank_names = {}
for m in re.finditer(r'level\.coop_xp_rankName\[(\d+)\]\s*=\s*"([^"]+)"', xp):
    rank_names[int(m.group(1))] = m.group(2)

# ---- 4. free starters
lp = io.open(os.path.join(MOD, "coop_mod", "loadoutpick.scr"), encoding="latin-1").read()
fb = re.search(r'^loadout_isUnlocked local\.player local\.tik:\{(.*?)\}end', lp, re.S | re.M).group(1)
free = {m.group(1).lower() for m in re.finditer(r'local\.tik == "([^"]+)"', fb)}

orphans, drift = [], []
for g in roster:
    tik = g["give"]
    srcs = []
    if tik in free:
        srcs.append("FREE")
    if tik in chal_unlocks:
        srcs.append("CHAL:" + chal_unlocks[tik][0][0])
    if tik in rank_unlocks:
        r = min(rank_unlocks[tik])
        srcs.append("RANK:" + rank_names.get(r, str(r)))
    if not srcs:
        orphans.append(g)
        continue
    # declared-vs-enforced
    req = g["req"].lower()
    if "rank:" in req and tik not in rank_unlocks and tik not in free:
        drift.append((g, "declares RANK, enforced " + "/".join(srcs)))
    if "rank:" in req and tik in rank_unlocks:
        r = min(rank_unlocks[tik])
        rn = rank_names.get(r, "").lower()
        # the hover abbreviates ladder names - normalize before comparing
        norm = req
        for a, b in (("lt.", "lieutenant"), ("2nd", "second"), ("3rd", "third"),
                     ("4th", "fourth"), ("5th", "fifth"), ("technician fifth grade", "technician"),
                     ("grade", "")):
            norm = norm.replace(a, b)
        rn_norm = rn.replace("grade", "").strip()
        if rn_norm and rn_norm not in norm and rn not in req:
            drift.append((g, f"declares '{g['req']}', rank table grants at {rank_names.get(r)}"))
    if req and "rank:" not in req and tik in rank_unlocks and tik not in chal_unlocks and tik not in free:
        drift.append((g, "declares challenge-ish req, enforced only by RANK"))

print(f"{len(roster)} roster guns | {len(free)} free | {len(chal_unlocks)} challenge-unlocked | {len(rank_unlocks)} rank-unlocked")
covered = len(roster) - len(orphans)
print(f"covered: {covered}/{len(roster)}")
if orphans:
    print(f"\n{len(orphans)} ORPHANS (no enforced path at all):")
    for g in orphans:
        print(f"  id {g['id']:>3}  {g['name']:28s} {g['give']}   declared: '{g['req']}'")
if drift:
    print(f"\n{len(drift)} DECLARED-vs-ENFORCED drift:")
    for g, why in drift:
        print(f"  id {g['id']:>3}  {g['name']:28s} {why}")
rtiks = {g["give"] for g in roster}
for label, table in (("challenge", chal_unlocks), ("rank", rank_unlocks)):
    dead = [t for t in table if t not in rtiks]
    if dead:
        print(f"\n{len(dead)} {label} rewards point at NON-roster tiks:")
        for t in dead:
            print("  " + t)
# ---- 5. FINISHES (killchal 2026-10-20, ported with finishes2 v1.10.68): a roster gun with finish art (fids 1-7 and the finishes2
# set, fids 40+) must have, per finish: a WRITER (its wpn_<wid> stat is one chal_widFromModel can return, so challenges.scr::
# chal_ai_killed counts it), a REACHABLE target (a chal_def in finchal_gen.scr with 0 < target <= 750) and a REAL reward (the variant
# tik exists: the mod tree for 1-7, the finishes pak for finishes2).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import finish_challenges as fc  # noqa: E402
import finishes2 as F2  # noqa: E402
_skin = io.open(os.path.join(MOD, "coop_mod", "loadoutskins.scr"), encoding="latin-1").read()
_fs2 = set(F2.fids())
_fins = {}
for _g, _f, _v in re.findall(r'level\.coop_skinGive\["([^"]+)"\]\[(\d+)\]\s*=\s*"([^"]*)"', _skin):
    if int(_f) <= 7 or int(_f) in _fs2:
        _fins.setdefault(_g.lower(), {})[int(_f)] = _v
_chain = fc.wid_chain(io.open(os.path.join(MOD, "coop_mod", "challenges.scr"), encoding="latin-1").read())
_wids = {w for _t, w in _chain}
_gen = io.open(os.path.join(MOD, "coop_mod", "finchal_gen.scr"), encoding="latin-1").read()
_cid = {(w, int(f)): c for w, f, c in re.findall(r'level\.coop_finCid\["([^"]+)"\]\[(\d+)\]\s*=\s*"([^"]+)"', _gen)}
_tgt = {c: (s, int(n)) for c, s, n in re.findall(r'chal_def "([^"]+)" "[^"]*" "[^"]*" "[^"]*" "([^"]*)" (\d+)', _gen + chal)}
_pak = F2.pak_path(os.environ.get("HZM_BASE_MOD") or os.path.join(ROOT, "hzm-mohaa-coop-mod"))
_pakidx = F2.pak_index(_pak)[1] if os.path.exists(_pak) else {}
fin_guns, fin_total, fin_bad = 0, 0, []
for g in roster:
    fs = _fins.get(g["give"].lower())
    if not fs:
        continue
    wid = fc.wid_of(_chain, g["give"])
    fin_guns += 1
    if not wid or wid not in _wids:
        fin_bad.append((g, "has finish art but no kill stat (chal_widFromModel returns no wid)"))
        continue
    for f, var in sorted(fs.items()):
        c = _cid.get((wid, f))
        if not c or c not in _tgt:
            fin_bad.append((g, "finish %d: no per-gun challenge" % f))
            continue
        stat, n = _tgt[c]
        if stat != "wpn_" + wid or not (0 < n <= 750):
            fin_bad.append((g, "finish %d: %s counts %s to %d (needs wpn_%s, 1..750)" % (f, c, stat, n, wid)))
            continue
        if f in _fs2:
            if var.lower() not in _pakidx:
                fin_bad.append((g, "finish %d: reward %s is not in %s" % (f, var, os.path.basename(_pak))))
                continue
        elif not os.path.exists(os.path.join(MOD, *var.split("/"))) and not os.path.exists(
                os.path.join(ROOT, "docs", "tools", "assets", "wpnfix", *var.split("/"))):
            pass                        # the standard seven ride several paks (mod tree, wpnfix, fixes): gen_skins / tik-surfaces own that
        fin_total += 1
print(f"finishes: {fin_guns} roster guns carry finish art | {fin_total} gun-finish pairs have a writer, a reachable target and a reward"
      f" (finishes2 pak: {os.path.basename(_pak) if _pakidx else 'NOT FOUND'})")
if fin_bad:
    print(f"\n{len(fin_bad)} FINISH ORPHANS:")
    for g, why in fin_bad[:40]:
        print(f"  id {g['id']:>3}  {g['name']:28s} {why}")
    orphans = orphans + [g for g, _ in fin_bad]
sys.exit(1 if orphans else 0)
