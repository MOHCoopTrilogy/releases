"""Heavy lane (MGs / shotgun) common: paths, the pistol lane's shared tools as a LIBRARY, the lane's guns.

Nothing here writes outside heavy/ and the lane's own scratch dir / test install (G:\\mohaa-adsanim4, port 12598).
Run the lane tools with the staging tree as cwd:   cd heavy/assets; python ../tools/<tool>.py ...
(the bake library looks a clip up under ./models/human/animation first, then in the installed paks).
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
ASSETS = os.path.join(LANE, 'assets')
EVID = os.path.join(LANE, 'evidence')
SHARED = os.path.join(os.path.dirname(LANE), 'tools')                       # pistol lane's tools: read-only for us
BOLT = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
FIXES = r"C:\mohaa-coop-dev\docs\tools\assets\fixes"                        # the released fixes pak's tree (read-only)
SCR = os.path.join(r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9\scratchpad", 'adsheavy')
CLIENT = r"G:\mohaa-adsanim4"
RUNS = "G:/mohaa-adsanim4/runs"
PORT = 12598
OWNER = "adsanim4"
ANIMDIR = os.path.join('models', 'human', 'animation')

# prefix -> sight gun (ironsights sights.json key), weapon tik, physics class, idle row, where the staged aim pose goes
GUNS = {
    'bar':     dict(sight='bar', tik='models/weapons/bar.tik', cls='bar', idle='bar_idle1', vdir='viewmodel/mg'),
    'mp44':    dict(sight='stg44', tik='models/weapons/mp44.tik', cls='stg', idle='mp44_idle1', vdir='viewmodel/mp44'),
    'fg42':    dict(sight=None, tik='models/weapons/FG42.tik', cls='fg42', idle='fg42_idle', vdir='viewmodel/fg42'),
    'vickers': dict(sight='vickers_berthier', tik='models/weapons/Uk_W_Vickers.tik', cls='lmg', idle='vickers_idle', vdir='viewmodel/Vickers'),
    'breda':   dict(sight='breda', tik='models/weapons/It_W_Breda.tik', cls='lmg', idle='breda_idle', vdir='viewmodel/breda'),
    'dp28':    dict(sight='dp_28', tik='models/weapons/dp28.tik', cls='lmg', idle='dp28_idle1', vdir='viewmodel/coop_dp28'),
    'shotgun': dict(sight='shotgun', tik='models/weapons/shotgun.tik', cls='shotgun', idle='shotgun_idle1', vdir='viewmodel/shotgun'),
}


def lib():
    """-> (H hold_bake, R rig lib, V vmcam, CTL) with the bolt tools importable; cwd is kept"""
    for p in (SHARED, BOLT):
        if p not in sys.path:
            sys.path.insert(0, p)
    c = os.getcwd(); os.chdir(BOLT)
    try:
        import hold_bake as H
    finally:
        os.chdir(c)
    CTL = json.load(open(os.path.join(BOLT, '..', 'assets', 'ctl_stand.json')))
    return H, H.R, H.V, CTL


def staged(rel):
    """absolute path of a game-relative file in the staging tree"""
    return os.path.join(ASSETS, rel.replace('/', os.sep))
