"""Generate a single clean stats.svg matching andriidrok1's aesthetic exactly.

His stats.svg is a single-card, borderless, monospace SVG with:
- Light mode: muted grey text (#6e7681)
- Dark mode: off-white (#c9d1d9)
- No terminal boxes, no accent colour borders
- Clean labelled rows of data
- JetBrains Mono embedded subset
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Optional

from .config import Config, load_config
from .github_api import GitHubAPIClient, GitHubUserData
from .svg_utils import get_font_face_css, escape_xml

logger = logging.getLogger(__name__)

FG_LIGHT = "#6e7681"
FG_DARK = "#c9d1d9"
DIM_LIGHT = "#8b949e"
DIM_DARK = "#8b949e"
FAMILY = "JBMono,ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
FONT_SIZE = 13
LINE_H = 22
PAD_X = 28
PAD_Y = 26


def _row(y: float, label: str, value: str) -> str:
    """Render a single label: value row."""
    return (
        f'<text x="{PAD_X}" y="{y:.0f}" class="dim" font-size="{FONT_SIZE}">'
        f'{escape_xml(label)}</text>'
        f'<text x="330" y="{y:.0f}" class="fg" font-size="{FONT_SIZE}" font-weight="600">'
        f'{escape_xml(value)}</text>'
    )


def generate_stats_svg(
    user_data: GitHubUserData,
    config: Optional[Config] = None,
    output_path: Optional[Path] = None
) -> str:
    """Generate a clean, minimal stats card matching andriidrok1."""
    cfg = config or load_config()

    rows = [
        ("contributions (last year)", f"{user_data.total_contributions:,}"),
        ("commits authored",          f"{user_data.total_commits:,}"),
        ("pull requests",             f"{user_data.total_prs:,}"),
        ("issues opened",             f"{user_data.total_issues:,}"),
        ("stars earned",              f"{user_data.total_stars:,}"),
        ("public repos",              f"{user_data.public_repos_count:,}"),
    ]

    width = 620
    height = PAD_Y * 2 + len(rows) * LINE_H + 4

    row_svgs = []
    for i, (label, value) in enumerate(rows):
        y = PAD_Y + i * LINE_H + FONT_SIZE
        row_svgs.append(_row(y, label, value))

    body = "\n".join(row_svgs)

    all_chars = "".join(set(
        "contributions last year commits authored pull requests issues opened stars earned public repos"
        "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ(),:. "
        + "".join(v for _, v in rows)
    ))
    font_css = get_font_face_css(cfg.font_path, all_chars, "JBMono")

    style = f"""
    {font_css}
    .fg  {{ fill: {FG_LIGHT}; }}
    .dim {{ fill: {DIM_LIGHT}; }}
    @media (prefers-color-scheme: dark) {{
        .fg  {{ fill: {FG_DARK}; }}
        .dim {{ fill: {DIM_DARK}; }}
    }}
    """

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" fill="none" '
        f'font-family="{FAMILY}">'
        f'<style>{style}</style>'
        f'{body}'
        f'</svg>'
    )

    target_file = output_path or (cfg.output_dir / "stats.svg")
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if not target_file.exists() or target_file.read_text(encoding="utf-8") != svg:
        target_file.write_text(svg, encoding="utf-8")
        logger.info(f"Generated stats SVG: {target_file}")

    return svg


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cfg = load_config()
    client = GitHubAPIClient(cfg)
    data = client.fetch_user_data()
    generate_stats_svg(data, cfg)
