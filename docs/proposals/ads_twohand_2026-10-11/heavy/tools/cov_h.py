"""Heavy lane status file (heavy/coverage_status.json) in the shape of the pistol lane's tools/coverage_status.json.

The shared coverage.py knows the lanes 'rifles' and 'smg' only (2026-10-12: its LANES gives the mg / heavy classes to
'smg'), so `coverage.py --lane heavy` does not exist yet. This is the same scan rule (coverage.py scan(), copied) on
this lane's runs folder, plus the qa / rule / action / note setters.

    python cov_h.py scan <session> [...]
    python cov_h.py qa|rule|action|note <tik stem or gun key> <text...>
    python cov_h.py show [gun key]
"""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
STATUS = os.path.join(hv.LANE, 'coverage_status.json')
KEY = {"bar": "models/weapons/bar.tik", "breda": "models/weapons/it_w_breda.tik", "vickers": "models/weapons/uk_w_vickers.tik",
       "dp28": "models/weapons/dp28.tik", "fg42": "models/weapons/fg42.tik", "mp44": "models/weapons/mp44.tik",
       "shotgun": "models/weapons/shotgun.tik", "30cal": "models/weapons/30calportable.tik",
       "mg42": "models/weapons/mg42portable.tik"}


def load():
    return json.load(open(STATUS, encoding='utf-8')) if os.path.isfile(STATUS) else {}


def save(st):
    json.dump(st, open(STATUS, 'w', encoding='utf-8', newline='\n'), indent=1, sort_keys=True)


def scan(sessions):
    st = load()
    for sess in sessions:
        log = open('%s/%s/qconsole.log' % (hv.RUNS, sess), encoding='latin-1', errors='replace').read().splitlines()
        cur, rows, seg, fref = None, {}, {}, {}
        for ln in log:
            m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
            if m:
                cur = m.group(2) if m.group(1) == 'begin' else None
                if cur:
                    rows[cur] = []
                continue
            m = re.search(r'\^~\^~\^ DEMO (\w+) (\d+)', ln)
            if cur and m and 'echo' not in ln and '__demo__after' in cur:
                if m.group(1) == 'fire' and cur not in fref:
                    fref[cur] = rows[cur][-4:]
                if m.group(1) == 'reload':
                    g = cur.split('__')[2]
                    stn = cur.split('__')[3]                      # run_h.py --stdemo: the stance is in the tag
                    lane = not stn.startswith('yaw') and cur not in fref
                    seg[cur] = 'ab__%s__%s__%s__reload__after' % (sess, g, 'stand' if stn.startswith('yaw') else stn)
                    # stdemo has no `fire` mark: its first frames are the settled aim before the shots
                    rows[seg[cur]] = list(fref.get(cur) or (rows[cur][:4] if lane else rows[cur][-4:]))
                elif cur in seg:
                    del seg[cur]
                continue
            if cur in seg and 'ADSFRAME' in ln:
                p = re.search(r'pose=([-\d.]+).*sight=\(([-\d.]+) ([-\d.]+)\)', ln)
                if p:
                    rows[seg[cur]].append((float(p.group(1)), float(p.group(2)), float(p.group(3))))
            if cur and 'ADSFRAME' in ln:
                p = re.search(r'pose=([-\d.]+).*sight=\(([-\d.]+) ([-\d.]+)\)', ln)
                if p:
                    rows[cur].append((float(p.group(1)), float(p.group(2)), float(p.group(3))))
        for tag, r in rows.items():
            m = re.match(r'ab__%s__(\w+?)__(\w+?)__(aim|reload|bolt)__after$' % re.escape(sess), tag)
            if not m or not r:
                continue
            gun, stance, kind = m.groups()
            if stance.startswith('yaw'):
                continue
            tik = KEY.get(gun, 'models/weapons/%s.tik' % gun)
            y0, p0 = r[min(3, len(r) - 1)][1:3]
            devs = [((x[1] - y0) ** 2 + (x[2] - p0) ** 2) ** 0.5 for x in r]
            k = max(1, int(len(devs) * 0.15))
            edge = max(devs[:k] + devs[-k:])
            ok = min(x[0] for x in r) > 0.9 and max(devs) <= 6.0 and edge <= 1.5
            e = st.setdefault(tik, {}).setdefault(kind, {})
            e[stance] = dict(run=sess, ok=bool(ok), dev=round(max(devs), 2), edge=round(edge, 2),
                             end=round(max(devs[-5:]), 2), pmin=round(min(x[0] for x in r), 2))
            print(sess, gun, stance, kind, e[stance])
    save(st)
    print('status:', STATUS, len(st), 'weapons')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'scan':
        scan(sys.argv[2:])
    elif cmd in ('qa', 'rule', 'action', 'note'):
        st = load()
        st.setdefault(KEY.get(sys.argv[2], sys.argv[2]), {})[cmd] = ' '.join(sys.argv[3:])
        save(st)
    elif cmd == 'show':
        st = load()
        for k, v in sorted(st.items()):
            if len(sys.argv) < 3 or KEY.get(sys.argv[2]) == k:
                print(k, json.dumps(v, indent=1)[:1500])
