"""gen_disc_stubs.py - the SHIPPED side of the bring-your-own-disc guns (H:\\hzm_work\\discguns\\PLAN.md, section 0 / 2 / 6).

Every Frontline / European Assault gun is a variant of a roster gun. The mod ships, per variant, two files of OUR OWN content:

  models/weapons/byo/<stub>.tik        the STUB: the base gun's own setup block (base mesh, base look) + `$include` of the body
  models/weapons/byo/body/<base>.txt   the shared BODY: everything below the base tik's setup block (init server + client,
                                       animations) - the base gun's exact stats, anims and sounds - with the variant name/rank

A player who converted their own disc gets a pak (written on their PC, never shipped) holding a tik at the SAME path, with its
own setup (the disc mesh fitted onto the base gun's bone block) that `$include`s the same body. So the server always gives the
stub path, every client without the pak sees the base gun, and stats / anims / tags can never drift between the two.

Body transform (the only changes against the effective base tik):
  * `$path <base path>` first: TIKI `path` is per script file, an included body resolves its .skc names against nothing
    otherwise (Phase 0 finding 1)
  * `name` -> the variant display name, `rank` -> a unique disc-band rank (4000-4049 FL, 4050-4099 EA, 4100+ new guns)
  * `surface <clip surface> ...` -> `surface <clip surface>* ...` - the converted mesh may carry its magazine in more than one
    surface (`Clip`, `Clip_2`, one per disc texture); on the base mesh the wildcard matches the one surface it always did
    (Entity::SurfaceCommand prefix match). The gate below proves the prefix hits exactly one base surface.

Also writes scripts/hzm_adssights_stub.txt: one `alias` row per stub (the cgame byo loader, engine e7cc7985), so a stub aims
with its base gun's sight row.

    python docs/tools/gen_disc_stubs.py build    write the stubs, bodies and the alias file into hzm-mohaa-coop-mod/
    python docs/tools/gen_disc_stubs.py check    exit 1 when a written file no longer matches what build would write

The base tik is read from the effective install (the last pak that carries it wins: wpnfix / late / stress copies), $HZM_GAME
(default G:/mohaa-gl2). Nothing disc-derived is read or written here.
"""
import io
import os
import re
import sys
import glob
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
GAME = os.environ.get("HZM_GAME", r"G:/mohaa-gl2")
GAMEDIRS = ("main", "mainta", "maintt")

