import sys, os
sys.argv=['x','out','none']
import sheet as S
R=S.R
for k,(tik,clips,ls,tn,side) in S.G.items():
    try:
        vm=[R.load(S.resolve(c)) for c in clips]; vml=[c.numFrames*c.frameTime for c in vm]
        tl=[]
        for n in tn:
            a=S.TORSO.get(n.lower()); c=R.load(a['skc']); tl.append(c.numFrames*c.frameTime)
        print('%-22s vm %-22s torso %-40s %s' % (k, '/'.join('%.2f'%x for x in vml), ','.join(tn), '/'.join('%.2f'%x for x in tl)))
    except Exception as e:
        print(k,'ERR',e)
