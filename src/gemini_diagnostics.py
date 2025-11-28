#!/usr/bin/env python3
"""
Run a set of diagnostics to find why Generative Language / Gemini HTTP calls fail.
Run this in the same activated venv and shell you use to run your CLI.

Usage:
  python src/gemini_diagnostics.py

It will print (redact API keys if you paste):
- python executable and sys.path[0:6]
- GEMINI_API_KEY present? GEMINI_TEXT_ENDPOINT
- last 5 lines of outputs/enhancements.jsonl (if present)
- direct HTTP POST to v1 for models: text-bison-001 and gemini-2.0-flash
- attempt to import genai clients and (optionally) make a small library call
"""
import os, sys, json, traceback, requests
from pathlib import Path

def print_header(s):
    print("\n" + "="*8 + " " + s + " " + "="*8)

print_header("Python & env")
print("python executable:", sys.executable)
print("cwd:", os.getcwd())
print("sys.path (first 6):")
for p in sys.path[:6]:
    print("  ", p)

print_header("Env vars")
print("GEMINI_API_KEY set:", bool(os.environ.get("GEMINI_API_KEY")))
print("GEMINI_TEXT_ENDPOINT:", os.environ.get("GEMINI_TEXT_ENDPOINT"))
print("Note: do NOT paste API keys publicly. Redact if you share output.")

RESP_FILE = Path("outputs/enhancements.jsonl")
if RESP_FILE.exists():
    print_header("Last entries in outputs/enhancements.jsonl (up to 5)")
    try:
        lines = RESP_FILE.read_text(encoding="utf-8").strip().splitlines()
        for ln in lines[-5:]:
            try:
                j = json.loads(ln)
                # hide API key in url if present
                rec = j.get("record", j.get("response", j.get("record", {})))
                # print only some fields
                print(json.dumps({
                    "timestamp": j.get("timestamp"),
                    "prompt": j.get("prompt") or j.get("original"),
                    "record_sample": {k: rec.get(k) for k in list(rec)[:3]}
                }, indent=2, ensure_ascii=False)[:1000])
            except Exception:
                print("RAW:", ln[:1000])
    except Exception as e:
        print("Could not read enhancements.jsonl:", e)
else:
    print("No outputs/enhancements.jsonl file found at", RESP_FILE.resolve())

def http_test(model_id):
    print_header(f"HTTP test -> model={model_id}")
    # Build v1 URL; prefer env endpoint if set but force v1 replacement
    env = os.environ.get("GEMINI_TEXT_ENDPOINT", "").strip()
    if env:
        url = env
        if "v1beta2" in url:
            url = url.replace("v1beta2", "v1")
    else:
        url = f"https://generativelanguage.googleapis.com/v1/models/{model_id}:generate"
    print("Using URL:", url)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("No GEMINI_API_KEY set; skipping HTTP test.")
        return
    # append ?key= if missing
    if "?" in url:
        url_with_key = url + "&key=" + api_key
    else:
        url_with_key = url + "?key=" + api_key
    payload = {"prompt": {"text": "Enhance: Explain photosynthesis as a 3-scene animation."}, "maxOutputTokens": 256}
    try:
        r = requests.post(url_with_key, json=payload, headers={"Content-Type":"application/json"}, timeout=30)
        print("HTTP status:", r.status_code)
        try:
            print("Response JSON (truncated):", json.dumps(r.json(), indent=2)[:1500])
        except Exception:
            print("Response text (truncated):", r.text[:1500])
    except Exception as e:
        print("HTTP request raised exception:", repr(e))
        traceback.print_exc()

# try both common model names
for mid in ("text-bison-001", "gemini-2.0-flash"):
    http_test(mid)

print_header("GenAI library test (import + optional call)")
# Try importing the two common client packages and do a safe non-destructive call if possible
import_errs = {}
for name, import_stmt in [("from google import genai", "from google import genai"), ("google.generativeai", "import google.generativeai")]:
    try:
        if "from google import genai" in import_stmt:
            from google import genai as gclient  # type: ignore
            print("Imported: from google import genai -> OK")
            try:
                # Try a harmless call if client provides a lightweight format check (do not send user prompt)
                if hasattr(gclient, "Client"):
                    c = gclient.Client(api_key=os.environ.get("GEMINI_API_KEY"))
                    print("Created genai.Client -> OK")
                else:
                    print("genai has no Client attribute; skipping client construct.")
            except Exception as e:
                print("genai.Client construction error (non-fatal):", repr(e))
        else:
            import google.generativeai as gg  # type: ignore
            print("Imported: google.generativeai -> OK")
            try:
                if hasattr(gg, "configure"):
                    gg.configure(api_key=os.environ.get("GEMINI_API_KEY"))
                    print("Configured google.generativeai with API key (no network call).")
            except Exception as e:
                print("google.generativeai configure error (non-fatal):", repr(e))
    except Exception as e:
        import_errs[name] = repr(e)
        print(f"{name} import FAILED ->", repr(e))

if import_errs:
    print_header("GenAI import errors")
    for k,v in import_errs.items():
        print(k, "->", v)

print_header("Diagnostics complete")