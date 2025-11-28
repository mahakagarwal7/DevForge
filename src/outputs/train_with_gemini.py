#!/usr/bin/env python3
"""
Simple helper to:
  1) Use Gemini (via src.gemini_client) to create N enhanced examples from a prompt.
  2) Save them into a JSONL training file suitable for train_slm.py.
  3) Optionally invoke the local training script (training/train_slm.py).

Usage examples:
  # generate 20 variants, save to training/data/photosynthesis.jsonl but do not train
  python -m src.train_with_gemini --prompt "Photosynthesis" --subject science --n 20 --out training/data/science_photosynthesis.jsonl

  # generate and train locally (requires training dependencies installed)
  python -m src.train_with_gemini --prompt "Photosynthesis" --subject science --n 40 --train_local --base_model bigscience/bloom-560m

Notes:
  - Ensure GEMINI_API_KEY is set in the same shell, and the genai client is installed:
      pip install google-genai python-dotenv
  - This script writes JSONL lines with {"instruction", "input", "output"}.
"""
import os
import argparse
import json
import subprocess
from typing import List
from pathlib import Path

# import our gemini helper
try:
    from src.gemini_client import generate_variants  # type: ignore
except Exception:
    try:
        from gemini_client import generate_variants  # type: ignore
    except Exception:
        raise SystemExit("gemini_client not found. Ensure src/gemini_client.py exists and is importable.")

def _make_examples(prompt: str, variants: List[str], subject: str) -> List[dict]:
    out = []
    for i, v in enumerate(variants):
        ex = {
            "instruction": f"Create an educational animation plan for: {prompt} (variant {i+1})",
            "input": prompt,
            "output": v
        }
        out.append(ex)
    return out

def save_jsonl(examples: List[dict], path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

def run_local_training(train_script: str, train_file: str, base_model: str, output_dir: str, epochs: int, batch: int):
    cmd = [os.environ.get("PYTHON", "python"), train_script, "--model_name_or_path", base_model, "--train_file", train_file, "--output_dir", output_dir, "--num_train_epochs", str(epochs), "--per_device_train_batch_size", str(batch)]
    print("Launching training:", " ".join(cmd))
    subprocess.check_call(cmd)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--model", default="gemini-2.0-flash")
    parser.add_argument("--out", default=None, help="Path to append JSONL (default: training/data/<subject>.jsonl)")
    parser.add_argument("--train_local", action="store_true", help="Run training/train_slm.py after data generation")
    parser.add_argument("--base_model", default="bigscience/bloom-560m", help="Base model for local training")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch", type=int, default=4)
    args = parser.parse_args()

    out_path = args.out or f"training/data/{args.subject}.jsonl"
    print(f"Generating {args.n} enhanced variants for prompt: {args.prompt!r} using model {args.model}")
    variants = generate_variants(args.prompt, n=args.n, model=args.model, max_output_tokens=512, temperature=0.4)
    print(f"Generated {len(variants)} variants (unique).")
    examples = _make_examples(args.prompt, variants, args.subject)
    save_jsonl(examples, out_path)
    print(f"Saved {len(examples)} examples to {out_path}")

    if args.train_local:
        out_dir = os.path.join("outputs", f"slm_{args.subject}")
        print(f"Starting local training: base_model={args.base_model}, epochs={args.epochs}, batch={args.batch}")
        run_local_training("training/train_slm.py", out_path, args.base_model, out_dir, args.epochs, args.batch)
        print("Local training finished. Adapter saved to", out_dir)

if __name__ == "__main__":
    main()