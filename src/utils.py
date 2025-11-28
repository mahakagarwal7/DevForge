# src/utils.py
import os
import json
import hashlib
from typing import Dict, Any

def ensure_directory(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def save_plan(plan: Dict[str, Any], prefix: str = "plan") -> str:
    ensure_directory("outputs/plans")
    h = hashlib.md5(json.dumps(plan, sort_keys=True).encode()).hexdigest()[:8]
    path = os.path.join("outputs", "plans", f"{prefix}_{h}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
    return path

def clean_filename(text: str) -> str:
    import re
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', text)
    return cleaned[:100]