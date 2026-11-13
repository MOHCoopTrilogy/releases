"""apply_knob.py - shorten the actuator-knob stem on the Thompson 50rd and M1928 meshes in zzzzzzzzzzzz_coop_fixes2.pk3.

User decision 2026-11-13 ("make it based on real life"): on the M1928/M1928A1 the shooter sees the front blade OVER the
actuator knob - the knob sits low in the sight picture. Our meshes' knob (the ADS lane's generated round knob: stem
r 0.27 u x 0.4 u, knurled cap r 0.42 u x 0.4 u) stood so tall that only 7 % (50rd) / 12 % (M1928) of the blade showed.
knobfit.py moves the cap down by DROP and compresses the stem under it (cap shape kept, nothing else touched):
Thompson50.skd `Skin5` 0.28 u, coop_tommy28 `Skin5` 0.22 u -> 96 % of the blade visible offline (eye line unchanged).
The 1928 Tommy (coop_tommy1928d): its cap already sits on the receiver, so instead lyman.py adds a raised Lyman leaf
with a 0.20 u aperture centred at z -5.60 (1.30 in above the bore); the engine sight row R moves there with it
(cg_adssights.h, rel-1.10.38-engine). The mesh and the cgame have to ship together.

    python apply_knob.py                       dry run
    python apply_knob.py --apply [--base DIR]  back up to H:/hzm_work/thompson/bak, then rewrite the pak in DIR
Idempotent only against the retail-lane knob: it refuses a knob whose top is already below the original height.
"""
import hashlib, os, shutil, sys, time, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knobfit  # noqa: E402
import lyman  # noqa: E402
import skdlib  # noqa: E402

PAK = "zzzzzzzzzzzz_coop_fixes2.pk3"
# entry -> (tik, surface, drop, knob top z of the unmodified mesh)
MESHES = {"models/weapons/thompson/thompson50.skd": ("models/weapons/thompson50.tik", "Skin5", 0.28, -6.0),
          "models/weapons/coop_tommy28/thompsonsmg.skd": ("models/weapons/thompsonsmg_tommy28.tik", "Skin5", 0.22, -5.596)}
BAK = r"H:\hzm_work\thompson\bak"


def arg(n, d):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def main():
    src = os.path.join(arg("--base", r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"), PAK)
    zin = zipfile.ZipFile(src)
    new = {}
    for info in zin.infolist():
        key = info.filename.lower()
        if key == "models/weapons/coop_tommy1928d/thompsonsmg.skd":
            raw = zin.read(info)
            n6 = [x.numVerts for x in skdlib.read_skd(raw).surfaces if x.name == "Skin6"][0]
            if n6 != 407:
                print("%s: Skin6 has %d verts (not the original 407) - leaf already added or mesh regenerated, skipped" % (info.filename, n6))
                continue
            out, rep = lyman.build(raw, zc=-5.60, dia=0.20)
            print(info.filename, hashlib.sha256(raw).hexdigest()[:16], "->", hashlib.sha256(out).hexdigest()[:16], rep)
            new[info.filename] = out
        if key in MESHES:
            tik, surf, drop, top0 = MESHES[key]
            raw = zin.read(info)
            try:
                out, rep = knobfit.lower(raw, tik, surf, drop=drop)
            except AssertionError:
                # the pak's knob differs from the one the live VFS fits against = it was already shortened here
                print("%s: knob differs from the live mesh (already applied?) - skipped" % info.filename)
                continue
            if abs(rep["top_before"] - top0) > 0.01:
                print("%s: knob top %.3f is not the original %.3f - already applied or regenerated, skipped" % (info.filename, rep["top_before"], top0))
                continue
            print(info.filename, hashlib.sha256(raw).hexdigest()[:16], "->", hashlib.sha256(out).hexdigest()[:16], rep)
            new[info.filename] = out
    if not new or "--apply" not in sys.argv:
        print("dry run" if new else "nothing to change")
        return
    os.makedirs(BAK, exist_ok=True)
    bak = os.path.join(BAK, PAK + "." + time.strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(src, bak)
    tmp = src + ".knob_tmp"
    with zipfile.ZipFile(tmp, "w") as zout:
        for info in zin.infolist():
            data = new.get(info.filename)
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time if data is None else time.localtime()[:6])
            zi.compress_type = info.compress_type
            zi.external_attr = info.external_attr
            zout.writestr(zi, zin.read(info) if data is None else data)
    zin.close()
    assert zipfile.ZipFile(tmp).testzip() is None
    os.replace(tmp, src)
    print("applied: %s (backup %s)" % (src, bak))


if __name__ == "__main__":
    main()
