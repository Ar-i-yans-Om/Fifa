"""
share_card.py — render a single match prediction to a branded PNG for sharing.

Pure image layer: no Streamlit, no app imports. `build_match_card()` takes the
match + prediction data (plus pre-resolved flag codes) and returns PNG bytes.
Fonts resolve to DejaVuSans (bundled with matplotlib, also present on Linux/Cloud);
flags are fetched from flagcdn and cached. Everything degrades gracefully.
"""

from __future__ import annotations

import io
import os
import re
import urllib.request
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

# ── palette (mirrors the dashboard dark theme) ──────────────────────────────
BG       = (13, 17, 23)
PANEL    = (22, 27, 34)
PANEL2   = (28, 33, 40)
BORDER   = (48, 54, 61)
TEXT     = (240, 246, 252)
MUTED    = (139, 148, 158)
ACCENT   = (0, 201, 110)
ACCENT_D = (10, 35, 24)
BLUE     = (56, 139, 253)
DRAW     = (110, 118, 129)
LOSS     = (245, 158, 11)

W = H = 1080
M = 72


@lru_cache(maxsize=16)
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    try:
        import matplotlib
        d = os.path.join(os.path.dirname(matplotlib.__file__),
                         "mpl-data", "fonts", "ttf")
        candidates.append(os.path.join(d, "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"))
    except Exception:
        pass
    candidates += [
        "C:/Windows/Fonts/" + ("arialbd.ttf" if bold else "arial.ttf"),
        "/usr/share/fonts/truetype/dejavu/" + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


@lru_cache(maxsize=128)
def _flag(code: str, w: int = 160):
    if not code:
        return None
    try:
        url = f"https://flagcdn.com/w{w}/{code}.png"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            return Image.open(io.BytesIO(r.read())).convert("RGBA")
    except Exception:
        return None


def _flag_resized(code: str, target_w: int):
    img = _flag(code)
    if img is None:
        return None
    ratio = target_w / img.width
    return img.resize((target_w, max(1, int(img.height * ratio))), Image.LANCZOS)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def build_match_card(
    home: str, away: str, group: str | None, md,
    pa, pd, pb, scoreline, headline: str,
    home_code: str = "", away_code: str = "",
    accuracy: int | None = None,
) -> bytes:
    """Render the prediction to a 1080×1080 PNG and return the raw bytes."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # subtle top accent band
    d.rectangle([0, 0, W, 8], fill=ACCENT)
    # faint pitch arc motif top-right
    d.ellipse([W - 240, -140, W + 140, 240], outline=(20, 40, 30), width=3)
    d.line([W - 70, 0, W - 70, 70], fill=(20, 40, 30), width=3)

    # ── header row ──
    d.text((M, 70), "SIUUUMULATOR", font=_font(34, True), fill=ACCENT, anchor="lm")
    d.text((W - M, 70), "FIFA WORLD CUP 2026", font=_font(22, True), fill=MUTED, anchor="rm")
    d.line([M, 112, W - M, 112], fill=BORDER, width=2)

    meta = " · ".join(x for x in [
        f"GROUP {group}" if group else None,
        f"MATCHDAY {md}" if md else None,
    ] if x)
    if meta:
        d.text((W / 2, 158), meta, font=_font(24, True), fill=MUTED, anchor="mm")

    # ── teams + flags ──
    cy = 300
    fw = 190
    for cx, team, code in ((300, home, home_code), (W - 300, away, away_code)):
        fl = _flag_resized(code, fw)
        if fl is not None:
            img.paste(fl, (int(cx - fw / 2), int(cy - fl.height / 2)), fl)
            d.rectangle([int(cx - fw / 2), int(cy - fl.height / 2),
                         int(cx + fw / 2), int(cy + fl.height / 2)], outline=BORDER, width=2)
        name_f = _font(34, True)
        # shrink long names to fit a 360px column
        while d.textlength(team, font=name_f) > 360 and name_f.size > 20:
            name_f = _font(name_f.size - 2, True)
        d.text((cx, cy + 110), team, font=name_f, fill=TEXT, anchor="mm")
    d.text((W / 2, cy), "vs", font=_font(30, False), fill=MUTED, anchor="mm")

    # ── predicted scoreline ──
    hg = ag = None
    if scoreline:
        m = re.search(r"(\d+)\s*-\s*(\d+)", str(scoreline))
        if m:
            hg, ag = m.group(1), m.group(2)
    sy = 540
    if hg is not None:
        d.text((W / 2, sy), f"{hg}  -  {ag}", font=_font(132, True), fill=TEXT, anchor="mm")
    else:
        d.text((W / 2, sy), "vs", font=_font(96, True), fill=MUTED, anchor="mm")
    d.text((W / 2, sy + 96), "PREDICTED SCORELINE", font=_font(20, True), fill=MUTED, anchor="mm")

    # ── win / draw / loss bar ──
    by, bh = 700, 60
    bx0, bx1 = M, W - M
    bw = bx1 - bx0
    try:
        tot = max(1, int(pa) + int(pd) + int(pb))
        segs = [(int(pa), BLUE, f"{int(pa)}%"),
                (int(pd), DRAW, f"{int(pd)}%"),
                (int(pb), LOSS, f"{int(pb)}%")]
        x = bx0
        for val, col, lab in segs:
            seg_w = int(bw * val / tot)
            if seg_w <= 0:
                continue
            d.rectangle([x, by, x + seg_w, by + bh], fill=col)
            if seg_w > 64:
                tcol = (4, 19, 11) if col is LOSS else TEXT
                d.text((x + seg_w / 2, by + bh / 2), lab, font=_font(26, True),
                       fill=tcol, anchor="mm")
            x += seg_w
        d.rounded_rectangle([bx0, by, bx1, by + bh], radius=10, outline=BORDER, width=2)
        # legend
        ly = by + bh + 34
        leg = [(BLUE, f"{home} win"), (DRAW, "Draw"), (LOSS, f"{away} win")]
        spacing = bw / 3
        for i, (col, lab) in enumerate(leg):
            lx = bx0 + spacing * i + 6
            d.rounded_rectangle([lx, ly - 9, lx + 18, ly + 9], radius=4, fill=col)
            d.text((lx + 28, ly), lab, font=_font(22, False), fill=MUTED, anchor="lm")
    except (TypeError, ValueError):
        d.text((W / 2, by + bh / 2), "Prediction pending", font=_font(26, True),
               fill=MUTED, anchor="mm")

    # ── headline ──
    if headline:
        hf = _font(28, False)
        lines = _wrap(d, headline.strip(), hf, W - 2 * M)[:3]
        hy = 850
        for ln in lines:
            d.text((W / 2, hy), ln, font=hf, fill=(200, 208, 218), anchor="mm")
            hy += 40

    # ── footer ──
    d.line([M, H - 92, W - M, H - 92], fill=BORDER, width=2)
    d.text((M, H - 56), "AI multi-agent prediction engine",
           font=_font(22, False), fill=MUTED, anchor="lm")
    right = "siuuumulator"
    if accuracy is not None:
        right = f"{accuracy}% model accuracy  ·  siuuumulator"
    d.text((W - M, H - 56), right, font=_font(22, True), fill=ACCENT, anchor="rm")

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
