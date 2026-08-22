"""Generate section header SVGs and a pinned-repos card — andriidrok1 style.

Produces:
  hd-about.svg   — small bold heading, like andriidrok1's divider headers
  hd-projects.svg — heading for the pinned repos section
  about.svg       — the actual about text block (bio + orgs)
  projects.svg    — the pinned repos list
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from .config import Config, load_config
from .github_api import GitHubAPIClient, GitHubUserData, PinnedRepo, OrgInfo
from .svg_utils import get_font_face_css, escape_xml

logger = logging.getLogger(__name__)

FAMILY   = "JBMono,ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
FG_LIGHT = "#6e7681"
FG_DARK  = "#c9d1d9"
HL_LIGHT = "#0d1117"   # near-black heading on light
HL_DARK  = "#e6edf3"   # near-white heading on dark
DIM_LIGHT = "#8b949e"
DIM_DARK  = "#8b949e"
W        = 620


def _style(font_css: str) -> str:
    return f"""
    {font_css}
    .h  {{ fill: {HL_LIGHT}; font-weight: 600; }}
    .fg {{ fill: {FG_LIGHT}; }}
    .dim{{ fill: {DIM_LIGHT}; }}
    @media (prefers-color-scheme: dark) {{
        .h  {{ fill: {HL_DARK}; }}
        .fg {{ fill: {FG_DARK}; }}
        .dim{{ fill: {DIM_DARK}; }}
    }}
    """


def _svg(width: int, height: int, style: str, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" fill="none" font-family="{FAMILY}">'
        f'<style>{style}</style>'
        f'{body}'
        f'</svg>'
    )


def _heading_svg(label: str, font_css: str) -> str:
    """Same tiny bold label as andriidrok1's hd-about.svg / hd-stack.svg."""
    return _svg(W, 26, _style(font_css),
        f'<text x="0" y="19" class="h" font-size="13">{escape_xml(label)}</text>'
    )


def generate_section_headers(
    config: Optional[Config] = None,
    output_dir: Optional[Path] = None,
) -> None:
    """Emit hd-about.svg and hd-projects.svg heading banners."""
    cfg     = config or load_config()
    out_dir = output_dir or cfg.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    all_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ."
    font_css  = get_font_face_css(cfg.font_path, all_chars, "JBMono")

    for fname, label in [
        ("hd-about.svg",    "about."),
        ("hd-projects.svg", "projects."),
        ("hd-stack.svg",    "stack."),
    ]:
        svg = _heading_svg(label, font_css)
        p   = out_dir / fname
        if not p.exists() or p.read_text("utf-8") != svg:
            p.write_text(svg, "utf-8")
            logger.info(f"Generated {fname}")


def generate_about_svg(
    user_data: GitHubUserData,
    config: Optional[Config] = None,
    output_path: Optional[Path] = None,
) -> str:
    """Bio text + orgs list — displayed below hd-about.svg heading."""
    cfg = config or load_config()

    lines: List[str] = [
        "Engineering undergrad.  Cybersecurity · Game Dev · AI.",
        "Building things that break boundaries — one commit at a time.",
    ]

    orgs = user_data.organizations
    if orgs:
        org_names = " · ".join(o.name or o.login for o in orgs[:6])
        lines.append("")
        lines.append(f"member of  {org_names}")

    FONT_SIZE = 13
    LINE_H    = 22
    PAD_X     = 0
    PAD_Y     = 6
    height    = PAD_Y * 2 + len(lines) * LINE_H + 4

    all_chars = "".join(set("".join(lines) + "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789·. "))
    font_css  = get_font_face_css(cfg.font_path, all_chars, "JBMono")

    rows = []
    for i, line in enumerate(lines):
        y = PAD_Y + i * LINE_H + FONT_SIZE
        cls = "dim" if (line == "" or line.startswith("member")) else "fg"
        rows.append(
            f'<text x="{PAD_X}" y="{y}" class="{cls}" font-size="{FONT_SIZE}">'
            f'{escape_xml(line)}</text>'
        )

    svg = _svg(W, height, _style(font_css), "\n".join(rows))

    target = output_path or (cfg.output_dir / "about.svg")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.read_text("utf-8") != svg:
        target.write_text(svg, "utf-8")
        logger.info(f"Generated about.svg")
    return svg


def generate_projects_svg(
    user_data: GitHubUserData,
    config: Optional[Config] = None,
    output_path: Optional[Path] = None,
) -> str:
    """Pinned repos list — displayed below hd-projects.svg heading.
    Falls back to top-starred repos if no pinned items."""
    cfg = config or load_config()

    repos = user_data.pinned_repos
    # If no pinned repos, skip (don't emit an empty card)
    if not repos:
        return ""

    FONT_SIZE = 13
    LINE_H    = 32
    PAD_Y     = 6
    height    = PAD_Y * 2 + len(repos) * LINE_H + 4

    all_chars = "".join(set(
        "".join(r.name + r.description + r.language for r in repos)
        + "★ · ()abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    ))
    font_css = get_font_face_css(cfg.font_path, all_chars, "JBMono")

    rows = []
    for i, repo in enumerate(repos):
        y_name = PAD_Y + i * LINE_H + FONT_SIZE
        y_desc = y_name + FONT_SIZE + 3
        lang   = f"  {repo.language}" if repo.language else ""
        stars  = f"  ★ {repo.stars}" if repo.stars else ""
        meta   = escape_xml(f"{lang}{stars}".strip(" ·"))
        name   = escape_xml(repo.name)
        desc   = escape_xml(repo.description[:72] + ("…" if len(repo.description) > 72 else ""))

        rows.append(
            f'<text x="0" y="{y_name}" class="h" font-size="{FONT_SIZE}" font-weight="600">'
            f'{name}</text>'
            f'<text x="200" y="{y_name}" class="dim" font-size="{FONT_SIZE - 1}">'
            f'{meta}</text>'
        )
        if desc:
            rows.append(
                f'<text x="0" y="{y_desc}" class="fg" font-size="{FONT_SIZE - 1}">'
                f'{desc}</text>'
            )

    svg = _svg(W, height, _style(font_css), "\n".join(rows))

    target = output_path or (cfg.output_dir / "projects.svg")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.read_text("utf-8") != svg:
        target.write_text(svg, "utf-8")
        logger.info(f"Generated projects.svg")
    return svg


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cfg    = load_config()
    client = GitHubAPIClient(cfg)
    data   = client.fetch_user_data()
    generate_section_headers(cfg)
    generate_about_svg(data, cfg)
    generate_projects_svg(data, cfg)
