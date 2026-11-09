"""fit_render.py - render armory_fit.py jobs on the private client (G:\\mohaa-wpnview, DISPLAY2, 1920x1080, ui_menuCenter 0).

    python fit_render.py prep <hero|card>              add roster guns missing from the solver state (from loadout_weapons.tsv), drop retired ids
    python fit_render.py run <hero|card> <jobs.json> <run>   every job [name, tik, xfm] in the hero box / the first card box; frames to
                                                       RUNS/<run>/shots/hf_<name>.tga (+ hf_000 = the empty box) for armory_fit.py solve
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\wpnviewer_2026-11-04\tools")
import wpnview_run as W  # noqa: E402


def prep_var():
    """every model variant (loadoutskins.scr fid >= 8 of a host with an Armory tile), started from its host's solved hero transform"""
    import re
    mod = os.environ["WV_MOD"]
    sk = open(os.path.join(mod, "coop_mod", "loadoutskins.scr"), encoding="latin-1").read()
    tile = dict(re.findall(r'coop_skinMvTile\["([^"]+)"\] = "(\d+)"', sk))
    hero = json.load(open(os.path.join(HERE, "hero_fit_state.json")))
    st = {}
    for give, fid, tik in re.findall(r'coop_skinGive\["([^"]+)"\]\[(\d+)\] = "([^"]+)"', sk):
        if int(fid) >= 8 and give in tile and tile[give] in hero:
            st["%s_%s" % (tile[give], fid)] = {"x": list(hero[tile[give]]["x"]), "slope": None, "done": False, "round": 0, "tik": tik}
    json.dump(st, open(os.path.join(HERE, "var_fit_state.json"), "w"), indent=1)
    print("var state", len(st), "variants")


def prep(mode):
    if mode == "var":
        return prep_var()
    os.environ["HF_MODE"] = mode
    sys.path.insert(0, HERE)
    import armory_fit as F
    st = json.load(open(F.STATE))
    R = F.rows()
    live = {i for i, d in R.items() if d["tab"] != "" and i not in F.SKIP}
    for i in sorted(set(st) - live):
        del st[i]
    for i in sorted(live - set(st)):
        t = [float(v) for v in (R[i].get("xfmt") or R[i]["xfm"]).split()]
        st[i] = {"x": t, "slope": None, "done": False, "round": 0}
    json.dump(st, open(F.STATE, "w"), indent=1)
    print(mode, "state", len(st), "guns")


def run(mode, jobsf, name):
    jobs = json.load(open(jobsf))
    s = W.Script()
    s.cmd("echo ^~^~^ WV boot", 3000)
    s.cmd("pushmenu coop_loadout", 2500)
    if mode in ("hero", "var"):
        # the empty frame must differ from the gun frames ONLY by the gun: the hero flag also shows the name / caption labels
        s.cmd("set coop_loHeroIc 0;set coop_loHero 1", 100)
        s.cmd('set coop_loPrev ""', 600)
        s.cmd("screenshot hf_000", 400)
        # one cfg per job in the client's home (a pad-script command is < 63 characters; variant tik paths are longer)
        jd = os.path.join(W.MAINTT, "hfj")
        shutil.rmtree(jd, ignore_errors=True)
        os.makedirs(jd)
        for k, (nm, tik, x) in enumerate(jobs):
            open(os.path.join(jd, "j%d.cfg" % k), "w", newline="\n").write('set coop_loXfmHero "%s"\nset coop_loPrev "%s"\n' % (x, tik))
            s.cmd("exec hfj/j%d.cfg" % k, 740)
            s.cmd("screenshot hf_%s" % nm, 300)
    else:
        s.cmd("set coop_loK0V 1;set coop_loK0I 0;set coop_loK0L 0", 100)
        s.cmd('set coop_loK0M ""', 400)
        s.cmd("screenshot hf_000", 400)
        for nm, tik, x in jobs:
            s.cmd('set coop_loK0X "%s"' % x, 40)
            s.cmd("set coop_loK0M %s" % tik, 700)
            s.cmd("screenshot hf_%s" % nm, 300)
    s.cmd("quit", 0)
    out = W.launch(name, "1080", s, budget=900)
    sh = os.path.join(out, "shots")
    os.makedirs(sh, exist_ok=True)
    for f in os.listdir(out):
        if f.startswith("hf_"):
            shutil.move(os.path.join(out, f), os.path.join(sh, f))
    print("frames", len(os.listdir(sh)), "->", sh)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "prep":
        prep(a[1])
    else:
        run(a[1], a[2], a[3])
