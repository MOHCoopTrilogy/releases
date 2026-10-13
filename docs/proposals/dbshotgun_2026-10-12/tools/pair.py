"""labelled side-by-side / stacked stills:  python tools/pair.py out.jpg [--crop x0,y0,x1,y1] [--w cellwidth] label=file label=file ...
    --cols n   cells per row (default: all in one row)"""
import sys
from PIL import Image, ImageDraw, ImageFont


def main():
    a = sys.argv[1:]
    out = a.pop(0)
    crop = None; cw = 800; cols = None
    while a and a[0].startswith('--'):
        k = a.pop(0); v = a.pop(0)
        if k == '--crop':
            crop = tuple(int(x) for x in v.split(','))
        elif k == '--w':
            cw = int(v)
        elif k == '--cols':
            cols = int(v)
    try:
        font = ImageFont.truetype('arial.ttf', 18)
    except Exception:
        font = ImageFont.load_default()
    ims = []
    for it in a:
        lab, f = it.split('=', 1)
        im = Image.open(f).convert('RGB')
        if crop:
            im = im.crop(crop)
        im = im.resize((cw, round(im.height * cw / im.width)), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        w = d.textlength(lab, font=font)
        d.rectangle([0, 0, w + 12, 26], fill=(0, 0, 0))
        d.text((6, 3), lab, fill=(255, 235, 120), font=font)
        ims.append(im)
    cols = cols or len(ims)
    rows = (len(ims) + cols - 1) // cols
    ch = max(i.height for i in ims)
    sh = Image.new('RGB', (cols * cw + (cols - 1) * 4, rows * ch + (rows - 1) * 4), (16, 16, 16))
    for n, im in enumerate(ims):
        sh.paste(im, ((n % cols) * (cw + 4), (n // cols) * (ch + 4)))
    sh.save(out, quality=90)
    print('wrote', out, sh.size)


if __name__ == '__main__':
    main()
