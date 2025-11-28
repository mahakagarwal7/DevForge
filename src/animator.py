# src/animator.py
"""
High-level orchestrator: uses planner, generator, and renderer to produce a video.
"""
from typing import Tuple, Dict, Any
import os
from .planner import SimplePlanner
from .generator import SimpleGenerator
from .renderer import MoviePyRenderer
from .utils import save_plan

class EducationalAnimator:
    def __init__(self):
        self.planner = SimplePlanner()
        self.generator = SimpleGenerator()
        self.renderer = MoviePyRenderer()
        os.makedirs("outputs", exist_ok=True)

    def generate(self, text: str) -> Tuple[str, Dict[str,Any]]:
        # Step 1: plan
        plan = self.planner.plan_universal_scene(text)
        # Save raw plan for debugging
        plan_file = save_plan(plan, prefix="plan")
        plan["_saved_plan_file"] = plan_file

        # Step 2: normalize/generate
        plan = self.generator.normalize_plan(plan)

        # Step 3: render
        out_name = os.path.join("outputs", f"animation_{abs(hash(text))%100000}.mp4")
        try:
            video_path = self.renderer.render(plan, output_filename=out_name)
        except Exception as e:
            print("Renderer error:", e)
            video_path = None

        return video_path, plan