"""Loading-screen lint (docs/proposals/loading_screen_2026-09-26/research.md, section 5 P0.1). Exit 1 on any failure.

ui/loadingbar.txt
  * running brace depth never negative, 0 at every 'resource' and at the end (TRAPS T1: raw counts lie)
  * the four ENGINE-ADDRESSED widget names (cl_ui.cpp PassEventToWidget, first match only) each EXACTLY once
  * continuebutton byte-identical to retail main/Pak0.pk3 (single player's Continue must keep working)
  * every shader it names resolves: a coop scripts/*.shader block, a retail shader, or an image path
  * every scalecvar cvar is seeded by coop_defaults.cfg (it must exist when the urc is PARSED - Cvar_Find)
scripts/coop_loadscreens.shader, block hzmLoadMedal
  * defined exactly once across the coop scripts (TRAPS T6)
  * every image exists, 256x256, 32-bit, uncompressed TGA (type 2), with real alpha
  * star frames: outside radius 126 px fully transparent (clamp/rotate safe), frame count 24
  * animMap rate is not an aliasing speed (24 or 48 frames/s = 72 or 144 deg/s with 3-deg frames)
ui/loadhints.txt (skipped while absent)
  * ASCII 32-126 only; optional [C]/[M]/[G] tag; text <= 90 chars and <= 500 px in verdana-12 using the
    retail .RitualFont metrics (the label clips, it never wraps); no duplicates; 40-60 hints
"""
import glob
import io
import os
import re
import struct
import sys
import zipfile

ROOT = r"C:\mohaa-coop-dev"
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
GAME = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
ENGINE_NAMES = ("continuebutton", "loadingflasher", "loadingbar", "loadingbar_border")
MAX_PX, MAX_CHARS = 500.0, 90

fails = []


def fail(msg):
    fails.append(msg)
    print("FAIL", msg)


def ok(msg):
    print("ok  ", msg)


def retail_read(name):
    for p in sorted(glob.glob(os.path.join(GAME, "main", "*.pk3")), key=str.lower):
        z = zipfile.ZipFile(p)
        for n in z.namelist():
            if n.lower() == name.lower():
                return z.read(n)
    return None


def retail_shader_names():
    names = set()
    for d in ("main", "mainta", "maintt"):
        for p in glob.glob(os.path.join(GAME, d, "*.pk3")):
            if "co-op_hzm_mod" in p:
                continue
            try:
                z = zipfile.ZipFile(p)
            except Exception:
                continue
            for n in z.namelist():
                if n.lower().startswith("scripts/") and n.lower().endswith(".shader"):
                    names |= shader_blocks(z.read(n).decode("latin1"), strict=False).keys()
    return names


def shader_blocks(text, strict=True):
    text = re.sub(r"//[^\n]*", "", text)
    toks = re.findall(r'"[^"]*"|[{}]|[^\s{}]+', text)
    out, depth, name, body = {}, 0, None, []
    for t in toks:
        if t == "{":
            depth += 1
            if depth > 1:
                body.append(t)
        elif t == "}":
            depth -= 1
            if depth < 0:
                if strict:
                    raise ValueError("negative brace depth")
                depth = 0  # retail shader files are not all balanced; recover
                continue
            if depth == 0 and name:
                out.setdefault(name.lower(), []).append(body)
                name, body = None, []
            else:
                body.append(t)
        elif depth == 0:
            name = t.strip('"')
        else:
            body.append(t)
    if depth != 0 and strict:
        raise ValueError("unbalanced braces (depth %d at EOF)" % depth)
    return out


def depth_scan_urc(path, text):
    depth, bad = 0, False
    for ln, line in enumerate(text.splitlines(), 1):
        code = re.sub(r"//.*", "", line)
        code = re.sub(r'"[^"]*"', '""', code)
        if code.strip() == "resource" and depth != 0:
            fail("%s:%d 'resource' at brace depth %d" % (path, ln, depth))
            bad = True
        for ch in code:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth < 0:
                    fail("%s:%d brace depth went negative" % (path, ln))
                    return
    if depth != 0:
        fail("%s: brace depth %d at EOF" % (path, depth))
    elif not bad:
        ok("%s: running brace depth clean" % os.path.basename(path))


