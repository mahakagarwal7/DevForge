# src/generator.py
"""
Generator: normalize and enrich the planner output.
Keeps the plan consistent and fills in defaults.
"""
from typing import Dict, Any, List

class SimpleGenerator:
    def normalize_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        plan = dict(plan)  # shallow copy
        # Ensure required keys
        plan.setdefault("title", "Educational Animation")
        plan.setdefault("core_concept", "")
        plan.setdefault("visual_elements", [])
        plan.setdefault("animation_sequence", [])
        # Normalize element structure
        for i, e in enumerate(plan["visual_elements"]):
            e.setdefault("id", f"elem_{i}")
            e.setdefault("type", "circle")
            e.setdefault("description", e.get("description", e["id"]))
        # Normalize steps
        for i, s in enumerate(plan["animation_sequence"]):
            s.setdefault("step", i+1)
            s.setdefault("title", s.get("title", f"Step {i+1}"))
            s.setdefault("action", s.get("action", "show"))
            s.setdefault("elements", s.get("elements", [plan["visual_elements"][0]["id"]]) if plan["visual_elements"] else [])
            s.setdefault("duration", s.get("duration", 2.5))
        return plan