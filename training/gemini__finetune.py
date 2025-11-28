#!/usr/bin/env python3
"""
Simple Gemini/Generative-AI fine-tune helper.

This file shows:
- how to upload a dataset file to Google Cloud Storage (optional)
- how to POST a fine-tune request to a Gemini/Generative API endpoint (placeholder)
- how to poll job status and return result

IMPORTANT:
- Replace the placeholder GEMINI_FINETUNE_ENDPOINT with the real endpoint from your Google product docs.
- Provide credentials via one of:
  - GEMINI_API_KEY (for REST with API key)
  - GOOGLE_APPLICATION_CREDENTIALS (path to a service account JSON) and use oauth2 if required
- This script uses `requests`. Install with: pip install requests google-cloud-storage google-auth
"""

import os
import time
import json
import requests
from typing import Optional, Dict, Any

# Optional: use google-cloud-storage to upload dataset to GCS. Install: pip install google-cloud-storage
try:
    from google.cloud import storage
    _HAS_GCS = True
except Exception:
    _HAS_GCS = False

# Configuration — set as env vars or edit here
GEMINI_API_KEY = os.environ.get("Enter Your own API Key")  # if using API key auth
GEMINI_OAUTH = os.environ.get("GEMINI_OAUTH", "false").lower() == "true"
GEMINI_FINETUNE_ENDPOINT = os.environ.get("GEMINI_FINETUNE_ENDPOINT", "https://api.gemini.example/v1/fineTunes")  # <-- REPLACE with real endpoint
GCS_BUCKET = os.environ.get("GCS_BUCKET")  # optional GCS bucket to upload dataset

# === Helper: upload file to GCS (optional) ===
def upload_to_gcs(local_path: str, bucket_name: str, dest_path: Optional[str] = None) -> str:
    if not _HAS_GCS:
        raise RuntimeError("google-cloud-storage not installed; install with `pip install google-cloud-storage` or set GCS_BUCKET to None")
    dest_path = dest_path or os.path.basename(local_path)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(dest_path)
    blob.upload_from_filename(local_path)
    gcs_uri = f"gs://{bucket_name}/{dest_path}"
    return gcs_uri

# === Helper: send POST request to Gemini finetune endpoint ===
def post_gemini_finetune(payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    """
    Make a POST request to the GEMINI finetune endpoint.

    The actual field names depend on Google's API. This example sends a JSON body
    with 'training_file' pointing to the dataset location (GCS or a hosted URL).
    Replace the payload keys to match your API spec.
    """
    url = GEMINI_FINETUNE_ENDPOINT
    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()

# === Public: launch fine-tune job ===
def launch_gemini_finetune(local_jsonl_path: str,
                           model_name: str,
                           job_name: Optional[str] = None,
                           use_gcs: bool = False,
                           gcs_bucket: Optional[str] = None,
                           extra_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Launch a fine-tune job for Gemini.

    Args:
      local_jsonl_path: path to the JSONL training file on local disk
      model_name: base model to fine-tune (string identifier used by Gemini)
      job_name: optional user label for the job
      use_gcs: if True, upload the dataset to GCS first (requires GCS_BUCKET and google-cloud-storage)
      gcs_bucket: optional override for bucket
      extra_params: driver for API-specific options (learning_rate, epochs, etc.)

    Returns:
      parsed JSON response from the API (usually contains job id and metadata)
    """
    job_name = job_name or f"slm_finetune_{int(time.time())}"
    extra_params = extra_params or {}

    # Optionally upload to GCS and use a gcs:// URI
    dataset_location = local_jsonl_path
    if use_gcs:
        bucket = gcs_bucket or GCS_BUCKET
        if not bucket:
            raise RuntimeError("GCS bucket not configured; set GCS_BUCKET or pass gcs_bucket")
        print(f"Uploading dataset {local_jsonl_path} to GCS bucket {bucket} ...")
        dataset_location = upload_to_gcs(local_jsonl_path, bucket, dest_path=os.path.basename(local_jsonl_path))
        print("Uploaded to:", dataset_location)

    # Build API payload — adapt fields to your Gemini API specification
    payload = {
        "display_name": job_name,
        "base_model": model_name,
        "training_data": {"uri": dataset_location},  # placeholder shape — adapt to actual API
        "hyperparameters": {
            "epochs": int(extra_params.get("epochs", 3)),
            "batch_size": int(extra_params.get("batch_size", 8)),
            "learning_rate": float(extra_params.get("learning_rate", 2e-4))
        },
        # add any other API-specific options...
    }

    # Build headers (API key or OAuth)
    headers = {"Content-Type": "application/json"}
    if GEMINI_API_KEY:
        headers["Authorization"] = f"Bearer {GEMINI_API_KEY}"
    # If using OAuth (service account), the requests call should include an OAuth access token instead.
    # For a production implementation use google-auth to fetch an access token and set Authorization header.

    # === GEMINI API CALL HERE ===
    print("Calling Gemini fine-tune API at:", GEMINI_FINETUNE_ENDPOINT)
    result = post_gemini_finetune(payload=payload, headers=headers)
    # === END GEMINI API CALL ===

    return result

# === Polling helper ===
def poll_gemini_job_status(job_id: str, poll_endpoint_base: Optional[str] = None, interval: int = 10, timeout: int = 3600) -> Dict[str, Any]:
    """
    Poll job state until done. The job status endpoint and response structure vary by API.
    Replace the url format and parsing with the correct schema for your Gemini API.
    """
    poll_base = poll_endpoint_base or GEMINI_FINETUNE_ENDPOINT.rstrip("/")  # default fallback
    # Example: GET {poll_base}/{job_id}
    url = f"{poll_base}/{job_id}"
    headers = {"Content-Type": "application/json"}
    if GEMINI_API_KEY:
        headers["Authorization"] = f"Bearer {GEMINI_API_KEY}"

    start = time.time()
    while True:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", data.get("state", "")).lower()
        print(f"[poll] status={status}")
        if status in ("succeeded", "completed", "done"):
            return data
        if status in ("failed", "error"):
            raise RuntimeError(f"Fine-tune job failed: {data}")
        if time.time() - start > timeout:
            raise TimeoutError("Timed out waiting for gemini fine-tune job")

        time.sleep(interval)
