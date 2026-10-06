import sys; sys.argv=['x']
import skd_collapse as k
from collections import Counter, defaultdict
CUTS={
 'L_upperarm':['Bip01 L UpperArm','Bip01 L Forearm','Bip01 L Hand','helper Lelbow'],
 'L_forearm':['Bip01 L Forearm','Bip01 L Hand'],
 'R_upperarm':['Bip01 R UpperArm','Bip01 R Forearm','Bip01 R Hand','helper Relbow'],
 'R_forearm':['Bip01 R Forearm','Bip01 R Hand'],
 'L_thigh':['Bip01 L Thigh','Bip01 L Calf','Bip01 L Foot','Bip01 L Toe0','helper Lknee','helper Lankle'],
 'L_calf':['Bip01 L Calf','Bip01 L Foot','Bip01 L Toe0','helper Lankle'],
 'R_thigh':['Bip01 R Thigh','Bip01 R Calf','Bip01 R Foot','Bip01 R Toe0','helper Rknee','helper Rankle'],
 'R_calf':['Bip01 R Calf','Bip01 R Foot','Bip01 R Toe0','helper Rankle'],
}
def run(members):
  for member in members:
      ver,bones,surfs=k.parse_skd(k.load(member))
      names=[b['name'] for b in bones]
      print('\n##',member,'v%d'%ver,'surfaces',[s['name'] for s in surfs])
      tot=sum(len(s['verts']) for s in surfs)
      for cut,chain in CUTS.items():
          cs={i for i,n in enumerate(names) if n in chain}
          full=part=0; partners=Counter()
          for s in surfs:
              for ws in s['verts']:
                  w=sum(bw for bi,bw,_ in ws if bi in cs)
                  if w>0.999: full+=1
                  elif w>0.001:
                      part+=1
                      for bi,bw,_ in ws:
                          if bi not in cs: partners[names[bi]]+=1
          print(f'  {cut:11s} full={full:4d} seam={part:3d} /{tot}  seam-partners={dict(partners.most_common(4))}')

if __name__=='__main__':
    run(sys.stdin.read().split())