def resources(text):
    body = re.sub(r"//[^\n]*", "", text)
    return re.findall(r"resource\s+(\w+)\s*{(.*?)}", body, re.S)


def lint_loadingbar(coop_shaders, retail_names, seeded):
    p = os.path.join(MOD, "ui", "loadingbar.txt")
    text = open(p, "rb").read().decode("latin1")
    depth_scan_urc(p, text)
    res = resources(text)
    names = [re.search(r'name\s+"([^"]*)"', b).group(1) for _, b in res]
    for n in ENGINE_NAMES:
        c = names.count(n)
        (ok if c == 1 else fail)("loadingbar.txt: widget %s present %d time(s)" % (n, c))
    # continuebutton byte-identical to retail (compare the resource body, line endings normalised)
    retail = retail_read("ui/loadingbar.txt").decode("latin1").replace("\r\n", "\n")
    ours = text.replace("\r\n", "\n")
    rx = r'resource\s+Button\s*{\s*name "continuebutton".*?\n}'
    a, b = re.search(rx, retail, re.S), re.search(rx, ours, re.S)
    (ok if a and b and a.group(0) == b.group(0) else fail)("loadingbar.txt: continuebutton identical to retail")
    for cls, body in res:
        for sh in re.findall(r'^\s*shader\s+"?([^"\s]+)"?', body, re.M):
            s = sh.lower()
            if s in coop_shaders or s in retail_names:
                ok("loadingbar.txt: shader %s resolves" % sh)
            elif "/" in s:
                ok("loadingbar.txt: shader %s is an image path (implicit shader)" % sh)
            else:
                fail("loadingbar.txt: shader %s is defined nowhere" % sh)
        for cv in re.findall(r"^\s*scalecvar\s+(\S+)", body, re.M):
            (ok if cv.lower() in seeded else fail)("loadingbar.txt: scalecvar %s seeded in coop_defaults.cfg" % cv)


def tga_info(path):
    b = open(path, "rb").read()
    idlen, cmap, itype = b[0], b[1], b[2]
    w, h = struct.unpack("<HH", b[12:16])
    bpp, desc = b[16], b[17]
    return b, idlen, cmap, itype, w, h, bpp, desc


def lint_medal(coop_shader_files):
    hits = [(f, blk) for f, blks in coop_shader_files.items() for n, blk in blks.items() if n == "hzmloadmedal"]
    count = sum(len(blk) for _, blk in hits)
    (ok if count == 1 else fail)("hzmLoadMedal defined %d time(s) across the coop scripts" % count)
    if not hits:
        return
    body = hits[0][1][0]
    imgs = []
    i = 0
    while i < len(body):
        t = body[i].lower()
        if t in ("map", "clampmap"):
            imgs.append(("static", body[i + 1]))
            i += 2
        elif t == "animmap":
            rate = float(body[i + 1])
            j = i + 2
            frames = []
            while j < len(body) and body[j] not in ("{", "}") and "/" in body[j]:
                frames.append(body[j])
                j += 1
            (ok if len(frames) == 24 else fail)("hzmLoadMedal animMap has %d frames" % len(frames))
            (fail if rate in (24.0, 48.0) else ok)("hzmLoadMedal animMap %g frames/s = %g deg/s" % (rate, rate * 3))
            imgs += [("star", f) for f in frames]
            i = j
        else:
            i += 1
    for kind, rel in imgs:
        p = os.path.join(MOD, rel.replace("/", os.sep))
        if not os.path.exists(p):
            fail("missing image %s" % rel)
            continue
        b, idlen, cmap, itype, w, h, bpp, desc = tga_info(p)
        good = itype == 2 and w == 256 and h == 256 and bpp == 32 and cmap == 0
        if not good:
            fail("%s: type %d %dx%d %d bpp (want uncompressed type 2, 256x256, 32 bpp)" % (rel, itype, w, h, bpp))
            continue
        if desc & 0x20:
            # the engine ignores this bit (tr_image_tga.c: flip #if 0'd), so the image would load UPSIDE DOWN
            fail("%s: TGA declares top-down rows (descriptor 0x%02x); the engine needs bottom-up (bug-3019)" % (rel, desc))
            continue
        px = b[18 + idlen:18 + idlen + w * h * 4]
        alphas = px[3::4]
        if min(alphas) == 255:
            fail("%s: alpha channel is fully opaque" % rel)
            continue
        if kind == "star":
            outside = 0
            for y in range(h):
                for x in range(w):
                    if (x - 127.5) ** 2 + (y - 127.5) ** 2 > 126.0 ** 2 and alphas[y * w + x]:
                        outside += 1
            if outside:
                fail("%s: %d non-transparent texels outside r=126" % (rel, outside))
                continue
    ok("hzmLoadMedal: %d images checked (256x256 32-bit uncompressed TGA with alpha)" % len(imgs))


