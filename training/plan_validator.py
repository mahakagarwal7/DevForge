# plan_validator.py
from typing import Any, Dict, Tuple
import math

# Required top-level keys in plan
REQUIRED_PLAN_KEYS = ("title", "description", "scenes")

# Known object types and required params for physics objects
OBJECT_REQUIRED_PARAMS = {
    "Axes": [],
    "Dot": [],
    "Circle": ["radius"],
    "ParametricFunction": ["expr", "t_range"],
}

# For "projectile" type scenes we expect physics params in scene.params.physics
PHYSICS_REQUIRED = ["v0", "angle_degrees"]  # v0 in m/s, angle in degrees

def fill_defaults_for_scene(scene: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """
    Ensure scene has objects, actions, narration. Fill sensible defaults when missing.
    Returns (scene, changed_flag)
    """
    changed = False
    scene.setdefault("id", scene.get("title", "scene").lower().replace(" ", "_"))
    scene.setdefault("title", scene.get("id"))
    if "objects" not in scene or not isinstance(scene["objects"], list):
        scene["objects"] = []
        changed = True
    if "actions" not in scene or not isinstance(scene["actions"], list):
        scene["actions"] = []
        changed = True
    if "narration" not in scene:
        scene["narration"] = ""
        changed = True
    # Ensure every object has id and params
    for obj in scene["objects"]:
        if "id" not in obj:
            obj["id"] = "obj"
            changed = True
        obj.setdefault("params", {})
    # Ensure physics block if scene hint says projectile
    hint = scene.get("hint", "").lower()
    if "projectile" in hint or "parabolic" in hint or "trajectory" in hint:
        phys = scene.setdefault("params", {}).setdefault("physics", {})
        # Fill defaults if missing
        if "v0" not in phys:
            phys["v0"] = 12.0  # default m/s
            changed = True
        if "angle_degrees" not in phys:
            phys["angle_degrees"] = 45.0  # default degrees
            changed = True
        phys.setdefault("g", 9.81)
    return scene, changed

def validate_and_fill_plan(plan: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Validate top-level plan and scenes. Fill defaults when reasonable.
    Returns (filled_plan, diagnostics) where diagnostics contains:
    - success: bool
    - warnings: list[str]
    - errors: list[str]
    - auto_filled: bool (if any defaults were set)
    """
    diagnostics = {"success": True, "warnings": [], "errors": [], "auto_filled": False}
    if not isinstance(plan, dict):
        diagnostics["success"] = False
        diagnostics["errors"].append("plan is not a JSON object")
        return plan, diagnostics
    for k in REQUIRED_PLAN_KEYS:
        if k not in plan:
            diagnostics["errors"].append(f"missing top-level key: {k}")
    if diagnostics["errors"]:
        diagnostics["success"] = False
        return plan, diagnostics

    # Scenes must be list
    scenes = plan.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) == 0:
        diagnostics["errors"].append("plan.scenes must be a non-empty list")
        diagnostics["success"] = False
        return plan, diagnostics

    auto_filled = False
    for i, scene in enumerate(scenes):
        filled_scene, changed = fill_defaults_for_scene(scene)
        plan["scenes"][i] = filled_scene
        if changed:
            auto_filled = True

    diagnostics["auto_filled"] = auto_filled

    # If any scene looks like projectile, check physics params
    for scene in plan["scenes"]:
        hint = scene.get("hint", "") or ""
        if any(w in hint.lower() for w in ("projectile", "parabolic", "trajectory")):
            phys = scene.get("params", {}).get("physics", {})
            missing = [p for p in PHYSICS_REQUIRED if p not in phys]
            if missing:
                diagnostics["warnings"].append(f"scene '{scene.get('title')}' missing physics params: {missing}")
    return plan, diagnostics

# Physics helper: compute flight time & parametric function string for manim
def projectile_parametric_expr(v0: float, angle_deg: float, g: float = 9.81) -> Tuple[str, float]:
    """
    Return a python expression string for ParametricFunction and suggested t_end (flight time).
    x(t) = v0*cos(theta)*t
    y(t) = v0*sin(theta)*t - 0.5*g*t^2
    Returns (expr_string, t_end)
    """
    theta = math.radians(angle_deg)
    vx = v0 * math.cos(theta)
    vy = v0 * math.sin(theta)
    # flight time solve y=0 (excluding t=0): t = 2*vy/g
    t_end = 2.0 * vy / g if g != 0 else 3.0
    # expr string using numpy arrays (to be used in generated code)
    expr = f"lambda t: np.array([{vx:.6f}*t, {vy:.6f}*t - 0.5*{g:.6f}*t**2, 0])"
    return expr, max(0.5, t_end)
