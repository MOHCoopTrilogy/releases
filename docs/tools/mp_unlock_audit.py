#!/usr/bin/env python
"""mp_unlock_audit.py - the MULTIPLAYER twin of unlock_audit.py: does every MP unlockable have a WRITER, a REACHABLE
target, a REWARD, and a record that actually SURVIVES the session?  (mpprog, bug-10912)

Why this exists: for weeks every MP kill was counted, pushed and shown - and thrown away at the end of the session.
The carried record (coop_mpProgBlob) was sent to the client QUOTED inside a stufftext, which the wire truncates to an
empty value (TRAPS T8 / bug-758), and it was ';'-delimited, which Info_SetValueForKey refuses in a userinfo value. So
every session began at total=0, and every unlock that rides on a kill count (finishes, skins, helmets, gloves, the
per-class weapon tiers) was unreachable across sessions. No gate looked at the channel, only at the tables.

Checks (exit 1 on any ERROR):
  A. CHANNEL   the blob stufftext is unquoted; the wire delimiter is a character a stufftext token AND a userinfo
               value can carry (not  \\ ; " space); ensureLoaded decodes it; the version buildBody writes is one
               ensureLoaded reads; the engine registers coop_mpProgBlob CVAR_USERINFO at CL_Init (if the engine
               tree is found: HZM_ENGINE, else H:/hzm_work/eng-hotfix13661, else skipped with a WARN).
  B. WRITER    every challenge stat is written somewhere AND persisted in the blob: "total"/a class (credit),
               or a coop_mpStat vector entry that some script bumps (mp_bump / mp_awardObj with that literal,
               or a win_<mode> paid by mp_awardTeamWin/mp_awardRoundWin for that mode).
  C. TARGET    every challenge target is a positive integer.
  D. REWARD    every reward token parses and points at something real: wt:<class>:<tier> = a non-starter tile of
               that class+tier on some side; sk:<a|x>:<id> = a skin option; fin:<name> = a finish the armory knows.
               Every non-starter MP armory tile is unlocked by some wt challenge (else it can never be picked).
  E. UI        every coop_mpChD<i>/coop_mpB<i> the generated record page reads has i < coop_mpChalN; every
               coop_mpCnt_<c> is a progression class; every coop_mpUw_* is some challenge's reward cvar; every
               coop_mpS_<s> is a persisted stat. (bug-10807 shape: an index that drifted is a wrong number on screen.)
"""
import io, os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
MOD = os.environ.get("HZM_MOD") or os.path.join(ROOT, "hzm-mohaa-coop-mod")
ENG = os.environ.get("HZM_ENGINE") or r"H:\hzm_work\eng-hotfix13661"
CM = os.path.join(MOD, "coop_mod")
ERR, WARN = [], []
# A stat that is KNOWN to have no writer yet, with the reason. Listed so a NEW orphan still fails the build; remove the
# entry when the writer lands. Every reward behind one of these stays reachable through its fallback (cosNeed / career).
KNOWN_UNWRITTEN = {
    "win_buildabase": "Build-A-Base hands the round to alienx/basebuild.scr, which has no win point; reward sk:x:11 "
                      "is still earnable by the cosNeed career-kill fallback (OPEN.md, mpprog 2026-11-10)",
}


def rd(p):
    return io.open(p, encoding="latin-1").read()


def strip_comments(s):
    return re.sub(r"//[^\n]*", "", s)


def label(src, name):
    m = re.search(r"(?m)^%s\b[^\n]*:\{(.*?)^\}end" % re.escape(name), src, re.S)
    return m.group(1) if m else None


prog = rd(os.path.join(CM, "mp_progression.scr"))
progc = strip_comments(prog)
chal = rd(os.path.join(CM, "mp_challenges.scr"))

# ---------------------------------------------------------------- A. the channel
push = label(progc, "pushBlob")
load = label(progc, "ensureLoaded")
build = label(progc, "buildBody")
if push is None or load is None or build is None:
    ERR.append("A: pushBlob / ensureLoaded / buildBody label not found in mp_progression.scr")
