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
#   body       the body file name (default: the base) - a new gun never shares the base's body
#   silenced   the fire alias that replaces the base's, and every live `model models/fx/muzflash.tik` frame command is
#              commented out (the mod's silenced convention: greasegun_silenced / mp40silenced / ppsh43silenced)
#   set        {"<mode> <key>": "<value>"} - stat lines of the body replaced (its OWN stats, the rest stay the base's)
STUBS = [
    ("thompsonsmg_fl", "thompsonsmg", "Thompson (Frontline)", 4000),
    ("bar_fl", "bar", "BAR (Frontline)", 4001),
    ("mp40_fl", "mp40", "MP40 (Frontline)", 4002),
    ("mp44_fl", "mp44", "StG 44 (Frontline)", 4003),
    ("shotgun_fl", "shotgun", "Shotgun (Frontline)", 4004),
    # [coordinator 2026-11-16, 4b + decision 3] EA's Sten is the Mk II(S): its OWN weapon on the Sten rig. Its name does not
    # split to "Sten Mark II", so the base-name lookups (cgame CoopStripSkinSuffix, fgame CoopWeaponBaseName) reach the Sten
    # through its alias row below; its recoil / ROF / pattern rows are its own (coop_mod tables, stem sten_mk2s).
    ("sten_mk2s_ea", "sten", "Sten Mk II(S) (European Assault)", 4100,
     {"body": "sten_mk2s_ea", "silenced": "sten_silenced",
      "set": {"dm firedelay": "0.09", "realism firedelay": "0.09"}}),
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
    return names


def make(stub, base, display, rank, opts=None):
    opts = opts or {}
    bodyname = opts.get("body", base)
    text, pak = effective("models/weapons/%s.tik" % base)
    if text is None:
        raise SystemExit("base tik not found: %s" % base)
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
    hdr = HEADER + ("Shared BODY of the disc-gun variants of models/weapons/%s.tik\n" % base if bodyname == base else
                    "BODY of the NEW gun %s on the rig of models/weapons/%s.tik\n" % (display, base)) + \
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
    out["scripts/hzm_adssights_stub.txt"] = (
        "// HZM coop discguns [gen_disc_stubs.py] - SHIPPED: each disc-gun stub is its base gun under another name, so it\n"
        "// aims with the base gun's sight row (cgame byo loader). A converted gun pak adds `sight` rows that win for its tikis.\n"
        + "\n".join(alias) + "\n")
    return out


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
