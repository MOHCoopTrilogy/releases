"""collect_cams.py - qconsole.log (cg_engraveDebug 1) -> cams.json for gen_engrave_anchors.py.

Per gun tiki, the LAST settled reading: the camera in the gun's entity space (cam, fwd, right, up), the weapon fov, and
every bone of the gun as the engine posed it in first person (bones: name -> [origin, [ax0, ax1, ax2]]).
"Settled" = two consecutive ENGRAVECAM lines for the same tiki whose cam differs by under 0.5 units (the raise is over).

    python docs/tools/engrave/collect_cams.py <qconsole.log> [...] --out cams.json [--merge]
"""
import json, re, sys
import numpy as np

V = r"([-\d.]+) ([-\d.]+) ([-\d.]+)"
RC = re.compile(r"ENGRAVECAM tiki=(\S+) scale=\S+ cam=" + V + " fwd=" + V + " right=" + V + " up=" + V + r" fov=([\d.]+) ([\d.]+) wfov=([\d.]+)")
RT = re.compile(r'ENGRAVETAG tiki=(\S+) num=\d+ tag="([^"]*)" org=' + V + " ax0=" + V + " ax1=" + V + " ax2=" + V)


def f3(m, i):
    return [float(m.group(i)), float(m.group(i + 1)), float(m.group(i + 2))]


def main():
    out = sys.argv[sys.argv.index("--out") + 1]
    logs = [a for a in sys.argv[1:] if a.endswith(".log")]
    res = json.load(open(out)) if "--merge" in sys.argv else {}
    for lg in logs:
        last = {}
        bones = {}
        for line in open(lg, encoding="latin-1", errors="replace"):
            m = RC.search(line)
            if m:
                t = m.group(1).lower()
                cam = f3(m, 2)
                rec = dict(cam=cam, fwd=f3(m, 5), right=f3(m, 8), up=f3(m, 11), fov_x=float(m.group(14)), fov_y=float(m.group(15)),
                           wfov_x=float(m.group(16)))
                prev = last.get(t)
                if prev is not None and np.linalg.norm(np.array(prev["cam"]) - cam) < 0.5:
                    rec["settled"] = True
                    rec["bones"] = bones.get(t, {})
                    # the weapon is drawn with wfov: the screen test must use it (aspect from the world fov pair)
                    ax = np.tan(np.radians(rec["fov_y"]) / 2) / np.tan(np.radians(rec["fov_x"]) / 2)
                    rec["fov_y_w"] = float(np.degrees(2 * np.arctan(np.tan(np.radians(rec["wfov_x"]) / 2) * ax)))
                    res[t] = rec
                last[t] = rec
                bones[t] = {}
                continue
            m = RT.search(line)
            if m:
                t = m.group(1).lower()
                bones.setdefault(t, {})[m.group(2)] = [f3(m, 3), [f3(m, 6), f3(m, 9), f3(m, 12)]]
    json.dump(res, open(out, "w"), indent=1)
    print(len(res), "guns settled:", " ".join(sorted(k.split("/")[-1] for k in res)))


if __name__ == "__main__":
    main()
