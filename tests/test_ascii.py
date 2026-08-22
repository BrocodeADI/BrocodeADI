"""Tests for ASCII portrait processing and CV pipeline."""

import numpy as np

from scripts.config import Config
from scripts.generate_portrait import image_to_ascii, remove_background_fallback


def test_ascii_dimensions_and_aspect_ratio():
    # Synthetic test image 400x500
    img = np.full((500, 400, 3), 128, dtype=np.uint8)
    
    cfg = Config(ascii_width=80, aspect_ratio=0.52)
    rows, cols, h = image_to_ascii(img, cfg, invert=False)
    
    assert cols == 80
    # Expected height: int((500/400) * 80 * 0.52) = int(1.25 * 80 * 0.52) = 52
    assert len(rows) == 52
    assert all(len(r) == 80 for r in rows)


def test_ascii_ramp_mapping_and_gamma():
    # Gradient image from 0 to 255
    grad = np.linspace(0, 255, 100, dtype=np.uint8)
    grad_img = np.tile(grad, (20, 1))
    grad_bgr = np.stack([grad_img, grad_img, grad_img], axis=-1)
    
    ramp = " .`:-=+*cs#%@"
    cfg = Config(ascii_width=100, ascii_ramp=ramp, gamma=1.0, aspect_ratio=0.5)
    rows, cols, h = image_to_ascii(grad_bgr, cfg, invert=False)
    
    # Check that first character maps to lowest ramp and last maps to highest ramp
    first_char = rows[0][0]
    last_char = rows[0][-1]
    assert first_char == ramp[0] or first_char == ramp[1]
    assert last_char == ramp[-1] or last_char == ramp[-2]


def test_grabcut_fallback():
    img = np.full((100, 100, 3), 200, dtype=np.uint8)
    # Add a dark center square (subject)
    img[30:70, 30:70] = [40, 40, 40]
    
    result = remove_background_fallback(img)
    assert result.shape == (100, 100, 3)
    assert result.dtype == np.uint8
