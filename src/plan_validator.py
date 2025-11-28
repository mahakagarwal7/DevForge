#!/usr/bin/env python3
"""
Plan validator using the JSON Schema at src/plan_schema.json.

Functions:
- load_schema() -> dict
- validate_plan(obj_or_text) -> (is_valid: bool, plan_dict_or_none, errors: list[str])

Usage:
  from src.plan_validator import validate_plan
  ok, plan, errors = validate_plan(maybe_json_text)
"""
import json
from pathlib import Path
from typing import Any, Tuple, Optional, List

try:
    from jsonschema import Draft7Validator, exceptions as js_exceptions
except Exception as e:
    raise RuntimeError("jsonschema is required. Install with: pip install jsonschema") from e

_SCHEMA_PATH = Path(__file__).resolve().parent / "plan_schema.json"

def load_schema() -> dict:
    with _SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

_SCHEMA = load_schema()
_VALIDATOR = Draft7Validator(_SCHEMA)

def _make_error_messages(validator) -> List[str]:
    errors = []
    for e in sorted(validator.iter_errors(validator.instance if hasattr(validator, "instance") else {}), key=lambda x: x.path):
        path = ".".join([str(p) for p in e.absolute_path]) or "<root>"
        errors.append(f"{path}: {e.message}")
    return errors

def validate_plan(obj_or_text: Any) -> Tuple[bool, Optional[dict], List[str]]:
    """
    Validate a plan object or JSON text.

    Returns:
      (is_valid, plan_dict_or_none, errors_list)
    """
    plan = None
    errors: List[str] = []
    # parse if string
    if isinstance(obj_or_text, str):
        try:
            plan = json.loads(obj_or_text)
        except Exception as e:
            return False, None, [f"Invalid JSON: {e}"]
    elif isinstance(obj_or_text, dict):
        plan = obj_or_text
    else:
        return False, None, [f"Unsupported input type: {type(obj_or_text)}"]

    try:
        # use Draft7Validator to collect all errors
        validator = Draft7Validator(_SCHEMA)
        errs = list(validator.iter_errors(plan))
        if errs:
            for e in errs:
                path = ".".join([str(p) for p in e.absolute_path]) or "<root>"
                errors.append(f"{path}: {e.message}")
            return False, None, errors
        # successful
        return True, plan, []
    except Exception as e:
        return False, None, [f"Schema validation error: {e}"]