#!/usr/bin/env python3
"""TeamWorking by TechNexus — DB-driven satellite.

Renders content authored in technexus.com/admin and stored in the shared
Postgres tables `tw_pages` / `tw_articles` (isolated from technexus.com's own
pages/articles). Falls back to a local SQLite DB when DATABASE_URL is unset,
so the app is runnable/testable without the shared database.
"""
import os, json, re
from datetime import datetime

# Rewrite hotlinked teamworking.vc images to locally-rehosted copies (/images/wp/).
_WP_IMG = re.compile(r'https?://teamworking\.vc/wp-content/uploads/([^"\'\s)]+)')
def rehost(s):
    return _WP_IMG.sub(lambda m: '/images/wp/' + m.group(1).replace('/', '-'), s) if s else s
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
    posts = query("SELECT title,slug,excerpt,meta_description,published_at,external_url "
                  "FROM tw_articles WHERE published=1 AND external_url IS NULL "
                  "ORDER BY published_at DESC LIMIT 6")
    return render_template("home.html", posts=posts)

# Per-page hero images (real TeamWorking photos), by slug
PAGE_HERO = {
    "amenities": "/images/kitchen.jpg", "workspaces": "/images/office-suite.jpg",
    "membership": "/images/office.jpg", "meeting-center": "/images/conference.jpg",
    "executive-meeting-experience": "/images/conference.jpg", "events": "/images/event-space.jpg",
    "ecosystem": "/images/collaborative.jpg", "community-partners": "/images/collaborative.jpg",
    "member-resource-page-teamworking": "/images/office.jpg", "sponsorship": "/images/event-space.jpg",
    "virtual-tour": "/images/office.jpg", "referral-program": "/images/collaborative.jpg",
    "photo-gallery": "/images/office-suite.jpg",
}
DEFAULT_HERO = "/images/hero.jpg"

@app.route("/blog")
def blog_index():
    posts = query("SELECT title,slug,excerpt,meta_description,thumbnail_url,author,"
                  "published_at,external_url FROM tw_articles WHERE published=1 "
                  "ORDER BY published_at DESC")
    for p in posts:
        p["thumbnail_url"] = rehost(p.get("thumbnail_url"))
    return render_template("blog_index.html", posts=posts, hero_title="Insights",
                           hero_sub="News, newsletters, and thought leadership from the TeamWorking community.",
                           hero_image=DEFAULT_HERO)

@app.route("/blog/<slug>")
def article(slug):
    a = one("SELECT * FROM tw_articles WHERE slug=? AND published=1", (slug,))
    if not a:
        abort(404)
    if a.get("external_url"):
        return redirect(a["external_url"], code=302)
    a["body"] = rehost(a.get("body"))
    a["thumbnail_url"] = rehost(a.get("thumbnail_url"))
    sub = " · ".join(x for x in [a.get("author"), (str(a["published_at"])[:10] if a.get("published_at") else None)] if x)
    return render_template("article.html", a=a, hero_title=a["title"], hero_sub=sub,
                           hero_image=a.get("thumbnail_url") or "/images/collaborative.jpg")

@app.route("/assets/blocks.css")
def blocks_css():
    return send_from_directory(HERE, "blocks.css", mimetype="text/css")

@app.route("/membership")
def membership():
    # Block-composed page (AXL Page Builder engine). Content = content/membership.blocks.json.
    import blocks as _blocks
    doc = json.load(open(os.path.join(HERE, "content", "membership.blocks.json"), encoding="utf-8"))
    return render_template("blocks_page.html", title=doc.get("title", "Membership"),
                           meta_description=doc.get("meta_description"),
                           blocks_html=_blocks.render_page(doc))

@app.route("/<slug>")
def page(slug):
    p = one("SELECT * FROM tw_pages WHERE slug=? AND published=1", (slug,))
    if not p:
        abort(404)
    if p.get("page_type") == "redirect" and p.get("redirect_to"):
        return redirect(p["redirect_to"], code=302)
    if p.get("page_type") == "external" and p.get("external_url"):
        return redirect(p["external_url"], code=302)
    p["body"] = rehost(p.get("body"))
    return render_template("page.html", page=p, hero_title=p["title"],
                           hero_sub=p.get("meta_description"),
                           hero_image=PAGE_HERO.get(slug, DEFAULT_HERO))

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
    return render_template("page.html",
            page={"title": "Page not found", "meta_description": None,
                  "body": "<p>Sorry, that page doesn’t exist. "
                          "<a href='/'>Return home</a> or browse our "
                          "<a href='/blog'>insights</a>.</p>"},
            hero_title="Page not found", hero_image=DEFAULT_HERO), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 80)))