# stub, base tik (models/weapons/<base>.tik), display name, rank[, opts]. Rows are added as each disc gun passes its QA sheet.
# opts (a NEW gun built on a base gun's rig, not a cosmetic variant - PLAN.md phase-1 finding 4b):
#   body       the body file name (default: the base) - a new gun never shares the base's body, and a SECOND disc variant of
#              the same base (European Assault next to Frontline) needs its own: the body carries the variant's name / rank
#   new        a NEW gun (its own roster weapon), not a cosmetic variant: no disc-fid row in loadoutdisc.scr
#   silenced   the fire alias that replaces the base's, and every live `model models/fx/muzflash.tik` frame command is
#              commented out (the mod's silenced convention: greasegun_silenced / mp40silenced / ppsh43silenced)
#   set        {"<mode> <key>": "<value>"} - stat lines of the body replaced (its OWN stats, the rest stay the base's)
STUBS = [
    ("thompsonsmg_fl", "thompsonsmg", "Thompson (Frontline)", 4000),
    ("bar_fl", "bar", "BAR (Frontline)", 4001),
    ("mp40_fl", "mp40", "MP40 (Frontline)", 4002),
    ("mp44_fl", "mp44", "StG 44 (Frontline)", 4003),
    ("shotgun_fl", "shotgun", "Shotgun (Frontline)", 4004),
    # Frontline batch 2 (2026-11-16): the iron-sighted rifle and the three pistols
    ("m1_garand_fl", "m1_garand", "M1 Garand (Frontline)", 4005),
    ("colt45_fl", "colt45", "Colt 45 (Frontline)", 4006),
    ("p38_fl", "p38", "Walther P38 (Frontline)", 4007),
    ("silencedpistol_fl", "silencedpistol", "Hi-Standard Silenced (Frontline)", 4008),
    # Frontline batch 3: the scoped rifles
    ("springfield_fl", "springfield", "Springfield '03 Sniper (Frontline)", 4009),
    ("g43_fl", "g43", "G 43 (Frontline)", 4010),
    # Frontline batch 4: the launchers
    ("bazooka_fl", "bazooka", "Bazooka (Frontline)", 4011),
    ("panzerschreck_fl", "panzerschreck", "Panzerschreck (Frontline)", 4012),
    # Frontline batch 5: the grenades (include-only base tiks, inlined)
    ("m2frag_grenade_sp_start_fl", "m2frag_grenade_sp_start", "Frag Grenade (Frontline)", 4013),
    ("steilhandgranate_start_fl", "steilhandgranate_start", "Stielhandgranate (Frontline)", 4014),
    # [coordinator 2026-11-16, 4b + decision 3] EA's Sten is the Mk II(S): its OWN weapon on the Sten rig. Its name does not
    # split to "Sten Mark II", so the base-name lookups (cgame CoopStripSkinSuffix, fgame CoopWeaponBaseName) reach the Sten
    # through its alias row below; its recoil / ROF / pattern rows are its own (coop_mod tables, stem sten_mk2s).
    ("sten_mk2s_ea", "sten", "Sten Mk II(S) (European Assault)", 4100,
     {"body": "sten_mk2s_ea", "new": True, "silenced": "sten_silenced",
      "set": {"dm firedelay": "0.09", "realism firedelay": "0.09"}}),
] + [
    # European Assault (2026-11-16): every EA variant has its own body (its base's first body is the Frontline variant's).
    # The M9 bazooka is the second EA variant of the bazooka (fid 71).
    (stub, base, display, rank, {"body": stub}) for stub, base, display, rank in (
        ("thompsonsmg_ea", "thompsonsmg", "Thompson (European Assault)", 4050),
        ("bar_ea", "bar", "BAR (European Assault)", 4051),
        ("mp40_ea", "mp40", "MP40 (European Assault)", 4052),
        ("mp44_ea", "mp44", "StG 44 (European Assault)", 4053),
        ("ppsh_smg_ea", "ppsh_smg", "PPSh-41 (European Assault)", 4054),
        ("coop_bergmann_ea", "coop_bergmann", "MP28 (European Assault)", 4055),
        ("m1_garand_ea", "m1_garand", "M1 Garand (European Assault)", 4056),
        ("kar98_ea", "kar98", "Kar98k (European Assault)", 4057),
        ("coop_g43_irons_ea", "coop_g43_irons", "G 43 (European Assault)", 4058),
        ("mosin_nagant_rifle_ea", "mosin_nagant_rifle", "Mosin-Nagant 1891 (European Assault)", 4059),
        ("shotgun_ea", "shotgun", "Shotgun (European Assault)", 4060),
        ("colt45_ea", "colt45", "Colt 45 (European Assault)", 4061),
        ("g43_ea", "g43", "G 43 Sniper (European Assault)", 4062),
        ("garand_scoped_ea", "garand_scoped", "M1 Garand Sniper (European Assault)", 4063),
        ("enfieldsniper_ea", "enfieldsniper", "Lee-Enfield No.4 (T) (European Assault)", 4064),
        ("nagant_sniper_ea", "nagant_sniper", "Mosin-Nagant Sniper (European Assault)", 4065),
        ("bazooka_ea", "bazooka", "M1 Bazooka (European Assault)", 4066),
        ("bazooka_ea2", "bazooka", "M9 Bazooka (European Assault)", 4067),
        ("m2frag_grenade_sp_start_ea", "m2frag_grenade_sp_start", "Frag Grenade (European Assault)", 4068),
        ("mills_grenade_sp_start_ea", "mills_grenade_sp_start", "Mills Bomb (European Assault)", 4069),
        ("steilhandgranate_start_ea", "steilhandgranate_start", "Stielhandgranate (European Assault)", 4070),
    )
]
HEADER = "// HZM coop discguns [gen_disc_stubs.py] - generated, do not edit. "


def _paks():
    out = []
    for d in GAMEDIRS:
        ps = glob.glob(os.path.join(GAME, d, "*.pk3"))
        ps.sort(key=lambda p: os.path.basename(p).lower())
        out += ps
    return out


_IDX = None


def effective(path):
    global _IDX
    if _IDX is None:
        _IDX = {}
        for p in _paks():
            try:
                z = zipfile.ZipFile(p)
            except (zipfile.BadZipFile, OSError):
                continue
            for n in z.namelist():
                _IDX[n.lower()] = (p, n)
    hit = _IDX.get(path.lower())
    if not hit:
        return None, None
    return zipfile.ZipFile(hit[0]).read(hit[1]).decode("latin-1"), os.path.basename(hit[0])


