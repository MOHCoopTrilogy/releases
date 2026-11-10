"""v1.10.68 cut: take the Bren out of the PRIVATE finishes2 staging (H:\\hzm_work\\newguns\\fs2_build) and repack. Its state entry,
sheet and variant tiks are moved aside to fs2_build\\held_bren\\ (re-enable: move them back, merge held_bren\\state.json into
state.json, `fs2_ng.py pack`)."""
import json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
NG = os.environ.get('HZM_FS2_BUILD', r'H:\hzm_work\newguns\fs2_build')
HELD = os.path.join(NG, 'held_bren')
if len(sys.argv) > 1 and sys.argv[1] == 'restore':
    # [newguns2] the way back: the held state entry, sheet(s) and variant tiks return; then `fs2_ng.py pack`
    st = json.load(open(os.path.join(NG, 'state.json')))
    held = json.load(open(os.path.join(HELD, 'state.json')))
    assert 'coop_bren' not in st['guns'], 'already restored'
    st['guns'].update(held['guns']); st['sheets'].update(held['sheets'])
    wdir = os.path.join(NG, 'pak', 'models', 'weapons')
    n = 0
    for f in sorted(os.listdir(os.path.join(HELD, 'tiks'))):
        shutil.move(os.path.join(HELD, 'tiks', f), os.path.join(wdir, f)); n += 1
    for k in held['sheets']:
        if os.path.isdir(os.path.join(HELD, k)):
            shutil.move(os.path.join(HELD, k), os.path.join(NG, 'pak', 'textures', 'coop_finishes_hd', k))
    json.dump(st, open(os.path.join(NG, 'state.json'), 'w'), indent=1)
    shutil.rmtree(HELD)
    print('restored', n, 'tiks,', list(held['sheets']), '; guns now', len(st['guns']))
    sys.exit(0)
st = json.load(open(os.path.join(NG, 'state.json')))
gun = st['guns'].pop('coop_bren')
sheets = {k: v for k, v in st['sheets'].items() if v.get('baker') == 'coop_bren' or k.startswith('bren_')}
for k in sheets:
    st['sheets'].pop(k)
os.makedirs(os.path.join(HELD, 'tiks'), exist_ok=True)
json.dump(dict(guns={'coop_bren': gun}, sheets=sheets), open(os.path.join(HELD, 'state.json'), 'w'), indent=1)
wdir = os.path.join(NG, 'pak', 'models', 'weapons')
n = 0
for f in os.listdir(wdir):
    if f.startswith('coop_bren_fs2_'):
        shutil.move(os.path.join(wdir, f), os.path.join(HELD, 'tiks', f)); n += 1
for k in sheets:
    src = os.path.join(NG, 'pak', 'textures', 'coop_finishes_hd', k)
    if os.path.isdir(src):
        shutil.move(src, os.path.join(HELD, k))
json.dump(st, open(os.path.join(NG, 'state.json'), 'w'), indent=1)
print('held', n, 'tiks,', list(sheets), '; guns now', len(st['guns']))
