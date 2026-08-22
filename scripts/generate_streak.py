"""Generate GitHub Contribution Streak SVG Card."""

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
    render_progress_bar,
    render_stat_box,
    render_terminal_card,
)

logger = logging.getLogger(__name__)


def generate_streak_svg(
    user_data: GitHubUserData,
    config: Optional[Config] = None,
    output_path: Optional[Path] = None
) -> str:
    """Generate terminal-style streak metrics SVG card."""
    cfg = config or load_config()
    theme = cfg.theme
    streak = user_data.streak

    width = 460
    height = 240

    box_w = 200.0
    box_h = 76.0
    left_x = 20.0
    right_x = 240.0
    top_y = 16.0
    bot_y = 104.0

    current_sub = (
        f"{streak.current_start} → {streak.current_end}"
        if streak.current_start and streak.current_end
        else "No active streak"
    )
    longest_sub = (
        f"{streak.longest_start} → {streak.longest_end}"
        if streak.longest_start and streak.longest_end
        else "No streak recorded"
    )

    act_pct = (
        (streak.total_active_days / streak.total_days * 100.0)
        if streak.total_days > 0
        else 0.0
    )

    stat_boxes = [
        render_stat_box(
            x=left_x,
            y=top_y,
            width=box_w,
            height=box_h,
            label="CURRENT STREAK",
            value=f"{streak.current_streak} DAYS",
            theme=theme,
            subtext=current_sub,
            accent_color=theme.accent_secondary if streak.current_streak > 0 else theme.text_muted
        ),
        render_stat_box(
            x=right_x,
            y=top_y,
            width=box_w,
            height=box_h,
            label="LONGEST STREAK",
            value=f"{streak.longest_streak} DAYS",
            theme=theme,
            subtext=longest_sub,
            accent_color=theme.accent
        ),
        render_stat_box(
            x=left_x,
            y=bot_y,
            width=box_w,
            height=box_h,
            label="ACTIVE DAYS",
            value=f"{streak.total_active_days} / {streak.total_days}",
            theme=theme,
            subtext=f"{act_pct:.1f}% Annual Consistency",
            accent_color="#e3b341"
        ),
        render_stat_box(
            x=right_x,
            y=bot_y,
            width=box_w,
            height=box_h,
            label="STREAK STATUS",
            value="ACTIVE 🔥" if streak.current_streak > 0 else "IDLE ❄",
            theme=theme,
            subtext=f"Total: {user_data.total_contributions:,} Events",
            accent_color=theme.accent_secondary if streak.current_streak > 0 else theme.text_muted
        ),
    ]

    body_content = "\n".join(stat_boxes)
    title = "STREAK_ENGINE // ACTIVITY CADENCE"
    status = "RECORD"

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
        "CURRENT STREAK LONGEST ACTIVE DAYS STATUS RECORD ACTIVE IDLE DAYS" +
        f"{streak.current_streak}{streak.longest_streak}{streak.total_active_days}{streak.total_days}{act_pct:.1f}{user_data.total_contributions:,}" +
        current_sub + longest_sub +
        "🔥❄•→/:., 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz%"
    ))
    font_css = get_font_face_css(cfg.font_path, all_chars, cfg.font_family)

    svg_doc = create_svg_document(
        width=width,
        height=height,
        content=card_content,
        font_css=font_css
    )

    target_file = output_path or (cfg.output_dir / "streak.svg")
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if not target_file.exists() or target_file.read_text(encoding="utf-8") != svg_doc:
        target_file.write_text(svg_doc, encoding="utf-8")
        logger.info(f"Generated streak SVG: {target_file}")

    return svg_doc


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cfg = load_config()
    client = GitHubAPIClient(cfg)
    data = client.fetch_user_data()
    generate_streak_svg(data, cfg)
