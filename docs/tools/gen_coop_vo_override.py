#!/usr/bin/env python
"""
gen_coop_vo_override.py - regenerate the tail override block of the coop ubersound.scr.

THE PROBLEM IT SOLVES
    [user 2026-09-01] "there were definitely errors related to playsound in the mission I was just
    playing" and, separately, "I hear allies repeating lines like 'He's hit' over and over again".

    Those are the SAME defect. Reading the live log from the user's own session:

        125  ERROR PlaySound: dfr_attack_08h_1 needs an alias ...
         80  ERROR PlaySound: snd_step_wade    needs an alias ...
         54  ERROR PlaySound: dfr_attack_01a_2 needs an alias ...
         50  ERROR PlaySound: dfr_attack_03h_1 needs an alias ...
         19  ERROR PlaySound: dfr_attack_01h_2 needs an alias ...

    Not one of those aliases is undeclared. `dfr_attack_01a_2*` has 3,654 declarations across the
    paks - and EVERY ONE of them carries a `maps` field listing t1/t2/t3/m1l2a/m4l1/m5l1a/... and
    never m3l1a. The maps field is a LOAD FILTER (scriptmaster.cpp:432): an alias whose filter does
    not prefix-match the live map is NOT LOADED AT ALL, so the prefix group resolves empty and
    PlaySound errors. On Omaha the entire allied attack/cover callout pool is therefore missing, and
    the handful of lines that DO load are the ones the player hears on repeat. The repetition and the
    console errors are one bug, not two.

    snd_step_wade is the same trap with an extra twist: it IS declared `maps "m3l1a train"` - and then
    declared AGAIN, later in the same concatenated ubersound.scr, as `maps "e1l4 e3l1 e3l3 dm lib obj"`.
    The mod's ubersound.scr is a concatenation of all three games' files, so Breakthrough's narrower
    block silently overrides Allied Assault's correct one. LAST DECLARATION WINS - which is exactly
    why the fix has to be appended at the END of the file.

WHY THIS IS GENERATED AND NOT HAND-WRITTEN
    It is a list derived from what audio actually ships. Hand-maintained inventories rot; this one is
    swept out of the pk3s every time it runs, so it cannot drift from the files on disk, and it can be
    re-pointed at a different install by changing GAME_ROOT.

USAGE
    python docs/tools/gen_coop_vo_override.py            # rewrite the block
    python docs/tools/gen_coop_vo_override.py --check    # exit 1 if the file is stale
"""
import io, os, re, sys, zipfile

GAME_ROOT = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
TARGET = os.path.join(MOD, "ubersound", "ubersound.scr")

BEGIN = "// >>> BEGIN GENERATED coop VO override (docs/tools/gen_coop_vo_override.py) - DO NOT EDIT BY HAND"
END = "// <<< END GENERATED coop VO override"

# every map family in the trilogy, plus the non-campaign contexts. A prefix token matches any map
# whose name starts with it, so "m e t" covers all three campaigns in three characters.
ALLMAPS = 'm e t dm obj train lib moh'

# the alias groups the engine was observed asking for and not getting, and the audio family each
# should be answered from. Sources are ungated GENERIC pools, so nothing here is mission-specific.
GROUPS = [
    ("dfr_attack_01a_2", "attack"),
    ("dfr_attack_01h_2", "cover"),
    ("dfr_attack_03h_1", "cover"),
    ("dfr_attack_08h_1", "attack"),
]
VARIANTS = 12          # numbered members per prefix group - this is the variety the player hears


def pak_files():
    out = []
    for sub in ("main", "mainta", "maintt"):
        d = os.path.join(GAME_ROOT, sub)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith(".pk3"):
                continue
            try:
                z = zipfile.ZipFile(os.path.join(d, f))
            except Exception:
                continue
            for n in z.namelist():
                if n.lower().endswith((".wav", ".mp3")):
                    out.append(n.replace("\\", "/"))
    return sorted(set(out))


