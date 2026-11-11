"""Gate: every animation the coop player statemaps name must LOAD in the player model, and the files that define them
must parse the way the engine parses them.

History:
* bug-10394 (v1.10.58-59): cover v3 added `coop_cover_wall_r` to anims_shared.txt, but later-sorting paks carried
  whole-file copies of models/player/base/anims_shared.txt and the LAST one wins. The alias never loaded, the cover legs
  states ping-ponged ("possible infinite state loop") and the server dropped the player. This gate was born: a textual
  check of `coop_*` LEGS anims against the winning copy.
* bug-10899 (v1.10.73): equipping the FG 42 crashed the server the same way, from the TORSO statemap, and this gate
  passed - three blind spots:
    1. it searched the winning copy's TEXT. The stress pak's copy was an old copy cut off before its closing brace with a
       full copy appended; coop_reload_fg42 was IN the text but inside a broken block, so it never LOADED. Now the file
       is parsed with the engine's grammar (tiki_anims.py) and a name counts only if it loads.
    2. torso misses were only a warning - "log spam, not a crash". A torso state whose anim is missing ping-pongs exactly
       like a legs one (RELOAD_WEAPON / RELOAD_MG / STAND): blocking now.
    3. only `coop_*` names and only anims_shared.txt were checked. Now every anim of every legs / torso / action block in
       the coop statemaps is resolved against every file the player model includes (include_BT.txt, include_fps.txt),
       each at its winning copy.
  And a fourth rule: no pak that sorts after the mod's own may carry anims_shared.txt (the mod tree is the one copy) -
  a byte-identical copy is tolerated.

The VFS order is the engine's: main < mainta < maintt, pk3s by name within a folder, the last one wins; the mod tree's
own files ride in the zzzzzz_co-op_hzm_mod_assets_tey pak; a pak in the mod root replaces the deployed one of its name.

    python docs/tools/check_anim_aliases.py [--mod DIR] [--gog DIR] [-v]     exit 1 = something the game would choke on
"""
import glob
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tiki_anims  # noqa: E402


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


