"""SVG utility functions, font subsetting, and terminal-inspired card builders."""

from __future__ import annotations

import base64
import html
import io
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from fontTools import subset

from .config import Config, Theme

logger = logging.getLogger(__name__)

# Cache for font subset base64 strings to avoid re-subsetting identical character sets
_FONT_SUBSET_CACHE = {}


def escape_xml(text: str) -> str:
    """Escape XML special characters."""
    return html.escape(str(text), quote=True)


def subset_font_to_base64(font_path: Path, characters: str) -> str:
    """
    Subset a TTF/OTF font to only include the given characters and return WOFF2 base64.
    """
    if not font_path.exists():
        logger.warning(f"Font file not found at {font_path}. Skipping font embedding.")
        return ""

    # Sort and deduplicate characters for cache key stability
    unique_chars = "".join(sorted(set(characters)))
    cache_key = (str(font_path.resolve()), unique_chars)
    if cache_key in _FONT_SUBSET_CACHE:
        return _FONT_SUBSET_CACHE[cache_key]

    try:
        options = subset.Options()
        options.flavor = "woff2"
        options.desubroutinize = True
        options.hinting = True
        
        font = subset.load_font(str(font_path), options)
        subsetter = subset.Subsetter(options=options)
        subsetter.populate(text=unique_chars)
        subsetter.subset(font)
        
        buf = io.BytesIO()
        font.save(buf)
        woff2_data = buf.getvalue()
        b64_str = base64.b64encode(woff2_data).decode("ascii")
        _FONT_SUBSET_CACHE[cache_key] = b64_str
        return b64_str
    except Exception as e:
        logger.warning(f"Failed to subset font {font_path}: {e}")
        return ""


def get_font_face_css(
    font_path: Path, characters: str, font_family: str = "JetBrainsMono"
) -> str:
    """Generate @font-face CSS snippet with embedded subsetted WOFF2 font."""
    b64_font = subset_font_to_base64(font_path, characters)
    if not b64_font:
        return f"""
        * {{
            font-family: '{font_family}', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        }}
        """
        
    return f"""
        @font-face {{
            font-family: '{font_family}';
            src: url(data:font/woff2;base64,{b64_font}) format('woff2');
            font-weight: 400;
            font-style: normal;
            font-display: block;
        }}
        * {{
            font-family: '{font_family}', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
        }}
    """


