#!/usr/bin/env python3
"""
plan_validator.py

Validation, normalization, and semantic->concrete mapping for scene plans.

Responsibilities:
- Enforce allowed object types
- Map semantic types (e.g., "planet", "ball", "graph") to allowed types
- Fill sensible numeric defaults
- Provide physics helpers for projectiles
- Return diagnostics (errors/warnings/auto_filled/confidence)
"""
from typing import Any, Dict, List, Tuple, Optional
import math

ALLOWED_TYPES = {"Axes", "Dot", "Circle", "Square", "ParametricFunction", "Text", "Vector"}
# Semantic map: maps user-friendly semantic types -> (concrete_type, default_params)
SEMANTIC_MAP = {
    "planet": ("Circle", {"radius": 0.25}),
    "ball": ("Dot", {"color": "YELLOW"}),
    "dot": ("Dot", {}),
    "point": ("Dot", {}),
    "trajectory": ("ParametricFunction", {}),
    "path": ("ParametricFunction", {}),
    "curve": ("ParametricFunction", {}),
    "graph": ("Axes", {}),
    "axes": ("Axes", {}),
    "label": ("Text", {}),
    "arrow": ("Vector", {}),
    "vector": ("Vector", {}),
    "circle": ("Circle", {}),
    "square": ("Square", {}),
}

REQUIRED_TOP_LEVEL = ["title", "description", "scenes"]

PHYSICS_REQUIRED = ["v0", "angle_degrees"]

