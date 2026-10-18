"""make_sheet.py - builds contact_sheet.jpg from the harness shots.
    python -I make_sheet.py <outjpg> <label>=<jpg> [<label>=<jpg> ...]   (cells flow 2 per row, 760 px wide each)
"""
import sys
from PIL import Image, ImageDraw, ImageFont

CELL_W = 760
PAD = 8
CAP = 34


def main():
    out = sys.argv[1]
    items = []
    for a in sys.argv[2:]:
        lab, path = a.split("=", 1)
        items.append((lab, path))
    try:
        font = ImageFont.truetype("arial.ttf", 17)
    except Exception:
        font = ImageFont.load_default()
    cells = []
    for lab, path in items:
        im = Image.open(path).convert("RGB")
        h = int(im.height * CELL_W / im.width)
        cells.append((lab, im.resize((CELL_W, h), Image.LANCZOS)))
    cols = 2
    rows = [cells[i:i + cols] for i in range(0, len(cells), cols)]
    heights = [max(c[1].height for c in r) + CAP for r in rows]
    W = cols * CELL_W + (cols + 1) * PAD
    H = sum(heights) + (len(rows) + 1) * PAD
    sheet = Image.new("RGB", (W, H), (24, 24, 28))
    d = ImageDraw.Draw(sheet)
    y = PAD
    for r, rh in zip(rows, heights):
        x = PAD
        for lab, im in r:
            d.text((x + 4, y + 7), lab, fill=(235, 220, 160), font=font)
            sheet.paste(im, (x, y + CAP))
            x += CELL_W + PAD
        y += rh + PAD
    sheet.save(out, quality=88)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
