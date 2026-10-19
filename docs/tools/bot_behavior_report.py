"""Bot BEHAVIOUR report for a soak dir (docs/tools/bot_soak.ps1 logs, bot_probe on) - what the bots spend their time
on, and whether it serves the mode (user 2026-09-24: "they are spending more time being confused and doing weird stuff
than playing the mode").

    python docs/tools/bot_behavior_report.py <soakdir> [map ...]

Reads the probe2 telemetry (fgame/playerbot*.cpp, bug-2879):
  BOTPROBE ... od= st= why=   distance to the objective, state flags, the TAG of the route being walked
  BOTGOAL why= kind= ok= od= tod=   every route change and who asked for it
  BOTJUMP why=                every jump and its cause
  BOTSTATE on=/off=           state machine transitions
  BOTEV ev=                   tactic decisions / outcomes (breach*, cov*, nade*, hold, lane, ...)
  BOTELEV / MPELEV            lift telemetry and stalls
Per map it prints:
  ACTIVITY   share of alive time by what the bot is doing (fighting, or the tag of the route it walks)
  PROGRESS   for each route tag: mean objective approach speed (u/s, + = closing on the objective) and the share of
             its time spent moving AWAY from the objective
  REVERSALS  >= 4s episodes, out of combat, where the objective distance grows >= 250u - by the tag that started it
  LOOPS      20s windows, out of combat, >= 800u walked but <= 200u net - by the dominant tag
  GOALS      route requests per bot-minute by tag, and the share that found no path
  JUMPS      by cause
  BREACH / COVER / GRENADES  outcome counts
  LIFT       samples under the cab, in the shaft off the link, stalls
"""
import os, re, sys
from collections import Counter, defaultdict, deque

RXP = re.compile(r'BOTPROBE e=(\d+) tm=(\w) al=(\d) hp=-?\d+ px=(-?[\d.]+) py=(-?[\d.]+) pz=(-?[\d.]+) spd=([\d.]+) '
                 r'fm=(-?\d+) rm=(-?\d+) um=(-?\d+) fire=(\d+) blk=\d+ jmp=(\d+) pth=(\d+) gd=(-?[\d.]+) en=(-?\d+) '
                 r'ed=(-?[\d.]+) seen=(-?\d+) pain=(-?\d+) cov=(\d+) od=(-?[\d.]+) st=(\d+) why=(\w+)')
RXT = re.compile(r'\[\d+-\d+-\d+ (\d+):(\d+):(\d+)')
RXG = re.compile(r'BOTGOAL e=(\d+) why=(\w+) kind=(\w+) ok=(\d)')
RXJ = re.compile(r'BOTJUMP e=(\d+) why=(\w+)')
RXS = re.compile(r'BOTSTATE e=(\d+) (on|off)=(\w+)')
RXE = re.compile(r'BOTEV e=(\d+) tm=\w ev=(\w+)')
RXL = re.compile(r'BOTELEV e=(\d+) tm=\w link=(\d) appr=(\d) shaft=(\d) under=(\d) onmover=(\d) z=(-?\d+)')
PROBE_S = 0.5  # bot_soak -ProbeMs 500


def secs(line):
    m = RXT.search(line)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) if m else None


def analyse(path):
    per = defaultdict(list)  # e -> [(t, x, y, z, od, fighting, why, stuck-ish)]
    goals, goalfail, jumps, states, evs = Counter(), Counter(), Counter(), Counter(), Counter()
    elev = Counter()
    elev_under_bots = set()
    stalls = []
    t0 = None
    idx = Counter()
    for line in open(path, encoding='latin-1', errors='replace'):
        if 'BOTPROBE' in line:
            m = RXP.search(line)
            if not m:
                continue
            e = int(m.group(1))
            if m.group(3) != '1':
                per[e].append(None)  # death / not alive: break sequences
                continue
            t = secs(line)
            if t is None:
                t = idx[e] * PROBE_S
            idx[e] += 1
            if t0 is None:
                t0 = t
            x, y, z = float(m.group(4)), float(m.group(5)), float(m.group(6))
            spd, fm, rm = float(m.group(7)), int(m.group(8)), int(m.group(9))
            fire, en, st = m.group(11) != '0', int(m.group(15)), int(m.group(21))
            seen = int(m.group(17))
            od, why = float(m.group(20)), m.group(22)
            fighting = (st & 1) and en >= 0 and (fire or (0 <= seen < 3000))
            wants = abs(fm) > 20 or abs(rm) > 20
            per[e].append((t - t0, x, y, z, od, fighting, why, wants and spd < 12 and not fire, int(m.group(19))))
            continue
        m = RXG.search(line)
        if m:
            goals[m.group(2)] += 1
            if m.group(4) == '0':
                goalfail[m.group(2)] += 1
            if m.group(3) == 'avoidrandom':
                goals['!avoidrandom'] += 1
            continue
        m = RXJ.search(line)
        if m:
            jumps[m.group(2)] += 1
            continue
        m = RXS.search(line)
        if m:
            states[m.group(2) + ':' + m.group(3)] += 1
            continue
        m = RXE.search(line)
        if m:
            evs[m.group(2)] += 1
            continue
        m = RXL.search(line)
        if m:
            e = int(m.group(1))
            link, appr, shaft, under, onmover = (int(m.group(i)) for i in range(2, 7))
            elev['samples'] += 1
            if under:
                elev['under'] += 1
                elev_under_bots.add(e)
            if shaft and not link:
                elev['shaft_offlink'] += 1
            if link:
                elev['onlink'] += 1
            continue
        if 'MPELEV STALL ' in line:
            stalls.append(line[line.find('MPELEV'):].strip()[:120])
        elif 'MPELEV cab=' in line:
            elev['trips'] += 1
    return per, goals, goalfail, jumps, states, evs, elev, elev_under_bots, stalls


