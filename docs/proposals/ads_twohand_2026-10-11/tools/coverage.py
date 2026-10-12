"""ADS coverage matrix: every Armory weapon (docs/tools/loadout_weapons.tsv, grenades excluded) + every own-mesh variant
the sight table knows + every weapon tik a script hands out that is not in the table. Derived, not written by hand:

  view-model prefix   parsed from CG_GetVMAnimPrefixIndex (cg_viewmodelanim.c): weapon NAME -> prefix, class fallback
  sight row           cg_adssights.h (exact name match, as CG_FindAdsSightByName)
  can aim             player_Torso.st: the AIM state's exclusions (launchers, scoped rifles zoom instead)
  rows / clips        fps_anims_*.txt of the mod tree (= released), the fixes pak source (shipped overrides) and this
                      proposal's staged tree (assets/)
  tested              coverage_status.json, filled by `coverage.py scan <session> ...` from the engine's own ADSFRAME
                      probe (settled aim: pose 1.00 and sight 0.0; reload / bolt: logcheck STAYS IN ADS, edges <= 1.5)
  QA                  coverage_status.json `qa` (run id + note), set by `coverage.py qa <tik stem> <run> <note>` after
                      the frames were looked at. A row is DONE only with clips + all stance groups tested + QA.

    python coverage.py build            -> ../coverage.md
    python coverage.py scan th4 th5     -> merge those sessions' results into coverage_status.json
    python coverage.py qa p38 th4 "sheet + gif checked"
    python coverage.py note webley_revolver "reload is a plain re-bake"
"""
import os, re, sys, json, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r'C:\mohaa-coop-dev'
ENG = os.path.join(ROOT, 'openmohaa-hzm-ads', 'code', 'cgame')
MOD = os.path.join(ROOT, 'hzm-mohaa-coop-mod')
FIX = os.path.join(ROOT, 'docs', 'tools', 'assets', 'fixes')
STAGE = os.path.join(HERE, '..', 'assets')
STATUS = os.path.join(HERE, 'coverage_status.json')
CBOX = {}
OUT = os.path.join(HERE, '..', 'coverage.md')
sys.path.insert(0, os.path.join(ROOT, 'docs', 'proposals', 'ironsights_2026-09-28', 'blender'))
for _p in glob.glob(os.path.join(ROOT, 'docs', 'proposals', 'ironsights_2026-09-28', '**', 'vfs.py'), recursive=True):
    sys.path.insert(0, os.path.dirname(_p)); break
import vfs  # noqa: E402  (read-only view of the installed paks)

CLASSFILES = ('rifle', 'smg', 'mg', 'pistol', 'shotgun', 'bazooka')
GROUPS = [('stand', ('stand',)), ('crouch', ('crouch',)), ('prone', ('prone',)),
          ('lean', ('standL', 'standR', 'crouchL', 'crouchR')), ('braced', ('braced',))]


def read(path):
    return open(path, 'rb').read().decode('latin-1').replace(chr(13), '')


# ---------------------------------------------------------------------------------------------- engine parsing
def prefix_rules():
    s = read(os.path.join(ENG, 'cg_viewmodelanim.c'))
    names = re.findall(r'"([^"]*)"', s[s.index('AnimPrefixList[] = {'):s.index('enum animPrefix_e')].split('};')[0])
    enum = re.findall(r'\b(WPREFIX_\w+)', s[s.index('enum animPrefix_e'):s.index('int CG_GetVMAnimPrefixIndex')])
    assert len(names) == len(enum), (len(names), len(enum))
    pfx = dict(zip(enum, names))
    body = s[s.index('int CG_GetVMAnimPrefixIndex'):]
    body = body[:body.index('\n}\n')]
    byname, fallback, cls, pend = {}, {}, None, []
    for ln in body.splitlines():
        m = re.search(r'iWeaponClass & (WEAPON_CLASS_\w+)', ln)
        if m:
            cls = m.group(1)[len('WEAPON_CLASS_'):].lower(); pend = []
        pend += re.findall(r'Q_stricmp\(szWeaponName, "([^"]+)"\)', ln)
        m = re.search(r'return (WPREFIX_\w+);', ln)
        if m and cls:
            if pend:
                for n in pend:
                    byname[(cls, n.lower())] = pfx[m.group(1)]
                pend = []
            else:
                fallback[cls] = pfx[m.group(1)]
    guard = re.findall(r'\{"(\w+)", "([^"]+)"\}', s[s.index('kAuthored[][2]'):s.index('kAuthored[][2]') + 400])
    return byname, fallback, dict(guard)


