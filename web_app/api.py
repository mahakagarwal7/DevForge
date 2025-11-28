# web_app/api.py
"""
FastAPI endpoints with Gemini prompt-enhancement integration.

- POST /generate/scenes: calls Gemini to enhance the input, then runs the planner and returns the plan.
- POST /render: calls Gemini to enhance the input, enqueues a render job with the enhanced description.
- GET  /status/{job_id}: job status
- GET  /jobs: list jobs
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
import os, sys, traceback

# Ensure repo src is importable
root = os.getcwd()
src_path = os.path.join(root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import planner (use your planner implementation)
try:
    from planner import SimplePlanner  # type: ignore
    PlannerClass = SimplePlanner
except Exception:
    try:
        from universal_planner import UniversalPlanner  # type: ignore
        PlannerClass = UniversalPlanner
    except Exception:
        PlannerClass = None

# Job manager from earlier scaffolding
try:
    from job_manager import JobManager  # type: ignore
except Exception:
    JobManager = None

# Gemini client (local wrapper)
try:
    from gemini_client import enhance_text  # type: ignore
except Exception:
    # If gemini_client missing, define passthrough
    def enhance_text(prompt: str, model: str = "gemini", max_output_tokens: int = 256, temperature: float = 0.0) -> str:
        return prompt

app = FastAPI(title="Text→Scene Planner & Render API (with Gemini enhancement)")

planner = PlannerClass() if PlannerClass else None
job_manager = JobManager(max_workers=2) if JobManager else None

class GenerateRequest(BaseModel):
    description: str

class RenderRequest(BaseModel):
    description: str

@app.post("/generate/scenes", response_model=Dict[str, Any])
def generate_scenes(req: GenerateRequest):
    try:
        original = req.description
        # === GEMINI ENHANCEMENT CALL HERE ===
        enhanced = enhance_text(original, model="gemini", max_output_tokens=256, temperature=0.0)
        # === END GEMINI ENHANCEMENT CALL ===

        if not planner:
            raise HTTPException(status_code=500, detail="Planner not available")
        plan = planner.plan_universal_scene(enhanced if isinstance(enhanced, str) else original)
        # include both original and enhanced in the response for traceability
        plan_meta = {"original_input": original, "enhanced_input": enhanced, "plan": plan}
        return plan_meta
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "trace": tb})

@app.post("/render")
def render(req: RenderRequest):
    try:
        if not job_manager:
            raise HTTPException(status_code=500, detail="Job manager not available")

        original = req.description
        # === GEMINI ENHANCEMENT CALL HERE ===
        enhanced = enhance_text(original, model="gemini", max_output_tokens=256, temperature=0.0)
        # === END GEMINI ENHANCEMENT CALL ===

        # Enqueue the enhanced description (store original/enhanced in job metadata)
        job_id = job_manager.submit_render(enhanced)
        # Save original/enhanced mapping into job metadata for traceability
        meta = job_manager.get_status(job_id)
        if meta is not None:
            meta["original_input"] = original
            meta["enhanced_input"] = enhanced
        return {"job_id": job_id, "status": "queued", "enhanced_input": enhanced}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{job_id}")
def job_status(job_id: str):
    meta = job_manager.get_status(job_id) if job_manager else None
    if not meta:
        raise HTTPException(status_code=404, detail="Job not found")
    return meta

@app.get("/jobs")
def list_jobs():
    return job_manager.list_jobs() if job_manager else []

@app.get("/")
def root():
    return {"status": "ok", "endpoints": ["/generate/scenes (POST)", "/render (POST)", "/status/{job_id} (GET)"]}