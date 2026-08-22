# Typography & Font Subsetting

This directory contains the font assets used by the SVG generators.

## JetBrains Mono

- **Font Family**: JetBrains Mono
- **Author**: JetBrains s.r.o.
- **License**: SIL Open Font License 1.1 (see [`LICENSE`](LICENSE))
- **Repository**: https://github.com/JetBrains/JetBrainsMono

## Subsetting Mechanism

To keep generated SVG file sizes minimal (typically `< 25KB` instead of embedding full multi-megabyte fonts), `scripts/svg_utils.py` uses `fontTools.subset` to create a subset containing **only the exact glyphs required** for:
- ASCII ramp characters (` .`:-=+*cs#%@`)
- Numeric stats, dates, and metric labels
- Heading typography and box-drawing elements

The subsetted font is compressed using WOFF2 and embedded directly as base64 in SVG `<style>` tags.