def _ensure_scene_structure(scene: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """
    Ensure scene has keys: id, title, objects(list), actions(list), params(dict), hint(str), narration.
    Returns (scene, changed_flag)
    """
    changed = False
    if not isinstance(scene, dict):
        scene = {"id": "scene", "title": "scene", "objects": [], "actions": [], "params": {}, "hint": "", "narration": ""}
        return scene, True

    if "id" not in scene or not scene["id"]:
        scene["id"] = scene.get("title", "scene").lower().replace(" ", "_")
        changed = True
    scene.setdefault("title", scene["id"])
    if "objects" not in scene or not isinstance(scene["objects"], list):
        scene["objects"] = []
        changed = True
    if "actions" not in scene or not isinstance(scene["actions"], list):
        scene["actions"] = []
        changed = True
    scene.setdefault("params", {})
    scene.setdefault("hint", "")
    scene.setdefault("narration", "")
    # Ensure object shape
    for obj in scene["objects"]:
        if not isinstance(obj, dict):
            # replace with a default Dot
            idx = scene["objects"].index(obj)
            scene["objects"][idx] = {"id": f"obj_{idx}", "type": "Dot", "params": {}}
            changed = True
            continue
        if "id" not in obj or not obj["id"]:
            obj["id"] = f"obj_{scene['objects'].index(obj)}"
            changed = True
        obj.setdefault("params", {})
    return scene, changed

def _map_semantic_object(obj: Dict[str, Any], diagnostics: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    If obj.type is not in ALLOWED_TYPES, try to map semantics (type lowercased) to concrete type.
    If mapping fails, set to Dot and record warning.
    """
    typ = (obj.get("type") or "").strip()
    if not typ:
        diagnostics.setdefault("warnings", []).append(f"object '{obj.get('id')}' missing type; defaulting to Dot")
        obj["type"] = "Dot"
        obj.setdefault("params", {})
        return obj

    if typ in ALLOWED_TYPES:
        return obj

    # try semantic mapping
    key = typ.lower()
    if key in SEMANTIC_MAP:
        concrete, defaults = SEMANTIC_MAP[key]
        obj["type"] = concrete
        # merge defaults into params if not present
        for k, v in defaults.items():
            obj["params"].setdefault(k, v)
        diagnostics.setdefault("info", []).append(f"mapped semantic '{typ}' -> '{concrete}' for object '{obj.get('id')}'")
        return obj

    # try if 'type' contains semantic words like "planet", "ball"
    for sem, (concrete, defaults) in SEMANTIC_MAP.items():
        if sem in key:
            obj["type"] = concrete
            for k, v in defaults.items():
                obj["params"].setdefault(k, v)
            diagnostics.setdefault("info", []).append(f"mapped semantic '{typ}' -> '{concrete}' for object '{obj.get('id')}'")
            return obj

    # fail-safe
    diagnostics.setdefault("warnings", []).append(f"unsupported object type '{typ}' -> defaulting to Dot for object '{obj.get('id')}'")
    obj["type"] = "Dot"
    obj.setdefault("params", {})
    return obj

def _fill_physics_defaults(scene: Dict[str, Any], diagnostics: Dict[str, List[str]]) -> bool:
    """
    For projectile-like scenes (hint contains projectile/trajectory) ensure physics params exist.
    Fill defaults and return True if changed.
    """
    changed = False
    hint = (scene.get("hint") or "").lower()
    if any(w in hint for w in ("projectile", "trajectory", "parabolic", "parabola", "launch")):
        params = scene.setdefault("params", {})
        phys = params.setdefault("physics", {})
        if "v0" not in phys:
            phys["v0"] = 12.0
            diagnostics.setdefault("warnings", []).append(f"auto-filled v0=12.0 for scene '{scene.get('title')}'")
            changed = True
        if "angle_degrees" not in phys:
            phys["angle_degrees"] = 45.0
            diagnostics.setdefault("warnings", []).append(f"auto-filled angle_degrees=45.0 for scene '{scene.get('title')}'")
            changed = True
        phys.setdefault("g", 9.81)
    return changed

def validate_and_fill_plan(plan: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Validate plan structure, map semantics, fill defaults.
    Returns (filled_plan_dict_or_original, diagnostics)
    diagnostics: {success:bool, errors:list, warnings:list, info:list, auto_filled:bool, confidence: 'high'|'low'}
    """
    diagnostics: Dict[str, Any] = {"success": True, "errors": [], "warnings": [], "info": [], "auto_filled": False, "confidence": "high"}

    if not isinstance(plan, dict):
        diagnostics["success"] = False
        diagnostics["errors"].append("Plan is not a JSON object.")
        return plan, diagnostics

    # check top-level keys
    for k in REQUIRED_TOP_LEVEL:
        if k not in plan:
            diagnostics["errors"].append(f"Missing top-level key: {k}")
    if diagnostics["errors"]:
        diagnostics["success"] = False
        return plan, diagnostics

    # Validate scenes
    auto_filled = False
    scenes = plan.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) == 0:
        diagnostics["errors"].append("plan.scenes must be a non-empty list.")
        diagnostics["success"] = False
        return plan, diagnostics

    for i, sc in enumerate(scenes):
        sc, changed = _ensure_scene_structure(sc)
        if changed:
            auto_filled = True
        # map object types & fill defaults
        for obj in sc.get("objects", []):
            prev_type = obj.get("type")
            obj = _map_semantic_object(obj, diagnostics)
            if obj.get("type") != prev_type:
                auto_filled = True
        # fill physics if hint suggests
        if _fill_physics_defaults(sc, diagnostics):
            auto_filled = True
        # save back
        plan["scenes"][i] = sc

    diagnostics["auto_filled"] = auto_filled
    # Confidence low if auto-filled significant numeric params
    diagnostics["confidence"] = "low" if auto_filled else "high"
    return plan, diagnostics

# Physics helpers
def projectile_parametric_expr(v0: float, angle_deg: float, g: float = 9.81) -> Tuple[str, float]:
    """
    Return a Python expression string for ParametricFunction and t_end (flight time).
    x(t) = v0*cos(theta)*t
    y(t) = v0*sin(theta)*t - 0.5*g*t^2
    Returns (expr_string, t_end)
    """
    theta = math.radians(angle_deg)
    vx = v0 * math.cos(theta)
    vy = v0 * math.sin(theta)
    t_end = 2.0 * vy / g if g != 0 else 3.0
    expr = f"lambda t: np.array([{vx:.6f}*t, {vy:.6f}*t - 0.5*{g:.6f}*t**2, 0])"
    return expr, max(0.5, t_end)
