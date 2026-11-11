"""merge_anims_shared.py - bug-10899: make the mod tree's models/player/base/anims_shared.txt the ONE copy that loads.

WHY. Three out-of-band paks that sort after the mod's own (zzzzzzzzzz_coop_fixes, zzzzzzzzzzzz_coop_fixes2,
zzzzzzzzzzzzz_coop_stress) carried whole-file copies of anims_shared.txt, and the last one wins. Hand patches to the
stress copy (bug-10394 / 10431 / 10513) left it as an OLD copy cut off before its closing brace with a NEWER full copy
appended after it. The engine parses the second 'animations' header as an alias inside the first section, logs
'unknown anim command', and loses most of the second half - including coop_reload_fg42 / _s / _m. The torso statemap
then has no FG 42 reload, RELOAD_WEAPON / RELOAD_MG / STAND ping-pong, and the server stops on 'possible infinite
state loop' as soon as an FG 42 reloads (v1.10.73, reproduced with the release dlls).

WHAT. Start from the mod tree's file (it parses clean) and append, in one marked section, every alias the shadowing
copies define that it lacks - taking the block from the newest source that parses it cleanly (stress second half,
then fixes2, fixes, stress first half). The paks then drop their copies (strip_pak_entry.py), so this file wins.

    python merge_anims_shared.py <mod tree> <src dir with as_*.txt> [--write]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tikianims as T  # noqa: E402

ENTRY = os.path.join("models", "player", "base", "anims_shared.txt")


def blocks(text):
    """alias -> its definition text (the alias line plus its { } block), for a file that parses clean"""
    lines = text.splitlines()
    aliases, bad = T.parse(text)
    out = {}
    for k, (ln, name) in enumerate(aliases):
        start = ln - 1
        i = start + 1
        # a following { } block (only blank / comment lines may sit between)
        j = i
        while j < len(lines) and re.match(r"^\s*(//.*)?$", lines[j]):
            j += 1
        end = start + 1
        if j < len(lines) and lines[j].strip().startswith("{"):
            depth = 0
            m = j
            while m < len(lines):
                code = re.sub(r"//.*", "", lines[m])
                depth += code.count("{") - code.count("}")
                m += 1
                if depth == 0:
                    break
            end = m
        out.setdefault(name, "\n".join(lines[start:end]))
    return out, bad


def main():
    tree, src = sys.argv[1], sys.argv[2]
    path = os.path.join(tree, ENTRY)
    raw = open(path, "rb").read().decode("latin-1")
    nl = "\r\n" if "\r\n" in raw else "\n"
    base = raw.replace("\r\n", "\n")
    have, bad = blocks(base)
    assert not bad, bad[:3]
    stress = open(os.path.join(src, "as_stress.txt"), "rb").read().decode("latin-1").replace("\r\n", "\n").split("\n")
    cut = next(i for i, l in enumerate(stress) if i > 10 and l.strip() == "animations")
    head_end = cut - 2          # the two comment lines above the second header belong to it
    s1 = "\n".join(stress[:head_end]) + "\n}\n"           # the first copy, closed where it was cut off
    s2 = "\n".join(stress[head_end:])
    # the second copy's coop_blindfire_low_back block lost its closing brace (bug-10431's hand edit): every alias after
    # it was parsed as a command of that block. Repair it the way the mod tree's own copy has it.
    bad_tail = "\t\t\t11 fire\n\t\t}\n\n\t// HZM coop [240] BUILD-MODE ACTORS"
    assert s2.count(bad_tail) == 1, "stress second copy no longer has the known missing brace"
    s2 = s2.replace(bad_tail, "\t\t\t11 fire\n\t\t}\n\t}\n\n\t// HZM coop [240] BUILD-MODE ACTORS")
    sources = [("stress (second copy)", s2), ("fixes2", open(os.path.join(src, "as_fixes2.txt"), "rb").read().decode("latin-1")),
               ("fixes", open(os.path.join(src, "as_fixes.txt"), "rb").read().decode("latin-1")), ("stress (first copy)", s1)]
    add, origin = {}, {}
    for label, text in sources:
        b, bad = blocks(text.replace("\r\n", "\n"))
        if bad:
            print("  %s: %d unparsable lines - skipped" % (label, len(bad)))
            continue
        for name, blk in b.items():
            if name not in have and name not in add:
                add[name] = blk
                origin[name] = label
    print("mod tree: %d aliases; adding %d from the shadowing copies" % (len(have), len(add)))
    for name in sorted(add):
        print("   + %-40s (%s)" % (name, origin[name]))
    if "--write" not in sys.argv:
        return
    k = base.rstrip().rfind("}")
    sect = ["", "\t//===================== [bug-10899] merged from the shadowing pak copies =====================",
            "\t// These aliases lived only in the whole-file copies of this file that zzzzzzzzzz_coop_fixes, zzzzzzzzzzzz_coop_fixes2",
            "\t// and zzzzzzzzzzzzz_coop_stress carried (the last-sorting pak wins). The paks no longer carry the file: THIS is the",
            "\t// copy that loads. Add new aliases here, never to a pak (docs/tools/check_anim_aliases.py fails a shadowing copy)."]
    for label in [s[0] for s in sources]:
        names = [n for n in add if origin[n] == label]
        if names:
            sect.append("\t// --- from %s ---" % label)
            sect += [add[n] for n in names]
    new = base[:k].rstrip("\n") + "\n" + "\n".join(sect) + "\n}\n"
    a, bad = T.parse(new)
    assert not bad, bad[:5]
    names = [x[1] for x in a]
    assert len(names) == len(set(names)), "duplicate aliases"
    open(path, "wb").write(new.replace("\n", nl).encode("latin-1"))
    print("wrote %s: %d aliases, parses clean" % (path, len(names)))


if __name__ == "__main__":
    main()