def report(name, path):
    per, goals, goalfail, jumps, states, evs, elev, under_bots, stalls = analyse(path)
    alive = sum(1 for e in per for s in per[e] if s)
    if not alive:
        print(f"== {name}: no probe2 samples (old dll or bot_probe off)")
        return
    bots = len(per)
    minutes = max((s[0] for e in per for s in per[e] if s), default=60) / 60.0 or 1.0
    act = Counter()
    prog_sum, prog_n, away_n, tag_n = Counter(), Counter(), Counter(), Counter()
    stuck = Counter()
    reversals, loops = Counter(), Counter()
    for e, seq in per.items():
        prev = None
        hist = deque(maxlen=40)  # 20s at 500ms
        rev_start = None
        for s in seq:
            if s is None:
                prev, rev_start = None, None
                hist.clear()
                continue
            t, x, y, z, od, fighting, why, stuckish, cov = s
            key = 'FIGHT' if fighting else why
            act[key] += 1
            if stuckish:
                stuck[key] += 1
            if prev and not fighting and od >= 0 and prev[4] >= 0 and 0 < t - prev[0] <= 2.0:
                v = (prev[4] - od) / (t - prev[0])  # + = closing on the objective
                prog_sum[why] += v
                prog_n[why] += 1
                if v < -40:
                    away_n[why] += 1
                tag_n[why] += 1
            # reversal: od rising over >= 4s by >= 250u, out of combat
            if not fighting and od >= 0:
                if rev_start is None:
                    rev_start = (t, od, why)
                else:
                    if od < rev_start[1] - 50 or t - rev_start[0] > 12:
                        rev_start = (t, od, why)
                    elif od - rev_start[1] >= 250 and t - rev_start[0] >= 4:
                        reversals[rev_start[2]] += 1
                        rev_start = (t, od, why)
            else:
                rev_start = None
            hist.append((t, x, y, fighting, why))
            if len(hist) == hist.maxlen and not any(h[3] for h in hist):
                walked = sum(((hist[i][1] - hist[i - 1][1]) ** 2 + (hist[i][2] - hist[i - 1][2]) ** 2) ** 0.5
                             for i in range(1, len(hist)))
                net = ((hist[-1][1] - hist[0][1]) ** 2 + (hist[-1][2] - hist[0][2]) ** 2) ** 0.5
                if walked >= 800 and net <= 200:
                    loops[Counter(h[4] for h in hist).most_common(1)[0][0]] += 1
                    hist.clear()
            prev = s
    print(f"== {name}   {bots} bots, {alive} alive samples, {minutes:.1f} min")
    print('  ACTIVITY  ' + '  '.join(f"{k} {100.0 * v / alive:.1f}%" for k, v in act.most_common(14)))
    print('  STUCK     ' + '  '.join(f"{k} {100.0 * v / alive:.1f}%" for k, v in stuck.most_common(8)))
    rows = sorted(tag_n, key=lambda k: -tag_n[k])[:12]
    print('  PROGRESS  ' + '  '.join(f"{k} {prog_sum[k] / max(1, prog_n[k]):+.0f}u/s away{100.0 * away_n[k] / max(1, tag_n[k]):.0f}%"
                                     for k in rows))
    print('  REVERSALS ' + (', '.join(f"{k} {v}" for k, v in reversals.most_common(10)) or '-'))
    print('  LOOPS     ' + (', '.join(f"{k} {v}" for k, v in loops.most_common(10)) or '-'))
    bm = bots * minutes
    print('  GOALS/bm  ' + ', '.join(f"{k} {v / bm:.1f}" + (f"(fail{100.0 * goalfail[k] / v:.0f}%)" if goalfail[k] else '')
                                     for k, v in goals.most_common(14)))
    print('  JUMPS     ' + (', '.join(f"{k} {v}" for k, v in jumps.most_common()) or '-'))
    br = {k: v for k, v in evs.items() if k.startswith('breach') or k.startswith('nade')}
    cv = {k: v for k, v in evs.items() if k.startswith('cov') or k in ('bound', 'relocate', 'takecover', 'peek', 'leanL',
                                                                      'leanR', 'blindfire', 'holdcover')}
    other = {k: v for k, v in evs.items() if k not in br and k not in cv}
    print('  GRENADE   ' + (', '.join(f"{k} {v}" for k, v in sorted(br.items(), key=lambda kv: -kv[1])) or '-'))
    print('  COVER     ' + (', '.join(f"{k} {v}" for k, v in sorted(cv.items(), key=lambda kv: -kv[1])) or '-'))
    print('  OTHER EV  ' + (', '.join(f"{k} {v}" for k, v in sorted(other.items(), key=lambda kv: -kv[1])) or '-'))
    flips = sum(v for k, v in states.items() if k.startswith('on:'))
    print(f"  STATES    {flips / bm:.1f} state entries per bot-minute: " + ', '.join(f"{k} {v}" for k, v in states.most_common(8)))
    if elev['samples'] or stalls:
        print(f"  LIFT      samples {elev['samples']}, on link {elev['onlink']}, UNDER THE CAB {elev['under']} "
              f"(bots {sorted(under_bots)}), in shaft off the link {elev['shaft_offlink']}, trips {elev['trips']}, "
              f"STALLS {len(stalls)}")
        for s in stalls[:6]:
            print('            ' + s)


