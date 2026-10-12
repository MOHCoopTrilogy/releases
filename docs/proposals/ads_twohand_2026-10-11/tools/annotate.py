"""Mark the slide travel under each cell of a frame strip.
    python annotate.py <strip.jpg> <cols> <cell w> <clip frames comma list> <pull0> <pull1> <fwd0> <fwd1> <travel u>"""
import sys
from PIL import Image, ImageDraw
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import pistolgun
p, cols, cw = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
fr = [float(x) for x in sys.argv[4].split(',')]
pull = (int(sys.argv[5]), int(sys.argv[6])); fwd = (int(sys.argv[7]), int(sys.argv[8])); trav = float(sys.argv[9])
im = Image.open(p).convert('RGB'); d = ImageDraw.Draw(im)
rows = (len(fr) + cols - 1) // cols; ch = im.height // rows
for i, f in enumerate(fr):
    x, y = (i % cols) * cw, (i // cols) * ch
    b = pistolgun.rack_slide(f, pull, fwd) * trav
    t = 'clip f%.0f  slide %.1f u back' % (f, b) if b > 0.01 else 'clip f%.0f  slide forward' % f
    d.rectangle((x, y + ch - 15, x + cw, y + ch), fill=(0, 0, 0)); d.text((x + 4, y + ch - 13), t, fill=(120, 255, 120) if b > 0.01 else (255, 255, 255))
im.save(p, quality=90); print('annotated', p)