def sight_rows():
    s = read(os.path.join(ENG, 'cg_adssights.h'))
    rows = {}
    for m in re.finditer(r'\{"([^"]+)", (NULL|"[^"]*"), \{([^}]*)\}, \{([^}]*)\}', s):
        tik, name = m.group(1).lower(), m.group(2).strip('"')
        geo = (m.group(3).replace(' ', ''), m.group(4).replace(' ', ''))
        rows[tik] = (None if m.group(2) == 'NULL' else name, geo)
    return rows


def no_aim():
    s = read(os.path.join(MOD, 'coop_mod', 'player_Torso.st'))
    ln = [l for l in s.splitlines() if re.match(r'\s*AIM\s*:\s*COOP_ADS', l)][0]
    return ([n.lower() for n in re.findall(r'!IS_WEAPON_ACTIVE "mainhand" "([^"]+)"', ln)],
            [n.lower() for n in re.findall(r'!IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "([^"]+)"', ln)])


# ---------------------------------------------------------------------------------------------- rows and clips
def rows_of(base):
    """row name -> clip path, from a tree's models/player/base/fps_anims_*.txt (None if the tree has no such file)"""
    out, have = {}, set()
    for c in CLASSFILES:
        p = os.path.join(base, 'models', 'player', 'base', 'fps_anims_%s.txt' % c)
        if not os.path.isfile(p):
            continue
        have.add(c)
        for ln in read(p).splitlines():
            t = ln.split('//')[0].split()
            if len(t) >= 2 and t[1].lower().endswith('.skc') and t[0].lower() not in out:
                out[t[0].lower()] = t[1]
    return out, have


TIKFACT = {}


def tik_info(tik):
    d = vfs.read(tik)
    if d is None:
        p = os.path.join(MOD, tik.replace('/', os.sep))
        d = open(p, 'rb').read() if os.path.isfile(p) else None
    if d is None:
        return None, None
    s = d.decode('latin-1')
    n = re.search(r'(?m)^\s*name\s+"([^"]+)"', s)
    w = re.search(r'(?m)^\s*weapontype\s+(\w+)', s)
    fd = re.search(r'(?m)^\s*(?:sp |dm )?firedelay\s+([\d.]+)', s)
    TIKFACT[tik] = dict(firedelay=float(fd.group(1)) if fd else None, semi=bool(re.search(r'(?m)^\s*semiauto\b', s)))
    return (n.group(1) if n else None), (w.group(1).lower() if w else None)


def weapon_key(name):
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')


def strip_skin(name):
    m = re.match(r'^(.*\S)\s+\([^()]*\)$', name)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------------------------- weapon list
def weapons(sights):
    lst, seen = [], set()
    for ln in read(os.path.join(ROOT, 'docs', 'tools', 'loadout_weapons.tsv')).splitlines():
        t = ln.split('\t')
        if len(t) > 1 and re.match(r'^\d\d$', t[0]):
            lst.append((t[0], t[1].lower(), 'armory')); seen.add(t[1].lower())
    # own-mesh variants: a sight row whose geometry no Armory weapon has
    geo_seen = {sights[t][1] for t in seen if t in sights}
    var = []
    for tik, (name, geo) in sorted(sights.items()):
        if tik in seen or geo in geo_seen:
            continue
        geo_seen.add(geo); var.append(('v', tik, 'own-mesh variant')); seen.add(tik)
    # weapon tiks the scripts hand out
    found = collections.Counter()
    for d in ('maps', 'coop_mod', 'global'):
        for p in glob.glob(os.path.join(MOD, d, '**', '*.scr'), recursive=True):
            try:
                found.update(x.lower() for x in re.findall(r'models/weapons/[A-Za-z0-9_]+\.tik', read(p)))
            except OSError:
                pass
    scr = [('s', t, 'script-given') for t in sorted(found) if t not in seen and t not in sights]
    scr = [x for x in scr if not strip_skin(tik_info(x[1])[0] or '')]
    return lst, var, scr, len(sights)


# ---------------------------------------------------------------------------------------------- status
def load_status():
    return json.load(open(STATUS)) if os.path.isfile(STATUS) else {}


