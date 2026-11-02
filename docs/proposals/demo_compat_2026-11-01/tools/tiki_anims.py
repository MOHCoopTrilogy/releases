"""tiki_anims.py - the network anim numbering of a TIKI, at any mod revision.

The anim index a demo carries (entityState frameInfo[].index) is the position of the alias in
the tiki's anim list AFTER the engine sorts it and drops the clips that fail to load:
  tiki/tiki_anim.cpp  TIKI_GetAnimOrder  qsort by Q_stricmp(alias)
  tiki/tiki_files.cpp TIKI_InitTiki      "Failed to load animation" -> continue (no index)
So adding, renaming or removing any alias - or adding/removing its .skc - renumbers every anim
that sorts after it.

Files are looked up like the game's virtual FS for a release: the mod (hzm-mohaa-coop-mod at a
git revision, or the working tree with rev=None) beats the retail paks (main/Pak*, mainta/pak*,
maintt/pak* of the GOG install; later pak wins). .skc files are gitignored in the mod, so an old
revision's clip set is approximated as "tracked at that rev, or present in the working tree now".

usage:
  python tiki_anims.py models/player/american_army.tik [--rev <commit>] [--map m2l2a]
  python tiki_anims.py <tik> --diff <oldrev> [<newrev>]   # what each old index means now
"""
import argparse, glob, os, re, subprocess, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
MOD = os.path.join(REPO, "hzm-mohaa-coop-mod")
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"


class VFS:
    def __init__(self, rev=None, gog=GOG, stack=None):
        """stack: an explicit pk3 list in mount order (later wins) - the installed game, no repo."""
        self.rev = rev
        self.retail = {}  # lower path -> (zipfile, name)
        self.work, self.tracked = {}, {}
        if stack is not None:
            for p in stack:
                z = zipfile.ZipFile(p)
                for n in z.namelist():
                    self.retail[n.lower()] = (z, n)
            return
        for d in ("main", "mainta", "maintt"):
            for p in sorted(glob.glob(os.path.join(gog, d, "*.pk3")), key=lambda s: s.lower()):
                if not os.path.basename(p).lower().startswith("pak"):
                    continue  # retail only; the mod comes from the repo
                z = zipfile.ZipFile(p)
                for n in z.namelist():
                    self.retail[n.lower()] = (z, n)
        for root, _d, files in os.walk(MOD):
            if ".git" in root:
                continue
            for f in files:
                full = os.path.join(root, f)
                self.work[os.path.relpath(full, MOD).replace("\\", "/").lower()] = full
        if rev:
            out = subprocess.run(["git", "-C", MOD, "ls-tree", "-r", "--name-only", rev],
                                 capture_output=True, text=True, check=True).stdout
            self.tracked = {n.lower(): n for n in out.splitlines()}

    def read(self, path):
        k = path.replace("\\", "/").lower().lstrip("/")
        if self.rev:
            if k in self.tracked:
                return subprocess.run(["git", "-C", MOD, "show", "%s:%s" % (self.rev, self.tracked[k])],
                                      capture_output=True, check=True).stdout.decode("latin-1")
            # untracked text in the working tree is not trusted for an old rev (except clips, below)
        elif k in self.work:
            return open(self.work[k], "rb").read().decode("latin-1")
        if k in self.retail:
            z, n = self.retail[k]
            return z.read(n).decode("latin-1")
        return None

    def exists(self, path):
        k = path.replace("\\", "/").lower().lstrip("/")
        return k in self.tracked or k in self.work or k in self.retail


# ------------------------------------------------------------- tokenizer (TikiScript-like)
TOK = re.compile(r'"([^"]*)"|(\S+)')


class Script:
    def __init__(self, vfs, path, macros, warn):
        self.vfs, self.warn = vfs, warn
        self.stack = []  # [lines, lineno, path_prefix, macros, filename]
        self.push(path, dict(macros))

    def push(self, path, macros):
        txt = self.vfs.read(path)
        if txt is None:
            self.warn.append("missing include " + path)
            return
        # one pass, so "//***" is a line comment and not the start of a block comment
        txt = re.sub(r'("[^"\n]*")|//[^\n]*|/\*.*?\*/',
                     lambda m: m.group(1) or "\n" * m.group(0).count("\n"), txt, flags=re.S)
        lines = txt.splitlines()
        self.stack.append([lines, 0, "", macros, path, []])

    def expand(self, tok, macros):
        def sub(m):
            v = macros.get(m.group(1).lower())
            return v if v is not None else m.group(0)
        return re.sub(r"\$([A-Za-z0-9_]+)\$?", sub, tok)

    def line_tokens(self):
        """Yield (tokens_of_line, script_frame) with $include/$define/$path handled."""
        while self.stack:
            fr = self.stack[-1]
            lines = fr[0]
            if fr[1] >= len(lines):
                self.stack.pop()
                continue
            ln = lines[fr[1]]
            fr[1] += 1
            toks = [a if a else b for a, b in TOK.findall(ln)]
            if not toks:
                continue
            c = toks[0].lower()
            if c == "$define" and len(toks) >= 3:
                fr[3][toks[1].lower()] = toks[2]
                continue
            if c == "$include" and len(toks) >= 2:
                self.push(toks[1], fr[3])
                continue
            if c == "$path" and len(toks) >= 2:
                # applied by the parser, so a $path inside a skipped includes/$mapspec block does
                # not leak (retail new_generic_human.tik has one: ".../mp_tunisia_lib.tik")
                yield ["@@PATH", toks[1]], fr
                continue
            yield [self.expand(t, fr[3]) for t in toks], fr


