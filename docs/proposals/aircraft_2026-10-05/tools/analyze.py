"""analyze.py <rundir...> - per session: AIR lines, script errors, and the smoothness of every drawn aircraft from
cg_hzmAcDebug ACLERP lines (per render frame): speed = |dpos|/frametime; CV of the speed over the moving middle of
each pass, the share of frames with zero motion (stop-go judder), and the largest attitude step per frame."""
import collections, math, os, re, statistics, sys

RX = re.compile(r"ACLERP t=(\d+) ft=(\d+) e=(\d+) o=(\S+) (\S+) (\S+) a=(\S+) (\S+) (\S+) s=(\S+) fl=(\d)")


def angd(a, b):
    d = (a - b) % 360
    return min(d, 360 - d)


def smooth(L):
    per = collections.defaultdict(list)
    for m in RX.finditer(L):
        t, ft, e = int(m.group(1)), int(m.group(2)), int(m.group(3))
        o = tuple(float(m.group(k)) for k in (4, 5, 6))
        a = tuple(float(m.group(k)) for k in (7, 8, 9))
        per[e].append((t, ft, o, a))
    out = []
    for e, rows in per.items():
        rows.sort()
        # split into passes where the entity disappears for > 1 s
        passes, cur = [], [rows[0]]
        for r in rows[1:]:
            if r[0] - cur[-1][0] > 1000:
                passes.append(cur); cur = []
            cur.append(r)
        passes.append(cur)
        for p in passes:
            if len(p) < 30:
                continue
            sp, astep, zero = [], 0.0, 0
            for i in range(1, len(p)):
                dt = (p[i][0] - p[i - 1][0]) / 1000.0
                if dt <= 0:
                    continue
                d = math.dist(p[i][2], p[i - 1][2])
                sp.append(d / dt)
                astep = max(astep, max(angd(p[i][3][k], p[i - 1][3][k]) for k in range(3)))
            n = len(sp)
            mid = sp[n // 5: n - n // 5] if n > 10 else sp
            mean = statistics.mean(mid) if mid else 0
            cv = (statistics.pstdev(mid) / mean) if mean > 1 else 0
            zero = sum(1 for v in mid if v < 0.02 * mean) / max(1, len(mid))
            jit = [abs(mid[i] / mid[i - 1] - 1) for i in range(1, len(mid)) if mid[i - 1] > 1]
            jit.sort()
            fts = [r[1] for r in p]
            out.append({"ent": e, "frames": len(p), "mean_speed": round(mean), "cv": round(cv, 3),
                        "zero_frames": round(zero, 3),
                        "jitter_p50": round(jit[len(jit) // 2], 3) if jit else 0,
                        "jitter_p95": round(jit[int(len(jit) * 0.95)], 3) if jit else 0, "max_angle_step": round(astep, 2),
                        "frametime_ms": round(statistics.mean(fts), 1)})
    return out


def main():
    for run in sys.argv[1:]:
        for m in sorted(os.listdir(run)):
            f = os.path.join(run, m, "qconsole.log")
            if not os.path.exists(f):
                continue
            L = open(f, encoding="latin-1").read()
            print("=" * 10, run, m)
            for a in re.findall(r"\^~\^~\^ AIR[^\r\n]*", L)[:20]:
                print("  ", a[:230])
            errs = re.findall(r"[^\r\n]*(?:Script Error|was not properly loaded|Unknown command)[^\r\n]*", L)
            ours = [x for x in errs if re.search(r"aircraft|paradrop|officer|ac_probe|coop_aircraft", x)]
            print("   script errors: %d total, %d ours" % (len(errs), len(ours)))
            for x in ours[:10]:
                print("     ", x[:220])
            for x in re.findall(r"[^\r\n]*(?:aircraft|paradrop)\.scr[^\r\n]*", L)[:8]:
                print("     >", x[:220])
            for s in smooth(L):
                print("   pass", s)


if __name__ == "__main__":
    main()
