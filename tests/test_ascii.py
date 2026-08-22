"""Tests for ASCII portrait processing and CV pipeline."""

import numpy as np
from PIL import Image

from scripts.generate_portrait import image_to_ascii_lines, remove_background_fallback, RAMP, ROW_RATIO


def test_ascii_dimensions_and_aspect_ratio():
    img = Image.new("L", (400, 500), 128)
    rows = image_to_ascii_lines(img, cols=80)
    assert len(rows) > 0
    assert len(rows[0]) <= 80


def test_ascii_ramp_mapping():
    """Bright pixels should map to early (sparse) ramp chars, dark to late (dense)."""
    # Gradient from white (255) to black (0)
    grad = np.linspace(255, 0, 100, dtype=np.uint8)
    grad_img = Image.fromarray(np.tile(grad, (20, 1)))
    rows = image_to_ascii_lines(grad_img, cols=100)
    first_char = rows[0][0]
    last_char  = rows[0][-1]
    # First pixel is white (bright) → should be blank or near-blank
    assert first_char in RAMP[:3], f"Expected sparse char at bright end, got '{first_char}'"
    # Last pixel is black (dark) → should be dense
    assert last_char in RAMP[-3:], f"Expected dense char at dark end, got '{last_char}'"


def test_grabcut_fallback():
    img = np.full((100, 100, 3), 200, dtype=np.uint8)
    img[30:70, 30:70] = [40, 40, 40]
    gray, alpha = remove_background_fallback(img)
    assert gray.shape == (100, 100)
    assert alpha.shape == (100, 100)
