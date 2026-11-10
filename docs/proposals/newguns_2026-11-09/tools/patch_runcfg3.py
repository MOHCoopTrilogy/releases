P = r'C:\hzm-newguns\root\docs\proposals\newguns_2026-11-09\tools\run_cfg.py'
s = open(P, encoding='utf-8').read()
old = """        s.cmd('+button13', 1500); s.cmd('reload', 300)
        for i in range(6):
            s.cmd('screenshotJPEG %s_06_adsreload_%d' % (k, i), 400)"""
assert s.count(old) == 1
new = """        # [QA 2] aim, a burst so the magazine is not full, the aim picture AFTER the first shots, then reload while aiming
        s.cmd('+button13', 1500); s.cmd('+attack', 900); s.cmd('-attack', 1200)
        s.cmd('screenshotJPEG %s_03_ads_aftershot' % k, 300)
        s.cmd('reload', 300)
        for i in range(6):
            s.cmd('screenshotJPEG %s_06_adsreload_%d' % (k, i), 400)"""
s = s.replace(old, new)
open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
