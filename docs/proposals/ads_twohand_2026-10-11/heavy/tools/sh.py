"""Run one of the pistol lane's shared tools against THIS lane's runs folder.

Several shared tools (centrebox, dgif, sheet, animmarks, democheck, loopreact, evgun) carry the literal
'G:/mohaa-adsanim/runs'. They are not ours to edit, so the source is read, the runs folder swapped for the lane's
(G:/mohaa-adsanim4/runs) and the result executed as the script - no copy to drift.

    python sh.py <tool> [args ...]        e.g. python sh.py centrebox hb1 --dump
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv

tool = sys.argv[1]
path = os.path.join(hv.SHARED, tool + ('' if tool.endswith('.py') else '.py'))
src = open(path, encoding='utf-8').read()
n = src.count('G:/mohaa-adsanim/runs')
assert n >= 1, 'no runs literal in ' + path
src = src.replace('G:/mohaa-adsanim/runs', hv.RUNS)
sys.argv = [path] + sys.argv[2:]
sys.path.insert(0, hv.SHARED)
g = {'__name__': '__main__', '__file__': path}
exec(compile(src, path, 'exec'), g)
