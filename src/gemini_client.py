#!/usr/bin/env python3
"""
Robust, minimal Gemini client for producing scene-by-scene Manim-ready
instructions from a short user prompt.

Requirements:
    pip install google-generativeai python-dotenv

Behavior:
- Loads GEMINI_API_KEY from .env (repo root).
- Uses only google.generativeai.
- Maps some non-Gemini model names (e.g. "text-bison-001") to a Gemini fallback.
- Tries multiple call styles and extracts text from different response shapes.
- Returns a single enhanced string suitable for an SLM that converts to Manim.
"""

from pathlib import Path
import os
import json
import time
from typing import Optional, Any, Dict

# -----------------------------
# Environment Setup
# -----------------------------
from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv()
if env_path:
    load_dotenv(env_path)
else:
    load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found in environment variables. Put it in a .env file.")

# -----------------------------
# Import Official GenAI Library
# -----------------------------
import google.generativeai as genai

# configure client (works for typical google.generativeai versions)
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception:
    # some versions don't expose configure or throw; ignore
    pass

# -----------------------------
# Logging
# -----------------------------
RESP_FILE = Path("outputs/enhancements.jsonl")
RESP_FILE.parent.mkdir(parents=True, exist_ok=True)


def _save_record(prompt: str, record: Dict[str, Any]) -> None:
    rec = {
        "timestamp": int(time.time()),
        "prompt": prompt,
        "record": record,
    }
    try:
        with RESP_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


# -----------------------------
# Base Instruction Template
# -----------------------------
BASE_INSTRUCTION = """
You are an expert Manim animation designer.

Your job:
- Transform the user's short idea into a clear, expanded, scene-by-scene Manim animation plan.
- Each scene must include:
    1. Scene title
    2. What objects Manim should create (class names, shapes, basic params)
    3. Motions, transformations, durations/timings
    4. Camera moves / transitions (e.g., zoom, shift, frame.animate)
    5. 1–2 short narration lines for voiceover
- Produce concise, explicit steps that an SLM (trained to emit Manim code) can convert into Python/Manim.
- Do NOT merely echo the user's input; expand it into implementation-level detail.
"""

# -----------------------------
# Helpers: model mapping & response extraction
# -----------------------------


def _normalize_model_name(model: str) -> str:
    """
    Map common non-gemini names to recommended Gemini default(s).
    If the user supplies a Gemini name already, return it unchanged.
    """
    m = (model or "").strip().lower()
    # If they used older Vertex AI Bison names, map to a Gemini default
    bison_like = {"text-bison-001", "bison", "bison-text"}
    if m in bison_like:
        return "gemini-2.0-flash"
    # Allow some common Gemini variants
    if m.startswith("gemini-") or m.startswith("gpt-") or m.startswith("gemini"):
        return model
    # default to gemini-2.0-flash as a safe choice
    return model or "gemini-2.0-flash"


def _extract_text_from_response(resp: Any) -> str:
    """
    Try to extract a single text string from various possible response shapes.
    """
    try:
        # If it's None
        if resp is None:
            return ""

        # If response is a dict-like
        if isinstance(resp, dict):
            # Common places:
            for k in ("text", "content", "generated_text", "output", "result"):
                if k in resp and isinstance(resp[k], str):
                    return resp[k].strip()
            # candidates list
            cand = resp.get("candidates") or resp.get("outputs") or resp.get("choices")
            if isinstance(cand, (list, tuple)) and len(cand) > 0:
                first = cand[0]
                if isinstance(first, dict):
                    for k in ("content", "text"):
                        if k in first and isinstance(first[k], str):
                            return first[k].strip()
                if isinstance(first, str):
                    return first.strip()

        # If it's an object with attributes (library objects)
        # google.generativeai responses can have .candidates or .text
        if hasattr(resp, "text") and isinstance(getattr(resp, "text"), str):
            return getattr(resp, "text").strip()

        if hasattr(resp, "candidates"):
            cand = getattr(resp, "candidates")
            if cand:
                # candidate might be objects or dicts
                first = cand[0]
                if hasattr(first, "content"):
                    return getattr(first, "content").strip()
                if isinstance(first, dict) and "content" in first and isinstance(first["content"], str):
                    return first["content"].strip()
                if hasattr(first, "text"):
                    return getattr(first, "text").strip()
                if isinstance(first, str):
                    return first.strip()

        # Some libs use .outputs -> list of dicts with 'content'
        if hasattr(resp, "outputs"):
            outs = getattr(resp, "outputs")
            if outs and isinstance(outs, (list, tuple)):
                first = outs[0]
                if isinstance(first, dict) and "content" in first and isinstance(first["content"], str):
                    return first["content"].strip()

    except Exception:
        # fall through to return empty
        pass

    return ""


