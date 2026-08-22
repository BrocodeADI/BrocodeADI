"""Generate custom SVG editorial typography headings for profile sections."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

from .config import Config, load_config
from .svg_utils import (
    create_svg_document,
    escape_xml,
    get_font_face_css,
)

logger = logging.getLogger(__name__)

DEFAULT_HEADINGS: Dict[str, Dict[str, str]] = {
    "about": {
        "index": "01",
        "title": "PROFILE_MANIFEST",
        "subtitle": "IDENTITY & DIRECTIVES"
    },
    "stats": {
        "index": "02",
        "title": "TELEMETRY_METRICS",
        "subtitle": "CONTRIBUTIONS & CADENCE"
    },
    "languages": {
        "index": "03",
        "title": "TECH_STACK_DISTRIBUTION",
        "subtitle": "BYTE-WEIGHTED REPOSITORY CODE"
    },
    "activity": {
        "index": "04",
        "title": "CONTRIBUTION_MATRIX",
        "subtitle": "52-WEEK TEMPORAL HEATMAP"
    },
    "connect": {
        "index": "05",
        "title": "NETWORK_ENDPOINTS",
        "subtitle": "DISPATCH & COMMUNICATION"
    }
}


def generate_single_heading_svg(
    name: str,
    index_num: str,
    title: str,
    subtitle: str,
    config: Optional[Config] = None,
    output_dir: Optional[Path] = None
) -> str:
    """Render an editorial terminal heading SVG banner."""
    cfg = config or load_config()
    theme = cfg.theme

    width = 940
    height = 50

    title_esc = escape_xml(title)
    sub_esc = escape_xml(subtitle)
    idx_esc = escape_xml(index_num)

    content = f"""
    <!-- Terminal Prompt Indicator -->
    <rect x="0" y="8" width="4" height="34" rx="2" fill="{theme.accent}" />
    
    <!-- Index Tag -->
    <text x="16" y="24" fill="{theme.accent}" font-size="11" font-weight="700" letter-spacing="1">[{idx_esc}]</text>
    
    <!-- Heading Title -->
    <text x="56" y="25" fill="{theme.text_primary}" font-size="16" font-weight="700" letter-spacing="1.5">{title_esc}</text>
    
    <!-- Subtitle / Directive description -->
    <text x="56" y="38" fill="{theme.text_muted}" font-size="9" font-weight="500" letter-spacing="0.8">// {sub_esc}</text>
    
    <!-- Decorative Trailing Dash Rule -->
    <line x1="420" y1="24" x2="{width}" y2="24" stroke="{theme.border}" stroke-width="1" stroke-dasharray="4 4" opacity="0.6" />
    """

    all_chars = "".join(set(
        idx_esc + title + subtitle + "[] //->:0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_ "
    ))
    font_css = get_font_face_css(cfg.font_path, all_chars, cfg.font_family)

    svg_doc = create_svg_document(
        width=width,
        height=height,
        content=content,
        font_css=font_css
    )

    out_directory = output_dir or cfg.headings_dir
    out_directory.mkdir(parents=True, exist_ok=True)
    target_file = out_directory / f"{name}.svg"

    if not target_file.exists() or target_file.read_text(encoding="utf-8") != svg_doc:
        target_file.write_text(svg_doc, encoding="utf-8")
        logger.info(f"Generated heading SVG: {target_file}")

    return svg_doc


def generate_all_headings(
    config: Optional[Config] = None,
    output_dir: Optional[Path] = None
) -> Dict[str, str]:
    """Generate all standard section heading SVGs."""
    cfg = config or load_config()
    results = {}
    for name, info in DEFAULT_HEADINGS.items():
        results[name] = generate_single_heading_svg(
            name=name,
            index_num=info["index"],
            title=info["title"],
            subtitle=info["subtitle"],
            config=cfg,
            output_dir=output_dir
        )
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_all_headings()
