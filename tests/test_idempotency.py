"""Tests verifying strict idempotency and deterministic asset generation."""

import tempfile
from pathlib import Path

from scripts.config import Config
from scripts.generate_all import run_pipeline


def test_idempotency_and_zero_diff():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        cfg = Config(
            github_username="octocat",
            theme_name="dark",
            output_dir=tmp_path / "generated",
            headings_dir=tmp_path / "generated" / "headings"
        )
        
        # Run pipeline 1st time
        files_run1 = run_pipeline(cfg)
        snapshots_run1 = {}
        for k, p in files_run1.items():
            if p.is_file():
                snapshots_run1[str(p)] = p.read_text(encoding="utf-8")
            elif p.is_dir():
                for sub in p.glob("*.svg"):
                    snapshots_run1[str(sub)] = sub.read_text(encoding="utf-8")

        # Run pipeline 2nd time with identical input data
        files_run2 = run_pipeline(cfg)
        snapshots_run2 = {}
        for k, p in files_run2.items():
            if p.is_file():
                snapshots_run2[str(p)] = p.read_text(encoding="utf-8")
            elif p.is_dir():
                for sub in p.glob("*.svg"):
                    snapshots_run2[str(sub)] = sub.read_text(encoding="utf-8")

        # Assert every generated file is 100% byte-for-byte identical
        assert set(snapshots_run1.keys()) == set(snapshots_run2.keys())
        for path_str in snapshots_run1:
            assert snapshots_run1[path_str] == snapshots_run2[path_str], f"File {path_str} changed on second run!"
