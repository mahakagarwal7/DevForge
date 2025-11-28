#!/usr/bin/env python3
"""
training_pipeline.py (FINAL FIXED VERSION)

- Converts validated JSON plans → Manim code
- Returns BOTH the code and the class name properly
- Compatible with render_pipeline.py expecting (code, class_name)
"""

import argparse
import json
import os
import glob
import subprocess
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple

from plan_validator import validate_and_fill_plan, projectile_parametric_expr

# Output folders
ROOT = Path(".")
PLANS_GLOB = ROOT / "outputs" / "plans" / "*.json"
MANIM_DIR = ROOT / "outputs" / "manim_code"
VIDEO_DIR = ROOT / "outputs" / "videos"
DATASET_DIR = ROOT / "training" / "generated_data"

for p in (MANIM_DIR, VIDEO_DIR, DATASET_DIR):
    p.mkdir(parents=True, exist_ok=True)


# --------------------------
# Utility Functions
# --------------------------

def slugify(text: str) -> str:
    base = "".join(ch if ch.isalnum() else "_" for ch in str(text))[:30].strip("_")
    h = hashlib.sha1((str(text) + str(time.time())).encode()).hexdigest()[:8]
    return f"{base}_{h}"


def _make_valid_class_name(title: str) -> str:
    clean = "".join(ch for ch in str(title).title() if ch.isalnum())
    if not clean:
        clean = "GeneratedAnimation"
    if not clean[0].isalpha():
        clean = "Scene" + clean
    return clean


def obj_var(obj_id: str) -> str:
    return "obj_" + "".join(ch if ch.isalnum() else "_" for ch in obj_id)


# --------------------------
# Manim Code Generator
# --------------------------

def generate_manim_code(plan: Dict[str, Any]) -> Tuple[str, str]:
    """
    Converts your validated plan into executable Manim code.
    RETURNS:
        code_str, class_name  <-- IMPORTANT
    """
    title = plan.get("title", "Animation")
    class_name = _make_valid_class_name(title)
    scenes = plan.get("scenes", [])

    lines = []
    lines.append("from manim import *")
    lines.append("import numpy as np")
    lines.append("")
    lines.append(f"class {class_name}(Scene):")
    lines.append("    def construct(self):")

    for scene in scenes:
        objects = scene.get("objects", [])
        actions = scene.get("actions", [])
        hint = (scene.get("hint", "") or "").lower()

        # ---------------------------
        # Create Scene Objects
        # ---------------------------
        for obj in objects:
            oid = obj.get("id", "obj")
            otype = obj.get("type", "Dot")
            params = obj.get("params", {}) or {}
            var = obj_var(oid)

            if otype == "Dot":
                color = repr(params.get("color", "WHITE"))
                lines.append(f"        {var} = Dot(color={color})")

            elif otype == "Text":
                txt = repr(params.get("text", ""))
                lines.append(f"        {var} = Text({txt})")

            elif otype == "Circle":
                radius = params.get("radius", 0.7)
                lines.append(f"        {var} = Circle(radius={radius})")

            elif otype == "Square":
                side = params.get("side", 1.0)
                lines.append(f"        {var} = Square(side_length={side})")

            elif otype == "Axes":
                xr = params.get("x_range", [0, 10])
                yr = params.get("y_range", [0, 5])
                lines.append(f"        {var} = Axes(x_range={xr}, y_range={yr})")
                lines.append(f"        self.play(Create({var}), run_time=0.5)")

            elif otype == "ParametricFunction":
                expr = params.get("expr", "lambda t: np.array([t, 0, 0])")
                tr = params.get("t_range", [0, 1])
                lines.append(f"        {var} = ParametricFunction({expr}, t_range={tr})")

            else:
                lines.append(f"        {var} = Dot()  # fallback object")

        # ---------------------------
        # SPECIAL CASE: Projectile Motion
        # ---------------------------
        if "projectile" in hint or "parabola" in hint or "trajectory" in hint:
            phys = (scene.get("params") or {}).get("physics", {})
            v0 = float(phys.get("v0", 12))
            ang = float(phys.get("angle_degrees", 45))
            g = float(phys.get("g", 9.81))

            expr, t_end = projectile_parametric_expr(v0, ang, g)

            lines.append(f"        traj = ParametricFunction({expr}, t_range=[0,{t_end:.4f}])")
            lines.append("        ball = Dot(color=YELLOW)")
            lines.append("        self.play(FadeIn(ball))")
            lines.append(f"        self.play(MoveAlongPath(ball, traj), run_time={t_end:.4f})")
            lines.append("        self.wait(0.3)")
            continue

        # ---------------------------
        # Playback Actions
        # ---------------------------
        for act in actions:
            atype = act.get("type")
            target = act.get("target")
            var = obj_var(target) if target else None
            params = act.get("params", {}) or {}
            dur = params.get("duration", 0.8)

            if atype == "FadeIn" and var:
                lines.append(f"        self.play(FadeIn({var}), run_time={dur})")

            elif atype == "Create" and var:
                lines.append(f"        self.play(Create({var}), run_time={dur})")

            elif atype == "FadeOut" and var:
                lines.append(f"        self.play(FadeOut({var}), run_time={dur})")

            elif atype == "MoveAlongPath" and var:
                path = params.get("path")
                if path:
                    lines.append(f"        p_{var} = {path}")
                    lines.append(f"        self.play(MoveAlongPath({var}, p_{var}), run_time={dur})")

        lines.append("        self.wait(0.5)")

    code = "\n".join(lines)
    return code, class_name


# --------------------------
# Dataset Utility
# --------------------------

def plan_to_example(plan: Dict[str, Any]):
    code, _ = generate_manim_code(plan)
    return {
        "instruction": "Convert the JSON scene plan into Manim CE Python code.",
        "input": json.dumps(plan, ensure_ascii=False),
        "output": code
    }


# --------------------------
# Bulk Processing
# --------------------------

def process_plans(plans_dir: str = str(PLANS_GLOB), out_dataset: str = None):
    files = glob.glob(plans_dir)
    results = []
    dataset_entries = []

    for fp in files:
        plan = json.load(open(fp, "r", encoding="utf-8"))
        filled, diag = validate_and_fill_plan(plan)

        slug = slugify(filled.get("title", "plan"))
        code, class_name = generate_manim_code(filled)

        out_path = MANIM_DIR / f"{slug}.py"
        out_path.write_text(code, encoding="utf-8")

        dataset_entries.append(plan_to_example(filled))
        results.append({"slug": slug, "class": class_name})

    if out_dataset:
        p = Path(out_dataset)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            for e in dataset_entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    return results, dataset_entries


# --------------------------
# Command Line
# --------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plans_dir", default=str(PLANS_GLOB))
    parser.add_argument("--out_dataset", default=str(DATASET_DIR / "data.jsonl"))
    args = parser.parse_args()

    results, ds = process_plans(args.plans_dir, args.out_dataset)
    print(json.dumps(results, indent=2, ensure_ascii=False))