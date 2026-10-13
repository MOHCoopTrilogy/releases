"""scan.py <file.scr> ... - the project's parse scanners on single files (each file is copied into a temp root for the
two scanners that take a root). Plus two checks of my own: non-ASCII bytes, and '(-' (a parenthesised negative)."""
import os, re, subprocess, sys, shutil, tempfile
T = "C:/mohaa-coop-dev/docs/tools"
bad = 0
for f in sys.argv[1:]:
    b = open(f, "rb").read()
    na = [i for i, c in enumerate(b) if c > 126 or (c < 32 and c not in (9, 10, 13))]
    if na:
        print("NON-ASCII", f, "line", b[:na[0]].count(b"\n") + 1)
        bad = 1
    for n, line in enumerate(b.decode("latin-1").splitlines(), 1):
        code = line.split("//")[0]
        if re.search(r"\(\s*-\s*\d", code) and not re.search(r"\(\s*-?[\d.]+\s+-?[\d.]+\s+-?[\d.]+\s*\)", code):
            print("NEGATIVE-IN-PARENS?", f, n, line.strip()[:100])
            bad = 1
    for tool in ("depthscan2", "linecheck", "quotecheck", "prosecheck"):
        r = subprocess.run([sys.executable, os.path.join(T, tool + ".py"), f], capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
        if r.returncode != 0:
            print("FAIL", tool, f, out[-600:])
            bad = 1
    d = tempfile.mkdtemp()
    shutil.copy(f, d)
    for tool in ("check_empty_rhs", "scrlint"):
        r = subprocess.run([sys.executable, os.path.join(T, tool + ".py"), d], capture_output=True, text=True)
        if r.returncode != 0:
            print("FAIL", tool, f, (r.stdout + r.stderr).strip()[-600:])
            bad = 1
    shutil.rmtree(d, ignore_errors=True)
print("scan:", "FAILED" if bad else "clean", len(sys.argv) - 1, "file(s)")
sys.exit(bad)
