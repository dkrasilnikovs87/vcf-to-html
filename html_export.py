"""
HTML export — generates a self-contained interactive single-page HTML file.

New in this version:
  - Typed phones/emails/addresses (Mobile, Work, Home …)
  - URLs, social/IM profiles, custom fields shown in detail view
  - Rich filter bar: quick chips + organization dropdown + search
  - Categories shown as tags on detail page
"""

import os
import json
import html as htmllib
from vcf_parser import Contact

AVATAR_COLORS = [
    '#4A90D9', '#7B68EE', '#50C878', '#FF6B6B', '#FFB347',
    '#87CEEB', '#DDA0DD', '#98FB98', '#20B2AA', '#E07B54',
]


def _color(initials: str) -> str:
    return AVATAR_COLORS[sum(ord(c) for c in initials) % len(AVATAR_COLORS)]


def _contact_to_dict(c: Contact, idx: int) -> dict:
    return {
        "id":            idx,
        "full_name":     c.full_name,
        "first_name":    c.first_name,
        "last_name":     c.last_name,
        "nickname":      c.nickname,
        "organization":  c.organization,
        "title":         c.title,
        "role":          c.role,
        "phones":        c.phones,        # [{"value":..., "type":...}]
        "emails":        c.emails,        # [{"value":..., "type":...}]
        "addresses":     c.addresses,     # [{"value":..., "type":...}]
        "urls":          c.urls,          # [{"value":..., "type":...}]
        "birthday":      c.birthday,
        "anniversary":   c.anniversary,
        "categories":    c.categories,    # ["Family", ...]
        "note":          c.note,
        "custom_fields": c.custom_fields, # [{"label":..., "value":...}]
        "photo":         c.photo_b64 or "",
        "initials":      c.initials,
        "color":         _color(c.initials),
        "raw_vcf":       c.raw_vcf,
    }


_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f0f2f5; color: #222; min-height: 100vh;
}

