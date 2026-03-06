"""Tests for the DiagramGrid widget and helpers."""

import json
import pytest
from pathlib import Path

from brain.command_centre.diagram_grid import (
    DiagramGrid,
    list_diagrams,
    load_diagram,
    DIAGRAMS_DIR,
)


# --- Helpers ---

@pytest.fixture
def sample_diagram(tmp_path):
    """Create a minimal diagram JSON file for testing."""
    data = {
        "meta": {"title": "Test Diagram", "gridCols": 3, "gridRows": 2},
        "nodes": [
            {"id": "a", "label": "Node A", "gridPos": {"col": 0, "row": 0},
             "children": ["a1", "a2"], "meta": {"status": "live"}},
            {"id": "b", "label": "Node B", "gridPos": {"col": 1, "row": 0},
             "children": [], "meta": {}},
            {"id": "c", "label": "Node C", "gridPos": {"col": 0, "row": 1},
             "children": [], "meta": {"status": "planned"}},
        ],
        "layers": {
            "overview": {"title": "Overview", "visible": ["a", "b", "c"]},
            "a": {"title": "Node A Detail", "visible": ["a1", "a2"]},
        },
    }
    path = tmp_path / "test-diagram.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def empty_dir(tmp_path):
    """Empty directory with no diagrams."""
    d = tmp_path / "empty"
    d.mkdir()
    return d


# --- load_diagram ---

class TestLoadDiagram:
    def test_load_returns_dict(self, sample_diagram):
        result = load_diagram(sample_diagram)
        assert isinstance(result, dict)
        assert result["meta"]["title"] == "Test Diagram"

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_diagram(tmp_path / "nonexistent.json")

    def test_load_has_expected_keys(self, sample_diagram):
        result = load_diagram(sample_diagram)
        assert "meta" in result
        assert "nodes" in result
        assert "layers" in result


# --- list_diagrams ---

class TestListDiagrams:
    def test_list_diagrams_finds_json(self, tmp_path, monkeypatch):
        """list_diagrams should find .json files and ignore others."""
        diagrams_dir = tmp_path / "diagrams"
        diagrams_dir.mkdir()
        (diagrams_dir / "one.json").write_text("{}")
        (diagrams_dir / "two.json").write_text("{}")
        (diagrams_dir / "readme.txt").write_text("ignore me")

        import brain.command_centre.diagram_grid as dg_mod
        monkeypatch.setattr(dg_mod, "DIAGRAMS_DIR", diagrams_dir)

        result = list_diagrams()
        assert len(result) == 2
        names = [p.name for p in result]
        assert "one.json" in names
        assert "two.json" in names
        assert "readme.txt" not in names

    def test_list_diagrams_empty_dir(self, tmp_path, monkeypatch):
        """Empty dir returns empty list."""
        diagrams_dir = tmp_path / "diagrams"
        diagrams_dir.mkdir()

        import brain.command_centre.diagram_grid as dg_mod
        monkeypatch.setattr(dg_mod, "DIAGRAMS_DIR", diagrams_dir)

        result = list_diagrams()
        assert result == []

    def test_list_diagrams_missing_dir(self, tmp_path, monkeypatch):
        """Missing dir returns empty list (no crash)."""
        import brain.command_centre.diagram_grid as dg_mod
        monkeypatch.setattr(dg_mod, "DIAGRAMS_DIR", tmp_path / "nope")

        result = list_diagrams()
        assert result == []


# --- Visible nodes / layer logic (pure logic, no widget mount) ---

class TestDiagramLogic:
    def test_visible_nodes_overview(self, sample_diagram):
        """Overview layer should show all 3 nodes."""
        data = load_diagram(sample_diagram)
        layer = data["layers"]["overview"]
        visible_ids = set(layer["visible"])
        visible = [n for n in data["nodes"] if n["id"] in visible_ids]
        assert len(visible) == 3

    def test_child_layer_nodes(self, sample_diagram):
        """Node A's layer should show its children."""
        data = load_diagram(sample_diagram)
        layer = data["layers"]["a"]
        visible_ids = set(layer["visible"])
        assert visible_ids == {"a1", "a2"}

    def test_drill_requires_layer(self, sample_diagram):
        """A node without a matching layer entry cannot be drilled into."""
        data = load_diagram(sample_diagram)
        layers = data["layers"]
        # Node B has no children/layer
        assert "b" not in layers

    def test_grid_dimensions_from_meta(self, sample_diagram):
        data = load_diagram(sample_diagram)
        assert data["meta"]["gridCols"] == 3
        assert data["meta"]["gridRows"] == 2