MOD = arg("--mod", r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod")
GOG_ROOT = arg("--gog", r"G:\GOG\Medal of Honor - Allied Assault War Chest")
VERBOSE = "-v" in sys.argv
PAKDIR = arg("--pakdir", None)     # staged paks that replace the mod root's of the same name (a fix before it is applied)
BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_anim_aliases_baseline.txt")
SHARED = "models/player/base/anims_shared.txt"
TREE_PAK = "zzzzzz_co-op_hzm_mod_assets_tey.pk3"
STATEMAPS = ["coop_mod/player_legs.st", "coop_mod/player_torso.st"]
INCLUDES = ["models/player/base/include_bt.txt", "models/player/base/include_fps.txt"]


class VFS:
    """last-writer-wins resolution of a game path over main / mainta / maintt + the mod tree"""

    def __init__(self):
        self.where = {}      # lower path -> (pak label, reader)
        self.all = {}        # lower path -> [pak labels in load order]
        for folder in ("main", "mainta", "maintt"):
            paks = {}
            for p in glob.glob(os.path.join(GOG_ROOT, folder, "*.pk3")):
                paks[os.path.basename(p)] = p
            if folder == "maintt":
                for p in glob.glob(os.path.join(MOD, "*.pk3")):
                    paks[os.path.basename(p)] = p       # the mod root's pak replaces the deployed one
                if PAKDIR:
                    for p in glob.glob(os.path.join(PAKDIR, "*.pk3")):
                        paks[os.path.basename(p)] = p
                paks.setdefault(TREE_PAK, None)
            for name in sorted(paks, key=str.lower):
                if paks[name] is None:
                    if name == TREE_PAK:
                        self._add_tree(folder + "/" + name)
                    continue
                try:
                    z = zipfile.ZipFile(paks[name])
                except Exception:
                    continue
                for e in z.namelist():
                    le = e.lower()
                    if le.startswith("models/player/base/") or le.startswith("coop_mod/player"):
                        self._put(le, folder + "/" + name, (lambda z=z, e=e: z.read(e)))
                if name == TREE_PAK:
                    self._add_tree(folder + "/" + name)   # the build repacks this pak from the tree: the tree wins in it

    def _put(self, le, label, reader):
        self.where[le] = (label, reader)
        self.all.setdefault(le, []).append(label)

    def _add_tree(self, label):
        for rel in ("models/player/base",):
            d = os.path.join(MOD, *rel.split("/"))
            for f in glob.glob(os.path.join(d, "*.txt")):
                le = (rel + "/" + os.path.basename(f)).lower()
                self._put(le, label + " (mod tree)", (lambda f=f: open(f, "rb").read()))

    def read(self, path):
        hit = self.where.get(path.lower())
        if not hit:
            return None, None
        return hit[0], hit[1]().decode("latin-1")


def statemap_anims(text):
    """{anim name: [line numbers]} for every anim named in a legs / torso / action block"""
    out = {}
    block, depth, pending = None, 0, None
    for ln, line in enumerate(text.splitlines(), 1):
        code = re.sub(r"//.*", "", line).strip()
        if not code:
            continue
        if code in ("legs", "torso", "action") and depth == 1:
            pending = code
            continue
        if code.startswith("{"):
            depth += 1
            if pending and depth == 2:
                block = pending
            pending = None
            continue
        if code.startswith("}"):
            if depth == 2:
                block = None
            depth -= 1
            continue
        pending = None
        if block and depth == 2:
            m = re.match(r"([A-Za-z0-9_]+)\s*(:|$)", code)
            if m and m.group(1) != "none":
                out.setdefault(m.group(1), []).append(ln)
    return out


def main():
    vfs = VFS()
    fail = []

    # rule 4: one copy of anims_shared.txt - nothing sorting after the mod's pak may shadow it
    tree_shared = os.path.join(MOD, *SHARED.split("/"))
    tree_bytes = open(tree_shared, "rb").read() if os.path.exists(tree_shared) else None
    labels = vfs.all.get(SHARED, [])
    if labels and "(mod tree)" not in labels[-1]:
        win_label, win_text = vfs.read(SHARED)
        if tree_bytes is None or win_text.encode("latin-1") != tree_bytes:
            fail.append("anims_shared.txt is SHADOWED by %s (it sorts after the mod's own copy and differs from it) - "
                        "the mod tree is the one copy: drop the file from that pak" % win_label)

    # rule 1: every included anim file, at its winning copy, parses clean; collect what loads per model chain
    chains = {}
    for inc in INCLUDES:
        label, text = vfs.read(inc)
        if text is None:
            fail.append("%s not found" % inc)
            continue
        loaded = {}
        for f in re.findall(r"^\s*\$include\s+(\S+)", text, re.M):
            fl, ft = vfs.read(f)
            if ft is None:
                if f.lower().startswith("models/player/base/"):
                    fail.append("%s includes %s, which is in no pak" % (inc, f))
                continue
            aliases, bad = tiki_anims.parse(ft)
            if bad:
                fail.append("%s (winning copy %s): %d line(s) the engine logs as 'unknown anim command' - first at line "
                            "%d '%s' inside alias '%s'; every alias after a broken block is lost"
                            % (f, fl, len(bad), bad[0][0], bad[0][1], bad[0][2]))
            for _, a in aliases:
                loaded.setdefault(a.lower(), f)
        chains[inc] = loaded
        if VERBOSE:
            print("%s: %d aliases" % (inc, len(loaded)))

    # rules 2+3: every legs / torso / action anim of the coop statemaps loads in every player model chain.
    # A few STOCK rows name anims no retail or mod file ever defined (pistol_stand_idle, death_back, ...): they sit on
    # rows the game never selects, so they are a frozen baseline - any name NOT on it that does not load fails.
    dead = set()
    if os.path.exists(BASELINE):
        dead = {l.split()[0].lower() for l in open(BASELINE) if l.strip() and not l.startswith("#")}
    nanim = 0
    for sm in STATEMAPS:
        p = os.path.join(MOD, *sm.split("/"))
        if not os.path.exists(p):
            continue
        anims = statemap_anims(open(p, encoding="latin-1").read())
        nanim += len(anims)
        for inc, loaded in chains.items():
            if inc.endswith("include_fps.txt"):
                continue    # the first-person model is the client's view body; the statemaps drive the 3rd-person model
            for a in sorted(anims):
                if a.lower() not in loaded and a.lower() not in dead:
                    fail.append("%s line %d names '%s', which no file of %s loads (the state will ping-pong: 'possible "
                                "infinite state loop')" % (sm, anims[a][0], a, inc))

    # rule 5: every alias of the copy of anims_shared.txt that loads names an .skc the game can find (a missing file drops
    # the alias at load, the same as a missing alias)
    _, shared_text = vfs.read(SHARED)
    if shared_text:
        files = set()
        for folder in ("main", "mainta", "maintt"):
            for p in glob.glob(os.path.join(GOG_ROOT, folder, "*.pk3")) + glob.glob(os.path.join(MOD, "*.pk3")) +                     (glob.glob(os.path.join(PAKDIR, "*.pk3")) if PAKDIR else []):
                try:
                    files |= {n.lower() for n in zipfile.ZipFile(p).namelist()}
                except Exception:
                    pass
        root = "models/human/animation/"
        m = re.search(r"\$path\s+(\S+)", shared_text)
        if m:
            root = m.group(1).lower().rstrip("/") + "/"
        for line in shared_text.splitlines():
            c = re.sub(r"//.*", "", line).split()
            if len(c) >= 2 and c[1].lower().endswith(".skc"):
                f = root + c[1].lower()
                if f not in files and not os.path.exists(os.path.join(MOD, *f.split("/"))):
                    fail.append("anims_shared.txt alias '%s' names %s, which is in no pak" % (c[0], f))

    print("check_anim_aliases: %d statemap anims; anims_shared.txt loads from %s"
          % (nanim, (vfs.where.get(SHARED) or ("none",))[0]))
    if fail:
        print("FAILED:")
        for f in fail:
            print("   " + f)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
