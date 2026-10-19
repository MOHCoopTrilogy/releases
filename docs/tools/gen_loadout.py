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
    python docs/tools/gen_loadout.py hovers    # print the derived unlock hover text, one page a line

THE DATA
docs/tools/loadout_weapons.tsv is the source of truth. Adding a weapon to the armory is one row.
Columns are described in its header. The preview transform (xfm) is hand-dialled per gun the same
way the ADS table is - `extract` preserves whatever is there, and a new row starts from a sane
default that the user then tunes in-game.

The one thing that is NOT in the table is the hover unlock line (req<id>.cfg, reqf<fid>.cfg): it
is derived from the scripts that actually grant the unlock - see unlock_hovers() below.

HZM_MOD=<dir> points every read and write at another copy of hzm-mohaa-coop-mod (a scratch tree,
or the base checkout from a worktree). Default: <repo>/hzm-mohaa-coop-mod.
"""
import io
import os
import re
import sys

import armory_unlocks as au

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.environ.get("HZM_MOD") or os.path.join(ROOT, "hzm-mohaa-coop-mod")
# [ADS rollout step 5] a NEW gun's tiks ship in zzzzzzzzzz_coop_fixes.pk3 (docs/tools/assets/fixes) and are NOT in the
# mod tree (a new file under models/ re-hashes the 1.3 GB assets pak): look in both places.
FIXES_WEAPONS = os.path.join(ROOT, "docs", "tools", "assets", "fixes", "models", "weapons")


def _tik_exists(name):
    return os.path.exists(os.path.join(MOD, "models", "weapons", name)) or os.path.exists(os.path.join(FIXES_WEAPONS, name))

UI = os.path.join(MOD, "ui", "loadout")
TSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loadout_weapons.tsv")

COLS = ["id", "tik", "give", "xfm", "charanim", "cls", "tab", "name", "cd", "b0", "b1", "b2", "b3",
        "clip", "clipn", "recoil", "slots", "xfmt"]

# The server-side unlock roster. Absent from it, a weapon draws in the grid and does nothing
# when clicked - no commit command, no padlock, no unlock text.
ROSTER = os.path.join(MOD, "coop_mod", "loadoutroster.scr")

# The class token in the wNN_sN "unreg" / "who" lines is INDEPENDENT of the hold pose, which the
# first reconstruction got wrong: weapon 12 uses coop_hold_rifle but belongs to the sniper class,
# so a sniper holds a rifle pose and still gates on unreg_sniper.cfg. It is its own column.


# [armory B] guns whose 3D model cannot be shown (the Mills bomb renders solid black: texture alpha) get the stock 2D grenade icon
# (textures/hud/weap_grenade.tga) on cards, the hero and the slot tile instead.
ICON2D = ("66",)


HEROFIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "armory_hero_fit.tsv")
_HERO = {}


def hero_xfm(w):
    """The Armory HERO box transform of a gun: MEASURED per gun (armory_hero_fit.tsv, docs/proposals/armory_redesign_2026-10-18/tools/hero_fit.py); a gun
    not in the table falls back to its slot-thumbnail transform scaled by the aspect ratio (a rifle fits, a tall gun may clip)."""
    if not _HERO and os.path.isfile(HEROFIT):
        for ln in io.open(HEROFIT, encoding="latin-1"):
            if ln.startswith("#") or ln.startswith("id\t") or not ln.strip():
                continue
            a, b = ln.rstrip("\r\n").split("\t")
            _HERO[a] = b
    if w["id"] in _HERO:
        return _HERO[w["id"]]
    t = (w.get("xfmt") or w["xfm"]).split()
    return " ".join(t)       # the widget WIDTH frames the model (horizontal fov): the thumbnail transform fills the same width fraction in the hero


def _read(p):
    return io.open(p, "r", encoding="latin-1", newline="").read()


def _eol(p):
    """A page keeps its own line endings: the generated pages are LF, but the reqf*.cfg that were
    hand-written before this generator owned them are CRLF. New files are LF."""
    return "\r\n" if os.path.exists(p) and "\r\n" in _read(p) else "\n"


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
    MV_HOSTS = ("01", "03", "04", "05", "07", "08", "09", "12", "13", "14", "23", "24", "26", "36", "37", "44", "45", "46", "48", "50", "53", "55", "74", "78")
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
        finp.append("exec ui/loadout/finp%s_%d.cfg" % (w["id"], _i + 1) if _tik_exists("%s_%s.tik" % (_stem, _k)) else "")
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
    # [armory B 2026-10-18] the inspect page also drives the hero (big render + compare): hero xform = the gun's slot-thumbnail transform
    # (the hero box has the thumbnail's 2.16 aspect, so the fit data is reused as is), the locked/equip flags and the candidate stats.
    L += [
        'set coop_loXfmHero "%s"' % hero_xfm(w),
        "set coop_loHero %d" % (0 if w["id"] in ICON2D else 1),
        "set coop_loHeroIc %d" % (1 if w["id"] in ICON2D else 0),
        "set coop_loHeroLk 0",
        "set coop_loCanEq 0",
        "exec ui/loadout/hpg0.cfg",
        "exec ui/loadout/cand%s.cfg" % w["id"],
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
        'set coop_loXfmT%s "%s"' % (s, w.get("xfmt") or w["xfm"]),
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
    # [loadout review 2026-10-15] EQUIPPED tile marker: register this pick in the slot's per-tab archive (the marker label of
    # tile<id> reads coop_loEqV<id>, recomputed per tab by lktab<t>.cfg -> eqre<t>.cfg) and refresh the visible tab now.
    t = str(w["tab"])
    # [armory B] the marker is a CARD (position) flag now: coop_loEqOn<id> is published by the card chain when the gun is placed.
    L.append('seta coop_loEqR%s_%s "vstr coop_loEqOn%s"' % (t, s, w["id"]))
    for ot in "012345":
        if ot != t:
            L.append('seta coop_loEqR%s_%s ""' % (ot, s))
    # [armory B] the slot's gun is the EQUIPPED side of the compare: archive its publisher, publish now, refresh the inspected gun's compare
    if s == "4":
        L.append("set coop_loIc4 %d" % (1 if w["id"] in ICON2D else 0))
    L.append('seta coop_loPubS%s "exec ui/loadout/pubgun%s.cfg"' % (s, w["id"]))
    L.append("vstr coop_loPubS%s" % s)
    L.append('seta coop_loNsA%s "exec ui/loadout/nsn%s_%s.cfg"' % (s, s, w["id"]))   # the slot tile's (short) name line
    L.append("vstr coop_loNsA%s" % s)
    L.append("vstr coop_loCandRe")
    # [loadout review 2026-10-15] the pick as userinfo STATE too (cgame lp_w<slot>; the server converges on the last value, so quick
    # clicks cannot be lost to the name bus). A new gun also resets its slot's finish state to standard.
    L.append('set lp_w%s "%s"' % (s, w["id"]))
    L.append('set lp_f%s "0"' % s)
    L.append("vstr coop_loEqRe")
    return "\n".join(L) + "\n"


def tile(w):
    """tNN.cfg - what the grid tile runs when clicked.

    [loadout review 2026-10-15] The tile no longer previews first. coop_loCmt<id> (archived, pushed by the server's
    loadout_ui_exportUnlocks) is now the whole click: UNLOCKED -> `exec eq<id>.cfg` (preview + equip into the active
    slot, the old behaviour), LOCKED -> `exec lkw<id>.cfg` (show the requirement + deny beep; the gun is NOT previewed,
    so a locked gun can never look like it was equipped). Unset (no server yet) = fail-locked no-op."""
    return ("// GENERATED - the click is coop_loCmt<id>: eq<id>.cfg when earned, lkw<id>.cfg when locked\n"
            "vstr coop_loCmt%s\n" % w["id"])


def eqfile(w):
    """eqNN.cfg - the EARNED click: inspect this weapon, then commit it into the active slot."""
    # [armory B 2026-10-18] a click INSPECTS (hero render + compare against what the slot holds); the EQUIP button runs coop_loCcur.
    return ("// GENERATED - earned weapon click: inspect (hero + compare + selected mark); EQUIP commits into the active slot\n"
            "exec ui/loadout/p%s.cfg\n"
            "set coop_loCanEq 1\n"
            "exec ui/loadout/kselclr.cfg\n"
            "vstr coop_loSlOn%s\n" % (w["id"], w["id"]))


def lkwfile(w, has_req):
    """lkwNN.cfg - the LOCKED click: requirement text + deny beep, nothing previewed or equipped."""
    # The info panel is retitled to THIS gun with "LOCKED" and its stat bars are blanked, so the requirement line can never be
    # read as belonging to the gun that was already equipped (the first version left the previous gun's panel up).
    return ("// GENERATED - locked weapon click: show what unlocks it, beep, change nothing\n"
            'set coop_loNm "%s"\n'
            'set coop_loCd "LOCKED"\n'
            'set coop_loB0 "textures/hud/coop_bf0"\n'
            'set coop_loB1 "textures/hud/coop_bf0"\n'
            'set coop_loB2 "textures/hud/coop_bf0"\n'
            'set coop_loB3 "textures/hud/coop_bf0"\n'
            'set coop_loClip "textures/hud/clip/clip_0"\n'
            'set coop_loClipN ""\n' % w["name"]
            + ("exec ui/loadout/req%s.cfg\n" % w["id"] if has_req else "")
            # [armory B 2026-10-18] the hero shows the lock (no model), the compare still reads this gun's stats, and the server-pushed
            # progress (coop_loPgA<id> through hpub.cfg = bar level, coop_loPgT<id> = "74 / 100" text) says how close the player is.
            + "set coop_loHero 0\n"
            + "set coop_loHeroIc 0\n"
            + "set coop_loMvOn 0\n"
            + "set coop_loHeroLk 1\n"
            + "set coop_loCanEq 0\n"
            + "exec ui/loadout/cand%s.cfg\n" % w["id"]
            + "exec ui/loadout/hpg0.cfg\n"
            + "exec ui/loadout/hpub.cfg\n"
            + "vstr coop_loPgA%s\n" % w["id"]
            + "vstr coop_loPgT%s\n" % w["id"]
            + "exec ui/loadout/kselclr.cfg\n"
            + "vstr coop_loSlOn%s\n" % w["id"]
            + "vstr coop_loDeny\n")


def req(lines):
    """req<id>.cfg / reqf<fid>.cfg - the two-line hover unlock text."""
    return ('set coop_loReq "%s"\n'
            'set coop_loReq2 "%s"\n' % lines)


# ---------------------------------------------------------------- unlock hover text ----------
# [user 2026-09-28] The hover line under a padlocked tile (req<id>.cfg) and a finish chip
# (reqf<fid>.cfg) used to be typed by hand - into loadout_weapons.tsv and into the reqf files - and
# drifted from what the server enforces: MP40 said "Locked" (code: 50 MP40 kills), the .30 Cal,
# MG42 and the three launchers said "Skill Tree (coming soon)" (code: 40 / 15 kills), four sniper
# rows named the wrong gun or no count, and GOLD said 2500 kills (code: 250). It is now derived
# from the scripts that GRANT the unlock - challenges.scr rewards, xp.scr rank grants, the
# loadout_isUnlocked free list and the loadout_finish gates - through the same parsers
# armory_unlocks.py audits with. A challenge target that moves without the pages being rebuilt now
# fails `check`, and build.ps1 refuses to deploy.

# wreq/wreq2 in coop_loadout.urc are 152px of verdana-12, centred, so an overflow clips BOTH ends
# (bug-2785 was that on the MP armory). gen_cos_reqs.py measured the 130px cosReq labels (same
# font) at a little over 40 characters, which scales to ~46 here; 42 keeps a wide-glyph margin.
REQ_COLS = 42


def _script(name):
    return au.strip_comments(_read(os.path.join(MOD, "coop_mod", name)))


def _cond(desc):
    """A challenge description as a hover condition: 'Get 50 kills with the MP40' -> '50 kills w/ MP40'."""
    d = au.sanitise(desc)
    d = re.sub(r"\s+to unlock\b.*$", "", d)     # the tile under the cursor already says what it is
    d = re.sub(r"^Get\s+", "", d)
    return d.replace(" with the ", " w/ ")


def _fit(line, tail, clipped, key):
    """Lay a hover out on the two REQ_COLS label lines. The condition is what the player has to do,
    so it always wins; `tail` (challenge title, other ways, extra gates) keeps line 2 only if it fits.
    Anything dropped or cut is recorded in `clipped` so `check` can say so."""
    if len(line) <= REQ_COLS:
        if len(tail) > REQ_COLS:
            clipped.append(key)
            tail = ""
        return line, tail
    words, a = line.split(" "), ""
    while words and len((a + " " + words[0]).strip()) <= REQ_COLS:
        a = (a + " " + words.pop(0)).strip()
    b = " ".join(words)
    if tail and len(b + " " + tail) <= REQ_COLS:
        b += " " + tail
    elif tail:
        clipped.append(key)
    if len(b) > REQ_COLS:
        b = b[:REQ_COLS - 3].rsplit(" ", 1)[0] + "..."
        if key not in clipped:
            clipped.append(key)
    return a, b


def _other_ways(n):
    return "+%d other way%s" % (n, "" if n == 1 else "s") if n else ""


def unlock_hovers(rows):
    """{page name: cfg text} for every req<id>.cfg and reqf<fid>.cfg, plus the clipped keys."""
    xp, chal, lp = _script("xp.scr"), _script("challenges.scr"), _script("loadoutpick.scr")
    skins = _script("loadoutskins.scr")
    rnames = au.rank_names(xp)
    rewards = au.chal_rewards(chal)
    free = {t.lower() for t in au.free_guns(lp)}
    out, clipped = {}, []

    # guns - the earliest rank that grants it (a later grant of the same gun is unreachable first),
    # then every challenge that rewards it. Rank first, as armory_unlocks.requirement_text does.
    rank = {}
    for r, tok in au.rank_grants(xp):
        rank[tok.lower()] = min(r, rank.get(tok.lower(), r))
    for w in rows:
        give = (w["give"] or w["tik"]).lower()
        if give in free:
            continue                            # no hover at all for a free starter
        ways = []
        if give in rank:
            ways.append(("Rank: %s" % au.sanitise(rnames.get(rank[give], str(rank[give]))), ""))
        ways += [(_cond(d), "(%s)" % au.sanitise(t)) for _c, t, d, rw in rewards if rw.lower() == give]
        if not ways:
            ways = [("not currently obtainable", "")]
        cond, tail = ways[0]
        tail = " ".join(x for x in (tail, _other_ways(len(ways) - 1)) if x)
        out["req%s.cfg" % w["id"]] = req(_fit("UNLOCK: " + cond, tail, clipped, w["id"]))

    # finishes - loadout_finish applies fid 1-7 only when BOTH gates hold: loadout_finUnlocked (the
    # account-wide finish_* reward, looked up through coop_skinFinStat) and loadout_finMastered (the
    # gun's own wpn_ kill challenge). The second gate is per gun, so the chip can only name it - in
    # the words of the server's own refusal, "Master this weapon first (its kill challenge)".
    stat = {int(f): t for f, t in re.findall(r'coop_skinFinStat\[(\d+)\]\s*=\s*"([^"]+)"', skins)}
    fin = re.search(r"(?ms)^loadout_finish\b[^\n]*:\{(.*?)^\}end", lp)
    assert stat and fin, "coop_skinFinStat (loadoutskins.scr) or loadout_finish (loadoutpick.scr) not found"
    mastery = "+ master this gun" if "loadout_finMastered" in fin.group(1) else ""
    for fid in sorted(stat):
        src = [(t, d) for _c, t, d, rw in rewards if rw == stat[fid]]
        if src:
            cond = _cond(src[0][1])
            tail = " ".join(x for x in ("(%s)" % au.sanitise(src[0][0]), _other_ways(len(src) - 1)) if x)
        else:
            cond, tail = "not currently obtainable", ""
        if mastery:
            tail = (tail + " " + mastery) if tail and len(tail + " " + mastery) <= REQ_COLS else mastery
        out["reqf%d.cfg" % fid] = req(_fit("FINISH: " + cond, tail, clipped, "f%d" % fid))
    return out, clipped


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
            if _tik_exists("%s_%s.tik" % (_stem2, _k)):
                out["finp%s_%d.cfg" % (w["id"], _i + 1)] = (
                    'set coop_loPrev "models/weapons/%s_%s.tik"\n' % (_stem2, _k)
                    + 'set coop_loNm "%s (%s)"\n' % (w["name"], _lab))
        out["t%s.cfg" % w["id"]] = tile(w)
        for s in w["slots"]:
            out["w%s_s%s.cfg" % (w["id"], s)] = slotfile(w, s)
    hovers, clipped = unlock_hovers(rows)
    out.update(hovers)
    for w in rows:
        out["eq%s.cfg" % w["id"]] = eqfile(w)
        out["lkw%s.cfg" % w["id"]] = lkwfile(w, "req%s.cfg" % w["id"] in hovers)
    # [armory B 2026-10-18] the card chains, compare tables, progress joins and defaults (gen_armory.py); paths are mod-relative
    import gen_armory as ga
    extra = ga.build(rows, out, MOD)
    for rel, text in extra.items():
        if rel.startswith("ui/loadout/"):
            out[rel[len("ui/loadout/"):]] = text
        else:
            EXTRA[rel] = text
    return out, clipped


EXTRA = {}      # generated files outside ui/loadout/ (mod-relative path -> text), filled by render_all


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
            "slots": slots,
            "xfmt": _xfmt(wid),
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
           "# The hover unlock text (req<id>.cfg) is NOT a column: gen_loadout derives it from the\n"
           "# scripts that grant the unlock (challenges.scr, xp.scr, loadoutpick.scr).\n"
           + "\t".join(COLS) + "\n")
    body = "".join("\t".join(w[c] for c in COLS) + "\n" for w in rows)
    io.open(TSV, "w", encoding="utf-8", newline="\n").write(hdr + body)
    return rows


def _xfmt(wid):
    """slot-card thumbnail transform: whatever the first slot commit file of this weapon carries."""
    for sl in "1234":
        sp = os.path.join(UI, "w%s_s%s.cfg" % (wid, sl))
        if os.path.exists(sp):
            m = re.search(r'(?m)^set coop_loXfmT\d "([^"]*)"', _read(sp))
            if m:
                return m.group(1)
    return ""


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
    files, clipped = render_all(rows)

    if mode == "hovers":
        # the derived unlock text, one page per line, for reading before a build
        for name in sorted(n for n in files if n.startswith("req")):
            v = re.findall(r'"([^"]*)"', files[name])
            print("%-11s %-46s %s" % (name, v[0], v[1]))
        return 0

    if mode == "build":
        for name, text in sorted(files.items()):
            p = os.path.join(UI, name)
            text = text.replace("\n", _eol(p))
            io.open(p, "w", encoding="latin-1", newline="").write(text)
        for rel, text in sorted(EXTRA.items()):      # [armory B] files outside ui/loadout/ (the urc)
            p = os.path.join(MOD, rel.replace("/", os.sep))
            io.open(p, "w", encoding="latin-1", newline="").write(text.replace("\n", _eol(p)))
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
        elif _read(p) != text.replace("\n", _eol(p)):
            bad.append(name)
    for rel, text in sorted(EXTRA.items()):
        p = os.path.join(MOD, rel.replace("/", os.sep))
        if not os.path.exists(p):
            missing.append(rel)
        elif _read(p) != text.replace("\n", _eol(p)):
            bad.append(rel)
    rtext = _read(ROSTER)
    roster_ok = splice_roster(rows, rtext) == rtext

    orphan = [f for f in os.listdir(UI)
              if re.match(r"(p|t|eq|lkw|reqf?)\d+\.cfg$|w\d+_s\d\.cfg$", f) and f not in files]
    hover_bad = [n for n in bad if n.startswith("req")]
    print("%d weapons -> %d generated files" % (len(rows), len(files)))
    print("  byte-identical : %d" % (len(files) - len(bad) - len(missing)))
    if bad:
        print("  DIFFERENT      : %d  %s" % (len(bad), bad[:8]))
    if hover_bad:
        print("  hover text     : %d page(s) no longer say what challenges.scr / xp.scr enforce  %s"
              % (len(hover_bad), hover_bad[:8]))
    if missing:
        print("  MISSING        : %d  %s" % (len(missing), missing[:8]))
    if orphan:
        print("  on disk only   : %d  %s" % (len(orphan), orphan[:8]))
    if clipped:
        # not a failure: the condition always survives, only a title/other-ways tail was dropped or cut
        print("  hover clipped  : %d to fit %d cols  %s" % (len(clipped), REQ_COLS, clipped[:8]))
    print("  unlock roster  : %s" % ("in sync" if roster_ok else "OUT OF SYNC - weapons will not equip"))
    ok = not bad and not missing and not orphan and roster_ok
    if ok:
        verdict = "EXACT REPRODUCTION"
    elif bad and bad == hover_bad and not missing and not orphan and roster_ok:
        verdict = "HOVER TEXT DRIFTED from the unlock rules - rebuild the pages"
    else:
        verdict = "MISMATCH - format not fully understood"
    print("  -> %s" % verdict)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
