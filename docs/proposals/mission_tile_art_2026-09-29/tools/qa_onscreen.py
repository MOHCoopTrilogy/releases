"""qa_onscreen.py - every sample as the ENGINE will show it, per layout, at 1080p widget size.

    python tools/qa_onscreen.py    # ../samples/qa/onscreen_1080p.jpg

card_c -> 225x225 (ui_menuCenter 1: 100x100 units x 2.25), card_s -> 300x225 (default stretch at 16:9: x3, y2.25),
print_c -> 369x277 (164x123 units x 2.25), print_s -> 492x277 (x3, y2.25). The squeezed _s textures must come back to
their authored shape here; a stretched-looking person or tank is a defect.
"""
import glob
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)


def main():
    full = os.path.join(PROP, "samples", "full")
    ids = sorted({os.path.basename(f).split("_card_")[0] for f in glob.glob(os.path.join(full, "*_card_c_1024.jpg"))})
    sizes = [("card_c", "%s_card_c_1024.jpg", (225, 225)), ("card_s", "%s_card_s_1024.jpg", (300, 225)),
             ("print_c", "%s_print_c_1024x768.jpg", (369, 277)), ("print_s", "%s_print_s_1024x768.jpg", (492, 277))]
    W = sum(s[2][0] for s in sizes) + 12 * 5
    rowh = 277 + 30
    S = Image.new("RGB", (W, rowh * len(ids) + 10), (18, 34, 18))
    d = ImageDraw.Draw(S)
    for r, i in enumerate(ids):
        x = 12
        for name, pat, (w, h) in sizes:
            im = Image.open(os.path.join(full, pat % i)).convert("RGB").resize((w, h), Image.LANCZOS)
            S.paste(im, (x, r * rowh + 26))
            d.text((x, r * rowh + 8), "%s  %s  %dx%d" % (i, name, w, h), fill=(250, 199, 71))
            x += w + 12
    S.save(os.path.join(PROP, "samples", "qa", "onscreen_1080p.jpg"), quality=90)
    print("onscreen sheet", len(ids))


if __name__ == "__main__":
    main()
