import sys, glob, os
from PIL import Image
run, out = sys.argv[1], sys.argv[2]
os.chdir(run)
def crop(f):
    im=Image.open(f); w,h=im.size
    # the bench's preview box: 640x480 virtual, stretched to the window
    return im.crop((int(20/640*w),int(38/480*h),int(620/640*w),int(269/480*h))).resize((600,231))
for name in ('open','zoom','turn'):
    fl=sorted(glob.glob('*_%s.jpg'%name)); s=Image.new('RGB',(1200,231*5),(0,0,0))
    for i,f in enumerate(fl): s.paste(crop(f),((i%2)*600,(i//2)*231))
    s.save(os.path.join(out,'%s_%s.jpg'%(os.path.basename(run),name)),quality=85)
