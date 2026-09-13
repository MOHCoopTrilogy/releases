#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""check_mp_isolation.py - PROVE the multiplayer loadout cannot touch coop.

WHY THIS EXISTS
    The user, on approving the MP loadout build (2026-09-09): "I cannot stress this enough we need
    to make sure this does not in any way impact the coop mod or experience itself."

    A promise is not a safeguard. This is the safeguard: a mechanical test of the isolation contract
    that fails loudly the moment any of it is violated, so the guarantee survives the sessions that
    come after the one that made it.

THE CONTRACT, and why each clause is here rather than merely sensible

  1. NO COOP ENTRY POINT MAY REACH coop_mod/mp.scr.
     Coop maps enter through coop_mod/main.scr::main. MP maps will enter through
     coop_mod/mp.scr::main, hooked from global/ambient.scr. If main.scr, player.scr or any coop map
     script ever execs or threads mp.scr, the two frameworks are one framework and every other
     clause here is decoration.

  2. mp.scr MUST REFUSE TO RUN WHEN COOP IS LOADED.
     Belt and braces for clause 1. Even if the ambient.scr hook is wrong, mp.scr's first statement
     must bail on level.coop_mainScriptLoaded == 1. A guard that only exists at the call site is a
     guard that one future edit removes.

  3. THE ambient.scr HOOK MUST BE GATED.
     global/ambient.scr is exec'd by BOTH coop maps and stock MP maps - that is exactly why it was
     chosen as the hook. So the hook line itself must sit behind the coop test, or every coop map in
     the trilogy starts running the MP init at prespawn.

  4. MP MUST NEVER WRITE THE coop_health CVAR.
     Measured: server.scr:238 seeds level.coop_health from getcvar("coop_health") on every map, with
     a level.prevCoopHealth memo. So an MP cfg or script writing that CVAR does not stay in MP - the
     next coop map reads it back and every coop player spawns with MP health. The user asked for MP
     health 100 against coop's 750; the only safe way to deliver it is per-player at spawn.
     LEVEL vars reset per map and are safe; the CVAR is not.

  5. MP MUST NEVER WRITE coop_lockLoadout.
     server.scr:28 seeds it only when EMPTY. Once an MP map sets it to 0 it stays 0 for every coop
     map for the life of the server process - a genuine one-way latch, not a theoretical one. MP
     gets its own coop_mpLockLoadout.

  6. ui/coop_loadout.urc MUST BE BYTE-IDENTICAL TO HEAD.
     3,995 lines, and it CANNOT be regenerated: the generator its own line 1 credits
     (scratchpad/gen_loadout3.py) exists in no commit, branch or blob in this repo. A botched edit is
     recoverable only through `git show HEAD:`. The MP screen gets its own file, always.

  7. THE MP CVAR FAMILIES MUST NOT APPEAR IN COOP-ONLY SCRIPTS.
     coop_mpa* / coop_mpx* / coop_mpFreeKit / coop_mpLockLoadout belong to mp.scr, loadoutpick.scr's
     gated block, and the MP UI. Anywhere else means the projection has leaked.

  8. THE CHALLENGE SYSTEM STAYS COOP-ONLY IN MULTIPLAYER.
     mp.scr commits armory picks through loadout_set, whose unlock gate reaches challenges.scr via chal_ensure.
     chal_init must stop before its background loops (chal_pin_monitor re-seta's every client's saved Service
     Record pins every 3 s; autosave and the vehicle-kill monitor would let PvP write coop progression), and
     chal_ensure must stop after the unlock record and before the pin/medal writers. Both are
     `if( level.coop_mpRun == 1 ){ end }`, inert on every coop map because mp.scr refuses to run there.

  9. MP MUST NEVER SET flags["coop_isHost"].
     That flag unlocks dev godmode, noclip and give_all (developer.scr). MP detects the listen host itself.

 10. MP DOES NOT USE THE COOP ARMORY. (user 2026-09-13: MP gets its own Allied and Axis armories.)
     Committing MP picks through loadoutpick.scr::loadout_set wrote coop client state on every join - finish chips,
     padlocks, and Axis guns archived as unlocked in the coop armory. So mp.scr may not call into loadoutpick,
     challenges, xp, helmet, gloves or loadoutskins, may not stufftext anything naming a coop_lo cvar, and the old
     team-blind MP "free floor" (coop_mpFreeKit) may not come back anywhere in coop_mod.