/* ── Header ── */
.header {
    background: #fff; border-bottom: 1px solid #e0e0e0;
    padding: 12px 20px; display: flex; align-items: center; gap: 12px;
    position: sticky; top: 0; z-index: 20; box-shadow: 0 1px 4px rgba(0,0,0,.05);
}
.header h1 { font-size: 1.1rem; color: #333; flex: 1; }
.search {
    border: 1px solid #ddd; border-radius: 8px; padding: 6px 12px;
    font-size: 0.88rem; outline: none; width: 180px; background: #fafafa;
}
.search:focus { border-color: #4A90D9; background: #fff; }

/* ── Filter bar ── */
.filter-bar {
    background: #fff; border-bottom: 1px solid #efefef;
    padding: 10px 20px; display: flex; align-items: center;
    gap: 8px; flex-wrap: wrap; position: sticky; top: 57px; z-index: 19;
}
.filter-count { font-size: 0.78rem; color: #aaa; margin-left: auto; white-space: nowrap; }

.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
    border: 1px solid #ddd; border-radius: 20px; padding: 4px 12px;
    font-size: 0.78rem; cursor: pointer; background: #fff; color: #555;
    transition: all .12s; white-space: nowrap;
}
.chip:hover { border-color: #4A90D9; color: #4A90D9; }
.chip.active { background: #4A90D9; border-color: #4A90D9; color: #fff; }

.org-select {
    border: 1px solid #ddd; border-radius: 8px; padding: 4px 10px;
    font-size: 0.78rem; outline: none; background: #fff; color: #555; cursor: pointer;
    max-width: 200px;
}
.org-select:focus { border-color: #4A90D9; }

/* ── Alpha header ── */
.alpha-header {
    font-size: 0.72rem; font-weight: 700; color: #aaa;
    letter-spacing: .1em; text-transform: uppercase;
    padding: 18px 20px 6px;
}

/* ── Grid ── */
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(var(--card-min, 175px), 1fr));
    gap: 12px; padding: 0 20px;
}

/* ── Card ── */
.card {
    background: #fff; border-radius: 14px; padding: 16px 12px;
    box-shadow: 0 1px 4px rgba(0,0,0,.07); text-align: center;
    cursor: pointer; transition: transform .13s, box-shadow .13s;
}
.card:hover { transform: translateY(-3px); box-shadow: 0 6px 16px rgba(0,0,0,.11); }

.card.expanded {
    text-align: left; cursor: default; padding: 14px;
    display: grid; grid-template-columns: 56px 1fr; gap: 10px; align-items: start;
}
.card.expanded:hover { transform: none; box-shadow: 0 1px 4px rgba(0,0,0,.07); }
.card.expanded .card-avatar { margin: 0; }

.card-avatar { margin: 0 auto 10px; display: block; width: 60px; }
.avatar {
    width: 60px; height: 60px; border-radius: 50%; object-fit: cover; display: block;
}
.placeholder {
    width: 60px; height: 60px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem; font-weight: 700; color: #fff;
}
.card-name  { font-weight: 600; font-size: 0.9rem; margin-bottom: 2px; }
.card-org   { font-size: 0.74rem; color: #4A90D9; margin-top: 2px; }
.card-phone { font-size: 0.74rem; color: #888; margin-top: 3px; }

/* ── Expanded card fields ── */
.expanded-fields { display: flex; flex-direction: column; gap: 2px; margin-top: 4px; }
.ef-row { display: flex; gap: 5px; font-size: 0.76rem; }
.ef-label { color: #bbb; min-width: 48px; flex-shrink: 0; font-size: 0.7rem; }
.ef-val { color: #333; word-break: break-word; }
.ef-val a { color: #4A90D9; text-decoration: none; }

/* ── Detail page ── */
#detail-view { display: none; padding: 20px; max-width: 640px; margin: 0 auto; }
.back-btn {
    background: none; border: 1px solid #ddd; border-radius: 8px;
    padding: 6px 14px; cursor: pointer; font-size: 0.86rem; color: #555;
    display: inline-flex; align-items: center; gap: 5px; margin-bottom: 16px;
}
.back-btn:hover { background: #f5f5f5; }
.detail-card { background: #fff; border-radius: 16px; box-shadow: 0 2px 10px rgba(0,0,0,.08); overflow: hidden; }

.detail-hero {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 28px 20px; text-align: center;
}
.detail-avatar {
    width: 96px; height: 96px; border-radius: 50%; object-fit: cover;
    border: 4px solid rgba(255,255,255,.3); cursor: pointer; transition: transform .13s;
}
.detail-avatar:hover { transform: scale(1.06); }
.detail-avatar-ph {
    width: 96px; height: 96px; border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 2rem; font-weight: 700; color: #fff;
    border: 4px solid rgba(255,255,255,.25);
}
.detail-name { color: #fff; font-size: 1.35rem; font-weight: 700; margin-top: 12px; }
.detail-sub  { color: rgba(255,255,255,.75); font-size: 0.85rem; margin-top: 3px; }

/* Categories shown in hero */
.cat-tags { margin-top: 10px; display: flex; flex-wrap: wrap; justify-content: center; gap: 5px; }
.cat-tag {
    background: rgba(255,255,255,.2); color: #fff;
    border-radius: 12px; padding: 2px 10px; font-size: 0.72rem;
}

.detail-body { padding: 18px 20px; }
.df-section { margin-bottom: 16px; }
.df-label {
    font-size: 0.66rem; font-weight: 700; color: #bbb;
    text-transform: uppercase; letter-spacing: .07em; margin-bottom: 4px;
}
.df-row { display: flex; align-items: baseline; gap: 8px; margin-top: 2px; }
.df-type { font-size: 0.7rem; color: #bbb; min-width: 44px; }
.df-val { font-size: 0.9rem; color: #333; word-break: break-word; }
.df-val a { color: #4A90D9; text-decoration: none; }
.df-val a:hover { text-decoration: underline; }
.no-fields { color: #ccc; font-size: 0.86rem; }

.detail-actions { padding: 14px 20px; border-top: 1px solid #f0f0f0; }
.btn-export {
    background: #4A90D9; color: #fff; border: none; border-radius: 8px;
    padding: 8px 18px; cursor: pointer; font-size: 0.86rem; font-weight: 500;
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

.empty { text-align: center; color: #bbb; padding: 60px 20px; font-size: 0.92rem; }
#grid-view { padding-bottom: 40px; }
"""

_JS = r"""
const contacts = CONTACTS_JSON;
const config   = CONFIG_JSON;

// ── Filter state ──────────────────────────────────────────────────────────────
let filtered    = contacts.slice();
let activeChip  = 'all';
let activeOrg   = '';
let searchQuery = '';
let savedScrollY = 0;

// ── Utilities ─────────────────────────────────────────────────────────────────
function esc(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;')
                          .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function groupLetter(name) {
    if (!name) return '#';
    const ch = name[0].toUpperCase();
    return /[A-ZА-ЯЁ]/.test(ch) ? ch : '#';
}
function avatarHTML(c, cssClass, onclickFn) {
    if (c.photo) {
        const h = onclickFn ? `onclick="${onclickFn}" style="cursor:pointer"` : '';
        return `<img class="${cssClass}" src="data:image/jpeg;base64,${c.photo}" alt="" ${h}>`;
    }
    return `<div class="${cssClass} placeholder" style="background:${c.color}">${esc(c.initials)}</div>`;
}

// ── Filter bar population ─────────────────────────────────────────────────────
function populateOrgDropdown() {
    const sel = document.getElementById('org-select');
    const orgs = [...new Set(contacts.map(c => c.organization).filter(Boolean))].sort();
    orgs.forEach(org => {
        const opt = document.createElement('option');
        opt.value = org; opt.textContent = org;
        sel.appendChild(opt);
    });
}

// ── Filter logic ──────────────────────────────────────────────────────────────
function applyFilters() {
    filtered = contacts.filter(c => {
        // Search
        if (searchQuery) {
            const q = searchQuery.toLowerCase();
            const hit = c.full_name.toLowerCase().includes(q)
                || c.organization.toLowerCase().includes(q)
                || c.phones.some(p => p.value.includes(q))
                || c.emails.some(e => e.value.toLowerCase().includes(q))
                || c.note.toLowerCase().includes(q)
                || c.custom_fields.some(f => f.value.toLowerCase().includes(q));
            if (!hit) return false;
        }
        // Org filter
        if (activeOrg && c.organization !== activeOrg) return false;
        // Chip filter
        switch (activeChip) {
            case 'has_photo':    return !!c.photo;
            case 'has_email':    return c.emails.length > 0;
            case 'has_mobile':   return c.phones.some(p => p.type === 'Mobile');
            case 'has_note':     return !!c.note;
            case 'has_birthday': return !!c.birthday;
            case 'has_url':      return c.urls.length > 0;
            case 'has_address':  return c.addresses.length > 0;
            case 'has_social':   return c.custom_fields.length > 0;
            case 'has_category': return c.categories.length > 0;
            default: return true;
        }
    });
    updateCount();
    renderGrid();
}

function updateCount() {
    const el = document.getElementById('filter-count');
    const total = contacts.length;
    el.textContent = filtered.length === total
        ? `${total} contacts`
        : `${filtered.length} of ${total}`;
}

// ── Grid rendering ────────────────────────────────────────────────────────────
function renderGrid() {
    const container = document.getElementById('cards');
    if (!filtered.length) {
        container.innerHTML = '<div class="empty">No contacts match the current filters</div>';
        return;
    }

    const groupMap = new Map();
    for (const c of filtered) {
        const letter = groupLetter(c.full_name);
        if (!groupMap.has(letter)) groupMap.set(letter, []);
        groupMap.get(letter).push(c);
    }
    const letters = [...groupMap.keys()].sort((a,b) => {
        if (a==='#') return 1; if (b==='#') return -1; return a.localeCompare(b);
    });

    const cardMin = config.grid_style === 'expanded' ? '260px' : '175px';
    let html = '';
    for (const letter of letters) {
        html += `<div class="alpha-header">${letter}</div>`;
        html += `<div class="grid" style="--card-min:${cardMin}">`;
        for (const c of groupMap.get(letter)) {
            html += config.grid_style === 'expanded' ? renderExpandedCard(c) : renderCompactCard(c);
        }
        html += `</div>`;
    }
    container.innerHTML = html;
}

function renderCompactCard(c) {
    const av  = avatarHTML(c, 'avatar', '');
    const org = (config.fields.organization && c.organization)
        ? `<div class="card-org">${esc(c.organization)}</div>` : '';
    const ph  = (config.fields.phones && c.phones.length)
        ? `<div class="card-phone">${esc(c.phones[0].value)}</div>` : '';
    return `<div class="card" onclick="showDetail(${c.id})" title="Click to open">
        <div class="card-avatar">${av}</div>
        <div class="card-name">${esc(c.full_name)}</div>${org}${ph}
    </div>`;
}

function renderExpandedCard(c) {
    const av = avatarHTML(c, 'avatar', c.photo ? `openLightbox(event,${c.id})` : '');
    let fields = '';
    const F = config.fields;

    if (F.nickname     && c.nickname)     fields += ef('Nickname', esc(c.nickname));
    if (F.organization && c.organization) fields += ef('Company',  esc(c.organization));
    if (F.title        && c.title)        fields += ef('Title',    esc(c.title));
    if (F.role         && c.role)         fields += ef('Role',     esc(c.role));
    if (F.phones       && c.phones.length)
        c.phones.forEach(p => fields += ef(p.type || 'Phone', `<a href="tel:${esc(p.value)}">${esc(p.value)}</a>`));
    if (F.emails       && c.emails.length)
        c.emails.forEach(e => fields += ef(e.type || 'Email', `<a href="mailto:${esc(e.value)}">${esc(e.value)}</a>`));
    if (F.addresses    && c.addresses.length)
        c.addresses.forEach(a => fields += ef(a.type || 'Address', esc(a.value)));
    if (F.urls         && c.urls.length)
        c.urls.forEach(u => fields += ef(u.type || 'Web', `<a href="${esc(u.value)}" target="_blank">${esc(u.value)}</a>`));
    if (F.birthday     && c.birthday)     fields += ef('Birthday',    esc(c.birthday));
    if (F.anniversary  && c.anniversary)  fields += ef('Anniversary', esc(c.anniversary));
    if (F.note         && c.note)         fields += ef('Note', esc(c.note));
    if (F.custom_fields)
        c.custom_fields.forEach(f => fields += ef(esc(f.label), esc(f.value)));

    return `<div class="card expanded">
        <div class="card-avatar">${av}</div>
        <div><div class="card-name">${esc(c.full_name)}</div>
        ${fields ? `<div class="expanded-fields">${fields}</div>` : ''}</div>
    </div>`;
}

function ef(label, value) {
    return `<div class="ef-row"><span class="ef-label">${label}</span><span class="ef-val">${value}</span></div>`;
}

// ── Detail page ───────────────────────────────────────────────────────────────
function showDetail(id) {
    savedScrollY = window.scrollY;
    const c = contacts.find(x => x.id === id);
    if (!c) return;

    const av = c.photo
        ? `<img class="detail-avatar" src="data:image/jpeg;base64,${c.photo}" alt="" onclick="openLightbox(event,${id})">`
        : `<div class="detail-avatar-ph" style="background:${c.color}">${esc(c.initials)}</div>`;

    const sub = [c.organization, c.title, c.role].filter(Boolean).join(' · ');
    const cats = c.categories.length
        ? `<div class="cat-tags">${c.categories.map(t => `<span class="cat-tag">${esc(t)}</span>`).join('')}</div>` : '';

    let body = '';
    const F = config.fields;

    if (F.nickname     && c.nickname)     body += ds('Nickname',    [[''  , c.nickname]]);
    if (F.phones       && c.phones.length)     body += ds('Phone',       c.phones.map(p => [p.type, `<a href="tel:${esc(p.value)}">${esc(p.value)}</a>`]));
    if (F.emails       && c.emails.length)     body += ds('Email',       c.emails.map(e => [e.type, `<a href="mailto:${esc(e.value)}">${esc(e.value)}</a>`]));
    if (F.addresses    && c.addresses.length)  body += ds('Address',     c.addresses.map(a => [a.type, esc(a.value)]));
    if (F.urls         && c.urls.length)       body += ds('Website',     c.urls.map(u => [u.type, `<a href="${esc(u.value)}" target="_blank">${esc(u.value)}</a>`]));
    if (F.birthday     && c.birthday)     body += ds('Birthday',    [[''  , esc(c.birthday)]]);
    if (F.anniversary  && c.anniversary)  body += ds('Anniversary', [[''  , esc(c.anniversary)]]);
    if (F.note         && c.note)         body += ds('Note',        [[''  , esc(c.note)]]);
    if (F.custom_fields && c.custom_fields.length)
        body += ds('More', c.custom_fields.map(f => [esc(f.label), esc(f.value)]));

    document.getElementById('detail-content').innerHTML = `
        <div class="detail-card">
            <div class="detail-hero">
                ${av}
                <div class="detail-name">${esc(c.full_name)}</div>
                ${sub ? `<div class="detail-sub">${esc(sub)}</div>` : ''}
                ${cats}
            </div>
            <div class="detail-body">${body || '<p class="no-fields">No additional fields</p>'}</div>
            <div class="detail-actions">
                <button class="btn-export" onclick="exportVCF(${id})">⬇ Export to VCF</button>
            </div>
        </div>`;

    document.getElementById('grid-view').style.display   = 'none';
    document.getElementById('detail-view').style.display = 'block';
    window.scrollTo(0, 0);
}

// Render a detail section with typed rows
function ds(label, rows) {
    const rowsHTML = rows.map(([type, val]) =>
        `<div class="df-row"><span class="df-type">${type || ''}</span><span class="df-val">${val}</span></div>`
    ).join('');
    return `<div class="df-section"><div class="df-label">${label}</div>${rowsHTML}</div>`;
}

function showGrid() {
    document.getElementById('detail-view').style.display = 'none';
    document.getElementById('grid-view').style.display   = 'block';
    requestAnimationFrame(() => window.scrollTo(0, savedScrollY));
}

// ── VCF export ────────────────────────────────────────────────────────────────
function exportVCF(id) {
    const c = contacts.find(x => x.id === id);
    if (!c) return;
    const blob = new Blob([c.raw_vcf], { type: 'text/vcard;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
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

// ── Event listeners ───────────────────────────────────────────────────────────
document.getElementById('search').addEventListener('input', function() {
    searchQuery = this.value;
    applyFilters();
});
document.getElementById('org-select').addEventListener('change', function() {
    activeOrg = this.value;
    applyFilters();
});
document.querySelectorAll('.chip').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.chip').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        activeChip = this.dataset.filter;
        applyFilters();
    });
});

// ── Init ──────────────────────────────────────────────────────────────────────
populateOrgDropdown();
applyFilters();
"""


def _build_page(contacts_data: list[dict], config: dict, title: str) -> str:
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

<!-- Sticky header with title and search -->
<div class="header">
    <h1>{htmllib.escape(title)}</h1>
    <input class="search" id="search" type="search" placeholder="Search…">
</div>

<!-- Filter bar: quick chips + org dropdown + live count -->
<div class="filter-bar">
    <div class="chips">
        <button class="chip active" data-filter="all">All</button>
        <button class="chip" data-filter="has_photo">📷 Photo</button>
        <button class="chip" data-filter="has_mobile">📱 Mobile</button>
        <button class="chip" data-filter="has_email">✉ Email</button>
        <button class="chip" data-filter="has_url">🌐 Website</button>
        <button class="chip" data-filter="has_address">📍 Address</button>
        <button class="chip" data-filter="has_note">📝 Note</button>
        <button class="chip" data-filter="has_birthday">🎂 Birthday</button>
        <button class="chip" data-filter="has_social">💬 Social</button>
        <button class="chip" data-filter="has_category">🏷 Category</button>
    </div>
    <select class="org-select" id="org-select">
        <option value="">All organizations</option>
    </select>
    <span class="filter-count" id="filter-count">{count} contacts</span>
</div>

<!-- Main grid view -->
<div id="grid-view">
    <div id="cards"></div>
</div>

<!-- Detail view (hidden initially) -->
<div id="detail-view">
    <button class="back-btn" onclick="showGrid()">&#8592; Back</button>
    <div id="detail-content"></div>
</div>

<!-- Photo lightbox -->
<div id="lightbox" onclick="this.classList.remove('open')">
    <img id="lb-img" src="" alt="">
</div>

<script>{js}</script>
</body>
</html>"""


def _all_fields() -> dict:
    return {k: True for k in [
        'nickname', 'organization', 'title', 'role', 'phones', 'emails',
        'addresses', 'urls', 'birthday', 'anniversary', 'note', 'custom_fields'
    ]}


def _make_config(fields: dict, grid_style: str) -> dict:
    return {"fields": fields, "grid_style": grid_style}


def export_single(contacts: list[Contact], out_path: str,
                  fields: dict = None, grid_style: str = "compact",
                  title: str = "Contacts"):
    if fields is None:
        fields = _all_fields()
    data   = [_contact_to_dict(c, i) for i, c in enumerate(contacts)]
    config = _make_config(fields, grid_style)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(_build_page(data, config, title))


def export_multiple(contacts: list[Contact], out_dir: str,
                    fields: dict = None, grid_style: str = "compact"):
    if fields is None:
        fields = _all_fields()
    os.makedirs(out_dir, exist_ok=True)
    config = _make_config(fields, grid_style)
    for i, c in enumerate(contacts):
        data = [_contact_to_dict(c, 0)]
        html = _build_page(data, config, c.full_name)
        safe = "".join(ch for ch in c.full_name if ch.isalnum() or ch in ' _-').strip() or f"contact_{i+1}"
        path = os.path.join(out_dir, f"{i+1:04d}_{safe}.html")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
