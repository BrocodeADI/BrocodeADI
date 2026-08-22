"""Generate 52-Week Contribution Heat Calendar SVG Card."""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import List, Optional

from .config import Config, load_config
from .github_api import GitHubAPIClient, GitHubUserData
from .svg_utils import (
    create_svg_document,
    escape_xml,
    get_font_face_css,
    render_terminal_card,
)

logger = logging.getLogger(__name__)


def get_contribution_level(count: int) -> int:
    """Map raw contribution count to 0-4 intensity level."""
    if count <= 0:
        return 0
    elif count <= 2:
        return 1
    elif count <= 5:
        return 2
    elif count <= 9:
        return 3
    else:
        return 4


def generate_year_svg(
    user_data: GitHubUserData,
    config: Optional[Config] = None,
    output_path: Optional[Path] = None
) -> str:
    """Generate 52-week contribution heatmap matrix SVG card."""
    cfg = config or load_config()
    theme = cfg.theme
    weeks = user_data.weeks

    width = 940
    height = 215

    # Grid layout geometry
    grid_start_x = 48.0
    grid_start_y = 28.0
    cell_size = 11.0
    cell_gap = 3.5
    pitch = cell_size + cell_gap  # 14.5 px

    # Day labels (Mon, Wed, Fri) -> weekdays 1, 3, 5
    day_labels = [
        (1, "Mon"),
        (3, "Wed"),
        (5, "Fri")
    ]
    day_label_elements: List[str] = []
    for day_idx, label in day_labels:
        ly = grid_start_y + day_idx * pitch + 9.0
        day_label_elements.append(
            f'<text x="20" y="{ly:.1f}" fill="{theme.text_muted}" font-size="9" font-weight="500">{label}</text>'
        )

    # Build heatmap cells and month headers
    cells: List[str] = []
    month_labels: List[str] = []
    last_month = None

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    for w_idx, week in enumerate(weeks):
        # Determine month for header
        if week.days:
            first_day_date = week.days[0].date
            if first_day_date:
                try:
                    dt = datetime.date.fromisoformat(first_day_date)
                    if dt.month != last_month and dt.day <= 14:
                        month_str = month_names[dt.month - 1]
                        mx = grid_start_x + w_idx * pitch
                        month_labels.append(
                            f'<text x="{mx:.1f}" y="{grid_start_y - 10:.1f}" fill="{theme.text_secondary}" font-size="10" font-weight="600">{month_str}</text>'
                        )
                        last_month = dt.month
                except ValueError:
                    pass

        # Draw 7 days in week
        for d_idx, day in enumerate(week.days):
            cx = grid_start_x + w_idx * pitch
            cy = grid_start_y + d_idx * pitch
            
            level = get_contribution_level(day.count)
            color = theme.contrib_levels[level]
            
            cells.append(
                f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cell_size:.1f}" height="{cell_size:.1f}" rx="2" fill="{color}">'
                f'<title>{day.date}: {day.count} contributions</title>'
                f'</rect>'
            )

    # Footer legend & stats
    legend_y = grid_start_y + 7 * pitch + 18.0
    legend_blocks: List[str] = []
    leg_start_x = width - 180.0
    
    legend_blocks.append(
        f'<text x="{leg_start_x - 30:.1f}" y="{legend_y + 9.0:.1f}" fill="{theme.text_muted}" font-size="10">Less</text>'
    )
    for lvl, col in enumerate(theme.contrib_levels):
        bx = leg_start_x + lvl * (cell_size + 3.0)
        legend_blocks.append(
            f'<rect x="{bx:.1f}" y="{legend_y:.1f}" width="{cell_size:.1f}" height="{cell_size:.1f}" rx="2" fill="{col}" />'
        )
    legend_blocks.append(
        f'<text x="{leg_start_x + 5 * (cell_size + 3.0) + 4:.1f}" y="{legend_y + 9.0:.1f}" fill="{theme.text_muted}" font-size="10">More</text>'
    )

    summary_text = (
        f'Activity: <tspan fill="{theme.accent}" font-weight="700">{user_data.total_contributions:,}</tspan> '
        f'contributions in the last {cfg.contribution_days} UTC days'
    )
    footer_summary = f'<text x="24" y="{legend_y + 9.0:.1f}" fill="{theme.text_secondary}" font-size="11">{summary_text}</text>'

    body_content = f"""
    <g>
        {"".join(day_label_elements)}
        {"".join(month_labels)}
        {"".join(cells)}
        {footer_summary}
        {"".join(legend_blocks)}
    </g>
    """

    title = "ACTIVITY_MATRIX // 52-WEEK TEMPORAL HEATMAP"
    status = f"{len(weeks)} WEEKS"

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
        "JanFebMarAprMayJunJulAugSepOctNovDecMonWedFriLessMoreActivity: contributions in the last UTC days" +
        f"{user_data.total_contributions:,}{cfg.contribution_days}{len(weeks)}" +
        "0123456789/.:_ -ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    ))
    font_css = get_font_face_css(cfg.font_path, all_chars, cfg.font_family)

    svg_doc = create_svg_document(
        width=width,
        height=height,
        content=card_content,
        font_css=font_css
    )

    target_file = output_path or (cfg.output_dir / "year.svg")
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if not target_file.exists() or target_file.read_text(encoding="utf-8") != svg_doc:
        target_file.write_text(svg_doc, encoding="utf-8")
        logger.info(f"Generated year heatmap SVG: {target_file}")

    return svg_doc


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cfg = load_config()
    client = GitHubAPIClient(cfg)
    data = client.fetch_user_data()
    generate_year_svg(data, cfg)
