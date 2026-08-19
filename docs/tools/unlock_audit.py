#!/usr/bin/env python
"""unlock_audit.py - does every armory gun have a legitimate, ENFORCED unlock path?

Three enforcement sources must union-cover the roster:
  1. free starters      loadoutpick.scr::loadout_isUnlocked hardcoded list
  2. challenge rewards  chal_def 7th arg == weapon tik  (SR-visible by construction:
                        gen_service_record.py parses the same chal_def list)
  3. rank unlocks       xp.scr level.coop_xp_rankUnlock[rank][k] tables, granted through
                        chal_add_unlock by xp_rank_unlock on identify/rank-up (idempotent)

Also cross-checks the DECLARED path (the armory hover's req1/req2 text in
loadout_weapons.tsv) against the enforced source - a gun that SAYS "Rank: Corporal" but is
actually only challenge-unlocked (or vice versa, or nothing) is UI drift.

Exit 1 on any orphan (no enforced path at all).
"""
import re, io, os, sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
MOD  = os.path.join(ROOT, "hzm-mohaa-coop-mod")

# ---- 1. roster (19 tab-separated cols: id tik give xfm charanim cls tab name cd b0..b3 clip clipn recoil slots req1 req2)
roster = []
for ln in io.open(os.path.join(ROOT, "docs", "tools", "loadout_weapons.tsv"), encoding="utf-8"):
    if not ln.strip() or ln.lstrip().startswith("#"):
        continue
    c = ln.rstrip("\n").split("\t")
    if len(c) < 8 or not c[0].isdigit():
        continue
    req = " ".join(x for x in c[17:19] if len(c) > 17 and x).strip()
    # empty give means "give the tik itself" (the newest imports use this)
    roster.append({"id": c[0], "give": (c[2] or c[1]).lower(), "name": c[7], "req": req})

# ---- 2. challenge rewards
chal = io.open(os.path.join(MOD, "coop_mod", "challenges.scr"), encoding="latin-1").read()
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
sys.exit(1 if orphans else 0)
