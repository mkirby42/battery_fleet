from pathlib import Path


def test_notebook_present():
    text = Path("analysis/compare.ipynb").read_text()
    assert "compare_runs" in text
