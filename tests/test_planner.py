# tests/test_planner.py
import pytest
from src.planner import SimplePlanner

@pytest.fixture
def planner():
    return SimplePlanner()

def test_photosynthesis_plan(planner):
    plan = planner.plan_universal_scene("Explain photosynthesis with sun and plant")
    assert "visual_elements" in plan and len(plan["visual_elements"]) >= 3
    assert "animation_sequence" in plan and len(plan["animation_sequence"]) >= 2

def test_sort_plan(planner):
    plan = planner.plan_universal_scene("Show bubble sort algorithm with array")
    assert any(e["type"] == "rectangle" for e in plan["visual_elements"])
    assert any(s["action"] in ("compare_swap", "finalize", "compare and swap", "show") for s in plan["animation_sequence"])