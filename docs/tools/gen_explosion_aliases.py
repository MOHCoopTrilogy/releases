"""Regenerate ubersound/coop_explosions.scr from the wavs already on disk. ASCII only."""
import io
import os
import glob

SND = 'C:/mohaa-coop-dev/hzm-mohaa-coop-mod/sound/coop_explosions/'
OUT = 'C:/mohaa-coop-dev/hzm-mohaa-coop-mod/ubersound/coop_explosions.scr'
MAPS = 'always maps "m e t dm obj lib train"'

PARMS = {
    'distant': '0.85 0.12 1.0 0.06 1200 8000 auto loaded',
    'sub':     '0.90 0.10 1.0 0.05  600 6000 auto loaded',
    'debris':  '0.70 0.15 1.0 0.10  300 2600 auto loaded',
}
DEFAULT = '0.95 0.12 1.0 0.08  500 4200 auto loaded'

L = []
w = L.append

w('// HZM coop - EXPLOSION POOL.')
w('//')
w('// The trilogy routes 366 explosion alias lines through about 34 distinct wavs. Explo_MetalMed1')
w('// alone is the tank, truck, plane, jeep, glider, AA gun, bunker, door, K-5 railgun and radio.')
w('// That single fact is why every explosion sounds like every other one, and no amount of alias')
w('// juggling fixes it - the pool itself has to grow.')
w('//')
w('// Categories: close (dry, no tail) / grenade / large (with tail) / distant (off-map, the')
w('// vocabulary MOHAA lacks entirely) / debris / sub (concussion bed) / bomb (heavy ordnance).')
w('//')
w('// Derivatives: downsampled to 22050 mono and re-normalised, not library files. The source')
w('// library is licensed and deliberately unnamed here and everywhere else in the repo.')
w('//')
w('// Every line carries BOTH always and a maps list. always alone makes an alias RESOLVE on any')
w('// map but does NOT precache - CacheResource is still gated by bLoadForMap - and a sound that')
w('// registers lazily at first play arrives as a post-gamestate reliable command, which is the')
w('// bug-1183 "server disconnected on spawn" failure. The token list is a PREFIX match, so')
w('// "m e t dm obj lib train" covers the whole trilogy.')
w('')

prev = None
for f in sorted(os.path.basename(x) for x in glob.glob(SND + '*.wav')):
    stem = f.replace('coop_ex_', '').rsplit('_', 1)[0]
    if stem != prev:
        w('')
        prev = stem
    parms = PARMS.get(stem, DEFAULT)
    w('aliascache %-24s sound/coop_explosions/%-28s soundparms %s %s'
      % (f[:-4], f, parms, MAPS))

w('')
w('// ---------------------------------------------------------------------------------------------')
w('// REPOINTING THE COOP-OWNED EXPLOSION ALIASES ONTO THE NEW POOL.')
w('//')
w('// These names are defined in ubersound.scr and are OURS - no retail script calls them - so')
w('// repointing them changes only coop content. The override works on load order: G_RegisterSounds')
w('// parses ubersound/*.scr alphabetically and Alias_ListAdd is FIRST-DEFINITION-WINS, and')
w('// "coop_explosions.scr" sorts before "ubersound.scr". Same mechanism coop_pain.scr already uses')
w('// to beat uberdialog.scr.')
w('//')
w('// Sound() resolves by PREFIX, so NN-numbered variants turn a single cue into a random pool with')
w('// no call-site change. Two digits always - a one-digit "hit1" would also prefix-match "hit10".')
w('//')
w('// soundparms are copied from the originals (tuned against the maps) - only the file moves.')
w('//')
w('// DELIBERATELY NOT REPOINTED: coop_arty_incoming and coop_stuka_bomb are the incoming WHISTLE')
w('// cues. None of the source libraries contains a shell whistle or a dive siren, so repointing')
w('// them at a blast would lose the warning that makes them useful - they stay on retail audio')
w('// until a real source exists. coop_snd_explosion is left alone too: it lives in')
w('// coop_buildsounds.scr, which sorts BEFORE this file, so an override here could never win.')
w('// ---------------------------------------------------------------------------------------------')
w('')

OVER = [
    # [user 2026-08-21] "any idea why I am randomly getting damaged" -> the m3l3 church mortar
    # barrage, landing SILENTLY. Retail scopes every mortarNN alias to maps "t dm lib obj" - no "m" -
    # so on the whole m-series campaign they never register and Sound("mortar") resolves to nothing
    # ("ERROR PlaySound: mortar needs an alias"). Being shelled with no audio cue is exactly why the
    # damage felt random. Fourth instance of this maps-gate trap today, after the Spearhead pain
    # outage, the ricochet alias and all 1389 AI chatter lines.
    #
    # Redefining mortarNN here wins on load order (coop_explosions.scr sorts before ubersound.scr and
    # Alias_ListAdd is first-definition-wins) and carries `always`, so it resolves on every map.
    ('mortar', ['coop_ex_large_03.wav', 'coop_ex_large_06.wav', 'coop_ex_large_08.wav',
                'coop_ex_close_02.wav', 'coop_ex_sub_02.wav', 'coop_ex_debris_04.wav'],
     '1.0 0.25 0.95 0.25 1200 9000 auto loaded'),
    ('coop_arty_hit', ['coop_ex_large_01.wav', 'coop_ex_large_04.wav',
                       'coop_ex_large_07.wav', 'coop_ex_sub_01.wav'],
     '1.0 0.3 0.8 0.4 1000  8000 weapon loaded'),
    ('coop_stuka_hit', ['coop_ex_bomb_01.wav', 'coop_ex_bomb_03.wav', 'coop_ex_bomb_05.wav'],
     '1.0 0.3 0.8 0.4  800  8000 weapon loaded'),
    ('coop_demo_explosion', ['coop_ex_bomb_02.wav', 'coop_ex_large_02.wav', 'coop_ex_large_09.wav'],
     '1.4 0.2 0.9 0.1 1500  8000 weapon loaded'),
    ('coop_radio_blast', ['coop_ex_close_05.wav', 'coop_ex_close_09.wav', 'coop_ex_large_05.wav'],
     '3.0 0.2 0.7 0.15 1500 14000 weapon loaded'),
]
missing = []
for name, files, parms in OVER:
    for i, f in enumerate(files, 1):
        if not os.path.isfile(SND + f):
            missing.append(f)
        w('aliascache %-24s sound/coop_explosions/%-28s soundparms %s %s'
          % ('%s%02d' % (name, i), f, parms, MAPS))
    w('')

if missing:
    raise SystemExit('referenced files missing: %s' % missing)

io.open(OUT, 'w', encoding='ascii', newline='\r\n').write('\n'.join(L) + '\n')
n = sum(1 for x in L if x.startswith('aliascache'))
print('coop_explosions.scr regenerated: %d aliascache lines' % n)
