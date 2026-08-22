"""High-Definition ASCII Portrait generator matching the visual standard of andriidrok1.

Pipeline:
1. Subject isolation using rembg (u2netp model)
2. Alpha compositing onto pure white
3. Edge-preserving bilateral filter (11, 50, 50)
4. CLAHE adaptive local contrast equalization
5. Darkening power curve (gray / 255.0) ** 1.7
6. Alpha matte clamp (alpha < 20 -> 255)
7. Monospace geometry aspect ratio correction (0.48)
8. High-density character ramp quantization (" .`:-=+*cs#%@")
9. SMIL animated clipPath wipe with riding cursor block
10. Embedded JetBrains Mono typography
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from .config import Config, load_config
from .svg_utils import (
    create_svg_document,
    escape_xml,
    get_font_face_css,
)

logger = logging.getLogger(__name__)


def remove_background_fallback(img_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """GrabCut fallback for background separation if rembg is unavailable."""
    h, w = img_bgr.shape[:2]
    if h < 20 or w < 20:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        return gray, np.full((h, w), 255, dtype=np.uint8)

    try:
        cv2.setRNGSeed(42)
        mask = np.zeros((h, w), np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        
        margin_x = max(2, int(w * 0.04))
        margin_y = max(2, int(h * 0.04))
        rect = (margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)
        
        cv2.grabCut(img_bgr, mask, rect, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_RECT)
        alpha = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype("uint8")
        
        white_bg = np.full((h, w, 3), 255, dtype=np.uint8)
        norm_alpha = (alpha / 255.0)[:, :, np.newaxis]
        composite_bgr = (img_bgr * norm_alpha + white_bg * (1.0 - norm_alpha)).astype(np.uint8)
        gray = cv2.cvtColor(composite_bgr, cv2.COLOR_BGR2GRAY)
        return gray, alpha
    except Exception as e:
        logger.warning(f"GrabCut fallback failed ({e}), using direct grayscale.")
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        return gray, np.full((h, w), 255, dtype=np.uint8)


def prep_image(
    img_path: Path,
    crop: Optional[Tuple[int, int, int, int]] = None,
    curve: float = 1.7,
    clahe_clip: float = 3.0
) -> Image.Image:
    """Cut out background, enhance local contrast, and apply darkening curve."""
    if not img_path.exists():
        raise FileNotFoundError(f"Portrait image not found at: {img_path}")

    src = Image.open(img_path).convert("RGBA")
    w, h = src.size
    
    # Apply proportional face-centered crop
    if crop:
        src = src.crop(crop)
    elif h > 400:
        crop_box = (int(w * 0.04), int(h * 0.06), int(w * 0.96), int(h * 0.92))
        src = src.crop(crop_box)

    alpha: np.ndarray
    gray: np.ndarray

    try:
        from rembg import new_session, remove
        session = new_session("u2netp")
        cut = remove(src, session=session)
        alpha = np.array(cut.split()[-1])
        white = Image.new("RGBA", cut.size, (255, 255, 255, 255))
        gray = np.array(Image.alpha_composite(white, cut).convert("L"))
    except (ImportError, Exception) as e:
        logger.info(f"rembg u2netp unavailable ({e}); applying GrabCut background separation.")
        src_rgb = src.convert("RGB")
        img_bgr = cv2.cvtColor(np.array(src_rgb), cv2.COLOR_RGB2BGR)
        gray, alpha = remove_background_fallback(img_bgr)

    # 1. Bilateral filter: smooth skin, keep sharp facial edges
    gray = cv2.bilateralFilter(gray, 11, 50, 50)

    # 2. CLAHE local adaptive contrast
    clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # 3. Darkening curve to preserve facial features, eyebrows, eyes, and lips
    gray = (255.0 * ((gray / 255.0) ** curve)).astype("uint8")

    # 4. Force background to pure white (blank ASCII)
    gray[alpha < 20] = 255

    return Image.fromarray(gray)


def image_to_ascii_lines(
    img: Image.Image,
    cols: int = 90,
    gamma: float = 1.0,
    ramp: str = " .`:-=+*cs#%@",
    row_ratio: float = 0.48
) -> List[str]:
    """Convert prepped image to ASCII lines."""
    w, h = img.size
    rows = max(10, int(cols * (h / w) * row_ratio))
    resized = img.resize((cols, rows), Image.Resampling.LANCZOS)
    px = list(resized.getdata())
    n = len(ramp)

    lines: List[str] = []
    for r in range(rows):
        row_chars = []
        for c in range(cols):
            val = px[r * cols + c]
            norm = max(0.0, min(1.0, 1.0 - val / 255.0))
            idx = min(n - 1, int((norm ** gamma) * n))
            row_chars.append(ramp[idx])
        lines.append("".join(row_chars).rstrip())

    # Strip empty leading/trailing blank rows
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    return lines


def build_animated_portrait_svg(
    lines: List[str],
    config: Config,
    cols: int = 90,
    char_w: float = 7.74,
    font_size: float = 12.9,
    line_h: float = 15.0,
    row_delay: float = 0.08
) -> str:
    """Build SMIL animated SVG with clipPath wipe and cursor blocks."""
    pad = 16.0
    theme = config.theme
    
    max_line_len = max(len(l) for l in lines) if lines else cols
    render_cols = max(cols, max_line_len)
    width = int(render_cols * char_w + pad * 2)
    height = int(len(lines) * line_h + pad * 2)

    svg_parts: List[str] = []

    # Card background & border
    svg_parts.append(
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" '
        f'fill="{theme.card_bg}" stroke="{theme.border}" stroke-width="1" />'
    )

    # Text Rows & Animated Wipes
    for i, line in enumerate(lines):
        y = pad + i * line_h
        begin = f"{i * row_delay:.3f}s"
        end = f"{(i + 1) * row_delay:.3f}s"
        w = max(len(line), 1) * char_w
        safe_text = escape_xml(line)

        clip_id = f"cp_{i}"
        
        # Row clipPath wipe
        svg_parts.append(
            f'<clipPath id="{clip_id}">'
            f'<rect x="{pad:.1f}" y="{y:.1f}" height="{line_h:.1f}" width="0">'
            f'<animate attributeName="width" from="0" to="{w:.1f}" begin="{begin}" dur="{row_delay:.3f}s" fill="freeze" />'
            f'</rect>'
            f'</clipPath>'
        )

        # Row Text Content
        svg_parts.append(
            f'<g clip-path="url(#{clip_id})">'
            f'<text xml:space="preserve" x="{pad:.1f}" y="{y + 11.2:.1f}" '
            f'fill="{theme.accent}" font-size="{font_size:.1f}">{safe_text}</text>'
            f'</g>'
        )

        # Riding Terminal Cursor Block
        svg_parts.append(
            f'<rect y="{y + 1:.1f}" width="6" height="12" fill="{theme.accent}" opacity="0">'
            f'<animate attributeName="x" from="{pad:.1f}" to="{pad + w:.1f}" begin="{begin}" dur="{row_delay:.3f}s" fill="freeze" />'
            f'<set attributeName="opacity" to="0.8" begin="{begin}" />'
            f'<set attributeName="opacity" to="0" begin="{end}" />'
            f'</rect>'
        )

    body_svg = "\n    ".join(svg_parts)

    all_chars = "".join(set(config.ascii_ramp + " ".join(lines) + "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.:_-"))
    font_css = get_font_face_css(config.font_path, all_chars, config.font_family)

    return create_svg_document(
        width=width,
        height=height,
        content=body_svg,
        font_css=font_css
    )


def generate_portrait_svg(
    config: Optional[Config] = None,
    output_path: Optional[Path] = None
) -> str:
    """Master generation function for high-definition ASCII portrait."""
    cfg = config or load_config()
    
    prepped = prep_image(
        img_path=cfg.portrait_path,
        curve=1.7,
        clahe_clip=3.0
    )

    lines = image_to_ascii_lines(
        img=prepped,
        cols=cfg.ascii_width,
        gamma=1.0,
        ramp=cfg.ascii_ramp,
        row_ratio=0.48
    )

    svg_doc = build_animated_portrait_svg(
        lines=lines,
        config=cfg,
        cols=cfg.ascii_width,
        row_delay=cfg.row_delay
    )

    target_file = output_path or (cfg.output_dir / "portrait.svg")
    target_file.parent.mkdir(parents=True, exist_ok=True)

    if not target_file.exists() or target_file.read_text(encoding="utf-8") != svg_doc:
        target_file.write_text(svg_doc, encoding="utf-8")
        logger.info(f"Generated high-definition portrait SVG: {target_file}")

    return svg_doc


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_portrait_svg()
