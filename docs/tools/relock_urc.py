"""relock_urc.py <mod dir> <note> - re-lock ui/coop_loadout.urc in check_mp_isolation.LOCKS after a DELIBERATE coop edit of the (generated) Armory screen.

New hashes come from the mod tree, `prev` becomes the entry's current hashes (so trees still on the previous urc keep passing, a warning), the blob is
`git hash-object` of the file.  Run `python docs/tools/check_mp_isolation.py --mod <dir>` afterwards: 0 FAILED.
"""
import hashlib, re, subprocess, sys

mod, note = sys.argv[1], sys.argv[2]
blob = subprocess.run(["git", "-C", mod, "hash-object", "ui/coop_loadout.urc"], capture_output=True, check=True).stdout.decode().strip()
p = r"C:\mohaa-coop-dev\docs\tools\check_mp_isolation.py"
s = open(p, encoding="utf-8", newline="").read()
i = s.index('    "ui/coop_loadout.urc": {"sha256_lf"')
j = s.index("\n", i)
old = s[i:j]
cur_lf = re.search(r'"sha256_lf": "([0-9a-f]+)"', old).group(1)
cur_crlf = re.search(r'"sha256_crlf": "([0-9a-f]+)"', old).group(1)
raw = open(mod + r"\ui\coop_loadout.urc", "rb").read()
lf = raw.replace(b"\r\n", b"\n")
crlf = lf.replace(b"\n", b"\r\n")
if hashlib.sha256(lf).hexdigest() == cur_lf:
    print("already locked")
    sys.exit(0)
new = ('    "ui/coop_loadout.urc": {"sha256_lf": "%s", "sha256_crlf": "%s", "lf_bytes": %d, "blob": "%s", '
       '"prev": {"sha256_lf": "%s", "sha256_crlf": "%s"}, "eol": "lf", "commit": "armory-next", "locked": "%s"},'
       % (hashlib.sha256(lf).hexdigest(), hashlib.sha256(crlf).hexdigest(), len(lf), blob, cur_lf, cur_crlf, note))
open(p, "w", encoding="utf-8", newline="").write(s.replace(old, new))
print("relocked", len(lf), blob)