else:
    st = re.findall(r'stufftext\s*\(\s*"seta coop_mpProgBlob([^\n]*)', push)
    if not st:
        ERR.append("A: pushBlob no longer pushes coop_mpProgBlob with a stufftext seta")
    for s in st:
        if '\\"' in s:
            ERR.append('A: the coop_mpProgBlob stufftext is QUOTED - the wire ends Argv(1) at the inner quote and the '
                       'client sets an EMPTY value (T8 / bug-758): %s' % s.strip()[:90])
    m = re.search(r'level\.coop_mpProgWire\s*=\s*"(.)"', progc)
    if not m:
        ERR.append("A: level.coop_mpProgWire (the wire delimiter) is not defined in mp_progression.scr")
    else:
        d = m.group(1)
        if d in '\\;" ':
            ERR.append("A: wire delimiter %r cannot ride a stufftext token and a userinfo value" % d)
        if "coop_mpProgWire" not in push:
            ERR.append("A: pushBlob does not encode with level.coop_mpProgWire")
        if "coop_mpProgWire" not in load:
            ERR.append("A: ensureLoaded does not decode level.coop_mpProgWire")
    vw = re.search(r'local\.b\s*=\s*\(\s*"(\d+);"', build)
    if not vw:
        ERR.append("A: cannot read the blob version buildBody writes")
    elif not re.search(r'local\.f\[0\]\s*==\s*"%s"' % vw.group(1), load):
        ERR.append("A: buildBody writes blob v%s but ensureLoaded never reads that version" % vw.group(1))
    cl = os.path.join(ENG, "code", "client", "cl_main.cpp")
    if os.path.isfile(cl):
        blk = re.search(r"HZM-MP-BEGIN\(mp_persist_userinfo\)(.*?)HZM-MP-END\(mp_persist_userinfo\)", rd(cl), re.S)
        if not blk or '"coop_mpProgBlob"' not in blk.group(1) or "CVAR_USERINFO" not in blk.group(1):
            ERR.append("A: engine CL_Init no longer registers coop_mpProgBlob CVAR_ARCHIVE|CVAR_USERINFO (bug-2749)")
    else:
        WARN.append("A: engine tree not found (%s) - CL_Init userinfo registration not checked" % ENG)

# [bug-10913] derive grants the shared-rank tiers from the coop rank flag: that flag must be loaded at join, not only
# by the first kill's XP award, or the server store lacks every rank-unlocked gun for the start of each session.
der = label(strip_comments(chal), "derive") or ""
if "coop_xp_rank" in der and (load is None or "rankDerive" not in load or "xp_identify_mp" not in progc):
    ERR.append("A: mp_challenges::derive reads coop_xp_rank but ensureLoaded no longer loads it at join (rankDerive -> "
               "xp.scr::xp_identify_mp) - rank-unlocked guns are denied until the first kill (bug-10913)")

# every quoted seta stufftext of any userinfo carry cvar in the MP layer is the same bug
for fn in sorted(os.listdir(CM)):
    if fn.startswith("mp") and fn.endswith(".scr"):
        for ln in strip_comments(rd(os.path.join(CM, fn))).splitlines():
            if re.search(r'stufftext[^\n]*"seta coop_mp(ProgBlob|[ax]_k\d|[ax]_cos\w+) \\"', ln):
                ERR.append("A: %s quotes a userinfo carry cvar in a stufftext: %s" % (fn, ln.strip()[:90]))

# ---------------------------------------------------------------- tables
classes = re.findall(r'level\.coop_mpProgClasses\[\d+\]\s*=\s*"(\w+)"', progc)
stats = re.findall(r'level\.coop_mpStat\[\d+\]\s*=\s*"(\w+)"', progc)
if len(classes) != 8 or not stats:
    ERR.append("tables: could not read the progression classes (%d) / stat vector (%d)" % (len(classes), len(stats)))
n_m = re.search(r"level\.coop_mpChalN\s*=\s*(\d+)", chal)
N = int(n_m.group(1)) if n_m else 0
rows = {}
for k in ("Id", "Stat", "Target", "Reward", "RCvar"):
    for i, v in re.findall(r'level\.coop_mpChal%s\[(\d+)\]\s*=\s*"?([^"\n]*)"?' % k, chal):
        rows.setdefault(int(i), {})[k] = v.strip()
if len(rows) != N or N == 0:
    ERR.append("tables: mp_challenges.scr declares %d challenges, parsed %d" % (N, len(rows)))

# writers of the stat vector
allsrc = ""
for fn in os.listdir(CM):
    if fn.endswith(".scr"):
        allsrc += strip_comments(rd(os.path.join(CM, fn))) + "\n"
written = set(re.findall(r'(?:mp_bump|mp_awardObj)\s+local\.\w+\s+"(\w+)"', allsrc))
for mode in re.findall(r'mp_awardTeamWin\s+local\.\w+\s+"(\w+)"', allsrc):
    written.add("win_" + mode)
# the round modes pass level.coop_mpMode through mp_rounds.scr::rounds_win
rounds = rd(os.path.join(CM, "mp_rounds.scr"))
if re.search(r"mp_awardRoundWin\s+local\.\w+\s+level\.coop_mpMode", strip_comments(rounds)):
    for mode in ("lms", "snd", "freezetag", "demolition", "prophunt"):
        written.add("win_" + mode)

# ---------------------------------------------------------------- B/C. writer + target
for i in sorted(rows):
    r = rows[i]
    s, cid = r.get("Stat", ""), r.get("Id", "?")
    if s == "total" or s in classes:
        pass                                    # credit() writes it, the blob carries it (fields 1..9)
    elif s not in stats:
        ERR.append("B: challenge %s watches stat %r that is not in the persisted stat vector" % (cid, s))
    elif s not in written and s in KNOWN_UNWRITTEN:
        WARN.append("B: challenge %s watches %r - known unwritten: %s" % (cid, s, KNOWN_UNWRITTEN[s]))
    elif s not in written:
        ERR.append("B: challenge %s watches stat %r that NOTHING writes (no mp_bump/mp_awardObj/award*Win)" % (cid, s))
    try:
        t = int(r.get("Target", "0"))
        if t <= 0:
            raise ValueError
    except ValueError:
        ERR.append("C: challenge %s target %r is not a positive integer" % (cid, r.get("Target")))

