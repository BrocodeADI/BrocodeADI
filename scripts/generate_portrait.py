"""ASCII portrait generator — exact port of andriidrok1/andriidrok1/scripts/make_portrait.py.

Produces a transparent, borderless, self-typing SVG portrait using:
  - rembg background removal (u2netp fast model)
  - bilateral filter + CLAHE + darkening power curve
  - SMIL clipPath row-wipe animation with riding cursor
  - JetBrains Mono embedded (0.600 em advance width)
  - GitHub light/dark adaptive fill colours, no background box
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from .config import Config, load_config
from .svg_utils import get_font_face_css, escape_xml, create_svg_document

logger = logging.getLogger(__name__)

# ── Exact constants from andriidrok1 ──────────────────────────────────────────
RAMP       = " .`:-=+*cs#%@"   # bright/sparse → dark/dense; leading space = blank
COLS       = 90                 # below ~88 the face muddies
CLAHE_CLIP = 3.0
GAMMA      = 1.0                # ramp mapping exponent
CURVE      = 1.7                # darkening curve — the difference-maker
ROW_RATIO  = 0.48               # monospace cells are ~2× as tall as wide

FG_LIGHT   = "#6e7681"          # GitHub light grey
FG_DARK    = "#c9d1d9"          # GitHub dark off-white
CHAR_W     = 7.74               # 0.600 em at FONT_SIZE
FONT_SIZE  = 12.9
LINE_H     = 15
ROW_DELAY  = 0.09               # per-row stagger, seconds
FAMILY     = "JBMono,ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"


# ── Background removal ────────────────────────────────────────────────────────

def remove_background_fallback(img_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """GrabCut fallback when rembg is unavailable."""
    h, w = img_bgr.shape[:2]
    if h < 20 or w < 20:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        return gray, np.full((h, w), 255, dtype=np.uint8)
    try:
        cv2.setRNGSeed(42)
        mask = np.zeros((h, w), np.uint8)
        bgd = np.zeros((1, 65), np.float64)
        fgd = np.zeros((1, 65), np.float64)
        mx, my = max(2, int(w * 0.04)), max(2, int(h * 0.04))
        rect = (mx, my, w - 2 * mx, h - 2 * my)
        cv2.grabCut(img_bgr, mask, rect, bgd, fgd, 3, cv2.GC_INIT_WITH_RECT)
        alpha = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype("uint8")
        white = np.full((h, w, 3), 255, dtype=np.uint8)
        na = (alpha / 255.0)[:, :, np.newaxis]
        comp = (img_bgr * na + white * (1.0 - na)).astype(np.uint8)
        return cv2.cvtColor(comp, cv2.COLOR_BGR2GRAY), alpha
    except Exception as e:
        logger.warning(f"GrabCut failed ({e}), using raw grayscale.")
        return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY), np.full((h, w), 255, dtype=np.uint8)


# ── Image preparation — exact andriidrok1 pipeline ────────────────────────────

def prep_image(img_path: Path, crop: Optional[Tuple[int,int,int,int]] = None) -> Image.Image:
    """Cut out background, equalize contrast, apply darkening curve."""
    src = Image.open(img_path).convert("RGBA")
    if crop:
        src = src.crop(crop)

    try:
        from rembg import remove, new_session
        session = new_session("u2netp")
        cut   = remove(src, session=session)
        alpha = np.array(cut.split()[-1])
        white = Image.new("RGBA", cut.size, (255, 255, 255, 255))
        gray  = np.array(Image.alpha_composite(white, cut).convert("L"))
    except Exception as e:
        logger.info(f"rembg unavailable ({e}), falling back to GrabCut.")
        img_bgr = cv2.cvtColor(np.array(src.convert("RGB")), cv2.COLOR_RGB2BGR)
        gray, alpha = remove_background_fallback(img_bgr)

    gray  = cv2.bilateralFilter(gray, 11, 50, 50)
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=(8, 8))
    gray  = clahe.apply(gray)
    gray  = (255.0 * (gray / 255.0) ** CURVE).astype("uint8")
    gray[alpha < 20] = 255          # hard-matte the background → blank space

    return Image.fromarray(gray)


# ── ASCII conversion ──────────────────────────────────────────────────────────

def image_to_ascii_lines(img: Image.Image, cols: int = COLS) -> List[str]:
    """Ramp-map the prepped image to ASCII character rows."""
    w, h = img.size
    rows    = max(10, int(cols * (h / w) * ROW_RATIO))
    resized = img.resize((cols, rows), Image.Resampling.LANCZOS)
    px      = list(resized.getdata())
    n       = len(RAMP)
    lines: List[str] = []
    for r in range(rows):
        row = []
        for c in range(cols):
            val  = px[r * cols + c]
            norm = max(0.0, min(1.0, 1.0 - val / 255.0))
            idx  = min(n - 1, int((norm ** GAMMA) * n))
            row.append(RAMP[idx])
        lines.append("".join(row).rstrip())

    while lines and not lines[0].strip():  lines.pop(0)
    while lines and not lines[-1].strip(): lines.pop()
    return lines


# ── SVG assembly — exact andriidrok1 structure ────────────────────────────────

def build_portrait_svg(lines: List[str], config: Config) -> str:
    """Borderless transparent SVG with SMIL animated row wipes and cursor."""
    pad    = 14.0
    n_cols = max(COLS, max(len(l) for l in lines) if lines else COLS)
    width  = int(n_cols * CHAR_W + pad * 2)
    height = int(len(lines) * LINE_H + pad * 2)

    all_chars = "".join(set(RAMP + " ".join(lines)))
    font_css  = get_font_face_css(config.font_path, all_chars, "JBMono")

    style = f"""
    {font_css}
    .a {{ fill: {FG_LIGHT}; }}
    @media (prefers-color-scheme: dark) {{
        .a {{ fill: {FG_DARK}; }}
    }}
    """

    parts: List[str] = []
    for i, line in enumerate(lines):
        y     = pad + i * LINE_H
        begin = f"{i * ROW_DELAY:.2f}s"
        end   = f"{(i + 1) * ROW_DELAY:.2f}s"
        w     = max(len(line), 1) * CHAR_W
        cid   = f"c{i}"
        safe  = escape_xml(line)

        # clipPath that wipes the row left → right
        parts.append(
            f'<clipPath id="{cid}">'
            f'<rect x="{pad:.1f}" y="{y:.1f}" height="{LINE_H:.1f}" width="0">'
            f'<animate attributeName="width" from="0" to="{w:.1f}" '
            f'begin="{begin}" dur="{ROW_DELAY:.2f}s" fill="freeze"/>'
            f'</rect>'
            f'</clipPath>'
        )
        # Text revealed by the clip
        parts.append(
            f'<g clip-path="url(#{cid})">'
            f'<text xml:space="preserve" x="{pad:.1f}" y="{y + 11.2:.1f}" '
            f'class="a" font-size="{FONT_SIZE}">{safe}</text>'
            f'</g>'
        )

    body = "\n".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" fill="none" '
        f'font-family="{FAMILY}">'
        f'<style>{style}</style>'
        f'{body}'
        f'</svg>'
    )


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_portrait_svg(
    config: Optional[Config] = None,
    output_path: Optional[Path] = None,
    crop: Optional[Tuple[int,int,int,int]] = None,
) -> str:
    cfg     = config or load_config()
    prepped = prep_image(cfg.portrait_path, crop=crop)
    lines   = image_to_ascii_lines(prepped, cols=COLS)
    svg     = build_portrait_svg(lines, cfg)

    target  = output_path or (cfg.output_dir / "portrait.svg")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.read_text(encoding="utf-8") != svg:
        target.write_text(svg, encoding="utf-8")
        logger.info(f"Generated portrait SVG → {target}")

    return svg


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_portrait_svg()
