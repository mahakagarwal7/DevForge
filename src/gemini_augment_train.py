#!/usr/bin/env python3
"""
Augment + Train using Gemini (library-only) and SLM.

Fixes:
- Uses src.gemini_client.generate_variants (library, no HTTP v1beta2, respects GEMINI_API_KEY/.env).
- Filters out echo outputs (where output == input).
- Only triggers training when the dataset contains non-echo examples.
- Makes it explicit when no valid data was generated so you don't unknowingly
  train on trivial/empty data.
"""
import os
import json
import argparse
import subprocess
from typing import List, Dict, Any

DATA_DIR = "training/data"
os.makedirs(DATA_DIR, exist_ok=True)

def _save_jsonl(examples: List[Dict[str, Any]], path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

def _create_examples(prompt: str, outputs: List[str]) -> List[Dict[str, str]]:
    res: List[Dict[str, str]] = []
    for i, out in enumerate(outputs):
        res.append({
            "instruction": f"Create an educational animation: variant {i+1}",
            "input": prompt,
            "output": out,
        })
    return res

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", required=True, help="Subject (e.g., mathematics, physics)")
    parser.add_argument("--prompt", required=True, help="User prompt to enhance for training")
    parser.add_argument("--n_variations", type=int, default=20)
    parser.add_argument("--model", default="gemini-2.0-flash")
    parser.add_argument("--max_tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.4)
    parser.add_argument("--train_local", action="store_true")
    parser.add_argument("--base_model", default="bigscience/bloom-560m")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch", type=int, default=4)
    args = parser.parse_args()

    # Import variants generator
    try:
        from .gemini_client import generate_variants  # type: ignore
    except Exception as e:
        raise SystemExit("src.gemini_client not importable: " + str(e))

    print(f"Generating up to {args.n_variations} variants for prompt: {args.prompt!r} using model={args.model}")
    raw_outputs = generate_variants(
        args.prompt,
        n=args.n_variations,
        model=args.model,
        max_output_tokens=args.max_tokens,
        base_temperature=args.temperature,
    )

    non_echo_outputs = [
        o for o in raw_outputs
        if isinstance(o, str) and o.strip() and o.strip().lower() != args.prompt.strip().lower()
    ]
    if not non_echo_outputs:
        print("No non-echo outputs produced by Gemini. Try increasing --temperature or using a different model.")
        print("Raw outputs (first few):")
        for o in raw_outputs[:5]:
            print(" -", repr(o)[:200])
        return

    examples = _create_examples(args.prompt, non_echo_outputs)
    out_path = os.path.join(DATA_DIR, f"{args.subject}.jsonl")
    _save_jsonl(examples, out_path)
    print(f"Appended {len(examples)} examples to {out_path}")

    if not args.train_local:
        print("Augmentation complete. Training not started (omit or use --train_local to train).")
        return

    # Sanity check before training
    valid_count = 0
    with open(out_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                ex = json.loads(line)
                if ex.get("output", "").strip().lower() != ex.get("input", "").strip().lower():
                    valid_count += 1
            except Exception:
                continue
    if valid_count == 0:
        print("Dataset has no valid non-echo outputs. Aborting training.")
        return

    out_dir = os.path.join("outputs", f"slm_{args.subject}")
    cmd = [
        "python", "training/train_slm.py",
        "--model_name_or_path", args.base_model,
        "--train_file", out_path,
        "--output_dir", out_dir,
        "--num_train_epochs", str(args.epochs),
        "--per_device_train_batch_size", str(args.batch),
    ]
    print("Launching local SLM training:", " ".join(cmd))
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print("Training failed:", e)
        return
    print("Training finished. Adapter saved to", out_dir)

if __name__ == "__main__":
    main()