def tiki_anims(vfs, tik, mapname="utils", servertype="breakthroughserver"):
    """Return (ordered_alias_list, warnings) in network index order."""
    warn = []
    sc = Script(vfs, tik, {}, warn)
    loaded = []
    gen = sc.line_tokens()
    flat = []  # flatten to (token, frame, first_on_line, line_id)
    lid = 0
    for toks, fr in gen:
        lid += 1
        for i, t in enumerate(toks):
            flat.append((t, fr, i == 0, lid))
    i = 0
    n = len(flat)

    def skip_block(i):
        depth = 0
        while i < n:
            t = flat[i][0]
            if t == "{":
                depth += 1
            elif t == "}":
                depth -= 1
                if depth <= 0:
                    return i + 1
            i += 1
        return i

    def setpath(k):
        p = flat[k + 1][0]
        flat[k][1][2] = p if p.endswith(("/", "\\")) else p + "/"

    while i < n:
        t = flat[i][0].lower()
        if flat[i][0] == "@@PATH":
            setpath(i); i += 2
            continue
        if t == "animations":
            i += 1
            if i < n and flat[i][0] == "{":
                i += 1
            mapspec_on = False
            while i < n:
                tok, fr, _first, line = flat[i]
                if tok == "@@PATH":
                    setpath(i); i += 2
                    continue
                path = fr[2]
                if tok == "}":
                    i += 1
                    if not mapspec_on:
                        break
                    mapspec_on = False
                    continue
                if tok.lower() == "$mapspec":
                    i += 1
                    names = []
                    while i < n and flat[i][0] != "{":
                        names.append(flat[i][0]); i += 1
                    hit = any(mapname.lower().startswith(x.lower()) for x in names)
                    if hit:
                        mapspec_on = True
                        i += 1
                    else:
                        i = skip_block(i)
                    warn.append("$mapspec %s -> %s" % (names, hit))
                    continue
                alias = tok
                fname = flat[i + 1][0] if i + 1 < n and flat[i + 1][3] == line else ""
                j = i + 2
                while j < n and flat[j][3] == line:
                    j += 1  # flags
                if j < n and flat[j][0] == "{":
                    j = skip_block(j)
                i = j
                full = path + fname
                ok = vfs.exists(full)
                if not ok:
                    warn.append("clip missing (anim dropped): %s %s" % (alias, full))
                    continue
                loaded.append(alias)
            continue
        if t == "setup":
            j = i + 1
            end = skip_block(j)
            for k in range(j, end):
                if flat[k][0].lower() == "path" and k + 1 < end:
                    p = flat[k + 1][0]
                    flat[k][1][2] = p if p.endswith(("/", "\\")) else p + "/"
                elif flat[k][0] == "@@PATH":
                    setpath(k)
            i = end
            continue
        if t == "includes":
            j = i + 1
            names = []
            while j < n and flat[j][0] != "{":
                names.append(flat[j][0]); j += 1
            hit = any(mapname.lower().startswith(x.lower()) or servertype.startswith(x.lower()) for x in names)
            warn.append("includes %s -> %s" % (names, hit))
            i = j + 1 if hit else skip_block(j)
            continue
        if t in ("{", "}"):
            i += 1
            continue
        if i + 1 < n and flat[i + 1][0] == "{":
            i = skip_block(i + 1)
            continue
        i += 1
    order = sorted(range(len(loaded)), key=lambda k: loaded[k].upper())  # Q_stricmp folds to UPPER: "_" sorts after letters
    return [loaded[k] for k in order], warn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tik")
    ap.add_argument("--rev")
    ap.add_argument("--map", default="utils")
    ap.add_argument("--diff", nargs="+", metavar="REV")
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args()
    if a.diff:
        old, w1 = tiki_anims(VFS(a.diff[0]), a.tik, a.map)
        new, w2 = tiki_anims(VFS(a.diff[1] if len(a.diff) > 1 else None), a.tik, a.map)
        print("old %d anims, new %d anims" % (len(old), len(new)))
        moved = sum(1 for k in range(min(len(old), len(new))) if old[k].lower() != new[k].lower())
        first = next((k for k in range(min(len(old), len(new))) if old[k].lower() != new[k].lower()), None)
        print("indices whose meaning changed: %d (first at %s)" % (moved, first))
        so, sn = set(x.lower() for x in old), set(x.lower() for x in new)
        print("added:", sorted(sn - so)[:40])
        print("removed:", sorted(so - sn)[:40])
        return
    lst, warn = tiki_anims(VFS(a.rev), a.tik, a.map)
    for k, al in enumerate(lst):
        print(k, al)
    if a.v:
        for w in warn:
            print("#", w, file=sys.stderr)


if __name__ == "__main__":
    main()


def install_stack(gog=GOG, home=None, exclude=(), extra=()):
    """pk3s the way the engine mounts them: main < mainta < maintt, basepath then homepath, by name."""
    out = []
    for d in ("main", "mainta", "maintt"):
        for root in [gog] + ([home] if home else []):
            ps = sorted(glob.glob(os.path.join(root, d, "*.pk3")), key=lambda s: os.path.basename(s).lower())
            out += [p for p in ps if os.path.basename(p).lower() not in exclude]
    out += list(extra)
    return out
