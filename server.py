#!/usr/bin/env python3
"""TeamWorking by TechNexus — DB-driven satellite.

Renders content authored in technexus.com/admin and stored in the shared
Postgres tables `tw_pages` / `tw_articles` (isolated from technexus.com's own
pages/articles). Falls back to a local SQLite DB when DATABASE_URL is unset,
so the app is runnable/testable without the shared database.
"""
import os, json
from datetime import datetime
from flask import (Flask, render_template, send_from_directory, abort,
                   redirect, jsonify, request)

app = Flask(__name__, template_folder="templates", static_folder=None)
HERE = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# ── DB layer (Postgres in prod, SQLite fallback for local dev/testing) ──
if DATABASE_URL:
    import psycopg2, psycopg2.extras
    def query(sql, params=()):
        c = psycopg2.connect(DATABASE_URL)
        try:
            cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(sql.replace("?", "%s"), params)
            return [dict(r) for r in cur.fetchall()]
        finally:
            c.close()
else:
    import sqlite3
    DB_PATH = os.environ.get("TW_SQLITE", os.path.join(HERE, "tw_local.db"))
    def query(sql, params=()):
        c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in c.execute(sql, params).fetchall()]
        finally:
            c.close()

def one(sql, params=()):
    rows = query(sql, params)
    return rows[0] if rows else None

# Curated top nav (slugs resolve to tw_pages). Book a Tour is an external CTA.
NAV = [
    ("Workspaces", "/workspaces"), ("Membership", "/membership"),
    ("Amenities", "/amenities"), ("Events", "/events"),
    ("Ecosystem", "/ecosystem"), ("Blog", "/blog"),
]
BOOK_TOUR = "https://calendly.com/teamworking"

@app.context_processor
def inject_globals():
    return {"NAV": NAV, "BOOK_TOUR": BOOK_TOUR, "year": datetime.utcnow().year}

# ── Routes ──
@app.route("/healthz")
def healthz():
    return "ok"

@app.route("/robots.txt")
def robots():
    return send_from_directory(HERE, "robots.txt", mimetype="text/plain")

@app.route("/images/<path:p>")
def images(p):
    return send_from_directory(os.path.join(HERE, "images"), p)

@app.route("/")
def home():
    page = one("SELECT * FROM tw_pages WHERE slug='home' AND published=1")
    return render_template("home.html", page=page)

@app.route("/blog")
def blog_index():
    posts = query("SELECT title,slug,excerpt,meta_description,thumbnail_url,author,"
                  "published_at,external_url FROM tw_articles WHERE published=1 "
                  "ORDER BY published_at DESC")
    return render_template("blog_index.html", posts=posts)

@app.route("/blog/<slug>")
def article(slug):
    a = one("SELECT * FROM tw_articles WHERE slug=? AND published=1", (slug,))
    if not a:
        abort(404)
    if a.get("external_url"):
        return redirect(a["external_url"], code=302)
    return render_template("article.html", a=a)

@app.route("/<slug>")
def page(slug):
    p = one("SELECT * FROM tw_pages WHERE slug=? AND published=1", (slug,))
    if not p:
        abort(404)
    if p.get("page_type") == "redirect" and p.get("redirect_to"):
        return redirect(p["redirect_to"], code=302)
    if p.get("page_type") == "external" and p.get("external_url"):
        return redirect(p["external_url"], code=302)
    return render_template("page.html", page=p)

@app.route("/api/contact", methods=["POST"])
def api_contact():
    data = request.get_json() or {}
    data["submitted_at"] = datetime.utcnow().isoformat()
    d = os.path.join(HERE, "data"); os.makedirs(d, exist_ok=True)
    fp = os.path.join(d, "submissions.json")
    subs = json.load(open(fp)) if os.path.exists(fp) else []
    subs.append(data); json.dump(subs, open(fp, "w"), indent=2)
    return jsonify({"ok": True})

@app.errorhandler(404)
def not_found(e):
    return render_template("page.html", page={"title": "Page not found",
            "body": "<p>Sorry, that page doesn’t exist. "
                    "<a href='/'>Return home</a>.</p>"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 80)))
