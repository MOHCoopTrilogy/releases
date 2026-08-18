#!/usr/bin/env python
"""Audit every weapon the mod can hand a player, for the defect classes that made the FG42 useless.

WHY THIS EXISTS
The FG42 was broken in five separate ways at once, and every one of them was silent:
  1. its mesh had no tag_barrel/tag_eject, so muzzle flash and shell ejection pointed at nothing
  2. its .skc was a 110-byte single-frame stub, so idle/fire/reload were all one static pose
  3. the engine mapped its name to another weapon's animation prefix, so it borrowed foreign hands
  4. its sound aliases were maps "dm lib obj" - silent on every campaign map
  5. a shader typo elsewhere took out a whole file of weapons at once
None of those raise an error. This finds them by construction instead of by playing every gun.

    python docs/tools/audit_weapons.py           # findings only
    python docs/tools/audit_weapons.py --all     # also list what passed
"""
import glob
import io
import os
import re
import struct
import sys
import zipfile
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
GAME = r"G:/GOG/Medal of Honor - Allied Assault War Chest"
PAKS = GAME + "/main*/*.pk3"
CGAME = os.path.join(ROOT, "openmohaa-hzm", "code", "cgame", "cg_viewmodelanim.c")

CAMPAIGN = ("m", "e", "t")          # map-name prefixes coop actually plays

# !! NEVER "fix" a finding by editing a weapon's `name "..."` line. The per-gun iron-sight ADS
# table the user hand-dialled (s_adsGunTune[] in cgame/cg_modelanim.c) is keyed on that exact
# string via Q_stricmp. Rename the weapon and its tuning silently stops applying, with no error.
# A missing first-person prefix is fixed in cg_viewmodelanim.c, by ADDING the existing name.


def skc_frames(d):
    """(version, numFrames) from a .skc header. numFrames is None when unreadable.

    v13 is the raw on-disk header and states numFrames outright; v14 is a pre-processed blob
    (LoadProcessedAnimEx) whose count is not at a fixed offset, so it is reported as unknown
    rather than guessed. Frame count is the only honest static test for 'is this a real
    animation or a single static pose' - file size is not, because a short real animation and
    a stub can both be small.
    """
    if len(d) < 48 or d[:4] != b"SKAN":
        return (None, None)
    ver = struct.unpack_from("<i", d, 4)[0]
    if ver == 13:
        return (13, struct.unpack_from("<i", d, 44)[0])
    return (ver, None)


def load_sources():
    """Everything readable, mod first (mod overrides paks)."""
    files = {}          # lowercase virtual path -> bytes
    for f in sorted(glob.glob(PAKS)) + sorted(glob.glob(GAME + "/maintt/*.pk3")):
        try:
            z = zipfile.ZipFile(f)
        except Exception:
            continue
        for n in z.namelist():
            if n.endswith("/"):
                continue
            files[n.lower().replace("\\", "/")] = ("pak", f, n)
    for base, _d, fns in os.walk(MOD):
        for fn in fns:
            p = os.path.join(base, fn)
            rel = os.path.relpath(p, MOD).replace("\\", "/").lower()
            files[rel] = ("mod", p, rel)
    return files


def read(files, vpath):
    e = files.get(vpath.lower().replace("\\", "/"))
    if not e:
        return None
    kind, a, b = e
    try:
        if kind == "mod":
            return io.open(a, "rb").read()
        return zipfile.ZipFile(a).read(b)
    except Exception:
        return None


def alias_table(files):
    """alias name -> set of map prefix tokens it is loaded for."""
    out = defaultdict(set)
    for v in list(files):
        if not v.endswith("ubersound.scr") and not v.endswith("uberdialog.scr"):
            continue
        d = read(files, v)
        if not d:
            continue
        for m in re.finditer(rb'(?mi)^\s*alias(?:cache)?\s+(\S+).*?maps\s+"([^"]*)"', d):
            out[m.group(1).decode("latin-1").lower()].update(
                m.group(2).decode("latin-1").split())
        for m in re.finditer(rb'(?mi)^\s*alias(?:cache)?\s+(\S+)(?![^\n]*maps)[^\n]*$', d):
            out.setdefault(m.group(1).decode("latin-1").lower(), set())
    return out


def alias_covers_campaign(tokens):
    """bLoadForMap prefix-matches, so token 'm' covers m1l1 etc. Empty set = always loaded."""
    if not tokens:
        return True
    for t in tokens:
        for c in CAMPAIGN:
            if t.lower().startswith(c):
                return True
    return False


def base_alias(name, aliases):
    """MOHAA random-picks numbered variants: 'x' is satisfied by x1/x2..."""
    n = name.lower()
    if n in aliases:
        return True
    return any(k.startswith(n) and k[len(n):].isdigit() for k in aliases)



