"""apply_peep.py - put the cut Thompson peep (cutpeep.py) into the out-of-band pak zzzzzzzzzzzz_coop_fixes2.pk3.

The two meshes that carry the M1/M1A1 rear-sight plate (`site` surface) both load from fixes2 (it sorts after the mod
pak and after the HD weapon packs): models/weapons/ThompsonSMG/ThompsonSMG.skd (thompsonsmg + its 11 finishes + the 13
fs2 finishes) and models/weapons/coop_tommy27a1/ThompsonSMG.skd (27A1 Commando). The pak is a build input in the mod
root (untracked, *.pk3 is gitignored), so this script is the record of the change. Every other entry is copied
byte-for-byte with its own compression and timestamp; a mesh that is already cut is left as it is (idempotent), so this
can be re-run after any other lane regenerates one of these SKDs.

    python apply_peep.py                       dry run: what would change
    python apply_peep.py --apply [--base DIR]  back up to H:/hzm_work/thompson/bak, then replace the pak in DIR
                                               (default C:/mohaa-coop-dev/hzm-mohaa-coop-mod)
"""
import hashlib, os, shutil, sys, time, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cutpeep  # noqa: E402

PAK = "zzzzzzzzzzzz_coop_fixes2.pk3"
MESHES = {"models/weapons/thompsonsmg/thompsonsmg.skd": "models/weapons/thompsonsmg.tik",
          "models/weapons/coop_tommy27a1/thompsonsmg.skd": "models/weapons/thompsonsmg_tommy27a1.tik"}
DIA, N = 0.22, 20
BAK = r"H:\hzm_work\thompson\bak"


def arg(n, d):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def sha(b):
    return hashlib.sha256(b).hexdigest()[:16]


def main():
    base = arg("--base", r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod")
    src = os.path.join(base, PAK)
    zin = zipfile.ZipFile(src)
    new = {}
    for info in zin.infolist():
        key = info.filename.lower().replace("\\", "/")
        if key in MESHES:
            raw = zin.read(info)
            out, rep = cutpeep.cut(raw, MESHES[key], DIA, N)
            print("%-48s %s -> %s  %s" % (info.filename, sha(raw), sha(out), rep))
            if out != raw:
                new[info.filename] = out
    missing = set(MESHES) - {i.filename.lower() for i in zin.infolist()}
    assert not missing, missing
    if not new:
        print("nothing to change")
        return
    if "--apply" not in sys.argv:
        print("dry run: %d entr%s would change in %s" % (len(new), "y" if len(new) == 1 else "ies", src))
        return
    os.makedirs(BAK, exist_ok=True)
    bak = os.path.join(BAK, PAK + "." + time.strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(src, bak)
    tmp = src + ".peep_tmp"
    with zipfile.ZipFile(tmp, "w") as zout:
        for info in zin.infolist():
            data = new.get(info.filename)
            if data is None:
                data = zin.read(info)
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time if info.filename not in new else time.localtime()[:6])
            zi.compress_type = info.compress_type
            zi.external_attr = info.external_attr
            zout.writestr(zi, data)
    zin.close()
    chk = zipfile.ZipFile(tmp)
    assert chk.testzip() is None
    assert len(chk.infolist()) == len(zipfile.ZipFile(bak).infolist())
    chk.close()
    os.replace(tmp, src)
    print("applied: %s (backup %s)" % (src, bak))


if __name__ == "__main__":
    main()
