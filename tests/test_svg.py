"""Tests for SVG generation, font subsetting, and terminal UI components."""

from pathlib import Path

from scripts.config import Config, THEMES
from scripts.svg_utils import (
    create_svg_document,
    escape_xml,
    get_font_face_css,
    render_progress_bar,
    render_stat_box,
    render_terminal_card,
    subset_font_to_base64,
)


def test_escape_xml():
    assert escape_xml("<hello & 'world'>") == "&lt;hello &amp; &#x27;world&#x27;&gt;"


def test_font_subsetting_and_base64():
    font_path = Path("fonts/JetBrainsMono-Regular.ttf")
    if font_path.exists():
        b64 = subset_font_to_base64(font_path, "0123456789ABCDEF")
        assert len(b64) > 100
        css = get_font_face_css(font_path, "0123456789ABCDEF")
        assert "@font-face" in css
        assert "font-family: 'JetBrainsMono'" in css


def test_render_terminal_card():
    theme = THEMES["dark"]
    card = render_terminal_card(
        width=400,
        height=300,
        title="TEST CARD",
        theme=theme,
        body_content="<text>Hello</text>"
    )
    assert '<rect x="0.5" y="0.5"' in card
    assert "TEST CARD" in card
    assert theme.card_bg in card
    assert "<circle" in card  # control dots


def test_render_progress_bar():
    segments = [(0.6, "#3572A5"), (0.4, "#dea584")]
    bar = render_progress_bar(10, 20, 200, 10, segments)
    assert "clipPath" in bar
    assert "#3572A5" in bar
    assert "#dea584" in bar


def test_svg_document_structure():
    doc = create_svg_document(
        width=500,
        height=300,
        content="<circle cx='50' cy='50' r='20' fill='red' />"
    )
    assert doc.startswith("<svg xmlns=\"http://www.w3.org/2000/svg\"")
    assert doc.endswith("</svg>")
    assert 'viewBox="0 0 500 300"' in doc