def scan(sessions):
    st = load_status()
    sys.path.insert(0, os.path.join(ROOT, 'docs', 'proposals', 'ads_bolt_2026-10-04', 'tools'))
    keymap = {}
    try:
        src = read(os.path.join(ROOT, 'docs', 'proposals', 'ads_bolt_2026-10-04', 'tools', 'run_adsbolt.py'))
        keymap = {k: v.lower() for k, v in re.findall(r'"(\w+)": "(models/weapons/[^"]+)"', src)}
    except OSError:
        pass
    for sess in sessions:
        log = open('G:/mohaa-adsanim/runs/%s/qconsole.log' % sess, encoding='latin-1', errors='replace').read().splitlines()
        cur, rows, seg, fref = None, {}, {}, {}
        for ln in log:
            m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
            if m:
                cur = m.group(2) if m.group(1) == 'begin' else None
                if cur:
                    rows[cur] = []
                continue
            # a `demo` capture (hip, raise, shots, aimed reload, lower in one take): its reload segment counts as the
            # standing aimed reload - re-tagged here so the same verdict rule applies
            m = re.search(r'\^~\^~\^ DEMO (\w+) (\d+)', ln)
            if cur and m and 'echo' not in ln and '__demo__after' in cur:
                if m.group(1) == 'fire' and cur not in fref:
                    fref[cur] = rows[cur][-4:]           # the settled aim BEFORE the first shot: an emptied gun starts
                if m.group(1) == 'reload':               # its reload by itself, before the harness's reload marker
                    g = cur.split('__')[2]
                    seg[cur] = 'ab__%s__%s__stand__reload__after' % (sess, g)
                    rows[seg[cur]] = list(fref.get(cur) or rows[cur][-4:])     # the reference samples
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
            tik = keymap.get(gun, 'models/weapons/%s.tik' % gun)
            y0, p0 = r[min(3, len(r) - 1)][1:3]
            devs = [((x[1] - y0) ** 2 + (x[2] - p0) ** 2) ** 0.5 for x in r]
            k = max(1, int(len(devs) * 0.15))
            edge = max(devs[:k] + devs[-k:])
            ok = min(x[0] for x in r) > 0.9 and max(devs) <= 6.0 and edge <= 1.5
            e = st.setdefault(tik, {}).setdefault(kind, {})
            # `end` = how far off the sights the capture ENDS: a hand-keyed reload that lowers the gun on purpose
            # (status `lowered`, set with `coverage.py lowered <tik>`) is judged on pose >= 0.9 and end <= 1.5 deg
            e[stance] = dict(run=sess, ok=bool(ok), dev=round(max(devs), 2), edge=round(edge, 2),
                             end=round(max(devs[-5:]), 2), pmin=round(min(x[0] for x in r), 2))
    json.dump(st, open(STATUS, 'w'), indent=1, sort_keys=True)
    print('status:', STATUS, len(st), 'weapons')


def tested(st, tik, kind):
    e = st.get(tik, {}).get(kind, {})
    if not e:
        return '-', 0
    low = bool(st.get(tik, {}).get('lowered')) and kind == 'reload'
    if low:
        e = {k: dict(v, ok=(v.get('pmin', 1.0) >= 0.9 and v.get('end', 99.0) <= 1.5)) for k, v in e.items()}
    out, n = [], 0
    for g, sts in GROUPS:
        got = [e[s] for s in sts if s in e]
        if got and all(x['ok'] for x in got) and len(got) == len(sts if g != 'lean' else sts[:2]) or \
                (got and all(x['ok'] for x in got) and len(got) >= (2 if g == 'lean' else 1)):
            out.append(g); n += 1
        elif got and not all(x['ok'] for x in got):
            out.append(g + '!FAIL')
    runs = sorted({x['run'] for x in e.values()})
    worst = max(x['dev'] for x in e.values())
    if low:
        return '%s (%s; gun lowered by design, ends %.1f deg)' % (' '.join(out) or 'none pass', ','.join(runs), max(x.get('end', 99.0) for x in e.values())), n
    return '%s (%s, max %.1f deg)' % (' '.join(out) or 'none pass', ','.join(runs), worst), n


