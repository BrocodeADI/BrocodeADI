"""Tests for centralized configuration system."""

import os
from unittest.mock import patch

from scripts.config import THEMES, Config, load_config


def test_default_config():
    cfg = Config()
    assert cfg.github_username == "octocat"
    assert cfg.ascii_width == 90
    assert cfg.gamma == 1.7
    assert cfg.theme_name == "dark"
    assert cfg.theme.name == "dark"
    assert len(cfg.theme.contrib_levels) == 5


def test_theme_lookup():
    for name in ["dark", "light", "matrix", "nord", "dracula", "monokai", "amber"]:
        cfg = Config(theme_name=name)
        cfg.__post_init__()
        assert cfg.theme.name == name


def test_env_var_overrides():
    env = {
        "GITHUB_USERNAME": "testuser",
        "THEME": "nord",
        "ASCII_WIDTH": "100",
        "GAMMA": "2.2",
        "DISPLAY_NAME": "Alice"
    }
    with patch.dict(os.environ, env, clear=False):
        cfg = load_config()
        assert cfg.github_username == "testuser"
        assert cfg.theme_name == "nord"
        assert cfg.theme.name == "nord"
        assert cfg.ascii_width == 100
        assert cfg.gamma == 2.2
        assert cfg.display_name == "Alice"