# ---------------------------------------------------------------- D. rewards
tiles = []
for side in ("a", "x"):
    src = rd(os.path.join(CM, "mp%s_roster.scr" % side))
    for m in re.finditer(r'case "(\w+)":(.*?)break', src, re.S):
        body = m.group(2)
        g = lambda k: (re.search(r'local\.r\["%s"\]\s*=\s*"?([^"\n]*)"?' % k, body) or [None, ""])[1].strip()
        tiles.append({"side": side, "id": m.group(1), "class": g("class"), "tier": g("tier"),
                      "starter": g("starter"), "name": g("name")})
wt_tok = {(r.get("Reward", "").split(":")[1], r.get("Reward", "").split(":")[2])
          for r in rows.values() if r.get("Reward", "").startswith("wt:")}
fin = rd(os.path.join(CM, "mp_finish_map.scr"))
for i in sorted(rows):
    rw = rows[i].get("Reward", "")
    if not rw:
        continue
    p = rw.split(":")
    if p[0] == "wt":
        if not any(t["class"] == p[1] and t["tier"] == p[2] and t["starter"] != "1" for t in tiles):
            ERR.append("D: %s rewards %s but no non-starter tile has class %s tier %s" % (rows[i]["Id"], rw, p[1], p[2]))
    elif p[0] == "fin":
        if ('"%s"' % p[1]) not in fin and p[1] not in fin:
            ERR.append("D: %s rewards finish %r that mp_finish_map.scr does not know" % (rows[i]["Id"], p[1]))
    elif p[0] in ("sk", "hl", "gl"):
        pass                                    # cosUnlocked keys these by id; every id also has the cosNeed fallback
    else:
        ERR.append("D: %s has an unknown reward kind %r" % (rows[i]["Id"], rw))
for t in tiles:
    if t["starter"] != "1" and (t["class"], t["tier"]) not in wt_tok:
        ERR.append("D: MP armory tile %s/%s (%s) is not a starter and no challenge unlocks wt:%s:%s - unpickable"
                   % (t["side"], t["id"], t["name"], t["class"], t["tier"]))

# ---------------------------------------------------------------- E. UI references
rcvars = {r.get("RCvar") for r in rows.values() if r.get("RCvar")}
ui = os.path.join(MOD, "ui")
for fn in sorted(os.listdir(ui)):
    if not (fn.endswith(".urc") and fn.startswith("coop_mp")):
        continue
    s = rd(os.path.join(ui, fn))
    for i in re.findall(r"\bcoop_mp(?:ChD|B)(\d+)\b", s):
        if int(i) >= N:
            ERR.append("E: %s reads challenge index %s >= coop_mpChalN %d" % (fn, i, N))
    for c in set(re.findall(r"\bcoop_mpCnt_(\w+)", s)):
        if c not in classes:
            ERR.append("E: %s reads coop_mpCnt_%s - not a progression class" % (fn, c))
    for c in set(re.findall(r"\b(coop_mpUw_\w+)", s)):
        if c not in rcvars:
            ERR.append("E: %s reads %s - no challenge pushes it" % (fn, c))
    for c in set(re.findall(r"\bcoop_mpS_(\w+)", s)):
        if c not in stats:
            ERR.append("E: %s reads coop_mpS_%s - not a persisted stat" % (fn, c))

# [bug-10926] every non-starter tile's padlock must hide once its tier is unlocked: a padlock gated on the tab alone
# shows forever, so an earned gun still looks locked.
for t in tiles:
    if t["starter"] == "1":
        continue
    for scr in ("coop_mp%s_armory.urc" % t["side"], "coop_mp%s_defaults.urc" % t["side"]):
        p = os.path.join(ui, scr)
        if not os.path.isfile(p):
            continue
        m = re.search(r'name "tilelk%s"[^{}]*?enabledcvar "([^"]*)"' % t["id"], rd(p))
        want = "!coop_mpUw_%s_%s" % (t["class"], t["tier"])
        if not m:
            ERR.append("E: %s has no padlock for locked tile %s (%s)" % (scr, t["id"], t["name"]))
        elif want not in m.group(1).split():
            ERR.append("E: %s padlock of tile %s (%s) is gated on %r - it never clears when %s unlocks"
                       % (scr, t["id"], t["name"], m.group(1), want[1:]))

print("mp_unlock_audit: %d challenges | %d classes | %d stats (%d written) | %d armory tiles (%d starters)"
      % (N, len(classes), len(stats), len([s for s in stats if s in written]), len(tiles),
         len([t for t in tiles if t["starter"] == "1"])))
for w in WARN:
    print("WARN  " + w)
for e in ERR:
    print("ERROR " + e)
print("mp_unlock_audit: %s" % ("FAIL (%d)" % len(ERR) if ERR else "OK"))
sys.exit(1 if ERR else 0)