USAGE
    python docs/tools/check_mp_isolation.py          # exit 1 on any violation
    python docs/tools/check_mp_isolation.py -v       # list what was checked and passed

Clauses whose subject does not exist yet (mp.scr, the ambient hook, the MP UI) report as PENDING
rather than passing, so this cannot quietly go green by testing nothing.
"""
import io
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
VERBOSE = "-v" in sys.argv or "--verbose" in sys.argv

fails = []
pending = []
passed = []


def read(rel):
    p = os.path.join(MOD, rel)
    if not os.path.exists(p):
        return None
    return io.open(p, "rb").read().decode("latin-1")


def strip_comments(txt):
    """Morpheus // and /* */ - so a rule is never satisfied or broken by a comment."""
    txt = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
    return re.sub(r"//[^\n]*", "", txt)


def fail(clause, msg):
    fails.append("[%s] %s" % (clause, msg))


def ok(clause, msg):
    passed.append("[%s] %s" % (clause, msg))


def pend(clause, msg):
    pending.append("[%s] %s" % (clause, msg))


# ---------------------------------------------------------------- 1. no coop entry point reaches mp.scr
COOP_ENTRIES = ["coop_mod/main.scr", "coop_mod/player.scr", "coop_mod/server.scr",
                "coop_mod/variables.scr", "coop_mod/itemhandler.scr"]
hit = []
for rel in COOP_ENTRIES:
    txt = read(rel)
    if txt is None:
        continue
    if re.search(r"coop_mod/mp\.scr", strip_comments(txt)):
        hit.append(rel)
if hit:
    fail("1", "coop entry point(s) reference coop_mod/mp.scr: " + ", ".join(hit))
else:
    ok("1", "no coop entry point references coop_mod/mp.scr")

# every coop-integrated map script too
mapdir = os.path.join(MOD, "maps")
maphits = []
if os.path.isdir(mapdir):
    for dirpath, _dirs, files in os.walk(mapdir):
        for f in files:
            if not f.endswith(".scr"):
                continue
            p = os.path.join(dirpath, f)
            try:
                txt = io.open(p, "rb").read().decode("latin-1")
            except Exception:
                continue
            body = strip_comments(txt)
            if "coop_mod/main.scr::main" in body and "coop_mod/mp.scr" in body:
                maphits.append(os.path.relpath(p, MOD))
if maphits:
    fail("1", "coop-integrated map script(s) also reference mp.scr: " + ", ".join(maphits[:5]))
else:
    ok("1", "no coop-integrated map script references mp.scr")

# ---------------------------------------------------------------- 2. mp.scr refuses to run under coop
mp = read("coop_mod/mp.scr")
if mp is None:
    pend("2", "coop_mod/mp.scr does not exist yet - the refusal guard cannot be checked")
else:
    body = strip_comments(mp)
    if re.search(r"level\.coop_mainScriptLoaded\s*==\s*1", body):
        ok("2", "mp.scr carries a coop_mainScriptLoaded refusal guard")
    else:
        fail("2", "mp.scr has NO refusal guard - it must bail on level.coop_mainScriptLoaded == 1")

# ---------------------------------------------------------------- 3. the ambient.scr hook is gated
amb = read("global/ambient.scr")
if amb is None:
    fail("3", "global/ambient.scr is missing from the mod tree")
