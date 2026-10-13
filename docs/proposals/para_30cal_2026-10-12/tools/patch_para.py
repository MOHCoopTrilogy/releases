"""patch_para.py <mod root> <out root> - bug-3562. Writes the patched coop_mod/parasquad.scr and anim/mg42_idle.scr
under <out root> (which may be the mod root itself). Binary I/O, each file keeps its own line endings, every anchor
exactly once, depth scan + no-em-dash assert on the result."""
import os, re, sys
MOD, OUT = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))


def depthscan(text, name):
    depth, instr = 0, False
    for n, ln in enumerate(text.split("\n"), 1):
        code = ln
        if re.match(r"^[A-Za-z_][A-Za-z_0-9]*(\s+local\.[A-Za-z_0-9]+)*\s*:\s*\{?\s*$", ln) and depth != 0:
            raise SystemExit("%s:%d label at depth %d" % (name, n, depth))
        i, q = 0, False
        while i < len(code):
            ch = code[i]
            if q:
                if ch == "\\":
                    i += 1
                elif ch == '"':
                    q = False
            elif ch == '"':
                q = True
            elif ch == "/" and code[i:i + 2] == "//":
                break
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth < 0:
                    raise SystemExit("%s:%d depth below zero" % (name, n))
            i += 1
        if q:
            raise SystemExit("%s:%d unterminated string" % (name, n))
    if depth != 0:
        raise SystemExit("%s ends at depth %d" % (name, depth))


# ---- coop_mod/parasquad.scr (LF)
p = os.path.join(MOD, "coop_mod/parasquad.scr")
raw = open(p, "rb").read()
assert raw.count(b"\r") == 0
t = raw.decode("latin-1")
assert "bug-3562" not in t, "already patched"
a = "\ngunner local.a local.sid:{\n"
assert t.count(a) == 1
frag = open(os.path.join(HERE, "frag_parasquad_mg.scr"), "rb").read().decode("latin-1").replace("\r\n", "\n")
assert frag.startswith("gunner local.a local.sid:{\n") and frag.endswith("}end\n")
t = t[:t.index(a) + 1] + frag
old = """//   .30 CAL  member 1 carries an M1919; when the squad has held one spot for 6s he sets it up at
//            the best low-cover spot facing the threat and mans it as a real TurretGun
//            (actor machinegunner think, mg42_active.scr recipe); packs up when the squad moves on.
"""
new = """//   .30 CAL  member 1 carries an M1919; when the squad has held one spot for 6s he sets it up
//            facing the threat ON something that was traced - an object in the map under a bipod,
//            else the ground on a tripod, else (last) a sandbag rest - and mans it as a real
//            TurretGun (actor machinegunner think, mg42_active.scr recipe); packs up when the
//            squad moves on. See THE .30 CAL EMPLACEMENT below (bug-3562).
"""
assert t.count(old) == 1
t = t.replace(old, new)
for bad in ("—", "﻿", "\t\t\t\t\t\t\t\t\t\t"):
    assert bad not in t
assert not re.search(r"\(\s*-\d+(\.\d+)?\s*\)", t), "bare negative in parentheses"   # ( -1 ) kills; a vector ( -14 -14 0 ) is fine
depthscan(t, "parasquad.scr")
o = os.path.join(OUT, "coop_mod/parasquad.scr")
os.makedirs(os.path.dirname(o), exist_ok=True)
open(o, "wb").write(t.encode("latin-1"))
print("parasquad.scr: %d -> %d bytes" % (len(raw), len(t)))

# ---- anim/mg42_idle.scr (CRLF)
p = os.path.join(MOD, "anim/mg42_idle.scr")
raw = open(p, "rb").read()
assert raw.count(b"\r\n") == raw.count(b"\n")
t = raw.decode("latin-1").replace("\r\n", "\n")
assert "bug-3562" not in t, "already patched"
for side in ("left", "right"):
    old = ("\tlocal.n = randomint 2\n"
           "\tif (local.n == 0) { self setmotionanim mg42_stand_%s1 }\n"
           "\telse { self setmotionanim mg42_stand_%s2 }\n" % (side, side))
    new = ("\t// [bug-3562] a gunner the engine has crouched (gun low: self.position is \"crouch\") traverses with\n"
           "\t// the crouched clip - the standing ones stood him up for every turn of the gun\n"
           "\tlocal.n = randomint 2\n"
           "\tif (self.position == \"crouch\") { self setmotionanim mg42_crouch_%s }\n"
           "\telse if (local.n == 0) { self setmotionanim mg42_stand_%s1 }\n"
           "\telse { self setmotionanim mg42_stand_%s2 }\n" % (side, side, side))
    assert t.count(old) == 1, (side, t.count(old))
    t = t.replace(old, new)
depthscan(t, "mg42_idle.scr")
o = os.path.join(OUT, "anim/mg42_idle.scr")
os.makedirs(os.path.dirname(o), exist_ok=True)
open(o, "wb").write(t.replace("\n", "\r\n").encode("latin-1"))
print("mg42_idle.scr: %d -> %d bytes" % (len(raw), len(t.replace("\n", "\r\n"))))
