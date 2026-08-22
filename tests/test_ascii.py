"""Tests for ASCII portrait processing and CV pipeline."""

import numpy as np
from PIL import Image

from scripts.config import Config
from scripts.generate_portrait import image_to_ascii_lines, remove_background_fallback


def test_ascii_dimensions_and_aspect_ratio():
    img = Image.new("L", (400, 500), 128)
    rows = image_to_ascii_lines(img, cols=80, row_ratio=0.48)
    assert len(rows) > 0
    assert len(rows[0]) <= 80


def test_ascii_ramp_mapping():
    grad = np.linspace(255, 0, 100, dtype=np.uint8)
    grad_img = Image.fromarray(np.tile(grad, (20, 1)))
    
    ramp = " .`:-=+*cs#%@"
    rows = image_to_ascii_lines(grad_img, cols=100, ramp=ramp, row_ratio=0.5)
    
    first_char = rows[0][0]
    last_char = rows[0][-1]
    assert first_char == ramp[0] or first_char == ramp[1]
    assert last_char == ramp[-1] or last_char == ramp[-2]


def test_grabcut_fallback():
    img = np.full((100, 100, 3), 200, dtype=np.uint8)
    img[30:70, 30:70] = [40, 40, 40]
    
    gray, alpha = remove_background_fallback(img)
    assert gray.shape == (100, 100)
    assert alpha.shape == (100, 100)