def split_setup(t):
    """-> (text before setup, the setup block, text after it). Brace-matched, comments respected."""
    m = re.search(r"(?mi)^\s*setup\s*\{", t)
    if not m:
        raise ValueError("no setup block")
    i, depth = m.end() - 1, 0
    while i < len(t):
        if t.startswith("//", i):
            i = t.find("\n", i)
            continue
        c = t[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return t[:m.start()], t[m.start():i + 1], t[i + 1:]
        i += 1
    raise ValueError("unbalanced setup block")


def clip_surface(base_text):
    """the surface the base anims toggle with frame commands (`surface <name> +/-nodraw`)"""
    names = sorted(set(re.findall(r"(?mi)^[^/\n]*\bsurface\s+(\S+)\s+[+-]\w+", base_text)))
    return [n for n in names if n.lower() != "all"]     # `surface all` is the TIKI keyword for every surface, not a name


def inline_includes(text, depth=0):
    """[discguns grenades 2026-11-16] the grenade tiks are include-only (`TIKI` + `$include models/weapons/<x>_base.txt` + an
    extra init block): every `$include <file>` line is replaced by the effective copy of that file (recursively, 4 deep), so
    the stub gets the real setup block and the shipped body is self-contained (no include chain left to resolve)."""
    def sub(m):
        if depth >= 4:
            raise SystemExit("$include nested too deep: %s" % m.group(1))
        inc, _pak = effective(m.group(1))
        if inc is None:
            raise SystemExit("$include target not found: %s" % m.group(1))
        inc = re.sub(r"(?mi)^\s*TIKI\s*$", "", inc)
        return "// [gen_disc_stubs] inlined from %s\n%s\n// [gen_disc_stubs] end of %s" % (m.group(1), inline_includes(inc, depth + 1),
                                                                                         m.group(1))
    return re.sub(r"(?mi)^[ \t]*\$include[ \t]+(\S+)[ \t\r]*$", sub, text)


def make(stub, base, display, rank, opts=None):
    opts = opts or {}
    bodyname = opts.get("body", base)
    text, pak = effective("models/weapons/%s.tik" % base)
    if text is None:
        raise SystemExit("base tik not found: %s" % base)
    if re.search(r"(?mi)^\s*\$include", text):
        text = inline_includes(text)
    pre, setup, post = split_setup(text)
    path = re.search(r"(?mi)^\s*path\s+(\S+)", setup).group(1)
    pre = re.sub(r"(?mi)^\s*TIKI\s*$", "", pre).strip()
    if re.search(r"(?mi)^\s*\$include", pre + post):
        raise SystemExit("%s: base tik has $include lines - extend gen_disc_stubs before stubbing it" % base)
    body = post
    body, n = re.subn(r'(?m)^(\s*name\s+)"[^"]*"', lambda m: '%s"%s"' % (m.group(1), display), body, count=1)
    if n != 1:
        raise SystemExit("%s: no name line" % base)
    body, n = re.subn(r"(?mi)^(\s*rank\s+)\d+\s+\d+", lambda m: "%s%d %d" % (m.group(1), rank, rank), body, count=1)
    if n != 1:
        raise SystemExit("%s: no rank line" % base)
    for s in clip_surface(text):
        body = re.sub(r"(?mi)(\bsurface\s+)%s(\s+[+-]\w+)" % re.escape(s), r"\g<1>%s*\2" % s, body)
    for k, v in sorted(opts.get("set", {}).items()):
        mode, key = k.split()
        body, n = re.subn(r"(?mi)^(\s*%s\s+%s\s+)\S+" % (re.escape(mode), re.escape(key)),
                          lambda m: m.group(1) + v, body, count=1)
        if n != 1:
            raise SystemExit("%s: no '%s' line to set" % (base, k))
    if opts.get("silenced"):
        fire = sorted(set(re.findall(r"(?mi)^[^/\n]*\bentry\s+sound\s+(\S+_snd_fire)\b", body)))
        if len(fire) != 1:
            raise SystemExit("%s: silenced needs exactly one fire alias, found %s" % (base, fire))
        body = re.sub(r"(?m)\b%s\b" % re.escape(fire[0]), opts["silenced"], body)
        body, n = silence_flash(body)
        if not n:
            raise SystemExit("%s: silenced, but no muzzle flash frame command found" % base)
    hdr = HEADER + ("BODY of the NEW gun %s on the rig of models/weapons/%s.tik\n" % (display, base) if opts.get("new") else
                    "Shared BODY of the disc-gun variants of models/weapons/%s.tik\n" % base if bodyname == base else
                    "BODY of the disc-gun variant %s of models/weapons/%s.tik\n" % (display, base)) + \
        "// (effective copy: %s): everything below its setup block, name/rank of the variant, clip wildcard.\n" % pak + \
        "// Included by the shipped stub AND by a converted disc tik at the same path - one source of stats and anims.\n"
    body_txt = hdr + "$path %s\n\n" % path + (pre + "\n\n" if pre else "") + body.lstrip("\n")
    stub_txt = "TIKI\n" + HEADER + "Shipped STUB: the base %s look. A converted disc pak (made on the player's own\n" % base + \
        "// PC, never shipped) overrides this path with the disc mesh.\n" + setup + "\n\n" + \
        "$include models/weapons/byo/body/%s.txt\n" % bodyname
    return body_txt, stub_txt, text


FLASH = re.compile(r"muzflash\.tik|muzsprite\.spr|corona_util\.spr", re.I)


def silence_flash(body):
    """the silenced convention (greasegun_silenced / mp40silenced): every live muzzle-flash light and every live tagspawn
    block that spawns a flash (muzflash.tik, muzsprite.spr, corona_util.spr) commented out whole; smoke and shells stay.
    -> (body, number of commands commented)"""
    lines = body.split("\n")
    out, i, n = [], 0, 0
    while i < len(lines):
        ln = lines[i]
        code = ln.split("//")[0]
        if re.match(r"\s*entry\s+tagdlight\b", code):
            out.append("//" + ln)
            n += 1
            i += 1
            continue
        if re.match(r"\s*entry\s+tagspawn(linked)?\s+\S+\s*$", code) and i + 1 < len(lines) and \
                lines[i + 1].split("//")[0].strip() == "(":
            j = i + 1
            while j < len(lines) and lines[j].split("//")[0].strip() != ")":
                j += 1
            block = lines[i:j + 1]
            if any(FLASH.search(b.split("//")[0]) for b in block):
                out += ["//" + b for b in block]
                n += 1
                i = j + 1
                continue
        out.append(ln)
        i += 1
    return "\n".join(out), n


def skd_surfaces(b):
    """surface names of an SKMD (header: numSurfaces @72, ofsSurfaces @84; each surface chains by its ofsEnd @92)"""
    import struct
    ns = struct.unpack_from("<i", b, 72)[0]
    o = struct.unpack_from("<i", b, 84)[0]
    names = []
    for _ in range(ns):
        names.append(b[o + 4:o + 68].split(b"\0")[0].decode("latin-1"))
        o += struct.unpack_from("<i", b, o + 92)[0]
    return names


def clip_gate(base, text):
    """every wildcarded surface must prefix-match exactly ONE surface of the base mesh"""
    setup = split_setup(text)[1]
    path = re.search(r"(?mi)^\s*path\s+(\S+)", setup).group(1)
    skd = re.search(r"(?mi)^\s*skelmodel\s+(\S+)", setup).group(1)
    effective("x")
    hit = _IDX.get(("%s/%s" % (path, skd)).lower())
    if not hit:
        raise SystemExit("%s: skd %s/%s not found" % (base, path, skd))
    names = skd_surfaces(zipfile.ZipFile(hit[0]).read(hit[1]))
    for s in clip_surface(text):
        m = [n for n in names if n.lower().startswith(s.lower())]
        if len(m) != 1:
            raise SystemExit("%s: wildcard %s* matches %s on the base mesh" % (base, s, m))


def outputs():
    out, alias = {}, []
    bodies = {}
    for row in STUBS:
        stub, base, display, rank = row[:4]
        opts = row[4] if len(row) > 4 else {}
        bodyname = opts.get("body", base)
        body, st, text = make(stub, base, display, rank, opts)
        clip_gate(base, text)
        bodies.setdefault(bodyname, body)
        if bodies[bodyname] != body:
            # one body per base: a second variant of the same base needs its own body file (name / rank differ)
            raise SystemExit("two stubs share body %s: give the body a per-stub name" % bodyname)
        out["models/weapons/byo/body/%s.txt" % bodyname] = body
        out["models/weapons/byo/%s.tik" % stub] = st
        bname = re.search(r'(?m)^\s*name\s+"([^"]*)"', split_setup(text)[2]).group(1)
        alias.append('alias models/weapons/byo/%s.tik models/weapons/%s.tik "%s" "%s"' % (stub, base, display, bname))
    out["coop_mod/loadoutdisc.scr"] = disc_table()
    out["scripts/hzm_adssights_stub.txt"] = (
        "// HZM coop discguns [gen_disc_stubs.py] - SHIPPED: each disc-gun stub is its base gun under another name, so it\n"
        "// aims with the base gun's sight row (cgame byo loader). A converted gun pak adds `sight` rows that win for its tikis.\n"
        + "\n".join(alias) + "\n")
    return out


# [discguns unlock 2026-11-16] the loadout's disc-variant fids (PLAN.md section 6): 60 = Frontline, 70.. = European Assault (a
# second EA variant of the same base gun takes 71). A NEW gun (opts "body", e.g. the Sten Mk II(S)) is its own roster weapon,
# not a variant, and is not in this table.
DISC_GAMES = {"fl": (60, "Medal of Honor: Frontline", "FRONTLINE"), "ea": (70, "Medal of Honor: European Assault", "EUROPEAN ASSAULT")}
# [discguns ship 2026-11-22] a second variant of the same base gun gets its own chip name (gen_finish_ui.DISC must agree)
DISC_FIDNAME = {71: "EUROPEAN ASSAULT M9"}


def disc_table():
    """coop_mod/loadoutdisc.scr: level.coop_skinGive[<base give>][<fid>] = the stub, + the per-fid game key and titles, read by
    loadoutpick.scr (loadout_finish / loadout_finResolve / loadout_discOwned). CRLF like the other coop_mod tables."""
    L = ["//GENERATED by docs/tools/gen_disc_stubs.py - do not edit. The bring-your-own-disc gun variants: fids 60-79 of the",
         "//loadout finish slots (60 = Frontline, 70+ = European Assault). Each is the base gun's SHIPPED stub; only a player whose",
         "//PC converted that disc (userinfo \"byo\" carries guns_fl / guns_ea - engine CL_ByoInit) is given it, and only that",
         "//player's own client draws the disc mesh. Run after loadoutskins.scr::skin_init (it owns level.coop_skinGive).",
         "disc_init:{",
         "\tif( level.coop_discN != NIL ){ end }"]
    rows, used, new = [], {}, []
    for row in STUBS:
        stub, base = row[:2]
        opts = row[4] if len(row) > 4 else {}
        if opts.get("new"):
            # [discguns ship 2026-11-22] a NEW disc gun is a roster weapon (loadoutroster.scr) whose UNLOCK is the disc:
            # loadoutpick.scr loadout_isUnlocked grants it only to a player whose userinfo "byo" carries guns_<game>
            new.append('\tlevel.coop_discGun["models/weapons/byo/%s.tik"] = "%s"' % (stub, stub.rsplit("_", 1)[1].rstrip("0123456789")))
            continue
        g = stub.rsplit("_", 1)[1].rstrip("0123456789")      # bazooka_ea2 -> ea
        fid0 = DISC_GAMES[g][0]
        give = "models/weapons/%s.tik" % base
        fid = fid0 + used.get((give, g), 0)
        used[(give, g)] = used.get((give, g), 0) + 1
        assert 60 <= fid <= 79, (stub, fid)
        rows.append('\tlevel.coop_skinGive["%s"][%d] = "models/weapons/byo/%s.tik"' % (give, fid, stub))
    L.append("\tlevel.coop_discN = %d" % len(rows))
    for g, (fid0, title, chip) in sorted(DISC_GAMES.items(), key=lambda kv: kv[1][0]):
        for f in range(fid0, fid0 + 10):
            if any(('][%d] =' % f) in r for r in rows):
                L += ['\tlevel.coop_discGame[%d] = "%s"' % (f, g), '\tlevel.coop_discTitle[%d] = "%s"' % (f, title),
                      '\tlevel.coop_skinFinName[%d] = "%s"' % (f, DISC_FIDNAME.get(f, chip))]
    L += rows + new + ["}end", ""]
    return "\r\n".join(L)


def main(mode):
    out = outputs()
    bad = 0
    for rel, txt in sorted(out.items()):
        p = os.path.join(MOD, rel.replace("/", os.sep))
        old = io.open(p, encoding="latin-1", newline="").read() if os.path.exists(p) else None
        if mode == "check":
            if old != txt:
                print("STALE", rel)
                bad += 1
        elif old != txt:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            io.open(p, "w", encoding="latin-1", newline="\n").write(txt)
            print("wrote", rel)
    if mode == "check":
        print("gen_disc_stubs check: %d stale of %d" % (bad, len(out)))
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "check"))
