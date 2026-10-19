#!/usr/bin/env python3
"""patch_armory_cos.py - uniform / helmet / glove pages step in the player's order (unlocked first), by pointer commands.

The skin (s<NN>), helmet (h<NN>) and glove (g<NN>) pages hard-link their neighbours (`set coop_loCharN "exec ui/loadout/skin/s02.cfg"`), so
the < > order is fixed at generation time. The Armory now sorts unlocked first for every picker, which for the steppers means the NEXT page is
player-specific. Each page therefore points through a pointer cvar the server keeps current:

    page sNN:   set coop_loCharN "vstr coop_loSkNxNN"      set coop_loCharP "vstr coop_loSkPvNN"          (helmet: HmNx/HmPv, glove: GlNx/GlPv)
    server:     seta coop_loSkNxNN exec ui/loadout/skin/sMM.cfg     (coop_mod/cosorder.scr, diff-only, archived)
    default:    the natural ring, in ui/loadout/armory_defaults.cfg (gen_armory.py), so a cold profile behaves as before.

    python docs/tools/patch_armory_cos.py extract   # record the natural rings from an UNPATCHED tree -> docs/tools/assets/armory_cos_ring.json
    python docs/tools/patch_armory_cos.py check|apply          HZM_MOD=<mod dir>

The ring file is the record of the order before this change (and the data the generator and cosorder.scr are built from); `apply` is idempotent.
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.environ.get("HZM_MOD") or os.path.join(ROOT, "hzm-mohaa-coop-mod")
RING = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "armory_cos_ring.json")

# kind -> (page dir, page letter, next var, prev var, next pointer prefix, prev pointer prefix, flag prefix of the server's lock flags)
FAM = {
    "skin": ("skin", "s", "CharN", "CharP", "coop_loSkNx", "coop_loSkPv", "coop_loSkLkL"),
    "helm": ("helm", "h", "HelmN", "HelmP", "coop_loHmNx", "coop_loHmPv", "coop_loHmLkL"),
    "glove": ("glove", "g", "GloveN", "GloveP", "coop_loGlNx", "coop_loGlPv", "coop_loGlLkL"),
}


def rd(p):
    return io.open(p, "r", encoding="latin-1", newline="").read()


def wr(p, t):
    io.open(p, "w", encoding="latin-1", newline="").write(t)


def pages(kind):
    d, ltr = FAM[kind][0], FAM[kind][1]
    out = {}
    for f in os.listdir(os.path.join(MOD, "ui", "loadout", d)):
        m = re.fullmatch(ltr + r"(\d+)\.cfg", f)
        if m:
            out[int(m.group(1))] = os.path.join(MOD, "ui", "loadout", d, f)
    return out


def link_re(kind, var):
    d, ltr = FAM[kind][0], FAM[kind][1]
    return re.compile(r'set coop_lo%s "exec ui/loadout/%s/%s(\d+)\.cfg"' % (var, d, ltr))


def extract():
    ring = {}
    for kind in FAM:
        pg = pages(kind)
        nxt = {}
        for k, p in pg.items():
            m = link_re(kind, FAM[kind][2]).search(rd(p))
            assert m, "%s: no unpatched next link (run extract on an UNPATCHED tree)" % p
            nxt[k] = int(m.group(1))
        order, k = [], min(nxt)
        while k not in order and k in nxt:
            order.append(k)
            k = nxt[k]
        ring[kind] = order
    json.dump(ring, io.open(RING, "w"), indent=1)
    print("rings:", {k: len(v) for k, v in ring.items()})


def pad(n):
    return "%02d" % n if n < 10 else str(n)


def patch_page(kind, k, p, apply):
    d, ltr, vn, vp, pn, pp = FAM[kind][:6]
    t = rd(p)
    eol = "\r\n" if "\r\n" in t else "\n"
    new = t
    for var, ptr in ((vn, pn), (vp, pp)):
        rx = link_re(kind, var)
        if rx.search(new):
            new = rx.sub('set coop_lo%s "vstr %s%s"' % (var, ptr, pad(k)), new)
    changed = new != t
    if changed and apply:
        wr(p, new)
    return changed


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "extract":
        return extract()
    todo = 0
    for kind in FAM:
        for k, p in sorted(pages(kind).items()):
            if patch_page(kind, k, p, mode == "apply"):
                todo += 1
    if mode == "apply":
        print("patched %d pages" % todo)
        return 0
    print("patch_armory_cos: %s" % ("applied" if not todo else "%d pages still hard-link their neighbours" % todo))
    return 1 if todo else 0


if __name__ == "__main__":
    sys.exit(main())
