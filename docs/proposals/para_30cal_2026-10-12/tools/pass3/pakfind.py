"""pakfind.py <regex> [--cat] - which pak (GOG main / mainta / maintt, highest wins last) holds files matching; --cat prints text"""
import glob, os, re, sys, zipfile
G = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
rx = re.compile(sys.argv[1], re.I)
cat = "--cat" in sys.argv
out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
for d in ("main", "mainta", "maintt"):
    for p in sorted(glob.glob(os.path.join(G, d, "*.pk3")), key=lambda s: os.path.basename(s).lower()):
        try:
            z = zipfile.ZipFile(p)
        except Exception:
            continue
        for n in z.namelist():
            if rx.search(n):
                print(d + "/" + os.path.basename(p), n, z.getinfo(n).file_size)
                if cat and z.getinfo(n).file_size < 20000:
                    print(z.read(n).decode("latin-1"))
                if out:
                    os.makedirs(out, exist_ok=True)
                    open(os.path.join(out, d + "__" + os.path.basename(n)), "wb").write(z.read(n))
