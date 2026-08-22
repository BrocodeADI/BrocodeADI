"""ASCII Portrait generator with OpenCV computer vision pipeline and animated SVG rendering."""

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
    render_terminal_card,
)

logger = logging.getLogger(__name__)


def remove_background_fallback(img_bgr: np.ndarray) -> np.ndarray:
    """
    Intelligent background separation fallback when rembg is not available.
    Uses GrabCut algorithm with an outer boundary background assumption.
    Ensures deterministic output using fixed RNG seed.
    """
    h, w = img_bgr.shape[:2]
    # If image is very small or simple, return original
    if h < 20 or w < 20:
        return img_bgr

    try:
        cv2.setRNGSeed(42)
        mask = np.zeros((h, w), np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        
        # Assume margin of 5% around edges as probable background
        margin_x = max(2, int(w * 0.05))
        margin_y = max(2, int(h * 0.05))
        rect = (margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)
        
        cv2.grabCut(img_bgr, mask, rect, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_RECT)
        mask2 = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype("uint8")
        
        # Composite foreground over white background
        white_bg = np.full((h, w, 3), 255, dtype=np.uint8)
        alpha = (mask2 / 255.0)[:, :, np.newaxis]
        result = (img_bgr * alpha + white_bg * (1.0 - alpha)).astype(np.uint8)
        return result
    except Exception as e:
        logger.warning(f"GrabCut fallback failed ({e}), using direct image.")
        return img_bgr


def isolate_subject(img_path: Path) -> np.ndarray:
    """
    Load image and apply background removal (rembg if installed, GrabCut fallback otherwise).
    """
    if not img_path.exists():
        raise FileNotFoundError(f"Portrait image not found at: {img_path}")

    # Try rembg if installed
    try:
        import rembg
        pil_img = Image.open(img_path)
        nobg = rembg.remove(pil_img)
        # Composite on white background
        white_bg = Image.new("RGBA", nobg.size, (255, 255, 255, 255))
        composite = Image.alpha_composite(white_bg, nobg).convert("RGB")
        return cv2.cvtColor(np.array(composite), cv2.COLOR_RGB2BGR)
    except (ImportError, Exception) as e:
        logger.info(f"rembg not active ({e}); applying OpenCV background isolation.")
        img_bgr = cv2.imread(str(img_path))
        if img_bgr is None:
            raise ValueError(f"OpenCV could not decode image at {img_path}")
        return remove_background_fallback(img_bgr)


def image_to_ascii(
    img_bgr: np.ndarray,
    config: Config,
    invert: bool = True
) -> Tuple[List[str], int, int]:
    """
    Convert image to ASCII character matrix through CV pipeline:
    1. Grayscale conversion
    2. Bilateral filtering (edge-preserving smoothing)
    3. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    4. Nonlinear gamma brightness transformation
    5. Aspect ratio correction & resampling
    6. ASCII character ramp quantization
    """
    # 1. Convert to grayscale
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # 2. Bilateral filtering (preserves edges of eyes, jawline, glasses)
    filtered = cv2.bilateralFilter(
        gray,
        d=config.bilateral_d,
        sigmaColor=config.bilateral_sigma_color,
        sigmaSpace=config.bilateral_sigma_space
    )

    # 3. CLAHE local adaptive contrast enhancement
    clahe = cv2.createCLAHE(
        clipLimit=config.contrast_clip_limit,
        tileGridSize=config.contrast_tile_grid
    )
    enhanced = clahe.apply(filtered)

    # Invert if specified (for dark terminals, subject features become bright ASCII characters)
    if invert:
        enhanced = 255 - enhanced

    # 4. Nonlinear gamma brightness transformation: (v / 255.0) ** gamma
    norm = np.clip(enhanced / 255.0, 0.0, 1.0)
    gamma_corrected = (norm ** config.gamma) * 255.0
    processed_img = np.clip(gamma_corrected, 0, 255).astype(np.uint8)

    # 5. Aspect ratio geometry calculation
    h, w = img_bgr.shape[:2]
    ascii_width = config.ascii_width
    ascii_height = max(10, int((h / w) * ascii_width * config.aspect_ratio))

    # Resample to ASCII grid with area interpolation to prevent aliasing
    resized = cv2.resize(
        processed_img,
        (ascii_width, ascii_height),
        interpolation=cv2.INTER_AREA
    )

    # 6. Map brightness values to ASCII ramp characters
    ramp = config.ascii_ramp
    ramp_len = len(ramp)
    
    ascii_rows: List[str] = []
    for r in range(ascii_height):
        row_chars = []
        for c in range(ascii_width):
            val = resized[r, c]
            idx = int((val / 256.0) * ramp_len)
            idx = min(ramp_len - 1, max(0, idx))
            row_chars.append(ramp[idx])
        ascii_rows.append("".join(row_chars))

    return ascii_rows, ascii_width, ascii_height


def generate_portrait_svg(
    config: Optional[Config] = None,
    output_path: Optional[Path] = None
) -> str:
    """Generate animated SVG portrait from configured image asset."""
    cfg = config or load_config()
    theme = cfg.theme
    
    # 1. Process image to ASCII lines
    img_bgr = isolate_subject(cfg.portrait_path)
    # Dark themes benefit from inverting so subject silhouette pops against dark background
    invert_for_theme = (theme.name != "light")
    ascii_lines, cols, rows = image_to_ascii(img_bgr, cfg, invert=invert_for_theme)

    # 2. Dimensions and layout metrics
    char_width = cfg.font_size * 0.60
    line_height = cfg.line_height
    padding_x = 24.0
    padding_y = 20.0
    header_height = 36.0

    content_width = int(cols * char_width + 2 * padding_x)
    content_height = int(rows * line_height + 2 * padding_y + header_height)

    # 3. Build animated SMIL text rows
    svg_text_rows: List[str] = []
    for i, line in enumerate(ascii_lines):
        y_pos = padding_y + (i + 1) * line_height - 2
        line_esc = escape_xml(line)
        
        if cfg.enable_animation:
            # Sequential top-to-bottom reveal animation
            delay = i * cfg.row_delay
            anim_tag = (
                f'<animate attributeName="opacity" from="0" to="1" '
                f'dur="0.12s" begin="{delay:.3f}s" fill="freeze" />'
            )
            svg_text_rows.append(
                f'<text x="{padding_x:.1f}" y="{y_pos:.1f}" fill="{theme.accent}" '
                f'font-size="{cfg.font_size}" xml:space="preserve" opacity="0">{anim_tag}{line_esc}</text>'
            )
        else:
            svg_text_rows.append(
                f'<text x="{padding_x:.1f}" y="{y_pos:.1f}" fill="{theme.accent}" '
                f'font-size="{cfg.font_size}" xml:space="preserve">{line_esc}</text>'
            )

    body_content = "\n        ".join(svg_text_rows)

    # Card Title with dimensions metadata
    title = f"PORTRAIT // {cols}x{rows} MATRIX"
    status = f"GAMMA {cfg.gamma:.1f}"

    card_content = render_terminal_card(
        width=content_width,
        height=content_height,
        title=title,
        theme=theme,
        body_content=body_content,
        status_tag=status
    )

    # Gather characters needed for font subsetting
    all_needed_chars = "".join(set(cfg.ascii_ramp + title + status + "ONLINE" + "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.:_ "))
    font_css = get_font_face_css(cfg.font_path, all_needed_chars, cfg.font_family)

    svg_doc = create_svg_document(
        width=content_width,
        height=content_height,
        content=card_content,
        font_css=font_css
    )

    target_file = output_path or (cfg.output_dir / "portrait.svg")
    target_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write only if changed
    if not target_file.exists() or target_file.read_text(encoding="utf-8") != svg_doc:
        target_file.write_text(svg_doc, encoding="utf-8")
        logger.info(f"Generated portrait SVG: {target_file}")
        
    return svg_doc


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_portrait_svg()
