from pathlib import Path

from battery_fleet.diagram import mermaid_er, mermaid_planes, render_markdown
from battery_fleet.types import Location, Tick


def test_er_lists_fields_from_types():
    text = mermaid_er()
    for name in Location.__dataclass_fields__:
        assert name in text
    for name in Tick.__dataclass_fields__:
        assert name in text


def test_er_draws_install_and_grid_edges():
    text = mermaid_er()
    assert "Install" in text
    assert "Location ||--o{ Install" in text or "Install }o--|| Location" in text
    assert "Substation ||--o{ Location" in text or "Location }o--|| Substation" in text


def test_planes_are_four_subgraphs():
    text = mermaid_planes()
    for label in ("World pieces", "Reality", "Time", "Judgment"):
        assert label in text
    assert "Location" in text
    assert "Tick" in text
    assert "RunCard" in text
    assert "Scoreboard" in text


def test_checked_in_view_matches_types():
    path = Path(__file__).resolve().parents[1] / "battery_fleet" / "data-model.md"
    assert path.read_text() == render_markdown()