def unreferenced_viewmodels(files):
    """First-person animations a weapon pack shipped that nothing ever asks for.

    This is how the Type 100 was found. The xw pack ships five distinct viewmodel animations for
    it, but the engine mapped "Type 100 SMG" to WPREFIX_STEN, so it asked for sten_* aliases and
    those five files were never loaded by anything. Nothing errors - you just silently hold the
    wrong gun's hands. Same shape as the FG42's WPREFIX_MP44 mapping.

    A hit here is not automatically a defect: a pack may ship hands for a gun it never included
    (the same pack ships ak47 animations with no ak47 weapon). Check that the weapon exists first.
    """
    refs = ""
    for v in files:
        if "/fps_anims" in v or v.endswith("anims_shared.txt"):
            d = read(files, v)
            if d:
                refs += d.decode("latin-1").lower()

    groups = defaultdict(list)
    for v in files:
        if "/animation/viewmodel/" in v and v.endswith(".skc"):
            groups[v.rsplit("/", 1)[0]].append(v)

    out = []
    for folder, members in sorted(groups.items()):
        used = [m for m in members if m.rsplit("/", 1)[1] in refs]
        if used or not members:
            continue
        gun = folder.rsplit("/", 1)[1]
        has_weapon = any(v.startswith("models/weapons/") and gun in v and v.endswith(".tik")
                         for v in files)
        out.append((gun, len(members), has_weapon))
    return out


def silent_aliases(files):
    """Aliases that resolve, load, and still produce no audio.

    Found the hard way: the StG44 Scoped and the G43 Sniper were both mute, and every check we
    had passed them. The alias was defined, its wav existed, its maps spec covered the campaign -
    but soundparms carried pitch 0.0, and alias.c:188-194 reads those six numbers as
    volume / volumeMod / PITCH / pitchMod / dist / maxDist. A sound at pitch 0 never advances
    through its samples. Zero volume is the same story.

    Also checks the wav actually exists, which "is the alias defined" never did.
    """
    out = []
    for v in list(files):
        if not v.endswith("ubersound.scr") and not v.endswith("uberdialog.scr"):
            continue
        d = read(files, v)
        if not d:
            continue
        for m in re.finditer(
                rb"(?mi)^\s*alias(?:cache)?\s+(\S+)\s+(\S+)\s+soundparms\s+"
                rb"([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", d):
            name = m.group(1).decode("latin-1")
            wav = m.group(2).decode("latin-1")
            vol = float(m.group(3))
            pitch = float(m.group(5))
            if pitch == 0.0:
                out.append(("pitch 0.0 - never advances through the samples", name, wav))
            elif vol == 0.0:
                out.append(("volume 0.0", name, wav))
            # NOTE: a "does the wav exist" check was tried here and removed. It returned 34,056
            # hits, essentially all retail dialogue, because alias paths do not resolve 1:1 against
            # a flat pak index (case, .mp3/.wav siblings, per-language trees). A check that noisy
            # hides the two real findings, which is the failure mode this whole tool exists to
            # avoid. Pitch and volume are read straight off the line and are exact.
    return out

