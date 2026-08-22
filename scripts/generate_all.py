"""Master generator script for all GitHub Profile visual assets."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .config import THEMES, Config, load_config
from .generate_headings import generate_all_headings
from .generate_languages import generate_languages_svg
from .generate_portrait import generate_portrait_svg
from .generate_stats import generate_stats_svg
from .generate_streak import generate_streak_svg
from .generate_year import generate_year_svg
from .github_api import GitHubAPIClient, GitHubUserData

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("generate_all")


def parse_args() -> argparse.Namespace:
    """Parse CLI options for manual and automated profile generation."""
    parser = argparse.ArgumentParser(
        description="Generate GitHub Profile visual assets (ASCII portrait, stats, streaks, languages, calendar)."
    )
    parser.add_argument(
        "--username", "-u",
        type=str,
        help="GitHub username (overrides GITHUB_USERNAME env var)"
    )
    parser.add_argument(
        "--theme", "-t",
        type=str,
        choices=list(THEMES.keys()),
        help=f"Color theme ({', '.join(THEMES.keys())})"
    )
    parser.add_argument(
        "--token",
        type=str,
        help="GitHub GraphQL API Token (overrides GITHUB_TOKEN env var)"
    )
    parser.add_argument(
        "--portrait", "-p",
        type=str,
        help="Path to source portrait image"
    )
    parser.add_argument(
        "--width", "-w",
        type=int,
        help="ASCII portrait character width (default: 90)"
    )
    parser.add_argument(
        "--gamma", "-g",
        type=float,
        help="ASCII brightness gamma exponent (default: 1.7)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        help="Target output directory for generated assets"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force overwrite of generated assets even if identical"
    )
    return parser.parse_args()


def build_config_from_args(args: argparse.Namespace) -> Config:
    """Apply CLI overrides on top of base configuration."""
    cfg = load_config()
    
    if args.username:
        cfg.github_username = args.username
    if args.token:
        cfg.github_token = args.token
    if args.theme:
        cfg.theme_name = args.theme
        cfg.__post_init__()
    if args.portrait:
        cfg.portrait_path = Path(args.portrait)
    if args.width:
        cfg.ascii_width = args.width
    if args.gamma:
        cfg.gamma = args.gamma
    if args.output_dir:
        cfg.output_dir = Path(args.output_dir)
        cfg.headings_dir = cfg.output_dir / "headings"
        
    return cfg


def run_pipeline(config: Config) -> Dict[str, Path]:
    """
    Execute complete asset generation pipeline.
    Returns mapping of asset name -> file path.
    """
    logger.info("==================================================")
    logger.info("  GITHUB PROFILE VISUAL ASSET GENERATOR PIPELINE  ")
    logger.info("==================================================")
    logger.info(f"Target User:     @{config.github_username}")
    logger.info(f"Visual Theme:    {config.theme_name}")
    logger.info(f"ASCII Width:     {config.ascii_width} columns")
    logger.info(f"Gamma Exponent:  {config.gamma}")
    logger.info(f"Output Path:     {config.output_dir.resolve()}")
    logger.info("--------------------------------------------------")

    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.headings_dir.mkdir(parents=True, exist_ok=True)

    generated_files: Dict[str, Path] = {}

    # 1. Fetch GitHub data (GraphQL API or deterministic mock fallback)
    logger.info("Phase 1/5: Querying GitHub GraphQL telemetry...")
    client = GitHubAPIClient(config)
    user_data: GitHubUserData = client.fetch_user_data()
    logger.info(
        f"Retrieved {user_data.total_contributions:,} contributions across {len(user_data.weeks)} weeks. "
        f"Current streak: {user_data.streak.current_streak} days, Longest: {user_data.streak.longest_streak} days."
    )

    # 2. Generate ASCII Portrait SVG
    logger.info("Phase 2/5: Processing portrait CV pipeline & generating animated SVG...")
    portrait_target = config.output_dir / "portrait.svg"
    generate_portrait_svg(config=config, output_path=portrait_target)
    generated_files["portrait"] = portrait_target

    # 3. Generate Statistics and Streak SVGs
    logger.info("Phase 3/5: Rendering metric telemetry cards (stats.svg, streak.svg)...")
    stats_target = config.output_dir / "stats.svg"
    generate_stats_svg(user_data=user_data, config=config, output_path=stats_target)
    generated_files["stats"] = stats_target

    streak_target = config.output_dir / "streak.svg"
    generate_streak_svg(user_data=user_data, config=config, output_path=streak_target)
    generated_files["streak"] = streak_target

    # 4. Generate Languages and Year Heatmap SVGs
    logger.info("Phase 4/5: Rendering repository languages & 52-week calendar matrix...")
    lang_target = config.output_dir / "languages.svg"
    generate_languages_svg(user_data=user_data, config=config, output_path=lang_target)
    generated_files["languages"] = lang_target

    year_target = config.output_dir / "year.svg"
    generate_year_svg(user_data=user_data, config=config, output_path=year_target)
    generated_files["year"] = year_target

    # 5. Generate Section Typography Headings
    logger.info("Phase 5/5: Generating custom SVG typography section banners...")
    generate_all_headings(config=config, output_dir=config.headings_dir)
    generated_files["headings"] = config.headings_dir

    logger.info("==================================================")
    logger.info("  PIPELINE COMPLETE: All visual assets up to date ")
    logger.info("==================================================")

    return generated_files


def main() -> None:
    args = parse_args()
    cfg = build_config_from_args(args)
    try:
        run_pipeline(cfg)
    except Exception as e:
        logger.error(f"Generation pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