CONFUSED = ('stuckescape', 'blockrepath', 'wander', 'wandershort', 'routewp', 'lastdeath', 'avoidrandom')
OBJECTIVE = ('objective', 'curiousobj', 'attackobj', 'laneobj', 'lane', 'holdfront', 'bound', 'chase')


def summary(name, path):
    """One line: where the time goes and how often the bots reverse / loop / jump (the --summary table)."""
    per, goals, goalfail, jumps, states, evs, elev, under_bots, stalls = analyse(path)
    alive = sum(1 for e in per for s in per[e] if s)
    if not alive:
        print(f"{name:7s} no probe2 samples")
        return
    minutes = max((s[0] for e in per for s in per[e] if s), default=60) / 60.0 or 1.0
    act = Counter()
    rev = loops = 0
    for e, seq in per.items():
        start = None
        hist = deque(maxlen=40)
        for s in seq:
            if s is None:
                start = None
                hist.clear()
                continue
            t, x, y, z, od, fighting, why, stuckish, cov = s
            act['FIGHT' if fighting else why] += 1
            if not fighting and od >= 0:
                if start is None or od < start[1] - 50 or t - start[0] > 12:
                    start = (t, od)
                elif od - start[1] >= 250 and t - start[0] >= 4:
                    rev += 1
                    start = (t, od)
            else:
                start = None
            hist.append((x, y, fighting))
            if len(hist) == hist.maxlen and not any(h[2] for h in hist):
                walked = sum(((hist[i][0] - hist[i - 1][0]) ** 2 + (hist[i][1] - hist[i - 1][1]) ** 2) ** 0.5 for i in range(1, len(hist)))
                net = ((hist[-1][0] - hist[0][0]) ** 2 + (hist[-1][1] - hist[0][1]) ** 2) ** 0.5
                if walked >= 800 and net <= 200:
                    loops += 1
                    hist.clear()
    pct = lambda keys: 100.0 * sum(act[k] for k in keys) / alive
    bots = max(1, len(per))
    print(f"{name:7s} fight {100.0 * act['FIGHT'] / alive:5.1f}%  objective {pct(OBJECTIVE):5.1f}%  CONFUSED {pct(CONFUSED):5.1f}%  "
          f"none {100.0 * act['none'] / alive:4.1f}%  rev/bm {rev / bots / minutes:4.2f}  loops/bm {loops / bots / minutes:4.2f}  "
          f"jumps/bm {sum(jumps.values()) / bots / minutes:4.2f}  lift-stalls {len(stalls)}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    args = [a for a in sys.argv[1:] if a != '--summary']
    d = args[0]
    maps = args[1:] or sorted(f[:-4] for f in os.listdir(d) if f.endswith('.log'))
    for m in maps:
        p = os.path.join(d, m + '.log')
        if os.path.exists(p):
            (summary if '--summary' in sys.argv else report)(m, p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