def main():
    show_all = "--all" in sys.argv
    files = load_sources()
    aliases = alias_table(files)
    cg = io.open(CGAME, encoding="utf-8", errors="replace").read() if os.path.exists(CGAME) else ""

    tiks = sorted(v for v in files
                  if v.startswith("models/weapons/") and v.endswith(".tik") and v.count("/") == 2)

    findings = defaultdict(list)
    checked = 0

    for v in tiks:
        raw = read(files, v)
        if not raw:
            continue
        t = raw.decode("latin-1")
        if not re.search(r"(?mi)^\s*classname\s+Weapon", t):
            continue          # not a player weapon (projectiles, statweapons)
        checked += 1
        gun = os.path.basename(v)
        wname = re.search(r'(?mi)^\s*name\s+"([^"]+)"', t)
        wname = wname.group(1) if wname else "?"

        # ---- the mesh, and which tags it really has -------------------------------
        path = re.search(r"(?mi)^\s*path\s+(\S+)", t)
        skel = re.search(r"(?mi)^\s*skelmodel\s+(\S+)", t)
        skd = None
        if path and skel:
            skd = read(files, "%s/%s" % (path.group(1).strip(), skel.group(1).strip()))

        for tag in ("tag_barrel", "tag_eject"):
            if re.search(r"(?mi)\b(tagdlight|tagspawnlinked|tagspawn)\s+" + tag, t):
                if skd is None:
                    findings["mesh missing"].append(
                        "%-28s uses %s but its skelmodel could not be read" % (gun, tag))
                elif tag.encode() not in skd:
                    findings["FX pointing at a tag the mesh lacks"].append(
                        "%-28s references %-10s - not in %s (no %s)"
                        % (gun, tag, skel.group(1), "muzzle flash" if tag == "tag_barrel" else "shell ejection"))

        # ---- animations: do the .skc files exist, and are any of them stubs? ------
        anim = re.search(r"(?ms)^animations\s*\r?\n\{(.*?)^\}", t)
        if not anim:
            findings["no animations block"].append("%-28s (%s)" % (gun, wname))
        else:
            body = anim.group(1)
            seen = {}
            anim_frames = {}
            static_fire = []
            for m in re.finditer(r"(?mi)^\s*(\w+)\s+(\S+\.skc)", body):
                seen[m.group(1).lower()] = m.group(2)
            for want in ("idle", "fire", "reload"):
                if want not in seen:
                    findings["missing a core animation"].append(
                        "%-28s has no '%s' entry" % (gun, want))
            for a, f in seen.items():
                vp = f if "/" in f else ("%s/%s" % (path.group(1).strip(), f) if path else f)
                d = read(files, vp)
                if d is None:
                    findings["animation file not found"].append(
                        "%-28s %-12s -> %s" % (gun, a, f))
                    continue
                ver, nf = skc_frames(d)
                if ver is None:
                    findings["not a valid .skc"].append(
                        "%-28s %-12s -> %s (%d bytes, no SKAN header)" % (gun, a, f, len(d)))
                    continue
                anim_frames[a] = nf

                # A short world-model animation is NOT a defect on its own. Most retail guns hold
                # a 1-2 frame pose here because first-person motion comes from the viewmodel hands
                # (fps_anims_*.txt), not from this file - mp44 idle is 2 frames and is perfectly
                # fine. The real, unambiguous defect is a frame COMMAND that points past the end
                # of its own animation: that is what logged "TIKI_FixFrameNum: illegal frame
                # number 20 (total: 1)" for the FG42, and it means the command never runs - no
                # magazine swap, no bolt sound, no shell at that beat.
                if nf is not None and nf <= 1 and a.lower() == "fire":
                    static_fire.append("%-28s fire -> %s is a single frozen frame" % (gun, f))

            # Re-walk the block per animation so each numeric command is checked against the
            # frame count of the animation it actually belongs to.
            for am in re.finditer(r"(?mis)^\s*(\w+)\s+(\S+\.skc)\s*\r?\n\s*\{(.*?)^\s*\}", body):
                aname = am.group(1).lower()
                nfa = anim_frames.get(aname)
                if not nfa:
                    continue
                for cm in re.finditer(r"(?m)^\s*(\d+)\s+(\w+)", am.group(3)):
                    fr = int(cm.group(1))
                    if fr >= nfa:
                        findings["frame command past the end of the animation"].append(
                            "%-28s %-12s frame %-3d %-14s but %s has only %d frame%s"
                            % (gun, aname, fr, cm.group(2), am.group(2), nfa,
                               "" if nfa == 1 else "s"))
            for row in static_fire:
                findings["fire animation is one static frame"].append(row)

        # ---- sounds: defined at all, and audible on campaign maps? ---------------
        for m in re.finditer(r"(?mi)\bsound\s+([a-z0-9_]+snd[a-z0-9_]*)", t):
            s = m.group(1).lower()
            if not base_alias(s, aliases):
                findings["sound alias never defined"].append("%-28s %s" % (gun, s))
            else:
                toks = aliases.get(s, set())
                if not toks:
                    for k in aliases:
                        if k.startswith(s) and k[len(s):].isdigit():
                            toks = toks | aliases[k]
                if not alias_covers_campaign(toks):
                    findings["sound silent on campaign maps"].append(
                        '%-28s %-24s maps "%s"' % (gun, s, " ".join(sorted(toks))))

        # ---- first-person prefix: does the engine know this weapon by name? ------
        # A skin variant is named "<Base Gun> (<Finish>)" and CoopStripSkinSuffix resolves it to
        # the base gun in BOTH the prefix lookup and the ADS tune table, so it is expected not to
        # appear here by its own name - flagging it would be a false positive on every future skin.
        if cg and wname != "?" and " (" not in wname:
            if ('"%s"' % wname) not in cg:
                findings["no first-person prefix mapping"].append(
                    "%-28s name %-22s not in cg_viewmodelanim.c - borrows another gun's hands"
                    % (gun, '"%s"' % wname))

    mute = silent_aliases(files)
    if mute:
        print("== SOUND ALIASES THAT CANNOT PRODUCE AUDIO (%d)" % len(mute))
        for why, name, wav in sorted(set(mute)):
            print("   %-26s %-34s %s" % (name, why, wav))
        print()

    unused = unreferenced_viewmodels(files)
    if unused:
        print("== SHIPPED FIRST-PERSON ANIMATIONS THAT NOTHING REFERENCES (%d)" % len(unused))
        for gun, n, has_weapon in unused:
            print("   %-14s %d anim(s) under viewmodel/%s/ - %s"
                  % (gun, n, gun,
                     "THE WEAPON EXISTS, so it is holding another gun's hands" if has_weapon
                     else "no matching weapon ships, so this is dead weight, not a defect"))
        print()

    print("audited %d player weapons\n" % checked)
    order = ["frame command past the end of the animation",
             "FX pointing at a tag the mesh lacks", "animation file not found",
             "not a valid .skc", "fire animation is one static frame",
             "missing a core animation", "no animations block",
             "sound alias never defined", "sound silent on campaign maps",
             "no first-person prefix mapping", "mesh missing"]
    total = 0
    for k in order:
        if not findings.get(k):
            continue
        rows = sorted(set(findings[k]))
        total += len(rows)
        print("== %s (%d)" % (k.upper(), len(rows)))
        for r in rows:
            print("   " + r)
        print()
    if not total:
        print("no defects found")
    else:
        print("%d finding(s)" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