def ritual_widths():
    b = None
    for p in sorted(glob.glob(os.path.join(GAME, "main", "*.pk3")), key=str.lower):
        z = zipfile.ZipFile(p)
        for n in z.namelist():
            if n.lower() == "fonts/verdana-12.ritualfont":
                b = z.read(n).decode("latin1")
    ind = [int(x) for x in re.search(r"indirections\s*{([^}]*)}", b).group(1).split()]
    locs = re.findall(r"{\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*}", b[b.find("locations"):])
    widths = {}
    for c in range(32, 127):
        i = ind[c] if ind[c] >= 0 else ind[ord("?")]
        widths[chr(c)] = float(locs[i][2])
    return widths


def lint_hints():
    p = os.path.join(MOD, "ui", "loadhints.txt")
    if not os.path.exists(p):
        print("skip ui/loadhints.txt (not present yet)")
        return
    raw = open(p, "rb").read()
    widths = ritual_widths()
    seen, count, worst = set(), 0, (0.0, "")
    tags = {"C": 0, "M": 0, "G": 0}
    for ln, line in enumerate(raw.split(b"\n"), 1):
        line = line.rstrip(b"\r")
        s = line.strip()
        if not s or s.startswith(b"//") or s.startswith(b"#"):
            continue
        bad = [c for c in s if c < 32 or c > 126]
        if bad:
            fail("loadhints.txt:%d non-ASCII/control byte(s) %r" % (ln, bytes(bad[:4])))
            continue
        t = s.decode("ascii")
        m = re.match(r"^\[([CMG])\]\s*(.*)$", t)
        tag, text = (m.group(1), m.group(2)) if m else ("G", t)
        tags[tag] += 1
        if len(text) > MAX_CHARS:
            fail("loadhints.txt:%d %d chars > %d" % (ln, len(text), MAX_CHARS))
        px = sum(widths[c] for c in text)
        if px > MAX_PX:
            fail("loadhints.txt:%d %.0f px > %.0f in verdana-12" % (ln, px, MAX_PX))
        worst = max(worst, (px, text))
        if text.lower() in seen:
            fail("loadhints.txt:%d duplicate hint" % ln)
        seen.add(text.lower())
        count += 1
    # the one hint an OLD exe shows (coop_defaults.cfg seed): same width rules, and it must be mode-neutral
    cfg = open(os.path.join(MOD, "coop_defaults.cfg"), "rb").read().decode("latin1")
    m = re.search(r'^\s*set\s+ui_loadhint\s+"([^"]*)"', cfg, re.M)
    if not m:
        fail("coop_defaults.cfg: no 'set ui_loadhint' fallback seed")
    else:
        fb = m.group(1)
        px = sum(widths.get(c, 99.0) for c in fb)
        (ok if len(fb) <= MAX_CHARS and px <= MAX_PX else fail)(
            "coop_defaults.cfg fallback hint: %d chars, %.0f px: %s" % (len(fb), px, fb))
    # upper bound = the exe's table (client/cl_ui.cpp LOADHINTS_MAX 256; an exe older than 2026-10-05 shows only the first 128); lines past it are silently dropped
    (ok if 40 <= count <= 256 else fail)("loadhints.txt: %d hints (C %d / M %d / G %d)" % (count, tags["C"], tags["M"], tags["G"]))
    ok("loadhints.txt: widest line %.0f px: %s" % worst)


