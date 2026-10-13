"""one-off: the text edits of ship cut v2 (shiplist entry, README handover, coverage status). Idempotent."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
P = r'C:\mohaa-coop-dev\docs\proposals\ads_twohand_2026-10-11'

# shiplist.py: the Mk VI is a gun of its own in the list
p = os.path.join(HERE, 'shiplist.py')
s = open(p, encoding='utf-8').read()
a = "('nagant_revolver', 'Nagant Revolver', 'nagantrev', None)]"
if "'colt45_colt1911w'" not in s:
    assert a in s
    s = s.replace(a, "('nagant_revolver', 'Nagant Revolver', 'nagantrev', None), ('colt45_colt1911w', 'Webley Mk VI', 'webley', None)]")
    open(p, 'w', encoding='utf-8', newline='\n').write(s)

# README handover
p = os.path.join(P, 'README.md')
s = open(p, encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in s[:3000] else '\n'
a = "**`PISTOLS_SHIP.md` is the ship cut; the folder `ship/` is FROZEN**"
if 'SHIP CUT v2' not in s:
    assert a in s
    add = ("**SHIP CUT v2 (later the same morning):** `webley_revolver_lv_ttwebley.tik` staged (`finishclone.py --also`), the Webley Mk VI "
           "`colt45_colt1911w.tik` staged on the Webley's rows with its own gun clips retimed (`tools/mk6.py`), a sample of the finish tiks and three model "
           "variants run in the engine (pa25, pa27, pa28; pa26 = an empty folder, started by mistake while pa25 was still running - the wait loop had "
           "matched the previous run's `run ended` line; the second runner stopped at the busy log file and nothing was lost). **pa29 is next.** "
           "The coordinator's calls: the decided server-side changes stay in, Welrod / Luger ship on their new aim poses for the user's test, texture "
           "lifts stay out. Runs pa18-pa24 were moved to `H:\\hzm_archive\\pistols\\`; pa25-pa28 are still in `G:\\mohaa-adsanim\\runs`." + nl + nl)
    s = s.replace(a, add + a, 1)
    open(p, 'w', encoding='utf-8', newline='').write(s)

# coverage status
p = os.path.join(P, 'tools', 'coverage_status.json')
d = json.load(open(p))
k = 'models/weapons/colt45_colt1911w.tik'
e = d.setdefault(k, {})
if 'pa28' not in e.get('qa', ''):
    e['qa'] = (e.get('qa', '') + ('; ' if e.get('qa') else '')
               + 'pa28 (2026-10-13): staged on the Webley rows with ITS OWN gun clips retimed onto the Webley\'s frames (mk6.py); aimed + hip reload, '
                 'standing: opens and shuts in step with the Webley at the same capture frames (sheet looked at); hand points still the Webley\'s; '
                 'no stance other than standing, no centre-box figure')
    json.dump(d, open(p, 'w'), indent=1)
print('v2 text edits done')
