#!/usr/bin/env python3
"""
Call your Gemini text endpoint to "enhance" a user prompt and print the result.

Usage:
  python src/print_gemini_enhancement.py --prompt "Explain quadratic equation"

This script expects these environment variables (set them before running):
  GEMINI_API_KEY         - your Gemini API key (Bearer)
  GEMINI_TEXT_ENDPOINT   - the Gemini text/generation REST endpoint URL

The exact request/response shape may vary by Gemini product; adapt payload parsing as needed.
"""
import os
import argparse
import requests
import json
from typing import Optional

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_TEXT_ENDPOINT = os.environ.get("GEMINI_TEXT_ENDPOINT", "https://your.gemini.endpoint/v1/generate")

def _parse_response_for_text(resp_json: dict) -> Optional[str]:
    # Try common shapes; adapt if your Gemini returns a different structure
    if isinstance(resp_json.get("candidates"), list) and resp_json["candidates"]:
        cand = resp_json["candidates"][0]
        if isinstance(cand, dict) and "content" in cand:
            return cand["content"]
        if isinstance(cand, str):
            return cand
    for key in ("output", "generated_text", "text", "content"):
        if key in resp_json and isinstance(resp_json[key], str):
            return resp_json[key]
    if isinstance(resp_json.get("result"), dict):
        for key in ("content","text","output"):
            if key in resp_json["result"]:
                return resp_json["result"][key]
    return None

def enhance_with_gemini(prompt: str, model: str = "gemini", max_output_tokens: int = 256, temperature: float = 0.0) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set in environment")
    url = GEMINI_TEXT_ENDPOINT
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "input": prompt,
        "instruction": "Rewrite and expand this user description into a clear, step-by-step scene description suitable for creating an educational animated video. List visual elements and key steps.",
        "max_output_tokens": int(max_output_tokens),
        "temperature": float(temperature)
    }

    # === GEMINI API CALL HERE ===
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # === END GEMINI API CALL ===

    enhanced = _parse_response_for_text(data)
    if enhanced:
        return enhanced
    # Fallback: pretty-print api json as string (without secrets)
    return json.dumps(data, indent=2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", "-p", type=str, help="User prompt to enhance", required=False)
    parser.add_argument("--model", type=str, default="gemini", help="Gemini model id")
    parser.add_argument("--max_output_tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.0)
    args = parser.parse_args()

    if args.prompt:
        prompt = args.prompt
    else:
        prompt = input("Enter prompt: ")

    print("Original input:")
    print(prompt)
    try:
        enhanced = enhance_with_gemini(prompt, model=args.model, max_output_tokens=args.max_output_tokens, temperature=args.temperature)
        print("\nEnhanced output (from Gemini):")
        print(enhanced)
    except Exception as e:
        print("Error calling Gemini API:", str(e))

if __name__ == "__main__":
    main()