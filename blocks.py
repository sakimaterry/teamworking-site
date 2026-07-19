#!/usr/bin/env python3
"""AXL Page Builder — block renderer.

Pure function: a block document (ordered list of {type, data}) -> HTML.
Shared, app-agnostic module: the satellite renders live; the main app can use the
same module to bake HTML on save (see PAGE_BUILDER_SPEC.md). Styling lives in
blocks.css and is themed per-site via CSS custom properties.
"""
import html as _html, json

def esc(s):
    return _html.escape("" if s is None else str(s), quote=True)

def _button(cta, default_style="primary"):
    if not cta or not cta.get("label"):
        return ""
    style = esc(cta.get("style", default_style))
    href = esc(cta.get("href", "#"))
    ext = ' target="_blank" rel="noopener"' if str(cta.get("href", "")).startswith("http") else ""
    return f'<a class="blk-btn blk-btn-{style}" href="{href}"{ext}>{esc(cta["label"])}</a>'

def _buttons(items, default_style="primary"):
    return "".join(_button(b, default_style) for b in (items or []))

def render_hero(d):
    img = d.get("image")
    bg = f'<div class="blk-hero-bg" style="background-image:url(\'{esc(img)}\')"></div>' if img else ""
    eyebrow = f'<div class="blk-eyebrow">{esc(d["eyebrow"])}</div>' if d.get("eyebrow") else ""
    sub = f'<p class="blk-hero-sub">{esc(d["sub"])}</p>' if d.get("sub") else ""
    ctas = d.get("ctas") or ([d["cta"]] if d.get("cta") else [])
    return (f'<section class="blk blk-hero"><div class="blk-hero-overlay"></div>{bg}'
            f'<div class="blk-hero-inner">{eyebrow}'
            f'<h1 class="blk-h blk-hero-h">{esc(d.get("heading",""))}</h1>{sub}'
            f'<div class="blk-actions">{_buttons(ctas)}</div></div></section>')

def render_rich_text(d):
    # d["html"] is server-sanitized rich text
    return f'<section class="blk blk-rich"><div class="blk-wrap blk-prose">{d.get("html","")}</div></section>'

def render_gallery(d):
    cells = []
    for i in (d.get("images") or []):
        url = i if isinstance(i, str) else i.get("url")
        cap = "" if isinstance(i, str) else i.get("caption", "")
        if url:
            cells.append(f'<img src="{esc(url)}" alt="{esc(cap)}" loading="lazy">')
    layout = esc(d.get("layout", "grid"))
    return (f'<section class="blk blk-gallery blk-gallery-{layout}">'
            f'<div class="blk-gallery-grid">{"".join(cells)}</div></section>')

def render_pricing_tiers(d):
    head = ""
    if d.get("heading"):
        sub = f"<p>{esc(d['sub'])}</p>" if d.get("sub") else ""
        head = f'<div class="blk-head"><h2 class="blk-h">{esc(d["heading"])}</h2>{sub}</div>'
    tiers = ""
    for t in (d.get("tiers") or []):
        feats = "".join(f"<li>{esc(f)}</li>" for f in (t.get("features") or []))
        price = f'<div class="blk-tier-price">{esc(t["price"])}</div>' if t.get("price") else ""
        pop = '<span class="blk-tier-pop">Most popular</span>' if t.get("featured") else ""
        fine = f'<div class="blk-tier-fine">{esc(t["fine"])}</div>' if t.get("fine") else ""
        lede = f'<div class="blk-tier-lede">{esc(t["lede"])}</div>' if t.get("lede") else ""
        cls = "blk-tier featured" if t.get("featured") else "blk-tier"
        tiers += (f'<div class="{cls}">{pop}<h3 class="blk-h">{esc(t.get("name",""))}</h3>'
                  f'{price}{lede}<ul>{feats}</ul>{_button(t.get("cta"))}{fine}</div>')
    return (f'<section class="blk blk-pricing"><div class="blk-wrap">{head}'
            f'<div class="blk-tier-grid">{tiers}</div></div></section>')

def render_cta_band(d):
    theme = esc(d.get("theme", "dark"))
    body = f"<p>{esc(d['body'])}</p>" if d.get("body") else ""
    return (f'<section class="blk blk-cta blk-cta-{theme}"><div class="blk-cta-inner">'
            f'<h2 class="blk-h">{esc(d.get("heading",""))}</h2>{body}'
            f'<div class="blk-actions">{_buttons(d.get("buttons"))}</div></div></section>')

RENDERERS = {
    "hero": render_hero, "rich_text": render_rich_text, "gallery": render_gallery,
    "pricing_tiers": render_pricing_tiers, "cta_band": render_cta_band,
}

def render_page(blocks):
    """blocks: JSON string, {'blocks':[...]}, or a list. -> HTML string."""
    if isinstance(blocks, str):
        blocks = json.loads(blocks or "[]")
    if isinstance(blocks, dict):
        blocks = blocks.get("blocks", [])
    out = []
    for b in (blocks or []):
        fn = RENDERERS.get(b.get("type"))
        if fn:
            out.append(fn(b.get("data", {})))
    return "\n".join(out)
