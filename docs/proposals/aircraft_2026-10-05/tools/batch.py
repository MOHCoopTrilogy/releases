"""batch.py <name> - several planes_ingame sessions inside ONE hold of the "planes" test slot.
Plans are defined below; each entry = (label, mode, maps, events, cgame, game, fps, secs, extra)."""
import json, os, sys, time
import planes_ingame_v2 as P

DBG = ["set coop_acDebug 1", "set cg_hzmAcDebug 1", "set coop_acTrack 1", "set coop_acStukaHp 100"]
PLANS = {
    "b1": [
        ("before1", "before", "m2l1,m6l2b,m4l3", "para,binoc,stuka", "cgame_ac2", "game_live", 60, 0, ["set cg_hzmAcDebug 1"]),
        ("after1", "after", "m2l1", "para,binoc,stuka,down", "cgame_ac2", "game_ac2", 60, 0, DBG),
        ("after1", "after", "m6l2b,m4l3", "para,binoc,stuka", "cgame_ac2", "game_ac2", 60, 0, DBG),
        ("fps125", "after", "m2l1", "binoc", "cgame_ac2", "game_ac2", 125, 120, DBG),
    ],
    "b2": [
        ("before2", "before", "m2l1,e1l1,m5l1a", "para,binoc,stuka", "cgame_ac2", "game_live", 60, 0, ["set cg_hzmAcDebug 1"]),
        ("after2", "after", "m2l1", "para,binoc,stuka,down", "cgame_ac2", "game_ac2", 60, 0, DBG + ["set coop_acStukaHp 30"]),
        ("after2", "after", "e1l1,m5l1a", "para,binoc,stuka", "cgame_ac2", "game_ac2", 60, 0, DBG),
        # the ONE capped 125 fps run the user allowed (the b1 attempt stayed at 60: com_maxfpsUnfocused capped it)
        ("fps125b", "after", "m2l1", "binoc", "cgame_ac2", "game_ac2", 125, 120, DBG + ["set com_maxfpsUnfocused 125"]),
    ],
}


def main():
    name = sys.argv[1]
    plan = PLANS[name]
    P.log("batch", name, "waiting for slot ==", P.OWNER)
    while P.slot_value() != P.OWNER:
        time.sleep(10)
    P.log("slot is ours")
    try:
        if P.hg.user_game_running():
            raise SystemExit("the user's game is running - not launching")
        P.hg.acquire_slot(P.OWNER, P.EXE, P.HOME, [P.PORT], minutes=90)
        try:
            for (label, mode, maps, events, cg, gm, fps, secs, extra) in plan:
                if fps > 60 and not (secs and secs <= 120):
                    raise SystemExit("fps > 60 only for one capped run")
                out = {}
                for m in maps.split(","):
                    try:
                        out[m] = P.session(label, m, mode, events, cg, gm, fps, secs, list(extra))
                    except Exception as e:
                        P.log("[%s/%s] FAILED: %r" % (label, m, e))
                        out[m] = {"error": repr(e)}
                os.makedirs(os.path.join(P.RUNS, label), exist_ok=True)
                fn = os.path.join(P.RUNS, label, "summary_%s.json" % maps.replace(",", "_"))
                json.dump(out, open(fn, "w"), indent=1, default=str)
        finally:
            P.hg.release_slot(P.OWNER)
    finally:
        if P.slot_value() == P.OWNER:
            open(P.SLOTFILE, "w").write("free")
            P.log("test slot released: free")


if __name__ == "__main__":
    main()
