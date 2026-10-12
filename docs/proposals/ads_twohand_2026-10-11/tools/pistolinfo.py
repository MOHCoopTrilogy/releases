"""Facts for an aimed reload of one weapon tik: the gun's reload clip (which bones move, when), its reload sound's
clicks per clip frame, the tik's server commands on the reload, fire delay, and the torso alias' prop frames.

    python pistolinfo.py <tik stem> [torso alias]
"""
import sys, os, re, io, wave
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunskc
R = gunskc.R
vfs = R.vfs
MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'


def rd(p):
    f = os.path.join(MOD, p.replace('/', os.sep))
    if os.path.isfile(f):
        return open(f, 'rb').read()
    return vfs.read(p)


stem = sys.argv[1]
t = rd('models/weapons/%s.tik' % stem).decode('latin-1').replace('\r\n', '\n')
path = re.search(r'(?m)^\s*path\s+(\S+)', t).group(1)
print('tik', stem, '| path', path, '| name', re.search(r'(?m)^\s*name\s+"([^"]+)"', t).group(1),
      '| firedelay', re.findall(r'(?m)^\s*((?:sp |dm |realism )?firedelay\s+[\d.]+)', t), '| semiauto', bool(re.search(r'(?m)^\s*semiauto\b', t)),
      '| clipsize', re.findall(r'(?m)^\s*(?:sp |dm )?clipsize\s+(\d+)', t)[:1])
an = t[t.find('\nanimations'):]
for m in re.finditer(r'(?m)^\s*(reload\w*|idle\w*|fire\w*)\s+(\S+\.skc)[^\n]*\n(\s*\{(?:[^{}]|\{[^{}]*\})*\})?', an):
    blk = m.group(3) or ''
    cmds = [l.strip() for l in blk.split('\n') if re.match(r'\s*(\d+|first|last|entry|exit)\s', l) and 'tagspawn' not in l and 'viewkick' not in l][:8]
    print(' anim', m.group(1), m.group(2), '|', ' ; '.join(c[:70] for c in cmds))
    if m.group(1).startswith('reload'):
        try:
            a = R.load(path + '/' + m.group(2))
        except Exception as e:
            print('   load failed', e); continue
        print('   %d frames x %.4f' % (a.numFrames, a.frameTime))
        for c, nm in enumerate(a.names):
            v = a.V[:, c, :3] if nm.endswith(' pos') else a.V[:, c, :]
            dv = np.abs(np.diff(v, axis=0)).max(axis=1)
            mv = np.where(dv > 1e-3)[0]
            if len(mv) and not nm.startswith(('tag_', 'origin')):
                rng = float(np.abs(v - v[0]).max())
                runs = []
                st_ = mv[0]; pr = mv[0]
                for k in mv[1:]:
                    if k != pr + 1:
                        runs.append((st_, pr + 1)); st_ = k
                    pr = k
                runs.append((st_, pr + 1))
                print('   %-22s range %.2f  moves %s' % (nm, rng, ' '.join('f%d-%d' % r for r in runs[:8])))
        snd = re.search(r'entry\s+sound\s+(\S+)', blk)
        if snd:
            us = rd('ubersound/ubersound.scr').decode('latin-1')
            w = re.search(r'(?im)^\s*aliascache\s+%s\s+(\S+)([^\n]*)' % re.escape(snd.group(1)), us)
            if w:
                raw = vfs.read(w.group(1)) or rd(w.group(1))
                wv = wave.open(io.BytesIO(raw))
                sr, n, ch, sw = wv.getframerate(), wv.getnframes(), wv.getnchannels(), wv.getsampwidth()
                d = np.frombuffer(wv.readframes(n), dtype=np.int16 if sw == 2 else np.uint8).astype(float)
                if sw == 1:
                    d = (d - 128) * 256
                if ch > 1:
                    d = d.reshape(-1, ch).mean(1)
                hop = int(sr / 30)
                env = np.array([np.abs(d[i:i + hop]).max() for i in range(0, len(d), hop)])
                print('   sound', snd.group(1), w.group(1), '%.2f s' % (n / sr), '| parms', w.group(2).strip()[:60])
                print('   level/frame:', ''.join(str(int(round(9 * e / env.max()))) for e in env))
                print('   onsets:', [i for i in range(1, len(env)) if env[i] > 0.35 * env.max() and env[i] > 2.0 * env[i - 1]])
if len(sys.argv) > 2:
    al = sys.argv[2]
    for p in ('models/player/base/anims_pistol.txt', 'models/player/base/anims_shared.txt', 'models/player/base/anims_tt.txt',
              'models/player/base/anims_ta.txt', 'models/player/base/include_weapons.txt'):
        try:
            s = rd(p).decode('latin-1').replace('\r\n', '\n')
        except Exception:
            continue
        for m in re.finditer(r'(?m)^\s*%s\s+(\S+)[^\n]*\n(\s*\{(?:[^{}]|\{[^{}]*\})*\})?' % re.escape(al), s):
            print(' torso', p, al, m.group(1), '|', ' ; '.join(l.strip().split('//')[0].strip()[:80] for l in (m.group(2) or '').split('\n') if re.match(r'\s*(\d+|first|last)\s', l)))
rows = rd('models/player/base/fps_anims_pistol.txt').decode('latin-1')