def lint_memorial(coop_shader_files):
    """Launch memorial card (docs/tools/gen_memorial.py): one hzmMemorial shader, its TGA uncompressed, 2048x1024,
    BOTTOM-UP (bug-3019), and byte-identical to what the generator produces now."""
    hits = [blk for f, blks in coop_shader_files.items() for n, blk in blks.items() if n == "hzmmemorial"]
    count = sum(len(b) for b in hits)
    if count == 0:
        print("skip memorial (no hzmMemorial shader yet)")
        return
    (ok if count == 1 else fail)("hzmMemorial defined %d time(s) across the coop scripts" % count)
    rel = "ui/hzm_memorial/memorial.tga"
    p = os.path.join(MOD, rel.replace("/", os.sep))
    if not os.path.exists(p):
        fail("missing image %s" % rel)
        return
    b, idlen, cmap, itype, w, h, bpp, desc = tga_info(p)
    good = itype == 2 and cmap == 0 and (w, h) == (2048, 1024) and bpp in (24, 32) and not (desc & 0x20)
    (ok if good else fail)("%s: type %d %dx%d %d bpp desc 0x%02x (want uncompressed, 2048x1024, bottom-up)"
                           % (rel, itype, w, h, bpp, desc))
    gen = os.path.join(ROOT, "docs", "tools", "gen_memorial.py")
    import subprocess
    r = subprocess.run([sys.executable, gen, os.path.dirname(p), "--check"], capture_output=True, text=True)
    (ok if r.returncode == 0 else fail)("memorial.tga matches gen_memorial.py output (%s)" % r.stdout.strip())


def lint_morph(coop_shader_files):
    """Looping old<->new medal (design v4, gen_loadscreen_medal.py --morph): the whole shader file is generated, so it
    and its 6 textures must be byte-identical to the generator's output for the speed/period its header records; all
    stages must share ONE tcMod rotate (rigid logo) and one wave frequency, within MAX_SHADER_STAGES (8, both renderers)."""
    hits = [(f, blk) for f, blks in coop_shader_files.items() for n, blk in blks.items() if n == "hzmloadmedalmorph"]
    count = sum(len(blk) for _, blk in hits)
    if count == 0:
        print("skip morph (no hzmLoadMedalMorph shader yet)")
        return
    (ok if count == 1 else fail)("hzmLoadMedalMorph defined %d time(s) across the coop scripts" % count)
    path, body = hits[0][0], hits[0][1][0]
    stages = body.count("{")
    (ok if 2 <= stages <= 8 else fail)("hzmLoadMedalMorph: %d stages (MAX_SHADER_STAGES 8)" % stages)
    low = [t.lower() for t in body]
    rot = {body[i + 2] for i, t in enumerate(low) if t == "tcmod" and low[i + 1] == "rotate"}
    freq = {body[i + 6] for i, t in enumerate(low) if t == "alphagen" and low[i + 1] == "wave"}
    (ok if len(rot) == 1 and low.count("tcmod") == stages else fail)(
        "hzmLoadMedalMorph: every stage turns at one shared rate %s" % sorted(rot))
    (ok if len(freq) == 1 else fail)("hzmLoadMedalMorph: every fade shares one frequency %s" % sorted(freq))
    # bug-3059: tcMod rotate + clampMap repeats the EDGE texel into the quad's corners; it must be transparent at every
    # mip level the 48..216 px widget can use (LOD <= 2.4 -> levels 0..3), or the rim smears out as an X
    from PIL import Image
    for tp in sorted(glob.glob(os.path.join(MOD, "ui", "hzm_loadscreen", "morph_*.tga"))):
        a, bad = Image.open(tp).getchannel("A"), []
        for lvl in range(4):
            w, h = a.size
            edge = max(a.crop(box).getextrema()[1] for box in ((0, 0, w, 1), (0, h - 1, w, h), (0, 0, 1, h), (w - 1, 0, w, h)))
            if edge:
                bad.append("L%d=%d" % (lvl, edge))
            a = a.reduce(2)
        (ok if not bad else fail)("%s: edge texels transparent at mip levels 0..3 %s" % (os.path.basename(tp), " ".join(bad)))
    m = re.search(r"--morph --speed (\S+) --period (\S+)\.", open(path, "rb").read().decode("latin1"))
    if not m:
        fail("%s: no generator header (--morph --speed S --period T)" % os.path.basename(path))
        return
    gen = os.path.join(ROOT, "docs", "tools", "gen_loadscreen_medal.py")
    import subprocess
    r = subprocess.run([sys.executable, gen, os.path.join(MOD, "ui", "hzm_loadscreen"), "--morph", "--speed", m.group(1),
                        "--period", m.group(2), "--shader", path, "--check"], capture_output=True, text=True)
    (ok if r.returncode == 0 and "WARNING" not in r.stdout else fail)(
        "%s + morph_*.tga match gen_loadscreen_medal.py --morph --speed %s --period %s (%s)"
        % (os.path.basename(path), m.group(1), m.group(2), r.stdout.strip().replace("\n", " / ")))