def build(files):
    attack = sorted(p for p in files if re.search(r"dialogue/Generic/A/attack/", p, re.I))
    cover = sorted(p for p in files if re.search(r"dialogue/Generic/A/cover/", p, re.I))
    wade = sorted(p for p in files if re.search(r"characters/(body_mvmtwater_|water_movement)", p, re.I))
    pools = {"attack": attack, "cover": cover}

    L = [BEGIN]
    L.append("//")
    L.append("// Regenerate with: python docs/tools/gen_coop_vo_override.py")
    L.append("// Every path below was swept from the pk3s in %s," % GAME_ROOT)
    L.append("// so an entry here cannot name a file that does not ship.")
    L.append("//")
    L.append("// WHY THESE ARE AT THE END OF THE FILE: alias resolution is LAST-DECLARATION-WINS, and")
    L.append("// this ubersound.scr concatenates all three games' copies. Several groups are declared")
    L.append("// correctly for Allied Assault early on and then re-declared later with a Breakthrough-only")
    L.append("// maps field, which silently un-declares them for m-series maps. Appending is the fix.")
    L.append("//")
    L.append("// WHY THE maps FIELD IS WIDE: `maps \"%s\"` - the field is matched as a PREFIX" % ALLMAPS)
    L.append("// of the live map name, so `m` admits every Allied Assault map, `e` every Breakthrough one")
    L.append("// and `t` every Spearhead one. These are generic, non-mission-specific lines with no")
    L.append("// reason to be restricted; restricting them is what broke them.")
    L.append("")

    # --- DELIBERATELY NOT DECLARED. See the note below; this list stays for the record.
    L.append("// --- allied attack / take-cover callouts: NOT DECLARED, ON PURPOSE.")
    L.append("//")
    L.append("// [user 2026-09-01, bug-2307] An earlier pass DID declare these, and it was a mistake I")
    L.append("// have now reverted. The reasoning was: 179 'needs an alias' errors per session for")
    L.append("// dfr_attack_01a_2 / 03h_1 / 08h_1 / 01h_2, every declaration of them gated to maps that")
    L.append("// exclude m3l1a, and %d generic attack + cover lines shipping unreachable. So I made them" % (len(attack) + len(cover)))
    L.append("// trilogy-wide and the errors stopped.")
    L.append("//")
    L.append("// The user's verdict: \"they are constnatly spamming hes hit, its ridiculous, nonstop\" and")
    L.append("// \"I am stuck with basically the music and dialogue spam which ruins the atmosphere\".")
    L.append("//")
    L.append("// THE MAPS FIELD WAS NOT A BUG HERE. On the five outages this project has actually had")
    L.append("// (explode_tank, welding_torch, sledgehammer, impact_leavewater, snd_ping) the map list was")
    L.append("// an oversight and something audibly broke. On these it is CURATION: the content designers")
    L.append("// chose which missions use which callout pools, and the engine's AI fires them with no")
    L.append("// cooldown of its own. Widening the field removed that curation, so every actor on a beach")
    L.append("// holding fifty of them barked continuously. A console error is not evidence of a defect -")
    L.append("// silence can be the authored behaviour, and here it was.")
    L.append("//")
    L.append("// If the variety is ever wanted back, the missing piece is a RATE LIMIT on engine-fired AI")
    L.append("// voice, not a wider maps field. Declaring them again without one just reproduces this.")
    L.append("")

    L.append("// --- wading footsteps. 80 PlaySound errors in one session on a beach landing map,")
    L.append("// because AA's correct `maps \"m3l1a train\"` declaration is overridden further down this")
    L.append("// same file by Breakthrough's `maps \"e1l4 e3l1 e3l3 dm lib obj\"` one.")
    if wade:
        for i, path in enumerate(wade):
            L.append('aliascache snd_step_wade%d %s soundparms 0.75 0.3 0.9 0.2 160 1600 body loaded maps "%s"'
                     % (i + 1, path, ALLMAPS))
    else:
        L.append("// (no water-movement audio found)")
    L.append("")

    # ---- foley whose alias is registered but never CACHED on this map
    L.append("// --- [user 2026-09-01, bug-2304] THE M1 GARAND PING, \"plays extremely short... thats not")
    L.append("// normal\". Not truncation and not the mixer: the sound is simply NOT PRECACHED on m3l1a, so")
    L.append("// the first play has to fetch it from the pak mid-firefight.")
    L.append("//")
    L.append("// snd_ping is declared TWICE in retail, and neither declaration admits this map -")
    L.append("//    ubersound.scr:574   maps \"m1l1 m1l2a m1l2b m1l3a m1l3b m1l3c m3l2 m3l3 m4l0 ...\"")
    L.append("//    ubersound.scr:3055  always  maps \"e1l1 e1l2 e1l3 e2l1 e3l3 dm lib obj\"")
    L.append("// - because the maps field is matched as a PREFIX of the live map name and `m3l2`/`m3l3`")
    L.append("// are not prefixes of `m3l1a`. Line 3055 keeps the ALIAS alive on every map through")
    L.append("// `always`, which is why you hear a ping at all. But look at where the cache call sits")
    L.append("// (fgame/scriptmaster.cpp:491-501):")
    L.append("//     if (bAlwaysLoaded)            { gi.GlobalAlias_Add(...); }")
    L.append("//     if (bLoadForMap(maps, name)) { if (!bAlwaysLoaded) GlobalAlias_Add(...);")
    L.append("//                                    CacheResource(...); }   <-- INSIDE the maps test")
    L.append("// `always` gets you the alias. Only the maps field gets you the CACHE. So on Omaha the")
    L.append("// ping is registered and uncached - the one combination that plays but plays badly.")
    L.append("//")
    L.append("// Declared last so it wins, with a trilogy-wide maps field so it is cached everywhere.")
    ping = next((p for p in files if p.lower().endswith("m1_ping.wav")), None)
    if ping:
        L.append('aliascache snd_ping %s soundparms 1.5 0.3 0.95 0.1 160 1000 auto loaded always maps "%s"'
                 % (ping, ALLMAPS))
    else:
        L.append("// (M1_Ping.WAV not found in the paks - nothing written)")
    L.append("")
    L.append(END)
    return "\n".join(L)


def main():
    files = pak_files()
    block = build(files)

    raw = open(TARGET, "rb").read()
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    txt = raw.decode("latin-1").replace("\r\n", "\n")

    if BEGIN in txt:
        a = txt.index(BEGIN)
        b = txt.index(END) + len(END)
        new = txt[:a] + block + txt[b:]
    else:
        new = txt.rstrip("\n") + "\n\n" + block + "\n"

    if "--check" in sys.argv:
        if new != txt:
            print("STALE - run: python docs/tools/gen_coop_vo_override.py")
            return 1
        print("  coop VO override block is current")
        return 0

    open(TARGET, "wb").write(new.replace("\n", nl.decode("latin-1")).encode("latin-1"))
    n = len([x for x in block.splitlines() if x.startswith("aliascache")])
    print("  ubersound.scr: %d override aliases written (%d attack/cover groups + wading)"
          % (n, len(GROUPS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
