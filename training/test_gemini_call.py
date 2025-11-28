#!/usr/bin/env python3
"""
Quick test to call genai_enhancer and show the produced plan + deterministic Manim code.
Usage:
  python test_gemini_call.py "draw projectile motion"
"""
import sys
import json
from genai_enhancer import enhance_to_json
from training_pipeline import plan_to_manim_code

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_gemini_call.py \"draw projectile motion\"")
        raise SystemExit(1)
    q = " ".join(sys.argv[1:])
    print("Requesting plan from Gemini...")
    plan = enhance_to_json(q, temperature=0.25)
    print("---- JSON PLAN ----")
    print(json.dumps(plan, indent=2))
    print("\n---- GENERATED MANIM CODE (deterministic) ----")
    code = plan_to_manim_code(plan)
    print(code)
