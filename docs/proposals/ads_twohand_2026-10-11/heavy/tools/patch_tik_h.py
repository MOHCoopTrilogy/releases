"""Stage weapon tiks of the heavy lane with the aimed gun-side rows (apply-on-top of the CURRENT mod tree copy; the
mod tree itself is never written). Idempotent: the staged copy is rebuilt from the mod tree each run.

BAR family on the S93 mesh (path models/weapons/bar_lmg): bar.tik + its finishes
  * animations: `reload_ads_empty` (cgame shows it instead of `reload` when an aimed reload starts on an EMPTY gun):
    the retail reload with the `bolt` bone hauled back and run forward in the left hand's frames, the retail sound
  * `reload_ads_loaded`: the retail gun clip (the bolt does not move), with the reload sound cut before the handle
  * init client: aliascache bar_snd_reload_loaded (the retail BARReload1.wav faded out before the handle, f60)

    python patch_tik_h.py bar          -> assets/models/weapons/<tik> for every tik on that mesh, + the cut sound
"""
import sys, os, re, io, glob, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'
TAG0, TAG1 = '// HZM coop [ads heavy rows]', '// HZM coop [ads heavy rows end]'

SETS = {
    'bar': dict(mesh_path='models/weapons/bar_lmg', empty_clip='coop_reload_ads_empty.skc', loaded_clip='reload_bar.skc',
                snd='bar_snd_reload', snd_loaded='bar_snd_reload_loaded',
                # bug-3623: the other BAR meshes carry the SAME `bolt` bone and the byte-identical retail gun clip
                # (q: skd bone weights - retail models/weapons/BAR: 36 vertices of bar3 on `bolt`, the knob 0.7 u
                # higher than the S93's; coop_pabar = the S93 skeleton): the keyed clip works their handle too
                more_paths=('models/weapons/BAR', 'models/weapons/coop_pabar'),
                wav='sound/weapons/foley/BARReload1.wav', wav_out='sound/weapons/foley/coop_bar_reload_loaded.wav',
                cut=(58, 64),                       # clip frames: fade the retail sound out over these (the handle is f67-73)
                parms='soundparms 0.9 0.2 1.0 0.0 160 1000 auto loaded always maps "dm obj lib m e t"'),
    # DP-28 (the pack's mesh on models/weapons/coop_dp28). Its reload sound is the BAR's file: the same cut serves the
    # rounds-left reload (open bolt held by the sear: no handle work). The handle is bone `rechamb` (heavybake.py dp28)
    'dp28': dict(mesh_path='models/weapons/coop_dp28', empty_clip='coop_reload_ads_empty.skc', loaded_clip='coop_reload_ads_loaded.skc',
                 snd='bar_snd_reload', snd_loaded='bar_snd_reload_loaded',
                 wav='sound/weapons/foley/BARReload1.wav', wav_out='sound/weapons/foley/coop_bar_reload_loaded.wav',
                 cut=(58, 64),
                 parms='soundparms 0.9 0.2 1.0 0.0 160 1000 auto loaded always maps "dm obj lib m e t"'),
    # StG 44 (mesh path models/weapons/mp44: mp44.tik, its finishes, the scoped / skin variants on the same mesh).
    # The RETAIL gun clip cocks the handle in every reload; aimed, an EMPTY gun shows our re-keyed pull (the hand's
    # frames), a gun with rounds left a clip with the handle left alone and the sound cut before the cocking
    'mp44': dict(mesh_path='models/weapons/mp44', empty_clip='coop_reload_ads_empty.skc', loaded_clip='coop_reload_ads_loaded.skc',
                 snd='mp44_snd_reload', snd_loaded='mp44_snd_reload_loaded',
                 more_paths=('models/weapons/coop_mp44strap',),      # StG 44 (Strapped): the same mesh with a sling
                 # HIP too (as the MP40 of the SMG lane): the retail gun clip cocks in EVERY reload. `reload` becomes
                 # the handle-still clip with the cut sound (rounds left: one in the chamber), `reload_empty` (cgame
                 # shows it for a hip reload of an EMPTY gun) the retail clip with the retail sound
                 hip=True,
                 wav='sound/weapons/foley/MP44Reload1.wav', wav_out='sound/weapons/foley/coop_mp44_reload_loaded.wav',
                 cut=(56, 62),
                 parms='soundparms 0.9 0.2 1.0 0.0 160 1000 item loaded always maps "dm obj lib m e t"'),
}


