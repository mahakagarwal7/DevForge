# src/main.py
"""
CLI entrypoint to generate an animation from a text prompt.

This version calls Gemini to enhance the user prompt before running the animator.
"""
import sys
import os

# When executed as a script (python src/main.py), ensure repo root is on sys.path
if __name__ == "__main__" and __package__ is None:
    script_dir = os.path.dirname(os.path.abspath(__file__))  # .../src
    repo_root = os.path.dirname(script_dir)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

# Imports
try:
    from animator import EducationalAnimator  # type: ignore
except Exception:
    from src.animator import EducationalAnimator  # type: ignore

# Gemini client
try:
    from gemini_client import enhance_text  # type: ignore
except Exception:
    def enhance_text(prompt: str, model: str = "gemini", max_output_tokens: int = 256, temperature: float = 0.0) -> str:
        return prompt

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.main \"Your educational concept description\"")
        sys.exit(1)
    concept = " ".join(sys.argv[1:])

    # === GEMINI ENHANCEMENT CALL HERE ===
    enhanced = enhance_text(concept, model="gemini", max_output_tokens=256, temperature=0.0)
    # === END GEMINI ENHANCEMENT CALL ===

    print("Original input:", concept)
    print("Enhanced input:", enhanced)

    animator = EducationalAnimator()
    video, plan = animator.generate(enhanced)
    if video:
        print(f"✅ Video created: {video}")
        print(f"Plan saved at: {plan.get('_saved_plan_file')}")
    else:
        print("❌ Failed to render animation. See console for details.")

if __name__ == "__main__":
    main()