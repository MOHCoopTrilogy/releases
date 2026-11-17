"""Mute / quiet the private client's pristine cfgs (H:/hzm_work/m1reload/client/pristine) - the test-client rules."""
import re, sys
C = sys.argv[1] if len(sys.argv) > 1 else r"H:/hzm_work/m1reload/client/pristine"
SETS = (('s_volume', '0'), ('s_musicvolume', '0'), ('coop_tinnitusBaseVol', '0'), ('in_gamepad', '0'), ('in_joystick', '0'),
        ('in_mouse', '0'), ('in_nograb', '1'), ('com_maxfps', '60'))
for fn, quote in (('omconfig.cfg', True), ('coop_defaults.cfg', False), ('autoexec.cfg', False)):
    p = C + '/' + fn
    s = open(p, 'rb').read().decode('latin-1')
    for k, v in SETS:
        s = re.sub(r'(?im)^(seta?\s+%s\s+)"?[^"\r\n]*"?' % k, lambda m: m.group(1) + ('"%s"' % v if quote else v), s)
    open(p, 'wb').write(s.encode('latin-1'))
    print(fn, [ln for ln in s.splitlines() if re.match(r'(?i)seta?\s+(s_volume|s_musicvolume|coop_tinnitusBaseVol|com_maxfps)\s', ln)])
