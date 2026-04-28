"""
HTML export module.

Generates a self-contained interactive HTML file from a list of Contact objects.
All data (photos, JS, CSS) is embedded — no external dependencies.

Supports two grid display styles:
  'compact'  — small cards with avatar + name + first phone; click opens detail page
  'expanded' — larger cards showing all selected fields inline

Contacts are grouped alphabetically by the first letter of their name.
"""

import os
import json
import html as htmllib
from vcf_parser import Contact

# Avatar placeholder colours — assigned by hashing the contact's initials
AVATAR_COLORS = [
    '#4A90D9', '#7B68EE', '#50C878', '#FF6B6B', '#FFB347',
    '#87CEEB', '#DDA0DD', '#98FB98', '#20B2AA', '#E07B54',
]


def _color(initials: str) -> str:
    return AVATAR_COLORS[sum(ord(c) for c in initials) % len(AVATAR_COLORS)]


def _contact_to_dict(c: Contact, idx: int) -> dict:
    """Serialize a Contact to a plain dict that will be embedded as JSON in the HTML."""
    return {
        "id":           idx,
        "full_name":    c.full_name,
        "first_name":   c.first_name,
        "last_name":    c.last_name,
        "nickname":     c.nickname,
        "organization": c.organization,
        "title":        c.title,
        "phones":       c.phones,
        "emails":       c.emails,
        "addresses":    c.addresses,
        "birthday":     c.birthday,
        "note":         c.note,
        "photo":        c.photo_b64 or "",
        "initials":     c.initials,
        "color":        _color(c.initials),
        "raw_vcf":      c.raw_vcf,
    }


# ── CSS ─────────────────────────────────────────────────────────────────────

_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f0f2f5; color: #222; min-height: 100vh;
}

