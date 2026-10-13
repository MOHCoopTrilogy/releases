"""engine frames -> a GIF (for the user) :  python tools/mkgif.py out.gif width ms_per_frame frame1.jpg frame2.jpg ..."""
import sys
from PIL import Image

out, w, ms = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
ims = []
for f in sys.argv[4:]:
    im = Image.open(f).convert('RGB')
    ims.append(im.resize((w, round(im.height * w / im.width)), Image.LANCZOS).quantize(colors=128, method=Image.MEDIANCUT, dither=Image.NONE))
ims[0].save(out, save_all=True, append_images=ims[1:], duration=ms, loop=0, optimize=False)
print('wrote', out, len(ims), 'frames')
