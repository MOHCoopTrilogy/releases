"""GATE: an `anim <name>` on an actor goes into the MOTION (full-body) slot.

Actor::PlayAnimation -> global/anim.scr -> anim/anim.scr -> `setmotionanim`. A clip with no
'Bip01 pos' channel has NO root translation there (skelBone_PosRot has an empty SetBaseValue,
so there is no skd fallback, and GetLerpValue3 returns (0,0,0) for a channel no active slot
carries), and a clip with no 'Bip01 L/R Foot pos' drags the leg IK wrists to the root. The man
sinks by the clip's authored root height x the tik scale and splays. That is bug-2367's
"stuck in the ground" and the 2026-09-05 "underground flat" report; both survived a spawn-height
fix because the loss is inside the skeleton, not in the entity origin.

RULE: a clip without 'Bip01 pos' is an ACTION clip. Play it with `upperanim`, over a full-body
clip set with `anim`. This is what anim/aim.scr and anim/shoot.scr already do with
setmotionanim(<wg>_*_legs) + setactionanim(<wg>_aim|_shoot).

  python check_anim_rootless.py --map m3l1a --model models/human/dday_ranger_private.tik \
      --script hzm-mohaa-coop-mod/maps/m3l1a/coopified.scr
Exit 1 on any rootless clip driven through `anim`.
"""
import argparse, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "..", "..", "docs", "tools"))
# when this lands in docs/tools/ the line above becomes unnecessary
try:
    import check_map_anims as c
except ImportError:
    sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
    import check_map_anims as c


def channels(path):
    raw = c.read(path)
    if raw is None:
        return None
    nch, ofs, _nfr = struct.unpack_from("<iii", raw, 36)
    return [raw[ofs + 32 * i:ofs + 32 * i + 32].split(b"\0")[0].decode("latin-1")
            for i in range(nch)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default="m3l1a")
    ap.add_argument("--model", default="models/human/dday_ranger_private.tik")
    ap.add_argument("--script", required=True)
    a = ap.parse_args()

    aliases = c.collect_aliases(a.model, a.map)
    src = open(a.script, encoding="latin-1").read()
    bad = []
    for m in re.finditer(r"\banim\s+([A-Za-z_][A-Za-z0-9_]*)", src):
        name = m.group(1)
        entry = aliases.get(name)
        if not entry:
            continue                      # not a model anim on this map; check_map_anims covers that
        ch = channels(entry[0])
        if ch is None:
            continue
        missing = [k for k in ("Bip01 pos", "Bip01 L Foot pos", "Bip01 R Foot pos") if k not in ch]
        if missing:
            line = src[:m.start()].count("\n") + 1
            bad.append((line, name, os.path.basename(entry[0]), len(ch), missing))

    for line, name, skc, n, missing in bad:
        print("FAIL %s:%d  anim %s -> %s (%d channels) missing %s"
              % (a.script, line, name, skc, n, ", ".join(missing)))
    if bad:
        print("\n%d rootless clip(s) driven through `anim`. Use `upperanim` for these and set a "
              "full-body clip with `anim`." % len(bad))
        return 1

    # [2026-09-06, bug-2498] TWO WAYS THIS GATE PASSED A CLIP THE ENGINE REJECTED. (1) A `random` alias group
    # registers under its digit-stripped stem (tiki_files.cpp:1046, bug-2214): `crouch_beach_idle02` is not an
    # anim, `crouch_beach_idle` is, and the `continue` above treated the unknown name as "not ours". (2) A name
    # built by string concatenation - `anim ( "hedge_shake0" + local.k )` - never matched the regex at all.
    # Both are now failures: a numbered member of a random group, and any computed name.
    bad2 = []
    for m in re.finditer(r"\banim\s+([A-Za-z_][A-Za-z0-9_]*)", src):
        name = m.group(1)
        if name in aliases or name.startswith("local") or name.startswith("level") or name.startswith("self"):
            continue
        stem = re.sub(r"\d+$", "", name)
        if stem != name and stem in aliases:
            line = src[:m.start()].count("\n") + 1
            bad2.append((line, name, "numbered member of the `random` group `%s` - the engine strips the digits at "
                                     "load and only the stem exists (bug-2214)" % stem))
    for m in re.finditer(r"\banim\s*\(\s*\"", src):
        line = src[:m.start()].count("\n") + 1
        bad2.append((line, "( \"...\" + ... )", "computed anim name; write the literal alias so it can be checked"))
    for line, name, why in bad2:
        print("FAIL %s:%d  anim %s -> %s" % (a.script, line, name, why))
    if bad2:
        print("\n%d anim name(s) the engine cannot resolve." % len(bad2))
        return 1
    print("OK  every `anim` in %s resolves to a full-body clip" % a.script)
    return 0


if __name__ == "__main__":
    sys.exit(main())