# ---------------------------------------------------------------------------------------------- build
def build():
    byname, fallback, guard = prefix_rules()
    sights = sight_rows()
    by_sname = {n.lower(): t for t, (n, g) in sights.items() if n}
    noaim_names, noaim_classes = no_aim()
    mod_rows, _ = rows_of(MOD)
    stg_rows, stg_have = rows_of(STAGE)
    live_rows = {}
    for c in CLASSFILES:                       # what is LIVE: the installed paks, in engine priority order
        d = vfs.read('models/player/base/fps_anims_%s.txt' % c)
        for ln in (d.decode('latin-1').replace(chr(13), '').splitlines() if d else []):
            t = ln.split('//')[0].split()
            if len(t) >= 2 and t[1].lower().endswith('.skc') and t[0].lower() not in live_rows:
                live_rows[t[0].lower()] = t[1]
    st = load_status()
    arm, var, scr, nsight = weapons(sights)
    global CBOX
    CBOX = {}
    cbp = os.path.join(HERE, 'centrebox.json')
    if os.path.isfile(cbp):
        km = {}
        try:
            src_ = read(os.path.join(ROOT, 'docs', 'proposals', 'ads_bolt_2026-10-04', 'tools', 'run_adsbolt.py'))
            km = {k: v.lower() for k, v in re.findall(r'"(\w+)": "(models/weapons/[^"]+)"', src_)}
        except OSError:
            pass
        for g_, v_ in json.load(open(cbp)).items():
            CBOX[km.get(g_, 'models/weapons/%s.tik' % g_)] = v_

    def has_clip(tree, clip):
        return os.path.isfile(os.path.join(tree, 'models', 'human', 'animation', clip.replace('/', os.sep)))

    def row_state(name):
        """-> (state, clip). staged = this proposal's tree (row + clip there, and it differs from what is live);
        shipped = row and clip in the installed paks; tree-only = a row in the mod working tree that no installed pak
        has (unverified work in progress, held out of releases); missing"""
        n = name.lower()
        if n in stg_rows and has_clip(STAGE, stg_rows[n]) and stg_rows[n] != live_rows.get(n, ''):
            return 'staged', stg_rows[n]
        if n in stg_rows and has_clip(STAGE, stg_rows[n]) and n in live_rows:
            return 'staged (re-baked, replaces the shipped clip)', stg_rows[n]
        if n in live_rows and vfs.winner('models/human/animation/' + live_rows[n]):
            return 'shipped', live_rows[n]
        if n in mod_rows:
            return 'tree-only', mod_rows[n]
        return 'missing', None

    lines, counts = [], collections.Counter()
    table = []
    for wid, tik, src in arm + var + scr:
        name, wtype = tik_info(tik)
        if name is None and tik in sights and sights[tik][0]:
            name = sights[tik][0]
        if wtype in ('grenade', 'item') or (name is None and wtype is None):
            continue
        base = strip_skin(name) if name else None
        look = (base or name or '').lower()
        cls = {'pistol': 'pistol', 'rifle': 'rifle', 'smg': 'smg', 'mg': 'mg', 'heavy': 'heavy'}.get(wtype, wtype or '?')
        pfx = byname.get((cls, look)) or byname.get((cls, (name or '').lower())) or fallback.get(cls, '?')
        sight = 'yes' if (name or '').lower() in by_sname else 'NO'
        aims = not ((name or '').lower() in noaim_names or look in noaim_names or cls in noaim_classes)
        key = weapon_key(name or '')
        # aim pose
        cstate, cclip = row_state(pfx + '_charge')
        if not aims:
            aim = 'does not aim (Torso AIM excludes it)'
        elif cstate == 'missing':
            aim = 'NO aim row'
        elif cls == 'pistol':
            aim = ('two-handed %s' % cstate) if (cclip or '').endswith('_ads2h.skc') else 'one-handed (%s)' % cstate
        else:
            aim = cstate
        # aimed reload (per-weapon reload row wins, as CoopPerWeaponReloadAnim)
        parts = []
        own = ('coopr_%s_reload' % key) in mod_rows or ('coopr_%s_reload' % key) in live_rows
        rb = ('coopr_%s' % key) if own else pfx
        for suf in ('reload', 'reload_single', 'reload_end'):
            if row_state('%s_%s' % (rb, suf))[0] != 'missing':
                parts.append(suf)
        if not aims:
            rel = 'n/a'
        elif not parts:
            rel = 'no reload row'
        else:
            sts = [row_state('%s_%s_ads' % (rb, suf))[0] for suf in parts]
            rel = sts[0] if len(set(sts)) == 1 else '/'.join(sts)
            if len(parts) > 1:
                rel += ' (%d parts)' % len(parts)
            if own:
                rel += ' [own clip coopr_%s]' % key
        # aimed bolt / action cycle
        if not aims or row_state(pfx + '_rechamber')[0] == 'missing':
            bolt = 'n/a' if not aims else 'no cycle row'
        else:
            bolt = row_state(pfx + '_rechamber_ads')[0]
            if pfx in guard and bolt != 'missing' and (name or '').lower() != guard[pfx].lower() and look != guard[pfx].lower():
                bolt += ' but GUARDED OFF (authored on %s)' % guard[pfx]
        ta, na = tested(st, tik, 'aim')
        tr, nr = tested(st, tik, 'reload')
        tb, nb = tested(st, tik, 'bolt')
        qa = st.get(tik, {}).get('qa', '')
        need_bolt = bolt not in ('n/a', 'no cycle row')
        clips_ok = aims and aim not in ('NO aim row',) and not aim.startswith('one-handed') and \
            rel.split(' ')[0] in ('staged', 'shipped') and (not need_bolt or bolt.split(' ')[0] in ('staged', 'shipped'))
        clips_ok = clips_ok and 'missing' not in rel and 'tree-only' not in rel
        if not aims:
            status = 'N/A'
        elif clips_ok and na >= 5 and nr >= 5 and (not need_bolt or nb >= 5) and qa:
            status = 'DONE'
        elif clips_ok and qa and na >= 4 and nr >= 4:
            status = 'DONE but braced'
        elif clips_ok or na or nr:
            status = 'PARTIAL'
        else:
            status = 'TODO'
        tf = TIKFACT.get(tik, {})
        if not aims:
            cyc = 'n/a'
        elif row_state(pfx + '_rechamber')[0] != 'missing':
            cyc = 'bolt / action per shot (row: aimed clip %s)' % bolt.split(' but')[0]
        elif tf.get('firedelay') and tf['firedelay'] >= 0.8 and cls in ('pistol', 'rifle') and sight == 'yes':
            cyc = 'HAND-CYCLED per shot (fire delay %.1f s): aimed clip %s' % (tf['firedelay'], row_state(pfx + '_cycle_ads')[0])
        else:
            cyc = 'self-loading / none'
        cb = CBOX.get(tik) or {}
        cbt = ('%.1f deg / %.1f %% of frames (base %.0f %%, max %.0f %%; %s)' % (cb['dev'], cb['over'], cb['base'], cb['max'], cb['run'])) if cb else '-'
        act = st.get(tik, {}).get('action', 'not recorded')
        table.append(dict(id=wid, tik=tik, name=name or '?', cls=cls, pfx=pfx, sight=sight, aim=aim, rel=rel, bolt=bolt, cyc=cyc, cbt=cbt, act=act,
                          ta=ta, tr=tr, tb=tb, qa=qa, status=status, src=src, aims=aims))
        counts[(cls, status)] += 1
    # ------------------------------------------------------------------ write
    order = {'pistol': 0, 'rifle': 1, 'smg': 2, 'mg': 3, 'heavy': 4}
    table.sort(key=lambda r: (order.get(r['cls'], 9), {'armory': 0, 'own-mesh variant': 1, 'script-given': 2}[r['src']], r['id'], r['tik']))
    L = ['# ADS coverage matrix', '',
         'GENERATED by `tools/coverage.py build` - do not edit; re-run it. Sources and rules are in that file\'s header.',
         'Engine tree: `openmohaa-hzm-ads` (ads-next). Sight table rows: %d. A variant that shares its base gun\'s clips' % nsight,
         'still needs its own in-engine check: a row is DONE only with clips + every stance group tested + a QA run id.', '']
    cls_tot = collections.Counter(r['cls'] for r in table)
    L += ['## Summary', '', '| class | weapons | DONE | DONE but braced | PARTIAL | TODO | N/A (does not aim) | no sight row |', '|---|---|---|---|---|---|---|---|']
    for c in sorted(cls_tot, key=lambda c: order.get(c, 9)):
        L.append('| %s | %d | %d | %d | %d | %d | %d | %d |' % (
            c, cls_tot[c], counts[(c, 'DONE')], counts[(c, 'DONE but braced')], counts[(c, 'PARTIAL')], counts[(c, 'TODO')],
            counts[(c, 'N/A')], sum(1 for r in table if r['cls'] == c and r['sight'] == 'NO')))
    L.append('| **all** | %d | %d | %d | %d | %d | %d | %d |' % (
        len(table), sum(v for (c, s), v in counts.items() if s == 'DONE'), sum(v for (c, s), v in counts.items() if s == 'DONE but braced'),
        sum(v for (c, s), v in counts.items() if s == 'PARTIAL'), sum(v for (c, s), v in counts.items() if s == 'TODO'),
        sum(v for (c, s), v in counts.items() if s == 'N/A'), sum(1 for r in table if r['sight'] == 'NO')))
    by = collections.Counter()
    for r in table:
        if r['aims']:
            by[('aim', r['aim'])] += 1; by[('reload', r['rel'].split(' [')[0].split(' (')[0].split(',')[0])] += 1
            by[('bolt', r['bolt'].split(' but')[0])] += 1
    L += ['', 'Clip state over the weapons that aim:', '']
    for k in ('aim', 'reload', 'bolt'):
        L.append('- **%s**: ' % k + ', '.join('%s %d' % (s, n) for (kk, s), n in sorted(by.items(), key=lambda x: -x[1]) if kk == k))
    L += ['']
    cur = None
    for r in table:
        if r['cls'] != cur:
            cur = r['cls']
            L += ['', '## %s' % cur, '',
                  '| id | weapon | tik | prefix | sight row | aim pose | aimed reload | aimed bolt / action | per-shot cycle | action worked by (hand / control / shown) | on target: max sight dev / centre box covered | aim tested | reload tested | bolt tested | QA | status |',
                  '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
        L.append('| %s | %s | `%s` | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | **%s** |' % (
            r['id'], r['name'], r['tik'].replace('models/weapons/', ''), r['pfx'], r['sight'], r['aim'], r['rel'], r['bolt'], r['cyc'], r['act'], r['cbt'],
            r['ta'], r['tr'], r['tb'], (r['qa'] or '-') + (' / OPEN: ' + st[r['tik']]['note'] if st.get(r['tik'], {}).get('note') else ''), r['status']))
    L += ['', 'id `v` = own-mesh variant taken from the sight table (a finish whose sight geometry differs from every Armory',
          'weapon); id `s` = a weapon tik a script hands out that is in neither. Plain re-skins (same sight geometry as',
          'their base gun) are not listed: they share the base gun\'s row.', '']
    open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(L))
    print('wrote', OUT, len(table), 'weapons')
    for ln in L[6:6 + len(cls_tot) + 9]:
        print(ln)
    return table


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'build'
    if cmd == 'scan':
        scan(sys.argv[2:])
    elif cmd == 'lowered':                    # this weapon's aimed reload lowers the gun on purpose (hand-keyed)
        s = load_status()
        tik = sys.argv[2].lower()
        tik = tik if tik.startswith('models/') else 'models/weapons/%s.tik' % tik
        s.setdefault(tik, {})['lowered'] = True
        json.dump(s, open(STATUS, 'w'), indent=1, sort_keys=True)
    elif cmd == 'action':                     # which hand works which control, and whether it is shown (judgement, by hand)
        s = load_status()
        tik = sys.argv[2].lower()
        tik = tik if tik.startswith('models/') else 'models/weapons/%s.tik' % tik
        s.setdefault(tik, {})['action'] = ' '.join(sys.argv[3:])
        json.dump(s, open(STATUS, 'w'), indent=1, sort_keys=True)
    elif cmd == 'note':                       # an open remark on a weapon: shown, never counted as QA
        s = load_status()
        tik = sys.argv[2].lower()
        tik = tik if tik.startswith('models/') else 'models/weapons/%s.tik' % tik
        s.setdefault(tik, {})['note'] = ' '.join(sys.argv[3:])
        json.dump(s, open(STATUS, 'w'), indent=1, sort_keys=True)
    elif cmd == 'qa':
        s = load_status()
        tik = sys.argv[2].lower()
        tik = tik if tik.startswith('models/') else 'models/weapons/%s.tik' % tik
        s.setdefault(tik, {})['qa'] = '%s: %s' % (sys.argv[3], ' '.join(sys.argv[4:]))
        json.dump(s, open(STATUS, 'w'), indent=1, sort_keys=True)
    else:
        build()
