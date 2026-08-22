"""Generate GitHub Contribution Statistics SVG Card."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .config import Config, load_config
from .github_api import GitHubAPIClient, GitHubUserData
from .svg_utils import (
    create_svg_document,
    escape_xml,
    get_font_face_css,
    render_stat_box,
    render_terminal_card,
)

logger = logging.getLogger(__name__)


def generate_stats_svg(
    user_data: GitHubUserData,
    config: Optional[Config] = None,
    output_path: Optional[Path] = None
) -> str:
    """Generate terminal-style statistics SVG card."""
    cfg = config or load_config()
    theme = cfg.theme

    width = 460
    height = 240

    # 4 metric boxes in a 2x2 grid
    box_w = 200.0
    box_h = 76.0
    left_x = 20.0
    right_x = 240.0
    top_y = 16.0
    bot_y = 104.0

    stat_boxes = [
        render_stat_box(
            x=left_x,
            y=top_y,
            width=box_w,
            height=box_h,
            label="TOTAL CONTRIBUTIONS",
            value=f"{user_data.total_contributions:,}",
            theme=theme,
            subtext=f"Past {cfg.contribution_days} UTC Days",
            accent_color=theme.accent
        ),
        render_stat_box(
            x=right_x,
            y=top_y,
            width=box_w,
            height=box_h,
            label="TOTAL COMMITS",
            value=f"{user_data.total_commits:,}",
            theme=theme,
            subtext="Authored Commits",
            accent_color=theme.accent_secondary
        ),
        render_stat_box(
            x=left_x,
            y=bot_y,
            width=box_w,
            height=box_h,
            label="PULL REQUESTS & ISSUES",
            value=f"{user_data.total_prs + user_data.total_issues:,}",
            theme=theme,
            subtext=f"{user_data.total_prs:,} PRs • {user_data.total_issues:,} Issues",
            accent_color="#d29922"
        ),
        render_stat_box(
            x=right_x,
            y=bot_y,
            width=box_w,
            height=box_h,
            label="STARS & FORKS",
            value=f"{user_data.total_stars:,} ★",
            theme=theme,
            subtext=f"{user_data.total_forks:,} Forks • {user_data.public_repos_count} Public Repos",
            accent_color="#bc8cff"
        ),
    ]

    body_content = "\n".join(stat_boxes)
    title = f"METRICS // @{user_data.username.upper()}"
    status = "TELEMETRY"

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
        "TOTAL CONTRIBUTIONS COMMITS PULL REQUESTS ISSUES STARS FORKS" +
        f"{user_data.total_contributions:,}{user_data.total_commits:,}{user_data.total_prs:,}{user_data.total_issues:,}{user_data.total_stars:,}{user_data.total_forks:,}{user_data.public_repos_count}" +
        "★•/:., 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    ))
    font_css = get_font_face_css(cfg.font_path, all_chars, cfg.font_family)

    svg_doc = create_svg_document(
        width=width,
        height=height,
        content=card_content,
        font_css=font_css
    )

    target_file = output_path or (cfg.output_dir / "stats.svg")
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if not target_file.exists() or target_file.read_text(encoding="utf-8") != svg_doc:
        target_file.write_text(svg_doc, encoding="utf-8")
        logger.info(f"Generated stats SVG: {target_file}")

    return svg_doc


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cfg = load_config()
    client = GitHubAPIClient(cfg)
    data = client.fetch_user_data()
    generate_stats_svg(data, cfg)
