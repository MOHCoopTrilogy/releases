"""Webley: the OPEN and the CLOSE of the reload last 0.8 s each instead of 0.53 s (coordinator 2026-10-12, list item C:
"give them time and weight"; hip and aim - both hang on the one torso clip, whose length IS the state's duration).

Retail: 16-frame torso clips; the gun's barrel tips 90 deg in 4 frames (0.13 s), linear. Now:
  torso / hip-source clips   coop_webley_tp_start24.skc, coop_webley_tp_end24.skc (the retail clips resampled to 24 f)
  gun, hip                   coop_webley_open_hip.skc  (20 f, started at torso frame 4; tips over torso 12..23, eased)
                             coop_webley_close_hip.skc (21 f; shuts over torso 11..20, eased)
  gun, aimed                 coop_webley_open_ads.skc  (20 f; tips over torso 10..22 - a smoothstep's fast middle is a
                                                        third of its span: the first try, 12..20, still read as 0.1 s
                                                        in run tl9)
                             coop_webley_close_ads.skc (21 f; shuts over torso 5..15)
The hands (revbake.py webley(): 24-frame keys) are baked after this. Idempotent.

    python webslow.py <staged tree>
"""
import io, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(sys.argv[1])
A = os.path.join(root, 'models', 'human', 'animation', 'viewmodel', 'webley')
G = os.path.join(root, 'models', 'weapons', 'webley_revolver')
GS = 'models/weapons/webley_revolver/'
# gun-clip frame of each sound: the barrel starts to tip / latches shut
SND = dict(open_hip=8, open_ads=6, close_ads=13, close_hip=18)
CASES = dict(hip=22, ads=20, server=21)          # torso frame the six cases leave (barrel at its stop)


def rt(*a):
    o = subprocess.run([sys.executable, os.path.join(HERE, 'retime.py')] + list(a), capture_output=True, text=True)
    assert o.returncode == 0, o.stderr[-600:]
    print('  ', o.stdout.strip().split('\n')[-1][-110:])


rt('models/human/animation/viewmodel/webley/webley_reload_start.skc', os.path.join(A, 'coop_webley_tp_start24.skc'), '24')
rt('models/human/animation/viewmodel/webley/webley_reload_end.skc', os.path.join(A, 'coop_webley_tp_end24.skc'), '24')
# gun clips: warp new:old (retail open: shaft 0 -> 90 deg over frames 8..12; retail close: over frames 9..13)
rt(GS + 'webley_revolver_reload_start.skc', os.path.join(G, 'coop_webley_open_hip.skc'), 'warp', '0:0,8:8,19:12', '--frames', '20')
rt(GS + 'webley_revolver_reload_end.skc', os.path.join(G, 'coop_webley_close_hip.skc'), 'warp', '0:0,11:9,20:13', '--frames', '21')
rt(GS + 'webley_revolver_reload_start.skc', os.path.join(G, 'coop_webley_open_ads.skc'), 'warp', '0:0,6:8,18:12,19:12', '--frames', '20')
rt(GS + 'webley_revolver_reload_end.skc', os.path.join(G, 'coop_webley_close_ads.skc'), 'warp', '0:0,5:9,15:13,20:13', '--frames', '21')


def edit(path, pairs):
    s = io.open(path, encoding='latin-1', newline='').read()
    nl = '\r\n' if '\r\n' in s else '\n'
    n = 0
    for rx, new in pairs:
        s2, k = re.subn(rx, new.replace('\n', nl), s, count=1, flags=re.S | re.M)
        assert k == 1, (path, rx)
        n += s2 != s
        s = s2
    dp = 0
    for ln in s.replace('\r', '').split('\n'):
        c = ln.split('//')[0]
        dp += c.count('{') - c.count('}')
        assert dp >= 0, path
    assert dp == 0, path
    io.open(path, 'w', encoding='latin-1', newline='').write(s)
    print(os.path.relpath(path, root), 'edits that changed something:', n)


CL = r'(\r?\n\t\{\r?\n\t\tclient\r?\n\t\t\{\r?\n\t\t\t)\d+'
edit(os.path.join(root, 'models', 'weapons', 'webley_revolver.tik'), [
    (r'^(\treload \t)\S+\.skc' + CL + r'( sound webley_snd_reload_start)', r'\g<1>coop_webley_open_hip.skc\g<2>%d\g<3>' % SND['open_hip']),
    (r'^(\treload_ads_loaded\t)\S+\.skc' + CL + r'( sound webley_snd_reload_start)', r'\g<1>coop_webley_open_ads.skc\g<2>%d\g<3>' % SND['open_ads']),
    (r'^(\treload_ads_empty\t)\S+\.skc' + CL + r'( sound webley_snd_reload_start)', r'\g<1>coop_webley_open_ads.skc\g<2>%d\g<3>' % SND['open_ads']),
    (r'^(\treload_end_ads\t)\S+\.skc' + CL + r'( sound webley_snd_reload_end)', r'\g<1>coop_webley_close_ads.skc\g<2>%d\g<3>' % SND['close_ads']),
    (r'^(\treload_end \t)\S+\.skc(\r?\n\t\{\r?\n\t\tserver\r?\n\t\t\{\r?\n\t\t\tfirst surface shellmetal_cull \+nodraw\r?\n\t\t\}\r?\n\t\tclient\r?\n\t\t\{\r?\n\t\t\t)\d+( sound webley_snd_reload_end)',
     r'\g<1>coop_webley_close_hip.skc\g<2>%d\g<3>' % SND['close_hip']),
])
# ---- the torso aliases (server): the state lasts as long as these clips
edit(os.path.join(root, 'models', 'player', 'base', 'anims_shared.txt'), [
    (r'^(\tcoop_reload_webley_start\t)\S+\.skc', r'\g<1>viewmodel/webley/coop_webley_tp_start24.skc'),
    (r'^(\tcoop_reload_webley_start\t[^\n]*\n\t\{\r?\n\t\tserver\r?\n\t\t\{\r?\n\t\t\t)\d+( reloadweapon)', r'\g<1>4\g<2>'),
    (r'^(\tcoop_reload_webley_start\t.*?\n\t\t\t)\d+(\tcoop_ejectcases )', r'\g<1>%d\g<2>' % CASES['server']),
])
edit(os.path.join(root, 'models', 'player', 'base', 'anims_pistol.txt'), [
    (r'^(\twebley_reload_end\t+)\S+\.skc', r'\g<1>viewmodel/webley/coop_webley_tp_end24.skc'),
])
# ---- first person: the six cases of an emptied gun leave as the barrel reaches its stop
p = os.path.join(HERE, 'rows_webley_empty.txt')
s = io.open(p, encoding='latin-1', newline='').read()
s, k1 = re.subn(r'(webley_reload_empty\t[^\n]*\n\t\{\r?\n\t\tclient\r?\n\t\t\{\r?\n\t\t\t)\d+( tagspawn)', r'\g<1>%d\g<2>' % CASES['hip'], s, count=1)
s, k2 = re.subn(r'(webley_reload_empty_ads\t[^\n]*\n\t\{\r?\n\t\tclient\r?\n\t\t\{\r?\n\t\t\t)\d+( tagspawn)', r'\g<1>%d\g<2>' % CASES['ads'], s, count=1)
assert k1 == 1 and k2 == 1
io.open(p, 'w', encoding='latin-1', newline='').write(s)
print('rows_webley_empty.txt: case frames %d (hip) / %d (aimed)' % (CASES['hip'], CASES['ads']))
