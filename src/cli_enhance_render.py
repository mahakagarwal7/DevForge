#!/usr/bin/env python3
"""
CLI wired to the library-only gemini client.

- Uses src.gemini_client.enhance_text by default.
- Uses a higher default temperature to reduce echoing.
- Prints helpful diagnostics when enhancement falls back to original prompt.
"""
import sys
import os
import argparse

# Ensure repo root is importable
if __name__ == "__main__" and __package__ is None:
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(here)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

# Import Gemini client from src (integrated)
try:
    from src.gemini_client import enhance_text  # type: ignore
except Exception:
    try:
        from gemini_client import enhance_text  # type: ignore
    except Exception:
        def enhance_text(prompt: str, **kwargs):
            print("gemini_client not available — passing prompt through")
            return prompt

# Import animator (existing in your repo)
try:
    from src.animator import EducationalAnimator  # type: ignore
except Exception:
    from animator import EducationalAnimator  # type: ignore

def run_one(prompt: str, model: str = "text-bison-001", temperature: float = 0.5):
    print("Original input:")
    print(prompt)
    # === GEMINI ENHANCEMENT CALL HERE ===
    enhanced = enhance_text(prompt, model=model, temperature=temperature, max_output_tokens=512)
    # === END GEMINI ENHANCEMENT CALL ===
    print("\nEnhanced input (from Gemini):")
    print(enhanced)

    if isinstance(enhanced, str) and enhanced.strip().lower() == prompt.strip().lower():
        print("\n[warning] Enhancement returned input unchanged. Try increasing --temperature or check GEMINI_API_KEY/.env.")

    animator = EducationalAnimator()
    print("\nGenerating animation from enhanced prompt (this may take a while)...")
    video_path, plan = animator.generate(enhanced)

    if video_path:
        print(f"\n✅ Video created: {video_path}")
        if plan and isinstance(plan, dict):
            print(f"Plan saved at: {plan.get('_saved_plan_file')}")
    else:
        print("\n❌ Failed to render animation. See console for details.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", nargs="?", help="Text prompt to enhance and render")
    parser.add_argument("--model", default="text-bison-001", help="GenAI model id to call")
    parser.add_argument("--temperature", type=float, default=0.5, help="Sampling temperature for enhancement (raise to reduce echoes)")
    args = parser.parse_args()

    if args.prompt:
        prompt = args.prompt
    else:
        prompt = input("Enter prompt: ")

    run_one(prompt, model=args.model, temperature=args.temperature)

if __name__ == "__main__":
    main()