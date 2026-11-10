import os
from PIL import Image
RUNS = r'H:\hzm_work\newguns\runs'
OUT = r'C:\hzm-newguns\root\docs\proposals\newguns_2026-11-09\media\final'
PICK = {'ng18': ['g0_01_hip', 'g0_03_ads_b', 'g0_07_third_aim', 'g1_01_hip', 'g1_03_ads_b', 'g1_05_reload_04', 'g1_07_third_aim',
                 'g2_01_hip', 'g2_03_ads', 'g2_07_third', 'g2_08_after'],
        'ng19': ['g0_05_reload_00', 'g0_05_reload_01', 'g0_05_reload_05', 'g0_05_reload_07']}
for run, names in PICK.items():
    for n in names:
        Image.open(os.path.join(RUNS, run, n + '.jpg')).resize((1720, 720)).save(os.path.join(OUT, '%s_%s.jpg' % (run, n)), quality=82)
print(len(os.listdir(OUT)))