else:
    body = strip_comments(amb)
    if "coop_mod/mp.scr" not in body:
        pend("3", "global/ambient.scr does not hook mp.scr yet")
    else:
        # the hook line must be preceded, in the same file, by the coop test
        idx = body.index("coop_mod/mp.scr")
        before = body[:idx]
        if re.search(r"level\.coop_mainScriptLoaded\s*!=\s*1", before):
            ok("3", "the ambient.scr mp hook is gated on coop_mainScriptLoaded != 1")
        else:
            fail("3", "the ambient.scr mp hook is NOT gated - every coop map would run MP init")

# ---------------------------------------------------------------- 4/5. forbidden cvar writes from MP files
MP_FILES = ["coop_mod/mp.scr", "coop_mod/cfg/mp_start.cfg", "coop_mod/cfg/mp_reset.cfg"]
# [bug-2564] every saved coop cvar MP could plausibly touch, not just the two that started this list. Each one
# written from an MP file would follow the player into coop.
FORBIDDEN = [("4", r'(?:set|seta|setcvar)\s*\(?\s*"?coop_health"?', "coop_health"),
             ("5", r'(?:set|seta|setcvar)\s*\(?\s*"?coop_lockLoadout"?', "coop_lockLoadout")]
for _cv in ("coop_prone", "coop_coverAuto", "coop_pickupOneMag", "coop_dmgFalloff", "coop_limp",
            "coop_adsSpeedMult", "coop_tinnitusBaseVol", "coop_sprintStamina", "coop_breathShareStamina"):
    FORBIDDEN.append(("4", r'(?:set|seta|setcvar)\s*\(?\s*"?' + _cv + r'\b', _cv))
checked_any = False
for rel in MP_FILES:
    txt = read(rel)
    if txt is None:
        continue
    checked_any = True
    body = strip_comments(txt)
    for clause, pat, name in FORBIDDEN:
        if re.search(pat, body, re.I):
            fail(clause, "%s writes the saved coop cvar %s - it would follow the player into coop"
                         % (rel, name))
if not checked_any:
    pend("4/5", "no MP script or cfg exists yet - the forbidden-cvar rules have nothing to check")
else:
    ok("4/5", "no MP file writes a saved coop cvar (%d guarded)" % len(FORBIDDEN))

# ---------------------------------------------------------------- 6. coop_loadout.urc is untouched
rel = "ui/coop_loadout.urc"
if read(rel) is None:
    fail("6", "ui/coop_loadout.urc is MISSING - it cannot be regenerated, recover it from git")
else:
    try:
        r = subprocess.run(["git", "diff", "--exit-code", "--quiet", "--", rel],
                           cwd=MOD, capture_output=True)
        if r.returncode == 0:
            ok("6", "ui/coop_loadout.urc is byte-identical to HEAD")
        else:
            fail("6", "ui/coop_loadout.urc IS MODIFIED. It cannot be regenerated - its generator "
                      "exists in no commit. Recover with: git show HEAD:%s" % rel)
    except Exception as e:
        pend("6", "could not run git to compare coop_loadout.urc (%s)" % e)

# ---------------------------------------------------------------- 7. MP cvars stay out of coop scripts
MP_CVAR = re.compile(r"coop_mp(?:a\d|x\d|FreeKit|LockLoadout)")
ALLOWED = {"coop_mod/mp.scr", "coop_mod/loadoutpick.scr"}
leaks = []
for dirpath, _dirs, files in os.walk(os.path.join(MOD, "coop_mod")):
    for f in files:
        if not f.endswith(".scr"):
            continue
        p = os.path.join(dirpath, f)
        rel = os.path.relpath(p, MOD).replace("\\", "/")
        if rel in ALLOWED:
            continue
        try:
            body = strip_comments(io.open(p, "rb").read().decode("latin-1"))
        except Exception:
            continue
        if MP_CVAR.search(body):
            leaks.append(rel)
if leaks:
    fail("7", "MP cvar families appear in coop-only script(s): " + ", ".join(leaks))
else:
    ok("7", "MP cvar families appear only in mp.scr and loadoutpick.scr's gated block")

# ---------------------------------------------------------------- 8. the challenge system stays coop-only
chal = read("coop_mod/challenges.scr")
if chal is None:
    fail("8", "coop_mod/challenges.scr is missing")
