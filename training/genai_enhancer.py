#!/usr/bin/env python3
"""
genai_enhancer.py — enhanced to require numeric params and validate plans.

Key changes:
- Enhancer requests explicit numeric parameters (e.g., v0, angle_degrees) when relevant.
- After parsing Gemini output we validate and auto-fill defaults via plan_validator.
- If defaults are auto-filled we set plan['meta']['confidence']="low".
- Plans saved to outputs/plans/ flagged with confidence.
"""
from pathlib import Path
import os
import json
import time
import argparse
from typing import Any, Dict
from dotenv import load_dotenv, find_dotenv
import google.generativeai as genai
from plan_validator import validate_and_fill_plan

# load env
env = find_dotenv()
if env:
    load_dotenv(env)
else:
    load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in .env")

try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception:
    pass

RESP_FILE = Path("outputs/enhancements.jsonl")
PLANS_DIR = Path("outputs/plans")
RESP_FILE.parent.mkdir(parents=True, exist_ok=True)
PLANS_DIR.mkdir(parents=True, exist_ok=True)

BASE_INSTRUCTION = """
You are an assistant that MUST output ONLY valid JSON (no prose).
Produce a scene-by-scene animation plan suitable for automatic conversion into Manim CE Python code.

REQUIREMENTS:
- Provide 'title' and 'description' top-level strings.
- Provide 'scenes' list. Each scene must include:
  - id (string), title (string)
  - objects: list of objects with 'id','type' and 'params' (params is a dict).
  - actions: list of actions (type, target, params)
  - hint: optional short hint (e.g., 'projectile', 'parabolic arc') to indicate physics scenes.
- For physics scenes (hint contains 'projectile' or 'trajectory'), include a 'params.physics' dict with numeric fields:
    - v0 (float): initial speed in m/s
    - angle_degrees (float): launch angle in degrees
    - optionally: g (float) gravitational acceleration (default 9.81)
Return only valid JSON. If you cannot, return {}.
"""

def _save_record(query: str, rec: Dict[str, Any]):
    r = {"ts": int(time.time()), "query": query, "rec": rec}
    try:
        with RESP_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    except Exception:
        pass

def _extract_text(resp: Any) -> str:
    # defensive extraction similar to earlier hardened version
    try:
        if resp is None:
            return ""
        if isinstance(resp, dict):
            for k in ("text", "content", "output", "generated_text"):
                v = resp.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
            cand = resp.get("candidates") or resp.get("outputs") or resp.get("choices")
            if isinstance(cand, (list, tuple)) and cand:
                first = cand[0]
                if isinstance(first, dict):
                    for k in ("content", "text"):
                        v = first.get(k)
                        if isinstance(v, str) and v.strip():
                            return v.strip()
                if isinstance(first, str) and first.strip():
                    return first.strip()
        if hasattr(resp, "text") and isinstance(getattr(resp, "text"), str):
            return getattr(resp, "text").strip()
    except Exception:
        pass
    return ""

def _find_first_json_in_text(text: str):
    import re, json
    if not text:
        return None
    # strip markdown fences
    text = re.sub(r'(^\s*```(?:json)?\s*)|(\s*```\s*$)', '', text, flags=re.MULTILINE)
    # try to locate first {...} or [...]
    obj_match = re.search(r'(\{.*\})', text, flags=re.DOTALL)
    arr_match = re.search(r'(\[.*\])', text, flags=re.DOTALL)
    candidates = []
    if obj_match:
        candidates.append(obj_match.group(1))
    if arr_match:
        candidates.append(arr_match.group(1))
    candidates.append(text)
    for c in candidates:
        try:
            return json.loads(c)
        except Exception:
            continue
    return None

def enhance_to_json(user_text: str, model: str = "gemini-2.0-flash", max_tokens: int = 800, attempts:int=3, save:bool=True):
    full_prompt = BASE_INSTRUCTION.strip() + "\n\nUser request:\n" + user_text.strip()
    record = {"model": model, "attempts": []}
    temp = 0.2
    candidate_count = 1
    for i in range(attempts):
        # try multiple call shapes defensively
        try:
            if hasattr(genai, "models") and hasattr(genai.models, "generate_content"):
                try:
                    resp = genai.models.generate_content(model=model, contents=full_prompt, temperature=temp, max_output_tokens=max_tokens, candidate_count=(candidate_count if candidate_count>1 else None))
                except TypeError:
                    resp = genai.models.generate_content(model=model, prompt=full_prompt, temperature=temp, max_output_tokens=max_tokens)
                text = _extract_text(resp)
            elif hasattr(genai, "generate_text"):
                resp = genai.generate_text(model=model, prompt=full_prompt, temperature=temp, max_output_tokens=max_tokens)
                text = _extract_text(resp)
            else:
                # fallback to GenerativeModel
                gm = genai.GenerativeModel(model)
                try:
                    resp = gm.generate_content(full_prompt, generation_config={"temperature":temp, "max_output_tokens":max_tokens})
                except TypeError:
                    resp = gm.generate_content(contents=full_prompt, generation_config={"temperature":temp, "max_output_tokens":max_tokens})
                text = _extract_text(resp)
        except Exception as e:
            record["attempts"].append({"attempt": i+1, "error": str(e)})
            # increase randomness
            temp = min(1.0, temp + 0.2)
            candidate_count = min(6, candidate_count + 1)
            continue

        record["attempts"].append({"attempt": i+1, "temp": temp, "cand": candidate_count, "raw_sample": (text or "")[:500]})
        if not text:
            temp = min(1.0, temp + 0.2)
            candidate_count = min(6, candidate_count + 1)
            continue

        parsed = _find_first_json_in_text(text)
        if not parsed:
            record["attempts"][-1]["parse_error"] = "no json found"
            temp = min(1.0, temp + 0.2)
            candidate_count = min(6, candidate_count + 1)
            continue

        # Validate and fill defaults
        filled, diag = validate_and_fill_plan(parsed)
        # set confidence
        if diag.get("auto_filled"):
            filled.setdefault("meta", {})["confidence"] = "low"
        else:
            filled.setdefault("meta", {})["confidence"] = "high"

        record["final"] = {"diag": diag}
        _save_record(user_text, record)

        if save:
            # save plan
            safe_title = (filled.get("title") or "plan").strip().replace(" ", "_")[:40]
            fname = f"{int(time.time())}_{safe_title}.json"
            try:
                with (PLANS_DIR / fname).open("w", encoding="utf-8") as f:
                    json.dump(filled, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        return filled

    _save_record(user_text, record)
    return {}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="+")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()
    q = " ".join(args.query)
    plan = enhance_to_json(q, save=args.save)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
