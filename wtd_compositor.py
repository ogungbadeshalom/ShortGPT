#!/usr/bin/env python3
"""
wtd_compositor.py (v5) — reference-style "What's the difference?" frames.
v5 changes:
  - NEW BEAT FLOW: (1) first image ALONE, (2) both images, (3) shrug +
    "What's the difference?" with both images
  - stickman assets border-free + transparent (comic panel borders stripped)
Layout (1080x1920):
  y 110:      labels
  y 230-680:  photo(s) — left pane, right pane, or single centered
  y 800-950:  question text (clear band)
  y 1000+:    stickman (transparent, fixed central position)
"""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920

STICK = {
    "left":  "/root/wtd_assets/stickmen_t/stick_1.png",
    "right": "/root/wtd_assets/stickmen_t/stick_2.png",
    "ask":   "/root/wtd_assets/stickmen_t/stick_3.png",
}

CONCEPT_IMGS = {
    "ssd": "/root/wtd_assets/ssd_th.png",
    "hdd": "/root/wtd_assets/hdd_th.png",
    "debit": "/root/wtd_assets/debit_th.png",
    "credit": "/root/wtd_assets/credit_th.png",
}

def font(sz):
    for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if os.path.exists(path):
            return ImageFont.truetype(path, sz)
    return ImageFont.load_default()

def _paste_photo(base, img_key, cx, top_y, pane_w=430, max_h=450):
    im = Image.open(CONCEPT_IMGS[img_key]).convert("RGB")
    im.thumbnail((pane_w, max_h))
    base.paste(im, (int(cx - im.width/2), top_y))

def render_beat(out_path, left_label, left_img, right_label, right_img,
                question, stick_key="ask", show="both", caption=None):
    """show: 'left' = ONLY the first image (centered), 'both' = the pair."""
    base = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(base)
    top_y = 230

    if show == "left":
        # FIRST IMAGE ALONE, centered, bigger
        fl = font(100)
        bb = d.textbbox((0, 0), left_label, font=fl)
        d.text((int((W-(bb[2]-bb[0]))/2) - bb[0], 110 - bb[1]), left_label,
               font=fl, fill=(0, 0, 0))
        _paste_photo(base, left_img, W//2, top_y, pane_w=520, max_h=520)
    else:
        pane_w, gap = 430, 40
        left_x = int((W - 2*pane_w - gap) / 2)
        right_x = left_x + pane_w + gap
        fl = font(92)
        for cx, label in [(left_x + pane_w//2, left_label),
                          (right_x + pane_w//2, right_label)]:
            bb = d.textbbox((0, 0), label, font=fl)
            d.text((cx - (bb[2]-bb[0])/2 - bb[0], 110 - bb[1]), label,
                   font=fl, fill=(0, 0, 0))
        _paste_photo(base, left_img, left_x + pane_w//2, top_y)
        _paste_photo(base, right_img, right_x + pane_w//2, top_y)

    # (question text removed — captions occupy the mid-frame spot now)

    # synced narration caption in the MID-FRAME spot (replaces question text)
    if caption:
        fc = font(96 if len(caption) <= 14 else 76)
        bc = d.textbbox((0, 0), caption, font=fc)
        d.text((int((W-(bc[2]-bc[0]))/2) - bc[0], 880 - bc[1]),
               caption, font=fc, fill=(15, 15, 15))

    # stickman: transparent, border-free, fixed central position
    st = Image.open(STICK[stick_key]).convert("RGBA")
    x = int((W - st.width) / 2)
    y = H - 60 - st.height
    base.paste(st, (x, y), st)

    base.save(out_path)
    return out_path

if __name__ == "__main__":
    os.makedirs("/root/wtd_frames5", exist_ok=True)
    render_beat("/root/wtd_frames5/t1_first.png", "SSD","ssd","HDD","hdd", "", "left", show="left")
    render_beat("/root/wtd_frames5/t2_both.png",  "SSD","ssd","HDD","hdd", "", "left", show="both")
    render_beat("/root/wtd_frames5/t3_ask.png",   "SSD","ssd","HDD","hdd", "What's the difference?", "ask", show="both")
    print("v5 test frames written")