else:
    body = strip_comments(chal)
    guard = re.compile(r"if\(\s*level\.coop_mpRun\s*==\s*1\s*\)\s*\{\s*end\s*\}")
    for anchor, where in (("thread chal_autosave_loop", "chal_init before its background loops"),
                          ("waitthread chal_pin_load local.player", "chal_ensure before the pin/medal writers")):
        idx = body.find(anchor)
        if idx < 0:
            fail("8", "challenges.scr: anchor %r not found - re-check the MP guard in %s" % (anchor, where))
        elif not guard.search(body[max(0, idx - 200):idx]):
            fail("8", "challenges.scr has NO MP guard in %s - PvP would write coop progression" % where)
        else:
            ok("8", "challenges.scr MP guard present in %s" % where)

xpt = read("coop_mod/xp.scr")
if xpt is None:
    fail("8", "coop_mod/xp.scr is missing")
else:
    xbody = strip_comments(xpt)
    xidx = xbody.find("thread xp_autosave_loop")
    if xidx < 0:
        fail("8", "xp.scr: anchor thread xp_autosave_loop not found - re-check the MP guard in xp_init")
    elif not re.search(r"if\(\s*level\.coop_mpRun\s*==\s*1\s*\)\s*\{\s*end\s*\}", xbody[max(0, xidx - 200):xidx]):
        fail("8", "xp.scr has NO MP guard before the xp_init loops - PvP would write coop XP")
    else:
        ok("8", "xp.scr MP guard present in xp_init before its loops")

# ---------------------------------------------------------------- 9. MP never grants coop_isHost
if mp is None:
    pend("9", "coop_mod/mp.scr does not exist yet")
elif re.search(r'coop_isHost"\]\s*=', strip_comments(mp)):
    fail("9", "mp.scr assigns flags[\"coop_isHost\"] - that unlocks dev godmode, noclip and give_all")
else:
    ok("9", "mp.scr never assigns flags[\"coop_isHost\"]")

# ---------------------------------------------------------------- 10. MP does not use the coop armory
if mp is None:
    pend("10", "coop_mod/mp.scr does not exist yet")
else:
    mpc = strip_comments(mp)
    hits = re.findall(r"coop_mod/(loadoutpick|challenges|xp|helmet|gloves|loadoutskins)\.scr::\w+", mpc)
    if hits:
        fail("10", "mp.scr calls coop armory/progression code: " + ", ".join(sorted(set(hits))))
    else:
        ok("10", "mp.scr calls no coop armory, challenge, xp or cosmetic code")
    if re.search(r'stufftext[^\n]*coop_lo', mpc, re.I):
        fail("10", "mp.scr stufftexts a coop_lo cvar - that is coop loadout state on the client")
    else:
        ok("10", "mp.scr stufftexts no coop_lo cvar")
floor = []
for dirpath, _dirs, files in os.walk(os.path.join(MOD, "coop_mod")):
    for f in files:
        if f.endswith(".scr"):
            p = os.path.join(dirpath, f)
            if "coop_mpFreeKit" in strip_comments(io.open(p, "rb").read().decode("latin-1")):
                floor.append(os.path.relpath(p, MOD).replace("\\", "/"))
if floor:
    fail("10", "the team-blind MP free floor is back: coop_mpFreeKit in " + ", ".join(floor))
else:
    ok("10", "no MP free floor (coop_mpFreeKit) anywhere in coop_mod")

# ---------------------------------------------------------------- report
print("MP/coop isolation contract")
print("=" * 74)
if VERBOSE:
    for line in passed:
        print("  PASS    " + line)
for line in pending:
    print("  PENDING " + line)
for line in fails:
    print("  FAIL    " + line)
print("-" * 74)
print("%d passed, %d pending, %d FAILED" % (len(passed), len(pending), len(fails)))
if fails:
    print("\nThe MP loadout must not be able to change the coop experience. Fix the above.")
    sys.exit(1)
sys.exit(0)
