"""animq.py <map> <model.tik> [alias ...] - does the alias resolve on this map for this model, loop flag, duration (s).
No aliases = list every alias whose name contains a substring given with --grep. MOD tree = the objectives2 worktree."""
import sys, os
sys.path.insert(0, "C:/mohaa-coop-dev/docs/tools")
import check_map_anims as C
C.MOD = "C:/mohaa-coop-dev/hzm-mod-objectives2"
mp, model = sys.argv[1], sys.argv[2]
rest = sys.argv[3:]
al = C.collect_aliases(model, mp)
print(len(al), "aliases resolve on", mp, "for", model)
if rest and rest[0] == "--grep":
    names = sorted(a for a in al if any(g.lower() in a for g in rest[1:]))
else:
    names = [a.lower() for a in rest]
for n in names:
    ps = al.get(n)
    if not ps:
        print("%-34s MISSING" % n); continue
    infos = [C.skc_info(p) for p in ps]
    print("%-34s %s" % (n, "; ".join(("loop" if i and i["loop"] else "once") + (" %.2fs" % i["dur"] if i else " unreadable") for i in infos)))
