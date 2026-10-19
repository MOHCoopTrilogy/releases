#!/usr/bin/env python3
"""patch_armory_pick.py - one-shot, idempotent: armory picks also travel as USERINFO STATE (lp_* cvars), loadout review 2026-10-15.

The name bus loses quick clicks (32-char name, one token per ~0.75 s batch). The cgame registers lp_s / lp_h / lp_g / lp_w1..4 /
lp_f1..4 (USERINFO|ARCHIVE); the server converges on their last values (loadoutpick.scr::loadout_pickPoll). The legacy name token is
KEPT everywhere, so an old client (no such cvars) works exactly as before and a new one is applied once (the setters are idempotent).
    python patch_armory_pick.py <mod_tree>
Pages: each skin/helm/glove page gets `set coop_loPk{S,H,G}v "set lp_x NN"`; the page's Go (what < > fires) also runs it, but only on
an ACCEPTED page - free pages directly, gated pages through uok.cfg. Finish files fin<f>_s<N>.cfg (f 0-7) set lp_f<N>. Weapon commit
files get lp_w<N> from gen_loadout.py (slotfile).
"""
import io, os, re, sys

CR, LF = chr(13), chr(10)
ROWS = {
    "skin": dict(Go="coop_loASkinGo", A="coop_loASkin", Pk="coop_loPkSv", key="lp_s", pre="s"),
    "helm": dict(Go="coop_loAHelmGo", A="coop_loAHelm", Pk="coop_loPkHv", key="lp_h", pre="h"),
    "glove": dict(Go="coop_loAGloveGo", A="coop_loAGlove", Pk="coop_loPkGv", key="lp_g", pre="g"),
}


def rd(p):
    return io.open(p, encoding="latin-1", newline="").read()


def wr(p, s):
    io.open(p, "w", encoding="latin-1", newline="").write(s)


def main(tree):
    d = os.path.join(tree, "ui", "loadout")
    for row, r in ROWS.items():
        rd_ = os.path.join(d, row)
        n = 0
        for f in sorted(os.listdir(rd_)):
            m = re.match(r"%s(\d+)\.cfg$" % r["pre"], f)
            if not m:
                continue
            p = os.path.join(rd_, f)
            s = rd(p)
            if r["Pk"] in s:
                continue
            nl = CR + LF if CR + LF in s else LF
            val = str(int(m.group(1))) if row == "glove" else m.group(1)   # the glove token is ,gn<digit>, skin/helm ,sn<NN>/,hn<NN>
            gm = re.search(r'^set %s "([^"]*)"' % r["Go"], s, re.M)
            if not gm:
                print("no Go line:", p)
                continue
            line = 'set %s "set %s %s"' % (r["Pk"], r["key"], val)
            if gm.group(1) == "vstr " + r["A"]:        # FREE page: Go also publishes the state
                new = 'set %s "vstr %s ; vstr %s"' % (r["Go"], r["A"], r["Pk"])
            else:                                       # gated page: Go stays a no-op until uok.cfg arms it
                new = gm.group(0)
            s = s[:gm.start()] + new + nl + line + s[gm.end():]
            wr(p, s)
            n += 1
        # uok: the armed Go also publishes the state
        up = os.path.join(rd_, "uok.cfg")
        u = rd(up)
        old = 'set %s "vstr %s"' % (r["Go"], r["A"])
        if old in u and r["Pk"] not in u:
            u = u.replace(old, 'set %s "vstr %s ; vstr %s"' % (r["Go"], r["A"], r["Pk"]))
            wr(up, u)
        print(row, "pages:", n)
    # finishes 0-7 (8 = the server-side variant CYCLE, which is an event, not a state)
    n = 0
    for f in sorted(os.listdir(d)):
        m = re.match(r"fin([0-7])_s([1-4])\.cfg$", f)
        if not m:
            continue
        p = os.path.join(d, f)
        s = rd(p)
        if "lp_f" in s:
            continue
        nl = CR + LF if CR + LF in s else LF
        if not s.endswith(nl):
            s += nl
        s += "set lp_f%s %s%s" % (m.group(2), m.group(1), nl)
        wr(p, s)
        n += 1
    print("finish files:", n)
    # a cleared slot (USE MAP DEFAULT, one-per-class bump) must not come back from the archived state at the next join
    for name, k in (("clrP1", 1), ("clrP2", 2), ("clr3", 3), ("clr4", 4)):
        p = os.path.join(d, name + ".cfg")
        s = rd(p)
        if "lp_w" in s:
            continue
        nl = CR + LF if CR + LF in s else LF
        if not s.endswith(nl):
            s += nl
        s += 'set lp_w%d ""%sset lp_f%d ""%s' % (k, nl, k, nl)
        wr(p, s)


if __name__ == "__main__":
    main(sys.argv[1])
