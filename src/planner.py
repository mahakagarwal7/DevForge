# src/planner.py
"""
Simple rule-based planner with extra handling for quadratic equations.
"""
import os
import re
import json
import hashlib
from typing import Dict, List, Any
import random

# Local helper for plan saving (best-effort)
try:
    from .utils import save_plan
except Exception:
    def save_plan(plan, prefix="plan"):
        os.makedirs("outputs/plans", exist_ok=True)
        h = hashlib.md5(json.dumps(plan, sort_keys=True).encode()).hexdigest()[:8]
        path = os.path.join("outputs", "plans", f"{prefix}_{h}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)
        return path

class SimplePlanner:
    def __init__(self):
        random.seed(0)
        os.makedirs("outputs/plans", exist_ok=True)

    def plan_universal_scene(self, concept: str) -> Dict[str, Any]:
        concept_lower = concept.lower()
        title = f"Understanding: {concept[:60]}"
        domain = self._detect_domain(concept_lower)

        # Quadratic-specific plan
        if "quadratic" in concept_lower or "quadratic equation" in concept_lower or "ax^2" in concept_lower or "a x^2" in concept_lower:
            # try to extract coefficients from the prompt like "ax^2 + bx + c" or numeric example "x^2 - 3x + 2"
            coef_match = re.search(r'([+-]?\d*)x\^2\s*([+-]\s*\d*)x\s*([+-]\s*\d+)', concept.replace(' ', ''))
            sample_eq = "ax² + bx + c = 0"
            if coef_match:
                sample_eq = coef_match.group(0).replace('^', '²') + " = 0"
            elements = [
                {"id": "equation", "type": "equation", "description": sample_eq},
                {"id": "discriminant", "type": "text", "description": "Discriminant: b² - 4ac"},
                {"id": "parabola", "type": "parabola", "description": "y = ax² + bx + c"},
                {"id": "vertex", "type": "circle", "description": "Vertex"},
                {"id": "roots", "type": "text", "description": "Roots: x₁, x₂"}
            ]
            animation_sequence = [
                {
                    "step": 1,
                    "title": "Show Equation",
                    "action": "introduce",
                    "elements": ["equation"],
                    "educational_explanation": "Display the quadratic equation",
                    "duration": 2.5
                },
                {
                    "step": 2,
                    "title": "Discriminant",
                    "action": "show inputs",
                    "elements": ["discriminant"],
                    "educational_explanation": "Explain discriminant b² - 4ac determines roots",
                    "duration": 3.0
                },
                {
                    "step": 3,
                    "title": "Graph Parabola",
                    "action": "plot_parabola",
                    "elements": ["parabola", "vertex", "roots"],
                    "educational_explanation": "Plot the parabola and show vertex and roots",
                    "duration": 5.0
                },
                {
                    "step": 4,
                    "title": "Highlight Roots",
                    "action": "highlight_roots",
                    "elements": ["roots"],
                    "educational_explanation": "Show how discriminant affects number of real roots",
                    "duration": 3.0
                }
            ]
            plan = {
                "title": title,
                "core_concept": concept,
                "educational_domain": "mathematics",
                "visual_elements": elements,
                "animation_sequence": animation_sequence
            }
            plan_file = save_plan(plan, prefix="plan_quadratic")
            plan["_saved_plan_file"] = plan_file
            return plan

        # Existing generic rules for photosynthesis/sorting/wave and fallback
        if "photosynthesis" in concept_lower or "plant" in concept_lower:
            elements = [
                {"id": "sun", "type": "circle", "description": "Sun providing light"},
                {"id": "plant", "type": "image", "description": "Plant / leaf"},
                {"id": "co2", "type": "text", "description": "CO2 input"},
                {"id": "h2o", "type": "text", "description": "H2O input"},
                {"id": "o2", "type": "text", "description": "O2 output"}
            ]
        elif any(k in concept_lower for k in ["sort", "bubble", "merge", "algorithm"]):
            elements = [
                {"id": f"bar{i}", "type": "rectangle", "description": f"array element {i}"} for i in range(1,6)
            ] + [{"id": "pointer", "type": "arrow", "description": "comparison pointer"}]
        elif any(k in concept_lower for k in ["sine", "sin", "wave", "graph"]):
            elements = [
                {"id": "axis", "type": "line", "description": "axes"},
                {"id": "curve", "type": "wave", "description": "sine curve"},
                {"id": "point", "type": "circle", "description": "moving point"}
            ]
        else:
            elements = [
                {"id": "main", "type": "circle", "description": f"Core: {concept[:30]}"},
                {"id": "detail1", "type": "rectangle", "description": "Supporting detail 1"},
                {"id": "detail2", "type": "triangle", "description": "Supporting detail 2"}
            ]

        elements = elements[:6]
        animation_sequence = self._create_sequence_for(elements, concept_lower)
        plan = {
            "title": title,
            "core_concept": concept,
            "educational_domain": domain,
            "visual_elements": elements,
            "animation_sequence": animation_sequence
        }
        plan_file = save_plan(plan, prefix="plan")
        plan["_saved_plan_file"] = plan_file
        return plan

    def _create_sequence_for(self, elements: List[Dict[str, Any]], concept_lower: str) -> List[Dict[str, Any]]:
        seq = []
        seq.append({
            "step": 1,
            "title": "Introduction",
            "action": "introduce",
            "elements": [elements[i]["id"] for i in range(min(2, len(elements)))],
            "educational_explanation": "Introduce the main objects",
            "duration": 2.0
        })
        if any(k in concept_lower for k in ["photosynthesis", "plant"]):
            seq.append({
                "step": 2,
                "title": "Inputs",
                "action": "show inputs",
                "elements": [e["id"] for e in elements if e["id"] in ("co2", "h2o")],
                "educational_explanation": "Show raw materials entering the plant",
                "duration": 3.0
            })
            seq.append({
                "step": 3,
                "title": "Products",
                "action": "show outputs",
                "elements": [e["id"] for e in elements if e["id"] in ("o2", "plant")],
                "educational_explanation": "Show products produced",
                "duration": 3.0
            })
        elif any(k in concept_lower for k in ["sort", "bubble", "algorithm"]):
            seq.append({
                "step": 2,
                "title": "Compare & Swap",
                "action": "compare_swap",
                "elements": [elements[0]["id"], elements[1]["id"], "pointer"],
                "educational_explanation": "Compare adjacent elements and swap if needed",
                "duration": 4.0
            })
            seq.append({
                "step": 3,
                "title": "Result",
                "action": "finalize",
                "elements": [e["id"] for e in elements if e["type"] == "rectangle"],
                "educational_explanation": "Array is sorted",
                "duration": 2.5
            })
        else:
            seq.append({
                "step": 2,
                "title": "Develop",
                "action": "demonstrate",
                "elements": [e["id"] for e in elements],
                "educational_explanation": "Work through the idea",
                "duration": 4.0
            })
            seq.append({
                "step": 3,
                "title": "Conclusion",
                "action": "summarize",
                "elements": [elements[0]["id"]],
                "educational_explanation": "Key takeaway",
                "duration": 2.0
            })
        return seq

    def _detect_domain(self, text: str) -> str:
        if any(w in text for w in ["photosynthesis", "plant", "cell", "molecule"]):
            return "science"
        if any(w in text for w in ["equation", "pythag", "graph", "sine", "quadratic"]):
            return "mathematics"
        if any(w in text for w in ["sort", "algorithm", "array", "bubble"]):
            return "computer_science"
        return "general"