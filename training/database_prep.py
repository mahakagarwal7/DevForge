#!/usr/bin/env python3
"""
dataset_prep.py

Helper to create a simple JSONL dataset for instruction tuning.
Each line: {"instruction": "...", "input": "...", "output": "..."}
Usage:
python training/dataset_prep.py --out training/sample_data.jsonl
"""
import argparse
import json
import os

SAMPLE_EXAMPLES = [
    {
        "instruction": "Explain quadratic equation and plot a parabola",
        "input": "",
        "output": "Show equation: ax^2 + bx + c = 0. Explain discriminant b^2 - 4ac. Plot y = x^2 - 4 and show vertex at (0,-4) and roots at x=-2 and x=2."
    },
    {
        "instruction": "Show bubble sort with array [5,3,8,1]",
        "input": "",
        "output": "Visualize array as vertical bars, step through adjacent comparisons and swaps until sorted: [1,3,5,8]."
    }
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=str, default="training/sample_data.jsonl")
    args = parser.parse_args()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for ex in SAMPLE_EXAMPLES:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print("Wrote sample data to", args.out)

if __name__ == "__main__":
    main()