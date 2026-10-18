"""python dump_skc.py <file.skc> [frames,...]  - channel values per frame"""
import sys
sys.path.insert(1, r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools')
import skdlib as S
a = S.read_skc(open(sys.argv[1], 'rb').read())
fr = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else [0]
print(a.numFrames, a.frameTime, a.totalDelta)
for f in fr:
    for i, c in enumerate(a.channels):
        print(f, c, [round(x, 4) for x in S.skc_channel(a, f, i)])
