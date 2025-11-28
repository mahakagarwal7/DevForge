# src/job_manager.py
"""
Simple background Job Manager to schedule render jobs and persist job metadata.
Uses ThreadPoolExecutor to run animator.generate in a background thread.
Jobs are stored in outputs/jobs.json (best-effort persistence).
"""
import os
import json
import uuid
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Any, Optional

# Try to import animator (repo layout: src is package)
try:
    from .animator import EducationalAnimator
except Exception:
    # last-resort import (if run from repo root where src is on sys.path)
    from animator import EducationalAnimator  # type: ignore

JOBS_FILE = os.path.join("outputs", "jobs.json")
os.makedirs("outputs", exist_ok=True)

class JobManager:
    def __init__(self, max_workers: int = 2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.futures: Dict[str, Future] = {}
        self._load_jobs()

    def _load_jobs(self):
        if os.path.exists(JOBS_FILE):
            try:
                with open(JOBS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Basic recovery: keep metadata, but not live futures
                for jid, meta in data.items():
                    self.jobs[jid] = meta
            except Exception:
                # ignore malformed jobs file
                pass

    def _persist_jobs(self):
        try:
            with open(JOBS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.jobs, f, indent=2)
        except Exception:
            pass  # best-effort

    def submit_render(self, description: str) -> str:
        job_id = uuid.uuid4().hex
        now = time.time()
        # initial job metadata
        self.jobs[job_id] = {
            "id": job_id,
            "description": description,
            "status": "queued",
            "created_at": now,
            "started_at": None,
            "finished_at": None,
            "video_path": None,
            "plan_file": None,
            "error": None
        }
        self._persist_jobs()

        # Submit work
        future = self.executor.submit(self._run_job, job_id, description)
        self.futures[job_id] = future
        return job_id

    def _run_job(self, job_id: str, description: str) -> None:
        self.jobs[job_id]["status"] = "running"
        self.jobs[job_id]["started_at"] = time.time()
        self._persist_jobs()
        try:
            animator = EducationalAnimator()
            video_path, plan = animator.generate(description)
            self.jobs[job_id]["video_path"] = video_path
            # plan may include _saved_plan_file
            self.jobs[job_id]["plan_file"] = plan.get("_saved_plan_file") if isinstance(plan, dict) else None
            self.jobs[job_id]["status"] = "finished" if video_path else "failed"
            if not video_path:
                self.jobs[job_id]["error"] = "Renderer returned no video"
        except Exception as e:
            self.jobs[job_id]["status"] = "failed"
            self.jobs[job_id]["error"] = str(e)
        finally:
            self.jobs[job_id]["finished_at"] = time.time()
            self._persist_jobs()

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.jobs.get(job_id)

    def list_jobs(self):
        return list(self.jobs.values())