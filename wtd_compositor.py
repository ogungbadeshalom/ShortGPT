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
ACCENT = (15, 118, 110)   # teal, brand accent

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
    "indexfund": "/root/wtd_assets/finance/indexfund_th.png",
    "etf": "/root/wtd_assets/finance/etf_th.png",
    "compound": "/root/wtd_assets/finance/compound_th.png",
    "simple": "/root/wtd_assets/finance/simple_th.png",
}

def register_concept(key, path):
    """Register a concept image at runtime (maps any string key to a local file)."""
    key = str(key)
    CONCEPT_IMGS[key] = path
    return key

def font(sz):
    for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if os.path.exists(path):
            return ImageFont.truetype(path, sz)
    return ImageFont.load_default()

def _paste_photo(base, img_key, cx, top_y, pane_w=430, max_h=450):
    if not img_key:
        return
    im = Image.open(CONCEPT_IMGS[img_key]).convert("RGB")
    im.thumbnail((pane_w, max_h))
    base.paste(im, (int(cx - im.width/2), top_y))

def _fit_font(d, text, max_w, start_sz, min_sz=36):
    """Auto-shrink a font so the text fits within max_w."""
    sz = start_sz
    while sz > min_sz:
        f = font(sz)
        bb = d.textbbox((0, 0), text, font=f)
        if (bb[2]-bb[0]) <= max_w:
            return f, bb
        sz -= 4
    f = font(min_sz)
    return f, d.textbbox((0, 0), text, font=f)

def _wrap(d, text, f, max_w, max_lines=2):
    """Word-wrap text so each line fits max_w, capped at max_lines."""
    words = text.split()
    if not words:
        return [text]
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textbbox((0, 0), trial, font=f)[2] <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:max_lines]

def _center_text(d, text, cx, y, f, fill):
    bb = d.textbbox((0, 0), text, font=f)
    d.text((int(cx - (bb[2]-bb[0])/2) - bb[0], y - bb[1]), text, font=f, fill=fill)
    return bb[3]-bb[1]