def lint_nav(coop_shader_files):
    """Hint arrows (user 2026-09-27): hzmLoadHintPrev/Next once each; their TGAs uncompressed 32x64 32-bit bottom-up and
    byte-identical to gen_loadscreen_medal.py --arrows; the two widgets gated on ui_loadHintNavOn, which only an exe
    that can page publishes - so an old exe never shows dead arrows. No cfg may seed that cvar."""
    names = {n for blks in coop_shader_files.values() for n in blks}
    if "hzmloadhintprev" not in names and "hzmloadhintnext" not in names:
        print("skip hint arrows (no hzmLoadHintPrev/Next shader yet)")
        return
    for sh in ("hzmloadhintprev", "hzmloadhintnext"):
        count = sum(len(blks.get(sh, [])) for blks in coop_shader_files.values())
        (ok if count == 1 else fail)("%s defined %d time(s) across the coop scripts" % (sh, count))
    for n in ("hint_prev.tga", "hint_next.tga"):
        p = os.path.join(MOD, "ui", "hzm_loadscreen", n)
        if not os.path.exists(p):
            fail("missing image ui/hzm_loadscreen/%s" % n)
            continue
        b, idlen, cmap, itype, w, h, bpp, desc = tga_info(p)
        (ok if (itype, cmap, w, h, bpp) == (2, 0, 32, 64, 32) and not desc & 0x20 else fail)(
            "%s: type %d %dx%d %d bpp desc 0x%02x (want uncompressed 32x64 32 bpp bottom-up)" % (n, itype, w, h, bpp, desc))
    gen = os.path.join(ROOT, "docs", "tools", "gen_loadscreen_medal.py")
    import subprocess
    r = subprocess.run([sys.executable, gen, os.path.join(MOD, "ui", "hzm_loadscreen"), "--arrows", "--check"],
                       capture_output=True, text=True)
    (ok if r.returncode == 0 else fail)("hint_prev/next.tga match gen_loadscreen_medal.py --arrows (%s)" % r.stdout.strip())
    bar = open(os.path.join(MOD, "ui", "loadingbar.txt"), "rb").read().decode("latin1")
    for wn in ("hzm_loadhint_prev", "hzm_loadhint_next"):
        m = re.search(r'name\s+"%s"(.*?)\n}' % wn, bar, re.S)
        (ok if m and "ui_loadHintNavOn" in m.group(1) else fail)("loadingbar.txt: %s gated on ui_loadHintNavOn" % wn)
    for cfg in ("coop_defaults.cfg", "autoexec.cfg"):
        t = open(os.path.join(MOD, cfg), "rb").read().decode("latin1")
        (fail if re.search(r"^\s*seta?\s+ui_loadHintNavOn\b", t, re.M | re.I) else ok)(
            "%s does not seed ui_loadHintNavOn (an old exe must keep the arrows hidden)" % cfg)


def seeded_cvars():
    t = open(os.path.join(MOD, "coop_defaults.cfg"), "rb").read().decode("latin1")
    return {m.lower() for m in re.findall(r"^\s*seta?\s+(\S+)", t, re.M)}


def main():
    coop_files = {}
    for sp in glob.glob(os.path.join(MOD, "scripts", "*.shader")):
        try:
            coop_files[sp] = shader_blocks(open(sp, "rb").read().decode("latin1"))
        except ValueError as e:
            if "loadscreen" in sp:
                fail("%s: %s" % (sp, e))
            coop_files[sp] = {}
    coop_names = set()
    for blks in coop_files.values():
        coop_names |= blks.keys()
    lint_loadingbar(coop_names, retail_shader_names(), seeded_cvars())
    lint_medal({f: b for f, b in coop_files.items()})
    lint_memorial(coop_files)
    lint_morph(coop_files)
    lint_nav(coop_files)
    lint_hints()
    print("RESULT:", "FAIL (%d)" % len(fails) if fails else "OK")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
