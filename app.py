#!/usr/bin/env python3
"""
Podcast Cleaner Web App
Flask web interface for transcribing and cleaning YouTube videos.
"""

import os
import threading
import uuid
from flask import Flask, render_template, request, jsonify, Response

from clean_podcast import process_video, extract_video_id

app = Flask(__name__)

# Store jobs in memory (for simplicity)
jobs = {}

# Cache completed transcripts by video ID
transcript_cache = {}


@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")


@app.route("/transcribe", methods=["POST"])
def transcribe():
    """Start a transcription job."""
    data = request.get_json()
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400

    # Extract video ID and check cache
    try:
        video_id = extract_video_id(url)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    # If we have a cached result, return it immediately
    if video_id in transcript_cache:
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            "status": "completed",
            "progress": "Loaded from cache",
            "result": transcript_cache[video_id],
            "error": None,
        }
        return jsonify({"job_id": job_id})

    # Get API key from environment
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return jsonify({"error": "GOOGLE_API_KEY not configured"}), 500

    # Create job
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "processing",
        "progress": "Starting...",
        "result": None,
        "error": None,
    }

    # Run in background thread
    def run_job():
        try:
            def progress_callback(message):
                jobs[job_id]["progress"] = message

            result = process_video(url, api_key, progress_callback)
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["result"] = result
            # Cache the result
            transcript_cache[video_id] = result
        except Exception as e:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)

    thread = threading.Thread(target=run_job)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id):
    """Check job status."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    response = {
        "status": job["status"],
        "progress": job["progress"],
    }

    if job["status"] == "completed":
        response["result"] = {
            "title": job["result"]["title"],
            "markdown": job["result"]["markdown"],
            "filename": job["result"]["filename"],
        }
    elif job["status"] == "error":
        response["error"] = job["error"]

    return jsonify(response)


@app.route("/download/<job_id>")
def download(job_id):
    """Download the transcript as a markdown file."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job["status"] != "completed":
        return jsonify({"error": "Job not completed"}), 400

    result = job["result"]
    # Use ASCII-safe filename and UTF-8 encoded filename for broader compatibility
    safe_filename = result["filename"].encode("ascii", "ignore").decode()
    if not safe_filename:
        safe_filename = "transcript.md"

    return Response(
        result["markdown"],
        mimetype="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=\"{safe_filename}\"; filename*=UTF-8''{result['filename']}"
        },
    )


if __name__ == "__main__":
    # Load .env file if it exists
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value

    print("Starting Podcast Cleaner Web App...")
    print("Open http://127.0.0.1:8080 in your browser")
    app.run(debug=True, host="0.0.0.0", port=8080)
