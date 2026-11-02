"""hypo.py - which content revision was a demo recorded with?

Rebuilds the anim numbering for several candidate content dates and scores how sensible the
demo's AI anims look under each (an mp40 soldier should mostly play mp40_* / generic / death
clips). The best-scoring date is the content the demo was recorded with.

Layers (later wins), mirroring a release install:
  1. retail + third-party pk3s in the GOG install (every pk3 that is not an HZM coop pak)
  2. hzm-mohaa-coop-mod/models at the candidate revision        (= zzzzzz_co-op_hzm_mod_assets_tex)
  3. docs/tools/assets/fixes at the candidate date               (= zzzzzzzzzz_coop_fixes)
  4. optional: the later coop overlay pk3s as installed now      (fixes2, fx, stress, late, tey)

usage: python hypo.py <samples.json from demo_probe --samples> <mapname> [date ...]
"""
import collections, json, os, subprocess, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tiki_anims as T  # noqa: E402

REPO = T.REPO
COOP_PAKS = ("zzzzzz_co-op_hzm", "zzzzzzzzz", "zzzzzzzzzzzzzz_hzm_menus3d")
LATE = ("zzzzzzzzzzzz_coop_fixes2.pk3", "zzzzzzzzzzzzz_coop_fx.pk3", "zzzzzzzzzzzzz_coop_stress.pk3",
        "zzzzzzzzzzzzzz_coop_late.pk3", "zzzzzz_co-op_hzm_mod_assets_tey.pk3")


def rev_at(repo, date):
    return subprocess.run(["git", "-C", repo, "rev-list", "-1", "--before=" + date + " 23:59", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()


class GitLayer:
    def __init__(self, repo, prefix, rev):
        self.repo, self.prefix, self.rev = repo, prefix.rstrip("/") + "/", rev
        out = subprocess.run(["git", "-C", repo, "ls-tree", "-r", "--name-only", rev, self.prefix],
                             capture_output=True, text=True, check=True).stdout
        self.files = {n[len(self.prefix):].lower(): n for n in out.splitlines()}

    def read(self, k):
        n = self.files.get(k)
        if n is None:
            return None
        return subprocess.run(["git", "-C", self.repo, "show", "%s:%s" % (self.rev, n)],
                              capture_output=True, check=True).stdout.decode("latin-1")


class StackVFS(T.VFS):
    def __init__(self, date, with_late=False, with_fixes=True):
        base = [p for p in T.install_stack()
                if not os.path.basename(p).lower().startswith(COOP_PAKS)]
        T.VFS.__init__(self, stack=base)
        mod = os.path.join(REPO, "hzm-mohaa-coop-mod")
        self.layers = [GitLayer(mod, "models", rev_at(mod, date)),
                       GitLayer(REPO, "docs/tools/assets/fixes", rev_at(REPO, date))][:2 if with_fixes else 1]
        self.late = []
        if with_late:
            for p in T.install_stack():
                if os.path.basename(p).lower() in LATE:
                    z = zipfile.ZipFile(p)
                    self.late.append({n.lower(): (z, n) for n in z.namelist()})
        # clips are gitignored: trust the working tree's .skc set as "present"
        self.clips = set()
        for root, _d, files in os.walk(os.path.join(mod, "models")):
            for f in files:
                self.clips.add(os.path.relpath(os.path.join(root, f), mod).replace("\\", "/").lower())

    def read(self, path):
        k = path.replace("\\", "/").lower().lstrip("/")
        for lay in reversed(self.late):
            if k in lay:
                z, n = lay[k]
                return z.read(n).decode("latin-1")
        for lay in reversed(self.layers):
            sub = k[len("models/"):] if lay.prefix == "models/" and k.startswith("models/") else (
                k if lay.prefix != "models/" else None)
            if sub is not None:
                t = lay.read(sub)
                if t is not None:
                    return t
        return T.VFS.read(self, path)

    def exists(self, path):
        k = path.replace("\\", "/").lower().lstrip("/")
        if k in self.clips or any(k in lay for lay in self.late):
            return True
        for lay in self.layers:
            sub = k[len("models/"):] if lay.prefix == "models/" else k
            if k.startswith("models/") and sub in lay.files:
                return True
        return T.VFS.exists(self, path)


WEAP = {"mp40": "mp40", "mauser kar 98k": "rifle", "mauser kar 98d sniper": "rifle", "walter p38": "pistol",
        "stg 44": "mp44", "mp44": "mp44", "none": None}
OK_ANY = ("death", "generic", "pain", "den_", "dfr_", "dgr_", "chair", "crate", "smoking", "radio", "corner")


def ai_key(model):
    parts = model.split("|")
    if len(parts) > 1 and parts[0] == "weapon":
        w = parts[1].lower()
        if w.startswith("models/weapons/"):
            w = os.path.basename(w).split("_")[0].replace(".tik", "")
        return WEAP.get(w, w)
    return None


def score(samples, vfs, mapname):
    cache, good, total = {}, 0, 0
    names = collections.Counter()
    for x in samples:
        if "human/" not in x["model"]:
            continue
        key = ai_key(x["model"])
        m = x["model"].split("|")[-1]
        if m not in cache:
            cache[m] = T.tiki_anims(vfs, m, mapname)[0]
        L = cache[m]
        for slot, idx, w in x["fi"]:
            if slot >= 12 or w < 128:
                continue
            nm = (L[idx] if idx < len(L) else "OOR").lower()
            total += 1
            names[nm] += 1
            if (key and nm.startswith(key)) or nm.startswith(OK_ANY):
                good += 1
    return good / max(total, 1), names.most_common(8)


def main():
    samples = json.load(open(sys.argv[1]))
    mapname = sys.argv[2]
    dates = sys.argv[3:] or ["2026-10-01", "2026-10-08", "2026-10-11", "2026-10-13", "2026-10-15",
                             "2026-10-19", "2026-10-25", "2026-11-01"]
    for d in dates:
        s, top = score(samples, StackVFS(d.split("+")[0], "+late" in d, "+nofix" not in d), mapname)
        print("%-16s plausible %.2f  %s" % (d, s, " ".join("%s:%d" % kv for kv in top[:5])))


if __name__ == "__main__":
    main()