def cut_wav(s):
    H, R, V, CTL = hv.lib()
    raw = R.vfs.read(s['wav'])
    w = wave.open(io.BytesIO(raw))
    sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
    assert sw == 2
    d = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64).reshape(-1, ch)
    a, b = int(s['cut'][0] / 30.0 * sr), int(s['cut'][1] / 30.0 * sr)
    d = d[:b].copy()
    k = np.linspace(1.0, 0.0, b - a)
    d[a:b] *= (k * k * (3 - 2 * k))[:, None]
    dst = hv.staged(s['wav_out'])
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    o = wave.open(dst, 'wb')
    o.setnchannels(ch); o.setsampwidth(2); o.setframerate(sr)
    o.writeframes(d.round().astype(np.int16).tobytes()); o.close()
    print('sound ->', s['wav_out'], '%.2f s of %.2f s' % (b / sr, n / sr))


def patch(name):
    s = SETS[name]
    n = 0
    for p in sorted(glob.glob(os.path.join(MOD, 'models', 'weapons', '*.tik'))):
        t = open(p, 'rb').read().decode('latin-1')
        m = re.search(r'(?mi)^\s*path\s+(\S+)', t)
        mp0 = m.group(1).rstrip('/') if m else ''
        mp = mp0.lower()
        if mp != s['mesh_path'].lower() and mp not in [x.lower() for x in s.get('more_paths', ())]:
            continue
        if mp != s['mesh_path'].lower():
            # a twin mesh on its own path (same handle geometry, byte-identical retail reload clip - checked with
            # gunmove.py): its tik reads the gun clips from ITS path, so they are staged there too
            for k in ('empty_clip', 'loaded_clip'):
                src = hv.staged(s['mesh_path'] + '/' + s[k])
                if os.path.isfile(src):
                    dstc = hv.staged(mp0 + '/' + s[k])
                    os.makedirs(os.path.dirname(dstc), exist_ok=True)
                    open(dstc, 'wb').write(open(src, 'rb').read())
        nl = '\r\n' if '\r\n' in t else '\n'
        assert TAG0 not in t
        r = re.search(r'(?m)^\treload\s+\S+', t)
        assert r, p
        blk = ['\t%s the gun worked under the centre box: an EMPTY gun shows the handle hauled back and run forward' % TAG0,
               '\treload_ads_empty\t%s' % s['empty_clip'], '\t{', '\t\tclient', '\t\t{', '\t\t\tentry sound %s' % s['snd'], '\t\t}', '\t}',
               '\treload_ads_loaded\t%s' % s['loaded_clip'], '\t{', '\t\tclient', '\t\t{', '\t\t\tentry sound %s' % s['snd_loaded'], '\t\t}', '\t}',
               '\t%s' % TAG1, '']
        if s.get('hip'):
            e = t.index(nl + '\t}', r.start()) + len(nl) + 2            # end of the retail `reload` block
            body = t[r.start():e]
            rm = re.match(r'(\treload\s+)(\S+)', body)
            retail = rm.group(2)
            blk[-2:-2] = ['\treload_empty\t%s' % retail, '\t{', '\t\tclient', '\t\t{', '\t\t\tentry sound %s' % s['snd'], '\t\t}', '\t}']
            nb = body.replace(rm.group(0), rm.group(1) + s['loaded_clip'], 1)
            assert re.search(r'entry sound %s\b' % s['snd'], nb), p
            nb = re.sub(r'entry sound %s\b' % s['snd'], 'entry sound %s' % s['snd_loaded'], nb)
            t = t[:r.start()] + nb + t[e:]
        t = t[:r.start()] + nl.join(blk) + t[r.start():]
        c = re.search(r'(?ms)^init\s*\{.*?^\tclient\s*\{\s*?(\r?\n)', t)
        assert c, p
        t = t[:c.end()] + '\t\taliascache %s %s %s%s' % (s['snd_loaded'], s['wav_out'], s['parms'], nl) + t[c.end():]
        assert t.count('{') == t.count('}')
        dst = hv.staged('models/weapons/' + os.path.basename(p))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(t.encode('latin-1'))
        n += 1
        print('tik ->', os.path.basename(p))
    assert n, 'no tik on ' + s['mesh_path']
    cut_wav(s)


if __name__ == '__main__':
    patch(sys.argv[1])
