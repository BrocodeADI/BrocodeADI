"""Generate Programming Languages Distribution SVG Card."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple

from .config import Config, load_config
from .github_api import GitHubAPIClient, GitHubUserData, LanguageStat
from .svg_utils import (
    create_svg_document,
    escape_xml,
    get_font_face_css,
    render_progress_bar,
    render_terminal_card,
)

logger = logging.getLogger(__name__)


def format_bytes(num_bytes: int) -> str:
    """Format byte count into human-readable string (KB, MB)."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    else:
        return f"{num_bytes / (1024 * 1024):.2f} MB"


def generate_languages_svg(
    user_data: GitHubUserData,
    config: Optional[Config] = None,
    output_path: Optional[Path] = None
) -> str:
    """Generate terminal-style programming language breakdown SVG card."""
    cfg = config or load_config()
    theme = cfg.theme
    languages = user_data.languages

    width = 940
    height = 200

    # Top 8 languages
    display_langs = languages[:8]
    if not display_langs:
        # Fallback if no public repo languages found
        display_langs = [
            LanguageStat("Python", "#3572A5", 1000, 100.0)
        ]

    # Build progress bar segments: (fraction 0.0-1.0, color)
    segments: List[Tuple[float, str]] = []
    for lang in display_langs:
        segments.append((lang.percentage / 100.0, lang.color))

    prog_x = 24.0
    prog_y = 18.0
    prog_w = width - 48.0
    prog_h = 14.0

    progress_svg = render_progress_bar(
        x=prog_x,
        y=prog_y,
        width=prog_w,
        height=prog_h,
        segments=segments,
        rx=4.0,
        bg_color=theme.bg
    )

    # 2 rows of 4 columns for legend items
    legend_items: List[str] = []
    cols = 4
    col_w = (width - 48.0) / cols
    row_start_y = 60.0
    row_h = 44.0

    for idx, lang in enumerate(display_langs):
        c_idx = idx % cols
        r_idx = idx // cols
        
        lx = prog_x + c_idx * col_w
        ly = row_start_y + r_idx * row_h
        
        name_esc = escape_xml(lang.name)
        pct_str = f"{lang.percentage:.1f}%"
        size_str = format_bytes(lang.bytes)
        
        item_svg = f"""
        <g>
            <circle cx="{lx + 6:.1f}" cy="{ly + 10:.1f}" r="5" fill="{lang.color}" />
            <text x="{lx + 18:.1f}" y="{ly + 14:.1f}" fill="{theme.text_primary}" font-size="12" font-weight="600">{name_esc}</text>
            <text x="{lx + 18:.1f}" y="{ly + 30:.1f}" fill="{theme.text_secondary}" font-size="10">{pct_str} <tspan fill="{theme.text_muted}">({size_str})</tspan></text>
        </g>
        """
        legend_items.append(item_svg)

    body_content = f"""
    {progress_svg}
    <g>
        {"".join(legend_items)}
    </g>
    """

    title = "LANGUAGES // BYTE-WEIGHTED REPOSITORY CODEBASE"
    status = f"{len(display_langs)} COMPILED"

    card_content = render_terminal_card(
        width=width,
        height=height,
        title=title,
        theme=theme,
        body_content=body_content,
        status_tag=status
    )

    all_chars = "".join(set(
        title + status + "ONLINE" +
        "".join(l.name for l in display_langs) +
        "".join(format_bytes(l.bytes) for l in display_langs) +
        "0123456789%().KBMB/.:_ -ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    ))
    font_css = get_font_face_css(cfg.font_path, all_chars, cfg.font_family)

    svg_doc = create_svg_document(
        width=width,
        height=height,
        content=card_content,
        font_css=font_css
    )

    target_file = output_path or (cfg.output_dir / "languages.svg")
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if not target_file.exists() or target_file.read_text(encoding="utf-8") != svg_doc:
        target_file.write_text(svg_doc, encoding="utf-8")
        logger.info(f"Generated languages SVG: {target_file}")

    return svg_doc


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cfg = load_config()
    client = GitHubAPIClient(cfg)
    data = client.fetch_user_data()
    generate_languages_svg(data, cfg)
