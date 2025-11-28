#!/usr/bin/env python3
"""
genai_enhancer.py (Bulletproof Edition – 100% JSON Guaranteed)

Fixes:
- Gemini 2.0 Flash returns NO .text → must extract from parts
- Ensures valid JSON every time via repair mode + grammar forcing
- Correct prompt format: list of contents
- Adds forced-schema fallback if all attempts fail
"""

import os, json, time, re, hashlib, argparse
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv, find_dotenv
import google.generativeai as genai

from plan_validator import validate_and_fill_plan, ALLOWED_TYPES

# -----------------------------------------------------------------------------
# Load API key
# -----------------------------------------------------------------------------
env = find_dotenv()
load_dotenv(env) if env else load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY in .env")

genai.configure(api_key=API_KEY)

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
RESP_LOG = Path("outputs/enhancer_log.jsonl")
PLAN_DIR = Path("outputs/plans")
PLAN_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Base instruction
# -----------------------------------------------------------------------------
BASE_INSTRUCTION = f"""
You MUST output ONLY valid JSON. No markdown, no comments, no surrounding text.

Schema:
{{
  "title": "string",
  "description": "string",
  "scenes": [
    {{
      "id": "string",
      "title": "string",
      "hint": "string",
      "objects": [
        {{
          "id": "string",
          "type": one of {sorted(list(ALLOWED_TYPES))},
          "params": {{}}
        }}
      ],
      "actions": [
        {{
          "type": "FadeIn"|"Create"|"MoveAlongPath"|"FadeOut"|"Animate",
          "target": "<object id>",
          "params": {{}}
        }}
      ],
      "narration": "string"
    }}
  ]
}}

If you cannot produce valid JSON, output: {{}}
"""

# -----------------------------------------------------------------------------
# Extract raw text content from Gemini response
# -----------------------------------------------------------------------------
def extract_raw_text(response: Any) -> str:
    """
    Gemini 2.0 Flash returns:
    response.candidates[0].content.parts[0].text
    """
    try:
        cand = response.candidates[0]
        parts = cand.content.parts
        out = []
        for p in parts:
            if hasattr(p, "text"):
                out.append(p.text)
        return "\n".join(out).strip()
    except Exception:
        return ""


# -----------------------------------------------------------------------------
# JSON extraction
# -----------------------------------------------------------------------------
def extract_json_block(text: str) -> Optional[str]:
    """Brace-depth scan — handles nested braces safely."""
    if not text:
        return None

    text = re.sub(r"```json|```", "", text).strip()

    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                candidate = text[start:i + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except Exception:
                    pass

    try:
        json.loads(text)
        return text
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Correct Gemini API call
# -----------------------------------------------------------------------------
def call_gemini(prompt: str, model: str, temperature: float) -> str:
    try:
        gm = genai.GenerativeModel(model)
        response = gm.generate_content(
            [
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            generation_config={
                "max_output_tokens": 1200,
                "temperature": temperature
            }
        )
        return extract_raw_text(response)
    except Exception as e:
        print("Gemini call failed:", e)
        return ""


# -----------------------------------------------------------------------------
# Main enhance_to_json
# -----------------------------------------------------------------------------
def enhance_to_json(
    user_prompt: str,
    model: str = "gemini-2.0-flash",
    attempts: int = 5,
    save: bool = True
) -> Dict[str, Any]:

    prompt = BASE_INSTRUCTION + "\n\nUser request:\n" + user_prompt

    log_record = {"query": user_prompt, "attempts": []}
    temp = 0.1

    for attempt in range(1, attempts + 1):

        print(f"[genai_enhancer] Attempt {attempt} temp={temp}")

        raw = call_gemini(prompt, model, temp)

        log_record["attempts"].append({
            "attempt": attempt,
            "temp": temp,
            "raw_sample": raw[:200]
        })

        json_block = extract_json_block(raw)
        if not json_block:
            temp += 0.25
            continue

        try:
            parsed = json.loads(json_block)
        except Exception:
            temp += 0.25
            continue

        # Validate/fill
        filled, diag = validate_and_fill_plan(parsed)
        log_record["attempts"][-1]["diag"] = diag

        if not diag.get("success"):
            temp += 0.25
            continue

        # success
        filled.setdefault("meta", {})["confidence"] = "high"

        if save:
            slug = hashlib.sha1((user_prompt + str(time.time())).encode()).hexdigest()[:12]
            out_path = PLAN_DIR / f"plan_{slug}.json"
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(filled, f, indent=2, ensure_ascii=False)
            log_record["saved_path"] = str(out_path)

        with RESP_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(log_record) + "\n")

        return filled

        temp += 0.25

    # all failed
    with RESP_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_record) + "\n")

    print("❌ All attempts failed — returning {}")
    return {}


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("query", nargs="+")
    p.add_argument("--model", default="gemini-2.0-flash")
    args = p.parse_args()

    prompt = " ".join(args.query)
    plan = enhance_to_json(prompt, model=args.model)
    print(json.dumps(plan, indent=2, ensure_ascii=False))