# -----------------------------
# Public: enhance_text()
# -----------------------------


def enhance_text(
    prompt: str,
    model: str = "gemini-2.0-flash",
    max_output_tokens: int = 800,
    temperature: float = 0.4,
    verbose: bool = False,
) -> str:
    """
    Produce an expanded, scene-by-scene Manim plan for an SLM.

    Strategy:
    - Normalize model name (map text-bison → gemini-2.0-flash).
    - Try modern .models.generate_content if available.
    - Fallback to genai.generate_text or GenerativeModel(...).generate_content.
    - Extract text from any response shape and return it.
    - Log attempts to outputs/enhancements.jsonl.
    """

    model = _normalize_model_name(model)
    full_prompt = f"{BASE_INSTRUCTION}\n\nUser request:\n{prompt.strip()}"

    record = {
        "model_requested": model,
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
        "attempts": [],
    }

    # Attempt 1: genai.models.generate_content (modern shape)
    try:
        if hasattr(genai, "models") and hasattr(genai.models, "generate_content"):
            if verbose:
                print("Trying genai.models.generate_content(...)")
            # Different genai versions accept either (model=..., contents=...) or (model=..., prompt=...)
            try:
                resp = genai.models.generate_content(
                    model=model,
                    contents=full_prompt,
                    temperature=float(temperature),
                    max_output_tokens=int(max_output_tokens),
                )
            except TypeError:
                # some older wrappers use keyword 'prompt' or different argument shapes
                resp = genai.models.generate_content(
                    model=model,
                    prompt=full_prompt,
                    temperature=float(temperature),
                    max_output_tokens=int(max_output_tokens),
                )
            text = _extract_text_from_response(resp)
            record["attempts"].append({"method": "models.generate_content", "success": bool(text), "sample": text[:200]})
            if text:
                _save_record(prompt, record)
                return text

    except Exception as e:
        record["attempts"].append({"method": "models.generate_content", "error": str(e)})
        # proceed to fallback

    # Attempt 2: genai.generate_text (older style)
    try:
        if hasattr(genai, "generate_text"):
            if verbose:
                print("Trying genai.generate_text(...)")
            resp = genai.generate_text(
                model=model,
                prompt=full_prompt,
                temperature=float(temperature),
                max_output_tokens=int(max_output_tokens),
            )
            text = _extract_text_from_response(resp)
            record["attempts"].append({"method": "generate_text", "success": bool(text), "sample": text[:200]})
            if text:
                _save_record(prompt, record)
                return text
    except Exception as e:
        record["attempts"].append({"method": "generate_text", "error": str(e)})

    # Attempt 3: genai.GenerativeModel(model).generate_content(...)
    try:
        if hasattr(genai, "GenerativeModel"):
            if verbose:
                print("Trying genai.GenerativeModel(...).generate_content(...)")
            gm = genai.GenerativeModel(model)
            # Some versions expect the prompt as the first positional arg or 'contents'
            try:
                resp = gm.generate_content(full_prompt, generation_config={"temperature": float(temperature), "max_output_tokens": int(max_output_tokens)})
            except TypeError:
                # try keyword form
                resp = gm.generate_content(contents=full_prompt, generation_config={"temperature": float(temperature), "max_output_tokens": int(max_output_tokens)})
            text = _extract_text_from_response(resp)
            record["attempts"].append({"method": "GenerativeModel.generate_content", "success": bool(text), "sample": text[:200]})
            if text:
                _save_record(prompt, record)
                return text
    except Exception as e:
        record["attempts"].append({"method": "GenerativeModel.generate_content", "error": str(e)})

    # If all attempts failed, record and return helpful error message for the caller
    _save_record(prompt, record)
    # helpful guidance for the user (keeps original prompt safe)
    guidance = (
        "ERROR: failed to call the installed google.generativeai client with the chosen model.\n"
        "Possible causes:\n"
        " - The model name is not supported by the installed client version.\n"
        " - The library version expects a different method signature.\n\n"
        "Suggested fixes:\n"
        " - Use a Gemini model name such as 'gemini-2.0-flash' (this code maps 'text-bison-001' → 'gemini-2.0-flash').\n"
        " - Upgrade google-generativeai to the latest release in your venv.\n"
        " - Print the saved log at outputs/enhancements.jsonl for details.\n\n"
        f"Original user request: {prompt.strip()}\n"
    )
    return guidance


# -----------------------------
# Example usage (if run as script)
# -----------------------------
if __name__ == "__main__":
    # quick test prompt
    user_prompt = "visualize Pascal's triangle"
    out = enhance_text(user_prompt, model="text-bison-001", verbose=True)
    print("=== ENHANCED OUTPUT ===")
    print(out)