/* ── Header ── */
.header {
    background: #fff; border-bottom: 1px solid #e0e0e0;
    padding: 14px 24px; display: flex; align-items: center; gap: 16px;
    position: sticky; top: 0; z-index: 10; box-shadow: 0 1px 4px rgba(0,0,0,.05);
}
.header h1 { font-size: 1.15rem; color: #333; flex: 1; }
.header .count { color: #aaa; font-size: 0.82rem; white-space: nowrap; }
.search {
    border: 1px solid #ddd; border-radius: 8px; padding: 6px 12px;
    font-size: 0.88rem; outline: none; width: 180px; background: #fafafa;
}
.search:focus { border-color: #4A90D9; background: #fff; }

/* ── Alpha group header ── */
.alpha-header {
    font-size: 0.75rem; font-weight: 700; color: #aaa;
    letter-spacing: .1em; text-transform: uppercase;
    padding: 20px 24px 8px;
}

/* ── Grid ── */
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(var(--card-min, 180px), 1fr));
    gap: 14px; padding: 0 24px;
}

/* ── Compact card ── */
.card {
    background: #fff; border-radius: 14px; padding: 18px 14px;
    box-shadow: 0 1px 4px rgba(0,0,0,.07); text-align: center;
    cursor: pointer; transition: transform .14s, box-shadow .14s;
}
.card:hover { transform: translateY(-3px); box-shadow: 0 6px 16px rgba(0,0,0,.11); }

/* ── Expanded card overrides ── */
.card.expanded {
    text-align: left; padding: 16px; cursor: default;
    display: grid; grid-template-columns: 56px 1fr; gap: 12px;
    align-items: start;
}
.card.expanded:hover { transform: none; box-shadow: 0 1px 4px rgba(0,0,0,.07); }
.card.expanded .card-avatar { margin: 0; }
.card.expanded .card-name { font-size: 0.92rem; margin-bottom: 6px; }

/* ── Avatar ── */
.card-avatar { margin: 0 auto 10px; display: block; width: 64px; }
.avatar {
    width: 64px; height: 64px; border-radius: 50%;
    object-fit: cover; display: block;
}
.placeholder {
    width: 64px; height: 64px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.25rem; font-weight: 700; color: #fff;
}
.card-name  { font-weight: 600; font-size: 0.93rem; margin-bottom: 3px; }
.card-org   { font-size: 0.76rem; color: #4A90D9; margin-top: 2px; }
.card-phone { font-size: 0.76rem; color: #888; margin-top: 3px; }

/* ── Expanded fields inside card ── */
.expanded-fields { display: flex; flex-direction: column; gap: 3px; margin-top: 2px; }
.ef-row { display: flex; gap: 6px; font-size: 0.78rem; }
.ef-label { color: #aaa; min-width: 52px; flex-shrink: 0; }
.ef-val { color: #333; word-break: break-word; }
.ef-val a { color: #4A90D9; text-decoration: none; }
.ef-val a:hover { text-decoration: underline; }
.note-val { color: #999; font-style: italic; }

/* ── Detail page ── */
#detail-view { display: none; padding: 24px; max-width: 620px; margin: 0 auto; }

.back-btn {
    background: none; border: 1px solid #ddd; border-radius: 8px;
    padding: 7px 16px; cursor: pointer; font-size: 0.88rem; color: #555;
    display: inline-flex; align-items: center; gap: 6px; margin-bottom: 20px;
}
.back-btn:hover { background: #f5f5f5; }

.detail-card { background: #fff; border-radius: 16px; box-shadow: 0 2px 10px rgba(0,0,0,.08); overflow: hidden; }

.detail-hero {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 32px 24px; text-align: center;
}
.detail-avatar {
    width: 100px; height: 100px; border-radius: 50%; object-fit: cover;
    border: 4px solid rgba(255,255,255,.35); cursor: pointer; transition: transform .14s;
}
.detail-avatar:hover { transform: scale(1.06); }
.detail-avatar-ph {
    width: 100px; height: 100px; border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 2.2rem; font-weight: 700; color: #fff;
    border: 4px solid rgba(255,255,255,.3);
}
.detail-name { color: #fff; font-size: 1.4rem; font-weight: 700; margin-top: 12px; }
.detail-sub  { color: rgba(255,255,255,.75); font-size: 0.88rem; margin-top: 4px; }

.detail-body { padding: 20px 24px; }
.df-group { margin-bottom: 14px; }
.df-label {
    font-size: 0.68rem; font-weight: 600; color: #bbb;
    text-transform: uppercase; letter-spacing: .07em; margin-bottom: 3px;
}
.df-val { font-size: 0.93rem; color: #333; margin-top: 1px; }
.df-val a { color: #4A90D9; text-decoration: none; }
.df-val a:hover { text-decoration: underline; }
.no-fields { color: #ccc; font-size: 0.88rem; }

.detail-actions { padding: 14px 24px; border-top: 1px solid #f0f0f0; }
.btn-export {
    background: #4A90D9; color: #fff; border: none; border-radius: 8px;
    padding: 9px 20px; cursor: pointer; font-size: 0.88rem; font-weight: 500;
}
.btn-export:hover { background: #357abd; }

/* ── Lightbox ── */
#lightbox {
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,.88); z-index: 100;
    align-items: center; justify-content: center; cursor: pointer;
}
#lightbox.open { display: flex; }
#lightbox img { max-width: 92vw; max-height: 92vh; border-radius: 8px; }

/* ── Empty state ── */
.empty { text-align: center; color: #bbb; padding: 60px 20px; font-size: 0.95rem; }

/* ── Bottom padding ── */
#grid-view { padding-bottom: 40px; }
"""

# ── JavaScript ───────────────────────────────────────────────────────────────

_JS = r"""
// All contact data and export configuration injected from Python
const contacts = CONTACTS_JSON;
const config   = CONFIG_JSON;   // { fields: {nickname:true, ...}, grid_style: 'compact'|'expanded' }

// Currently visible contacts (updated by search)
let filtered = contacts.slice();

// Saved scroll position — restored when navigating back from detail view
let savedScrollY = 0;

// ── Utilities ────────────────────────────────────────────────────────────────

function esc(str) {
    return String(str || '')
        .replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Returns the grouping letter for a contact name (supports Latin and Cyrillic)
function groupLetter(name) {
    if (!name) return '#';
    const ch = name[0].toUpperCase();
    if (/[A-Z]/.test(ch) || /[А-ЯЁ]/.test(ch)) return ch;
    return '#';
}

// Builds avatar HTML — real photo or coloured initials placeholder
function avatarHTML(c, cssClass, onclickFn) {
    if (c.photo) {
        const handler = onclickFn ? `onclick="${onclickFn}" style="cursor:pointer"` : '';
        return `<img class="${cssClass}" src="data:image/jpeg;base64,${c.photo}" alt="" ${handler}>`;
    }
    return `<div class="${cssClass} placeholder" style="background:${c.color}">${esc(c.initials)}</div>`;
}

// ── Grid rendering ────────────────────────────────────────────────────────────

function renderGrid() {
    const container = document.getElementById('cards');

    if (!filtered.length) {
        container.innerHTML = '<div class="empty">No contacts found</div>';
        return;
    }

    // Group contacts by first letter, preserving sorted order within groups
    const groupMap = new Map();
    for (const c of filtered) {
        const letter = groupLetter(c.full_name);
        if (!groupMap.has(letter)) groupMap.set(letter, []);
        groupMap.get(letter).push(c);
    }

    // Sort letter keys: A–Z (and А–Я) first, '#' at the end
    const letters = [...groupMap.keys()].sort((a, b) => {
        if (a === '#') return 1;
        if (b === '#') return -1;
        return a.localeCompare(b);
    });

    // Compact cards are narrower; expanded cards need more width
    const cardMin = config.grid_style === 'expanded' ? '260px' : '180px';
    document.querySelector('.grid') && null; // placeholder so we can set the var below

    let html = '';
    for (const letter of letters) {
        html += `<div class="alpha-header">${letter}</div>`;
        html += `<div class="grid" style="--card-min:${cardMin}">`;
        for (const c of groupMap.get(letter)) {
            html += config.grid_style === 'expanded'
                ? renderExpandedCard(c)
                : renderCompactCard(c);
        }
        html += `</div>`;
    }

    container.innerHTML = html;
}

// Compact card: avatar + name + optional org/phone. Whole card is clickable.
function renderCompactCard(c) {
    const av  = avatarHTML(c, 'avatar', '');
    const org = (config.fields.organization && c.organization)
        ? `<div class="card-org">${esc(c.organization)}</div>` : '';
    const ph  = (config.fields.phones && c.phones.length)
        ? `<div class="card-phone">${esc(c.phones[0])}</div>` : '';
    return `
        <div class="card" onclick="showDetail(${c.id})" title="Click to expand">
            <div class="card-avatar">${av}</div>
            <div class="card-name">${esc(c.full_name)}</div>
            ${org}${ph}
        </div>`;
}

// Expanded card: all selected fields shown inline; photo clickable for lightbox.
function renderExpandedCard(c) {
    const av = avatarHTML(c, 'avatar', c.photo ? `openLightbox(event,${c.id})` : '');
    let fields = '';

    if (config.fields.nickname     && c.nickname)
        fields += ef('Nickname', esc(c.nickname));
    if (config.fields.organization && c.organization)
        fields += ef('Company',  esc(c.organization));
    if (config.fields.title        && c.title)
        fields += ef('Title',    esc(c.title));
    if (config.fields.phones       && c.phones.length)
        c.phones.forEach(p => fields += ef('Phone', `<a href="tel:${esc(p)}">${esc(p)}</a>`));
    if (config.fields.emails       && c.emails.length)
        c.emails.forEach(e => fields += ef('Email', `<a href="mailto:${esc(e)}">${esc(e)}</a>`));
    if (config.fields.addresses    && c.addresses.length)
        c.addresses.forEach(a => fields += ef('Address', esc(a)));
    if (config.fields.birthday     && c.birthday)
        fields += ef('Birthday', esc(c.birthday));
    if (config.fields.note         && c.note)
        fields += ef('Note', `<span class="note-val">${esc(c.note)}</span>`);

    return `
        <div class="card expanded">
            <div class="card-avatar">${av}</div>
            <div>
                <div class="card-name">${esc(c.full_name)}</div>
                ${fields ? `<div class="expanded-fields">${fields}</div>` : ''}
            </div>
        </div>`;
}

// Helper: one field row in an expanded card
function ef(label, value) {
    return `<div class="ef-row"><span class="ef-label">${label}</span><span class="ef-val">${value}</span></div>`;
}

// ── Detail page ───────────────────────────────────────────────────────────────

function showDetail(id) {
    savedScrollY = window.scrollY;   // remember position before navigating away
    const c = contacts.find(x => x.id === id);
    if (!c) return;

    // Avatar — photo clickable for lightbox, placeholder is static
    const av = c.photo
        ? `<img class="detail-avatar" src="data:image/jpeg;base64,${c.photo}" alt="" onclick="openLightbox(event,${c.id})">`
        : `<div class="detail-avatar-ph" style="background:${c.color}">${esc(c.initials)}</div>`;

    // Build body from selected fields
    let body = '';
    if (config.fields.nickname     && c.nickname)      body += df('Nickname',  [esc(c.nickname)]);
    if (config.fields.title        && c.title)         body += df('Job Title', [esc(c.title)]);
    if (config.fields.phones       && c.phones.length) body += df('Phone',     c.phones.map(p => `<a href="tel:${esc(p)}">${esc(p)}</a>`));
    if (config.fields.emails       && c.emails.length) body += df('Email',     c.emails.map(e => `<a href="mailto:${esc(e)}">${esc(e)}</a>`));
    if (config.fields.addresses    && c.addresses.length) body += df('Address', c.addresses.map(esc));
    if (config.fields.birthday     && c.birthday)      body += df('Birthday',  [esc(c.birthday)]);
    if (config.fields.note         && c.note)          body += df('Note',      [esc(c.note)]);

    document.getElementById('detail-content').innerHTML = `
        <div class="detail-card">
            <div class="detail-hero">
                ${av}
                <div class="detail-name">${esc(c.full_name)}</div>
                ${c.organization ? `<div class="detail-sub">${esc(c.organization)}</div>` : ''}
            </div>
            <div class="detail-body">
                ${body || '<p class="no-fields">No additional fields available</p>'}
            </div>
            <div class="detail-actions">
                <button class="btn-export" onclick="exportVCF(${c.id})">⬇ Export to VCF</button>
            </div>
        </div>`;

    document.getElementById('grid-view').style.display   = 'none';
    document.getElementById('detail-view').style.display = 'block';
    window.scrollTo(0, 0);
}

// Helper: one labelled field group in the detail view
function df(label, values) {
    return `<div class="df-group">
        <div class="df-label">${label}</div>
        ${values.map(v => `<div class="df-val">${v}</div>`).join('')}
    </div>`;
}

function showGrid() {
    document.getElementById('detail-view').style.display = 'none';
    document.getElementById('grid-view').style.display   = 'block';
    // Restore scroll position on the next paint tick so layout is ready
    requestAnimationFrame(() => window.scrollTo(0, savedScrollY));
}

// ── VCF export ────────────────────────────────────────────────────────────────

function exportVCF(id) {
    const c = contacts.find(x => x.id === id);
    if (!c) return;
    const blob = new Blob([c.raw_vcf], { type: 'text/vcard;charset=utf-8' });
    const a    = document.createElement('a');
    a.href     = URL.createObjectURL(blob);
    a.download = (c.full_name || 'contact').replace(/[^\w\s-]/g, '_') + '.vcf';
    a.click();
}

// ── Lightbox ──────────────────────────────────────────────────────────────────

function openLightbox(e, id) {
    e.stopPropagation();
    const c = contacts.find(x => x.id === id);
    if (!c || !c.photo) return;
    document.getElementById('lb-img').src = `data:image/jpeg;base64,${c.photo}`;
    document.getElementById('lightbox').classList.add('open');
}

// ── Search ────────────────────────────────────────────────────────────────────

document.getElementById('search').addEventListener('input', function () {
    const q = this.value.toLowerCase();
    filtered = contacts.filter(c =>
        c.full_name.toLowerCase().includes(q)    ||
        c.organization.toLowerCase().includes(q) ||
        c.phones.some(p => p.includes(q))        ||
        c.emails.some(e => e.toLowerCase().includes(q))
    );
    renderGrid();
});

// ── Init ──────────────────────────────────────────────────────────────────────

renderGrid();
"""


def _build_page(contacts_data: list[dict], config: dict, title: str) -> str:
    """Assemble the final HTML string with all data and config embedded."""
    contacts_json = json.dumps(contacts_data, ensure_ascii=False)
    config_json   = json.dumps(config,        ensure_ascii=False)
    js = _JS.replace('CONTACTS_JSON', contacts_json).replace('CONFIG_JSON', config_json)
    count = len(contacts_data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{htmllib.escape(title)}</title>
<style>{_CSS}</style>
</head>
<body>

<div class="header">
    <h1>{htmllib.escape(title)}</h1>
    <span class="count">{count} contact{'s' if count != 1 else ''}</span>
    <input class="search" id="search" type="search" placeholder="Search...">
</div>

<!-- Grid view: alphabetically grouped contact cards -->
<div id="grid-view">
    <div id="cards"></div>
</div>

<!-- Detail view: single contact page (hidden initially) -->
<div id="detail-view">
    <button class="back-btn" onclick="showGrid()">&#8592; Back</button>
    <div id="detail-content"></div>
</div>

<!-- Lightbox: full-size photo overlay -->
<div id="lightbox" onclick="this.classList.remove('open')">
    <img id="lb-img" src="" alt="">
</div>

<script>{js}</script>
</body>
</html>"""


def _make_config(fields: dict, grid_style: str) -> dict:
    """Build the JS config object from Python export settings."""
    return {"fields": fields, "grid_style": grid_style}


def export_single(contacts: list[Contact], out_path: str,
                  fields: dict = None, grid_style: str = "compact",
                  title: str = "Contacts"):
    """Export all contacts into one interactive HTML file."""
    if fields is None:
        fields = {k: True for k in ['nickname','organization','title','phones','emails','addresses','birthday','note']}
    data   = [_contact_to_dict(c, i) for i, c in enumerate(contacts)]
    config = _make_config(fields, grid_style)
    html   = _build_page(data, config, title)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)


def export_multiple(contacts: list[Contact], out_dir: str,
                    fields: dict = None, grid_style: str = "compact"):
    """Export each contact as its own HTML file into out_dir."""
    if fields is None:
        fields = {k: True for k in ['nickname','organization','title','phones','emails','addresses','birthday','note']}
    os.makedirs(out_dir, exist_ok=True)
    config = _make_config(fields, grid_style)
    for i, c in enumerate(contacts):
        data = [_contact_to_dict(c, 0)]
        html = _build_page(data, config, c.full_name)
        safe = "".join(ch for ch in c.full_name if ch.isalnum() or ch in ' _-').strip() or f"contact_{i+1}"
        path = os.path.join(out_dir, f"{i+1:04d}_{safe}.html")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
