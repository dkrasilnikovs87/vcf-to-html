# Changelog

## [1.2.0] - 2026-04-29

### Added
- **Photo compression** — resize photos before embedding using Pillow (Original / Large 1024 px / Medium 640 px / Small 320 px / Strip all); dramatically reduces output file size for large contact books with photos
- **Progress bar** — `CTkProgressBar` appears during conversion and hides on completion
- **Command-line interface** (`cli.py`) — full `argparse` CLI with `--mode`, `--grid`, `--dedup`, `--fuzzy`, `--photo`, `--fields`, `--title`, `--quiet` flags; usable in automation scripts
- **Fuzzy name matching** — optional dedup mode where name parts are sorted before comparison, so "Anna Maria" and "Maria Anna" are treated as the same person; phones and emails still required to match
- **Persistent settings** — all options saved to `~/.vcf_converter_config.json` on each successful export and restored on next launch
- **Logging** — structured log written to `~/.vcf_converter.log` with timestamps; full traceback on export errors
- **Automatic encoding detection** via `charset-normalizer` — covers Windows-1251, CP1252 and other regional encodings in addition to UTF-8, UTF-16 and Latin-1
- **Test suite** — 34 pytest tests covering the parser (vCard 2.1/3.0, QP encoding, RFC line folding, typed fields, social profiles, categories, catch-all) and dedup logic (delete/merge, richest-copy selection, fuzzy matching, false-positive guards); sample `.vcf` fixtures in `tests/samples/`

### Fixed
- **Template injection risk** — replaced `CONTACTS_JSON` / `CONFIG_JSON` placeholders with `__CONTACTS_DATA__` / `__CONFIG_DATA__` to prevent collision when contact notes contain the placeholder string
- **Window sizing** — window now measures its own natural height after layout and sets that as the minimum size; Convert button can no longer be scrolled off-screen; window grows when the custom field checklist is shown and shrinks when hidden
- **Radio button label truncation** — shortened radio button text to fit without clipping at any window width

### Changed
- `renderGrid()` in the HTML output now uses `DocumentFragment` — one DOM write per alphabetical group instead of one massive `innerHTML` on the whole container; noticeably faster at 1000+ contacts
- `deduplicate()` accepts a `fuzzy` parameter (default `False`) for backwards compatibility
- `requirements.txt` adds `charset-normalizer>=3.0.0` and `Pillow>=10.0.0`
- All UI labels, comments, and documentation are now in English

---

## [1.1a] - 2026-04-28

### Added
- **Phone/email/address type labels** — Mobile, Home, Work, Fax etc. now shown next to each value
- **Website field** — URLs from the `URL` property are now parsed and displayed
- **Social & IM profiles** — Skype, Telegram, WhatsApp, ICQ, AIM, MSN, Yahoo, Jabber, Viber, LINE, WeChat, Facebook, Twitter, LinkedIn, Instagram and more (via `X-*` and `IMPP` fields)
- **ROLE field** — role within organization, separate from job title
- **ANNIVERSARY field** — anniversary date parsed and displayed
- **CATEGORIES field** — contact groups/tags shown as chips in the detail view
- **Custom fields catch-all** — any unknown vCard property is captured and shown rather than silently discarded
- **Rich filter bar** — quick filter chips: Photo, Mobile, Email, Website, Address, Note, Birthday, Social, Category
- **Organization dropdown filter** — filter contacts by organization with one click
- **Live contact count** — shows "42 of 150" when filters are active
- **Scroll position restored** on Back navigation (was resetting to top)

### Fixed
- **Contact names truncated** — `FN` (Formatted Name) is now always used as the authoritative display name; previously it was ignored if `N` components were already set
- **Long field values truncated** — vCard 2.1 Quoted-Printable multi-line values (soft breaks with `=`) are now correctly joined before decoding
- **Duplicate handling** updated for new typed data structures (phones/emails stored as `{value, type}` objects)

### Changed
- Phones, emails, addresses are now stored as `{value, type}` objects throughout the pipeline
- Detail view and expanded card mode show type labels alongside each phone and email
- `custom_fields`, `role`, `urls`, `anniversary` added to the GUI field selector

---

## [1.0.0] - 2026-04-28

### Initial Release
- Parse vCard 2.1 and 3.0 files (UTF-8, UTF-16-LE, Latin-1)
- Quoted-Printable and Base64 decoding
- Contacts grouped by alphabetical sections
- Two grid modes: compact clickable cards / expanded with all fields
- Detail page with photo lightbox and single-contact VCF export
- Duplicate detection: delete (keep richest) or merge (combine all fields)
- Custom field selection in GUI
- Self-contained HTML output — no external dependencies
