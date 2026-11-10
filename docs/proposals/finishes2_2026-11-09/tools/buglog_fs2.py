"""Append the finishes2 wiring entries to .wolf/buglog.json (mixed LF / CRLF: inserted textually before the final ], CRLF, 2-space
indent, ids = max + 1 at write time; validated with json.loads + the entry count).
    python buglog_fs2.py <buglog.json> [--apply]
"""
import json, re, shutil, sys

P = sys.argv[1]
TS = "2026-11-09T18:00:00-06:00"
E = [
    dict(error_message="finishes2 build: the agreed finish-tik rank band 1240+ collides with 350+ shipped ranks (e.g. rank 1506 bar_camo_winter.tik vs ppsh43silenced_fs2_pea.tik)",
         file="docs/proposals/finishes2_2026-11-09/tools/fs2_finish2.py (rerank) + docs/tools/gen_skins.py (fs2_pak_audit)",
         root_cause="the band was agreed without reading the ranks in use: the standard seven finishes + model variants already occupy 1000-1724 (and 3000-3006); gen_skins checked ranks only against the mod tree, not the out-of-band paks or the fixes / wpnfix sources. A shared rank hides a gun on the weapon wheel",
         fix="every finishes2 variant re-ranked to 2000-2909 (fs2_finish2.py rerank 2000); gen_skins.py check now asserts each finishes2 rank against every other weapon tik in the mod tree, docs/tools/assets/{fixes,wpnfix} and every out-of-band pak in the base checkout (HZM_BASE_MOD)",
         tags=["finishes2", "rank", "weapon-wheel", "generator", "v1.10.68"]),
    dict(error_message="user QA (sheet4_ww.jpg): the Splittertarn on the MP40 and Colt reads as rounded blobs, not angular splinter shards",
         file="docs/proposals/finishes2_2026-11-09/tools/patterns.py (splitter), finish_sheet.py (tile_cm)",
         root_cause="the tile was ~70 overlapping slivers at a fixed 34 cm: a pistol shows part of one or two big slivers, and overlapping slivers merge into soft shapes",
         fix="the tile is an anisotropic Voronoi partition of the torus (straight edges, hard corners, 88 cells, -25 deg lean) + the rain strokes; its size scales with the gun (half its length, 12-34 cm). Re-baked on all 126 sheets from the gun that baked each (fs2_finish2.py rebake splitter, mask registration asserted 0.000). patterns.py also gets a fixed per-tile seed (hash(name) was salted per process: a re-run redrew every tile)",
         tags=["finishes2", "camo", "splitter", "texture", "user-qa", "v1.10.68"]),
    dict(error_message="gen_finish_ui.py finishes2 block: the s<n>sel.cfg / init.cfg block-removal regex swallowed the hand-written lines after the block (coop_loMastApply, coop_loLkFV1-7) on the second run - gen_loadout check DIFFERENT on 5 files right after a build",
         file="docs/tools/gen_finish_ui.py",
         root_cause="the removal pattern was any 'set coop_lo...' line, and the lines that follow the block are 'set coop_lo...' too; caught by build-then-check (idempotency), before anything shipped",
         fix="B2_LINES matches exactly the lines the block writes (coop_loF2On, coop_loFgo4x/5x, coop_loFqCur4x/5x, coop_loLkFV4x/5x, vstr coop_loMast<n>_4x/5x); build twice + check = EXACT REPRODUCTION",
         tags=["generator", "cfg", "idempotency", "armory", "finishes2", "T2"]),
    dict(error_message="chal_finSeed scaled O(finish rungs x challenges per stat) in one frame at join; finishes2 adds 13 rungs per gun (1019 finish challenges)",
         file="hzm-mohaa-coop-mod/coop_mod/challenges.scr (chal_finSeed)",
         root_cause="each unseeded finish rung rescanned every challenge on its stat for the best progress",
         fix="pass 1 records the best progress per stat once, pass 2 seeds from it (same result, O(challenges)); applied by docs/proposals/finishes2_2026-11-09/tools/wire_loadoutpick.py",
         tags=["challenges", "performance", "finishes2", "join"]),
    dict(error_message="worktree generator runs: gen_loadout check DIFFERENT armory_defaults.cfg (helmet pages h30-h32 missing); gen_wpnfix_pak / gen_skins could not find the out-of-band paks",
         file="docs/tools/gen_armory_cos.py, docs/tools/gen_wpnfix_pak.py",
         root_cause="both resolved the mod tree as <repo>/hzm-mohaa-coop-mod instead of honouring HZM_MOD / a base-checkout override, so from a worktree root the off-ring helmet scan saw no pages and BASE_MOD did not exist",
         fix="gen_armory_cos reads HZM_MOD; gen_wpnfix_pak.BASE_MOD honours HZM_BASE_MOD. gen_loadout check = EXACT REPRODUCTION from the worktree",
         tags=["generator", "worktree", "HZM_MOD", "armory"]),
]


def main():
    raw = open(P, "rb").read()
    d = json.loads(raw.decode("utf-8"))
    n0 = len(d)
    mx = max(int(m.group(1)) for e in d for m in [re.match(r"bug-(\d+)$", e.get("id", ""))] if m)
    out = []
    for i, e in enumerate(E):
        ent = {"id": "bug-%d" % (mx + 1 + i), "timestamp": TS}
        ent.update(e)
        ent.update(related_bugs=[], occurrences=1, last_seen=TS)
        out.append(ent)
    txt = raw.decode("utf-8")
    end = txt.rstrip().rfind("]")
    body = txt[:end].rstrip()
    assert body.endswith("}")
    add = "".join(",\r\n" + "\r\n".join("  " + l for l in json.dumps(e, indent=2, ensure_ascii=False).split("\n")) for e in out)
    new = body + add + "\r\n]\r\n"
    d2 = json.loads(new)
    assert len(d2) == n0 + len(E)
    for e in out:
        print(e["id"], e["error_message"][:80])
    if "--apply" in sys.argv:
        shutil.copyfile(P, P + ".bak_fs2")
        open(P, "wb").write(new.encode("utf-8"))
        print("written: %d -> %d entries" % (n0, len(d2)))


if __name__ == "__main__":
    main()
