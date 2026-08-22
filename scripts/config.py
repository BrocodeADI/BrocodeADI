"""Centralized configuration system for GitHub Profile Generator."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

# Base repository root directory
REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Theme:
    """Color theme specification for SVG cards and visual assets."""
    name: str
    bg: str
    card_bg: str
    border: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent: str
    accent_secondary: str
    # 5-level contribution scale (0 = none, 4 = highest intensity)
    contrib_levels: List[str] = field(default_factory=lambda: [
        "#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"
    ])
    # Language progress bar / chart palette
    chart_palette: List[str] = field(default_factory=lambda: [
        "#58a6ff", "#3fb950", "#d29922", "#f85149", "#bc8cff",
        "#79c0ff", "#56d364", "#e3b341", "#ff7b72", "#d2a8ff"
    ])


THEMES: Dict[str, Theme] = {
    "dark": Theme(
        name="dark",
        bg="#0d1117",
        card_bg="#161b22",
        border="#30363d",
        text_primary="#f0f6fc",
        text_secondary="#8b949e",
        text_muted="#484f58",
        accent="#58a6ff",
        accent_secondary="#3fb950",
        contrib_levels=["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
        chart_palette=["#58a6ff", "#3fb950", "#d29922", "#f85149", "#bc8cff", "#79c0ff", "#56d364"]
    ),
    "light": Theme(
        name="light",
        bg="#ffffff",
        card_bg="#f6f8fa",
        border="#d0d7de",
        text_primary="#1f2328",
        text_secondary="#656d76",
        text_muted="#8c959f",
        accent="#0969da",
        accent_secondary="#1a7f37",
        contrib_levels=["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
        chart_palette=["#0969da", "#1a7f37", "#9a6700", "#cf222e", "#8250df", "#0550ae", "#116329"]
    ),
    "matrix": Theme(
        name="matrix",
        bg="#040d06",
        card_bg="#08180c",
        border="#164e22",
        text_primary="#00ff66",
        text_secondary="#00bb44",
        text_muted="#006622",
        accent="#00ff66",
        accent_secondary="#33ff88",
        contrib_levels=["#091d0e", "#0e4420", "#008833", "#00cc4c", "#00ff66"],
        chart_palette=["#00ff66", "#33ff88", "#66ffaa", "#00cc4c", "#009933", "#88ffcc", "#006622"]
    ),
    "nord": Theme(
        name="nord",
        bg="#2e3440",
        card_bg="#3b4252",
        border="#4c566a",
        text_primary="#eceff4",
        text_secondary="#d8dee9",
        text_muted="#616e88",
        accent="#88c0d0",
        accent_secondary="#a3be8c",
        contrib_levels=["#3b4252", "#4c566a", "#5e81ac", "#81a1c1", "#88c0d0"],
        chart_palette=["#88c0d0", "#81a1c1", "#a3be8c", "#ebcb8b", "#b48ead", "#bf616a", "#d08770"]
    ),
    "dracula": Theme(
        name="dracula",
        bg="#282a36",
        card_bg="#21222c",
        border="#6272a4",
        text_primary="#f8f8f2",
        text_secondary="#bd93f9",
        text_muted="#6272a4",
        accent="#ff79c6",
        accent_secondary="#50fa7b",
        contrib_levels=["#21222c", "#343746", "#6272a4", "#bd93f9", "#ff79c6"],
        chart_palette=["#ff79c6", "#bd93f9", "#50fa7b", "#8be9fd", "#f1fa8c", "#ffb86c", "#ff5555"]
    ),
    "monokai": Theme(
        name="monokai",
        bg="#272822",
        card_bg="#1e1f1c",
        border="#49483e",
        text_primary="#f8f8f2",
        text_secondary="#a6e22e",
        text_muted="#75715e",
        accent="#66d9ef",
        accent_secondary="#fd971f",
        contrib_levels=["#1e1f1c", "#49483e", "#a6e22e", "#66d9ef", "#fd971f"],
        chart_palette=["#66d9ef", "#a6e22e", "#fd971f", "#f92672", "#ae81ff", "#e6db74", "#38c774"]
    ),
    "amber": Theme(
        name="amber",
        bg="#0f0b04",
        card_bg="#1c1407",
        border="#4a3410",
        text_primary="#ffb000",
        text_secondary="#d48800",
        text_muted="#7a4f00",
        accent="#ffb000",
        accent_secondary="#ffd066",
        contrib_levels=["#1a1205", "#4a3410", "#8a5f15", "#c78c20", "#ffb000"],
        chart_palette=["#ffb000", "#ffd066", "#e09000", "#ffa000", "#cc7a00", "#ffdf99", "#995c00"]
    )
}


@dataclass
class Config:
    """Master configuration class."""
    # Identity
    github_username: str = "octocat"
    display_name: str = "Developer"
    role_title: str = "Systems & AI Engineer"
    bio: str = "Crafting high-performance systems and intelligent algorithms."
    location: str = "San Francisco, CA"
    website: str = "https://github.com"
    
    # Credentials & API
    github_token: str = ""
    github_api_url: str = "https://api.github.com/graphql"
    
    # Portrait Processing
    portrait_path: Path = REPO_ROOT / "assets" / "portrait.jpg"
    ascii_width: int = 90
    ascii_ramp: str = " .`:-=+*cs#%@"
    gamma: float = 1.7
    contrast_clip_limit: float = 2.5
    contrast_tile_grid: tuple = (8, 8)
    bilateral_d: int = 9
    bilateral_sigma_color: float = 50.0
    bilateral_sigma_space: float = 50.0
    aspect_ratio: float = 0.52  # monospace char width / height ratio
    
    # Animation settings
    enable_animation: bool = True
    row_delay: float = 0.035  # seconds per row reveal
    animation_duration: float = 2.5  # total base duration
    
    # Visual Theme
    theme_name: str = "dark"
    theme: Theme = field(init=False)
    
    # Typography
    font_path: Path = REPO_ROOT / "fonts" / "JetBrainsMono-Regular.ttf"
    font_family: str = "JetBrainsMono"
    font_size: int = 12
    line_height: float = 14.5
    
    # Contribution data window
    contribution_days: int = 365
    
    # Output Directories
    output_dir: Path = REPO_ROOT / "generated"
    headings_dir: Path = REPO_ROOT / "generated" / "headings"
    
    def __post_init__(self) -> None:
        object.__setattr__(self, "theme", THEMES.get(self.theme_name, THEMES["dark"]))


def load_config() -> Config:
    """Load configuration from environment variables with sensible defaults."""
    theme_name = os.getenv("THEME", "dark").lower()
    if theme_name not in THEMES:
        theme_name = "dark"
        
    portrait_env = os.getenv("PORTRAIT_PATH")
    portrait_path = Path(portrait_env) if portrait_env else (REPO_ROOT / "assets" / "portrait.jpg")
    
    font_env = os.getenv("FONT_PATH")
    font_path = Path(font_env) if font_env else (REPO_ROOT / "fonts" / "JetBrainsMono-Regular.ttf")
    
    output_env = os.getenv("OUTPUT_DIR")
    output_dir = Path(output_env) if output_env else (REPO_ROOT / "generated")
    headings_dir = output_dir / "headings"
    
    return Config(
        github_username=os.getenv("GITHUB_USERNAME", "octocat"),
        display_name=os.getenv("DISPLAY_NAME", "Developer"),
        role_title=os.getenv("ROLE_TITLE", "Systems & AI Engineer"),
        bio=os.getenv("BIO", "Crafting high-performance systems and intelligent algorithms."),
        location=os.getenv("LOCATION", "San Francisco, CA"),
        website=os.getenv("WEBSITE", "https://github.com"),
        github_token=os.getenv("GITHUB_TOKEN", ""),
        github_api_url=os.getenv("GITHUB_API_URL", "https://api.github.com/graphql"),
        portrait_path=portrait_path,
        ascii_width=int(os.getenv("ASCII_WIDTH", "90")),
        ascii_ramp=os.getenv("ASCII_RAMP", " .`:-=+*cs#%@"),
        gamma=float(os.getenv("GAMMA", "1.7")),
        contrast_clip_limit=float(os.getenv("CONTRAST_CLIP_LIMIT", "2.5")),
        aspect_ratio=float(os.getenv("ASPECT_RATIO", "0.52")),
        enable_animation=os.getenv("ENABLE_ANIMATION", "true").lower() in ("true", "1", "yes"),
        row_delay=float(os.getenv("ROW_DELAY", "0.035")),
        animation_duration=float(os.getenv("ANIMATION_DURATION", "2.5")),
        theme_name=theme_name,
        font_path=font_path,
        font_family=os.getenv("FONT_FAMILY", "JetBrainsMono"),
        font_size=int(os.getenv("FONT_SIZE", "12")),
        contribution_days=int(os.getenv("CONTRIBUTION_DAYS", "365")),
        output_dir=output_dir,
        headings_dir=headings_dir
    )
