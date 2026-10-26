import sys,glob,os
from PIL import Image, ImageDraw
d=sys.argv[1]; out=sys.argv[2]; names=sys.argv[3:]
cols=3; w=560
ims=[]
for n in names:
    im=Image.open(os.path.join(d,n+'.jpg')).convert('RGB'); h=int(im.height*w/im.width); im=im.resize((w,h))
    ImageDraw.Draw(im).text((6,6),n,fill=(255,255,0)); ims.append(im)
rows=(len(ims)+cols-1)//cols; H=ims[0].height
S=Image.new('RGB',(cols*w,rows*H))
for i,im in enumerate(ims): S.paste(im,((i%cols)*w,(i//cols)*H))
S.save(out,quality=80)
