# Changelog

## [1.3.0] - 2026-04-30

### Added
- **CSV export** — new export mode produces a `.csv` file (UTF-8 with BOM so Excel and Numbers open it correctly on all platforms without encoding issues); multi-value fields joined with ` | `; available in both GUI and CLI (`--mode csv`)
- **In-browser HTML editing** — "✎ Edit" button in the HTML output toggles edit mode; in edit mode each card shows a ✕ delete badge; clicking a card opens an edit form with inputs for name, phones, emails and note; "Save" updates the contact in-place; "Delete Contact" removes it with a confirmation prompt; "⬇ Save HTML" in the header downloads a new self-contained HTML file with all changes applied
- **GitHub Actions CI** (`.github/workflows/build.yml`) — on every version tag push, builds macOS `.app`, Windows `.exe` folder and Linux binary automatically and attaches them to the GitHub Release; no manual packaging needed
- **vCard 4.0 quoted TYPE params** — `TYPE="work,voice"` now stripped of quotes before parsing so labels resolve correctly

### Fixed
- **Progress bar clamping** — `_progress_bar()` in `cli.py` now clamps `value` to `[0.0, 1.0]` with `min(1.0, max(0.0, value))` to prevent index-out-of-range on floating-point rounding
- **`</script>` injection** — JSON data injected into `<script>` tags now has `</` replaced with `<\/` so a contact note containing `</script>` cannot break the HTML page

### Changed
- App renamed from "VCF → HTML Converter" to **"VCF Converter"** — reflects the broader export scope (HTML + CSV)
- Export Mode radio group now has three options: Single HTML / One HTML per contact / CSV file
- Photo compression OptionMenu is disabled when CSV mode is selected (not applicable)
- README rewritten with download table, full CLI reference, CI build notes and macOS Gatekeeper caveat

---

## [1.2.0] - 2026-04-29

### Added
- **Photo compression** — resize photos before embedding using Pillow (Original / Large 1024 px / Medium 640 px / Small 320 px / Strip all)
- **Progress bar** — `CTkProgressBar` shown during conversion, hidden at rest
- **CLI** (`cli.py`) — full `argparse` interface with `--mode`, `--grid`, `--dedup`, `--fuzzy`, `--photo`, `--fields`, `--title`, `--quiet`
- **Fuzzy name matching** — optional dedup mode where name parts are sorted before comparison (Anna Maria = Maria Anna); phones and emails still required to match
- **Persistent settings** — saved to `~/.vcf_converter_config.json`, restored on next launch
- **Logging** — `~/.vcf_converter.log` with timestamps and full tracebacks
- **Automatic encoding detection** via `charset-normalizer` (Windows-1251, CP1252 and other regional encodings)
- **Test suite** — 34 pytest tests with sample `.vcf` fixtures

### Fixed
- Template injection risk (`CONTACTS_JSON` → `__CONTACTS_DATA__` safe placeholder)
- Window sizing — Convert button can no longer be scrolled off-screen
- Custom field checklist grows/shrinks the window instead of overlapping content

### Changed
- `renderGrid()` uses `DocumentFragment` for faster rendering at 1000+ contacts
- All UI labels, comments and documentation in English

---

## [1.1a] - 2026-04-28

### Added
- Typed phone/email/address labels (Mobile, Home, Work, Fax …)
- Website field (`URL` property)
- Social & IM profiles via `X-*` and `IMPP` (Skype, Telegram, WhatsApp, ICQ, AIM, MSN, Yahoo, Jabber, Viber, LINE, WeChat, Facebook, Twitter, LinkedIn, Instagram)
- `ROLE`, `ANNIVERSARY`, `CATEGORIES` fields
- Custom fields catch-all — unknown properties captured and displayed
- Rich filter bar — chips: Photo, Mobile, Email, Website, Address, Note, Birthday, Social, Category
- Organization dropdown filter + live contact count
- Scroll position restored on Back navigation

### Fixed
- Contact name truncation — `FN` now used as authoritative display name
- Quoted-Printable multi-line values (soft breaks) joined correctly before decoding
- Duplicate handling updated for typed `{value, type}` data structures

---

## [1.0.0] - 2026-04-28

### Initial Release
- Parse vCard 2.1 and 3.0 (UTF-8, UTF-16-LE, Latin-1)
- Quoted-Printable and Base64 decoding
- Alphabetical contact groups
- Two grid modes: compact / expanded
- Detail page with photo lightbox and single-contact VCF export
- Duplicate detection: delete or merge
- Custom field selection in GUI
- Self-contained HTML output
