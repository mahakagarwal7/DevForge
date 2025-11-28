#!/usr/bin/env python3
"""
render_pipeline.py

End-to-end runner:
- Enhances user text → JSON plan
- Converts plan → Manim code
- Saves code → runs Manim
- Finds actual rendered video path from Manim (media/videos/**)
"""

import argparse
import json
import subprocess
import os
import glob
from pathlib import Path

from genai_enhancer import enhance_to_json
from training_pipeline import generate_manim_code, slugify, MANIM_DIR

ROOT = Path(".")
MANIM_DIR.mkdir(parents=True, exist_ok=True)


def find_manim_output(slug: str):
    """
    Manim outputs to: media/videos/<SceneName>/<resolution>/<filename>.mp4
    We scan for it automatically.
    """
    pattern = f"**/{slug}.mp4"
    matches = glob.glob(pattern, recursive=True)
    if matches:
        # Return the *first* real matching file
        return os.path.abspath(matches[0])
    return None


def write_and_render(plan: dict, open_video: bool = False):
    title = plan.get("title", "Generated")
    slug = slugify(title)

    # Generate Manim code
    code, class_name = generate_manim_code(plan)

    script_path = MANIM_DIR / f"{slug}.py"
    script_path.write_text(code, encoding="utf-8")

    # Command
    cmd = ["manim", "-qk", "-o", f"{slug}.mp4", str(script_path), class_name]
    print("Running:", " ".join(cmd))

    try:
        subprocess.run(cmd, check=True)

        # Manim wrote a file somewhere under media/videos
        real_video = find_manim_output(slug)

        if real_video:
            print("Rendered video:", real_video)

            if open_video:
                try:
                    os.startfile(real_video)
                except Exception:
                    print("Cannot auto-open video.")
        else:
            print("Render finished, but could NOT locate output file.")
            print("Search pattern failed for:", slug)

    except Exception as e:
        print("Render failed:", e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="+")
    parser.add_argument("--model", default="gemini-2.0-flash")
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    q = " ".join(args.query)
    plan = enhance_to_json(q, model=args.model, save=True)

    if not plan:
        print("Failed to generate plan.")
    else:
        print("Plan generated with meta:", plan.get("meta"))
        write_and_render(plan, open_video=not args.no_open)