def render_beat(out_path, left_label, left_img, right_label, right_img,
                question, stick_key="ask", show="both", caption=None):
    """show: 'left' = ONLY the first image (centered), 'both' = the pair."""
    base = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(base)
    top_y = 230

    if show == "left":
        # FIRST IMAGE ALONE, centered, bigger
        f, _ = _fit_font(d, left_label, 900, 100)
        _center_text(d, left_label, W//2, 110, f, (0, 0, 0))
        _paste_photo(base, left_img, W//2, top_y, pane_w=520, max_h=520)
    else:
        pane_w, gap = 430, 40
        left_x = int((W - 2*pane_w - gap) / 2)
        right_x = left_x + pane_w + gap
        for cx, label in [(left_x + pane_w//2, left_label),
                          (right_x + pane_w//2, right_label)]:
            f, _ = _fit_font(d, label, pane_w - 20, 92)
            _center_text(d, label, cx, 110, f, (0, 0, 0))
        _paste_photo(base, left_img, left_x + pane_w//2, top_y)
        _paste_photo(base, right_img, right_x + pane_w//2, top_y)

    # synced narration caption in the MID-FRAME spot — auto-fit + wrap so it
    # never collides with the photos above or the stickman below (band 780-990)
    if caption:
        fc, _ = _fit_font(d, caption, 960, 96 if len(caption) <= 14 else 76)
        lines = _wrap(d, caption, fc, 960, max_lines=2)
        # center the line-block at y=880
        fb = fc.getbbox(caption) or fc.getbbox("Ag")
        line_h = (fb[3]-fb[1]) * 1.4 if fb else 90
        block_h = line_h * len(lines)
        y = 880 - int(block_h / 2) + int(line_h / 2)
        for ln in lines:
            _center_text(d, ln, W//2, int(y), fc, (15, 15, 15))
            y += line_h

    # stickman: transparent, border-free, fixed central position
    st = Image.open(STICK[stick_key]).convert("RGBA")
    x = int((W - st.width) / 2)
    y = H - 60 - st.height
    base.paste(st, (x, y), st)

    # persistent watermark handle "@justthediff" — bottom-LEFT, beside stickman,
    # below the photo zone so it never overlays/drops on the images (photos live y~230-680)
    wm_text = "@justthediff"
    fw = font(46)
    wbb = d.textbbox((0, 0), wm_text, font=fw)
    wtw, wth = wbb[2]-wbb[0], wbb[3]-wbb[1]
    pad_x, pad_y = 30, 16
    bx = 60                                       # left margin
    by = H - 44 - int(wth + pad_y*2)              # near bottom-left, below photos
    # faint translucent white pill so it reads, subtle
    pw, ph = int(wtw + pad_x*2), int(wth + pad_y*2)
    pill = Image.new("RGBA", (pw, ph), (255, 255, 255, 130))
    base.paste(pill, (bx, by), pill)
    d.text((bx + pad_x, by + pad_y), wm_text, font=fw, fill=(50, 50, 50))

    base.save(out_path)
    return out_path

def render_cta(out_path, main="Follow for more money clarity.", sub="@justthediff", caption=None):
    """End-of-video CTA card: the SUBSCRIBE stickman (green beanie + red scarf,
    holding a red SUBSCRIBE! sign) at bottom-center + follow line above, no photos.
    Rendered as the last beat so the CTA lands after the payoff.
    caption: optional synced word-chunk shown big mid-frame (replaces static main)."""
    base = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(base)

    # subscribe stickman: wider (sign = hero), bottom-anchored & centered,
    # scaled to fit height so the sign + character are fully on screen
    SUB = "/root/wtd_assets/stickmen_t/stick_subscribe.png"
    st = Image.open(SUB).convert("RGBA")
    target_h = 880
    scale = target_h / st.height
    sw, sh = int(st.width * scale), int(st.height * scale)
    st = st.resize((sw, sh), Image.LANCZOS)
    sx = int((W - sw) / 2)
    sy = H - 40 - sh                  # bottom-anchored, clear of watermark below-left
    base.paste(st, (sx, sy), st)

    # the caption shown now is the synced CTA word-chunk (same as content beats);
    # main block sits ABOVE the subscribe sign (sign runs ~y880-1800 on the char)
    text = caption if caption else main
    fc, _ = _fit_font(d, text, 940, 96, min_sz=48)
    lines = _wrap(d, text, fc, 940, max_lines=2)
    fb = fc.getbbox(text) or fc.getbbox("Ag")
    line_h = (fb[3]-fb[1]) * 1.4 if fb else 90
    block_h = line_h * len(lines)
    y0 = 640 - int(block_h/2) + int(line_h/2)
    for ln in lines:
        _center_text(d, ln, W//2, int(y0), fc, (15, 15, 15))
        y0 += line_h

    # sub-line (handle) — below the text block, still above the sign
    if not caption:
        fs, _ = _fit_font(d, sub, 940, 56, min_sz=40)
        ysub = 640 + int(line_h * len(lines)) + int(line_h*0.6)
        _center_text(d, sub, W//2, int(ysub), fs, ACCENT)

    # persistent watermark (bottom-left)
    wm_text = "@justthediff"
    fw = font(46)
    wbb = d.textbbox((0, 0), wm_text, font=fw)
    wtw, wth = wbb[2]-wbb[0], wbb[3]-wbb[1]
    pad_x, pad_y = 30, 16
    bx = 60
    by = H - 44 - int(wth + pad_y*2)
    pw, ph = int(wtw + pad_x*2), int(wth + pad_y*2)
    pill = Image.new("RGBA", (pw, ph), (255, 255, 255, 130))
    base.paste(pill, (bx, by), pill)
    d.text((bx + pad_x, by + pad_y), wm_text, font=fw, fill=(50, 50, 50))

    base.save(out_path)
    return out_path

if __name__ == "__main__":
    os.makedirs("/root/wtd_frames5", exist_ok=True)
    render_beat("/root/wtd_frames5/t1_first.png", "SSD","ssd","HDD","hdd", "", "left", show="left")
    render_beat("/root/wtd_frames5/t2_both.png",  "SSD","ssd","HDD","hdd", "", "left", show="both")
    render_beat("/root/wtd_frames5/t3_ask.png",   "SSD","ssd","HDD","hdd", "What's the difference?", "ask", show="both")
    print("v5 test frames written")