def create_svg_document(
    width: int,
    height: int,
    content: str,
    font_css: str = "",
    extra_defs: str = "",
    view_box: Optional[Tuple[int, int, int, int]] = None
) -> str:
    """Wrap SVG content into a complete, standalone, sanitized SVG document."""
    vb_str = f'viewBox="{view_box[0]} {view_box[1]} {view_box[2]} {view_box[3]}"' if view_box else f'viewBox="0 0 {width} {height}"'
    
    style_block = f"<style>\n{font_css}\n</style>" if font_css else ""
    defs_block = f"<defs>\n{style_block}\n{extra_defs}\n</defs>" if (style_block or extra_defs) else ""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" {vb_str} fill="none" role="img">
{defs_block}
{content}
</svg>"""


def render_terminal_card(
    width: int,
    height: int,
    title: str,
    theme: Theme,
    body_content: str,
    status_tag: str = "ONLINE",
    header_extra: str = ""
) -> str:
    """
    Render an editorial terminal container with header bar, control buttons,
    subtle border stroke, and status indicator.
    """
    title_esc = escape_xml(title)
    status_esc = escape_xml(status_tag)
    
    # Terminal control dots (Close, Minimize, Maximize)
    dots = f"""
    <circle cx="20" cy="18" r="4.5" fill="#ff5f56" />
    <circle cx="34" cy="18" r="4.5" fill="#ffbd2e" />
    <circle cx="48" cy="18" r="4.5" fill="#27c93f" />
    """

    return f"""
    <!-- Terminal Background & Outer Border -->
    <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" fill="{theme.card_bg}" stroke="{theme.border}" stroke-width="1" />

    <!-- Terminal Header Bar -->
    <path d="M 1 8 A 7 7 0 0 1 8 1 L {width - 8} 1 A 7 7 0 0 1 {width - 1} 8 L {width - 1} 36 L 1 36 Z" fill="{theme.bg}" opacity="0.85" />
    <line x1="1" y1="36" x2="{width - 1}" y2="36" stroke="{theme.border}" stroke-width="1" />

    <!-- Control Dots -->
    {dots}

    <!-- Title and Status -->
    <text x="65" y="22" fill="{theme.text_secondary}" font-size="11" font-weight="600" letter-spacing="0.5">{title_esc}</text>
    {header_extra}
    
    <!-- Status Badge -->
    <rect x="{width - 78}" y="10" width="64" height="16" rx="4" fill="{theme.bg}" stroke="{theme.border}" stroke-width="0.8" />
    <circle cx="{width - 69}" cy="18" r="2.5" fill="{theme.accent_secondary}" />
    <text x="{width - 61}" y="21.5" fill="{theme.text_secondary}" font-size="9" font-weight="600">{status_esc}</text>

    <!-- Body Area -->
    <g transform="translate(0, 36)">
        {body_content}
    </g>
    """


def render_progress_bar(
    x: float,
    y: float,
    width: float,
    height: float,
    segments: List[Tuple[float, str]],  # (fraction 0.0-1.0, color)
    rx: float = 3.0,
    bg_color: str = "#21262d"
) -> str:
    """Render a segmented multi-color progress meter with exact dimensions."""
    if not segments or width <= 0:
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" rx="{rx}" fill="{bg_color}" />'

    # Filter out 0-length segments
    valid_segments = [(frac, color) for frac, color in segments if frac > 0.0001]
    if not valid_segments:
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" rx="{rx}" fill="{bg_color}" />'

    clip_id = f"prog_clip_{int(x)}_{int(y)}"
    rects: List[str] = []
    
    curr_x = x
    for frac, color in valid_segments:
        seg_w = frac * width
        rects.append(
            f'<rect x="{curr_x:.2f}" y="{y:.2f}" width="{seg_w:.2f}" height="{height:.2f}" fill="{color}" />'
        )
        curr_x += seg_w

    joined_rects = "\n        ".join(rects)
    return f"""
    <g>
        <clipPath id="{clip_id}">
            <rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" rx="{rx}" />
        </clipPath>
        <rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" rx="{rx}" fill="{bg_color}" />
        <g clip-path="url(#{clip_id})">
            {joined_rects}
        </g>
    </g>
    """


def render_stat_box(
    x: float,
    y: float,
    width: float,
    height: float,
    label: str,
    value: str,
    theme: Theme,
    subtext: str = "",
    accent_color: Optional[str] = None
) -> str:
    """Render a clean metric tile box with label, value, and optional indicator."""
    accent = accent_color or theme.accent
    label_esc = escape_xml(label)
    val_esc = escape_xml(value)
    sub_esc = escape_xml(subtext)

    sub_elem = f'<text x="{x + 14:.1f}" y="{y + height - 12:.1f}" fill="{theme.text_muted}" font-size="10">{sub_esc}</text>' if subtext else ""

    return f"""
    <g>
        <rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" rx="6" fill="{theme.bg}" stroke="{theme.border}" stroke-width="0.8" />
        <line x1="{x:.1f}" y1="{y + 6:.1f}" x2="{x:.1f}" y2="{y + height - 6:.1f}" stroke="{accent}" stroke-width="3" stroke-linecap="round" />
        <text x="{x + 14:.1f}" y="{y + 20:.1f}" fill="{theme.text_secondary}" font-size="10" font-weight="600" letter-spacing="0.5">{label_esc}</text>
        <text x="{x + 14:.1f}" y="{y + 44:.1f}" fill="{theme.text_primary}" font-size="18" font-weight="700">{val_esc}</text>
        {sub_elem}
    </g>
    """
