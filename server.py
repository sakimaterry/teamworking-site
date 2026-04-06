#!/usr/bin/env python3
"""TeamWorking by TechNexus — Flask server."""
from flask import Flask, send_from_directory, jsonify, request
import os

STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=None)

@app.route("/healthz")
def healthz():
    return "ok"

@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")

@app.route("/robots.txt")
def robots():
    return send_from_directory(STATIC_DIR, "robots.txt", mimetype="text/plain")

@app.route("/api/contact", methods=["POST"])
def api_contact():
    """Store contact form submission."""
    import json
    data = request.get_json() or {}
    DATA_DIR = os.path.join(STATIC_DIR, "data")
    os.makedirs(DATA_DIR, exist_ok=True)
    submissions_file = os.path.join(DATA_DIR, "submissions.json")
    submissions = []
    if os.path.exists(submissions_file):
        with open(submissions_file) as f:
            submissions = json.load(f)
    from datetime import datetime
    data["submitted_at"] = datetime.utcnow().isoformat()
    submissions.append(data)
    with open(submissions_file, "w") as f:
        json.dump(submissions, f, indent=2)
    return jsonify({"ok": True})

@app.route("/<path:path>")
def static_files(path):
    full = os.path.join(STATIC_DIR, path)
    if os.path.isfile(full):
        return send_from_directory(STATIC_DIR, path)
    # SPA fallback — return index for clean URLs
    if not "." in path.split("/")[-1]:
        page = path.rstrip("/") + ".html"
        if os.path.isfile(os.path.join(STATIC_DIR, page)):
            return send_from_directory(STATIC_DIR, page)
    return send_from_directory(STATIC_DIR, "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
