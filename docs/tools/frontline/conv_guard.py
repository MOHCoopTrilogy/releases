"""Release guard for the bring-your-own-disc converter.

A player's converted disc missions are re-converted (silently, by the updater and by the game itself) only when the
version word the shipped hzmconv.exe prints differs from the one in their byo_converted.txt. So a converter change
that ships WITHOUT a new HZMCONV_VERSION never reaches anybody who already converted a disc (2026-11-11: the user played
a first-day conversion of Sealed Orders with none of the later fixes).

    conv_guard.py check <hzmconv.zip>   exit 1 when the converter sources differ from the last shipped ones and
                                        HZMCONV_VERSION was not raised, or when hzmconv.zip is older than the sources
    conv_guard.py stamp                 record the current sources + version as shipped (publish_release.ps1, after a publish)
    conv_guard.py init <commit>         write the stamp from a commit (one-time)
"""
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DIRS = ["docs/tools/ea", "docs/tools/frontline"]
STAMP = os.path.join(HERE, "conv_shipped.json")
SELF = "docs/tools/frontline/conv_guard.py"


def version_of(text):
    m = re.search(r'^HZMCONV_VERSION\s*=\s*"([^"]+)"', text, re.M)
    if not m:
        raise SystemExit("conv_guard: no HZMCONV_VERSION in hzmconv.py")
    return m.group(1)


def digest(items):
    """items: sorted (relpath, bytes). Line ends are normalised so a checkout setting cannot change the answer."""
    h = hashlib.sha256()
    for rel, data in items:
        h.update(rel.encode() + b"\0" + data.replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def tree_now():
    out, newest = [], 0.0
    for d in DIRS:
        for base, _dirs, files in os.walk(os.path.join(ROOT, d)):
            if "__pycache__" in base:
                continue
            for f in files:
                if not f.endswith(".py"):
                    continue
                p = os.path.join(base, f)
                rel = os.path.relpath(p, ROOT).replace("\\", "/")
                if rel == SELF:
                    continue
                out.append((rel, open(p, "rb").read()))
                newest = max(newest, os.path.getmtime(p))
    return sorted(out), newest


def tree_at(commit):
    names = subprocess.check_output(["git", "-C", ROOT, "ls-tree", "-r", "--name-only", commit, "--"] + DIRS).decode().split("\n")
    out = []
    for rel in names:
        if rel.endswith(".py") and rel != SELF:
            out.append((rel, subprocess.check_output(["git", "-C", ROOT, "show", "%s:%s" % (commit, rel)])))
    return sorted(out)


def write(ver, dig, note):
    json.dump({"version": ver, "sha256": dig, "note": note}, open(STAMP, "w"), indent=1)
    print("conv_guard: shipped = %s %s (%s)" % (ver, dig[:12], note))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "init":
        items = tree_at(sys.argv[2])
        ver = version_of(dict(items)["docs/tools/frontline/hzmconv.py"].decode("latin-1"))
        write(ver, digest(items), "commit " + sys.argv[2])
        return 0
    items, newest = tree_now()
    ver = version_of(dict(items)["docs/tools/frontline/hzmconv.py"].decode("latin-1"))
    dig = digest(items)
    if mode == "stamp":
        write(ver, dig, "publish")
        return 0
    if not os.path.exists(STAMP):
        print("conv_guard: no conv_shipped.json - run: conv_guard.py init <last release commit>")
        return 1
    was = json.load(open(STAMP))
    if dig != was["sha256"] and ver == was["version"]:
        print("conv_guard: the converter sources changed since %s shipped but HZMCONV_VERSION is still %s.\n"
              "  Players who already converted a disc would keep their old missions. Raise HZMCONV_VERSION in\n"
              "  docs/tools/frontline/hzmconv.py, then rebuild hzmconv.zip (build_hzmconv.py)." % (was["version"], ver))
        return 1
    if len(sys.argv) > 2:
        z = sys.argv[2]
        if not os.path.exists(z):
            print("conv_guard: %s is missing" % z)
            return 1
        if dig != was["sha256"] and os.path.getmtime(z) < newest:
            print("conv_guard: %s is older than the converter sources - rebuild it (build_hzmconv.py)" % z)
            return 1
    print("conv_guard: ok (%s, %s)" % (ver, "unchanged since last release" if dig == was["sha256"] else "new version"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
