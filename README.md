# VCF → HTML Converter

A cross-platform desktop app that converts vCard contact files (`.vcf`) into a beautiful, self-contained interactive HTML file.

## Features

### HTML Output
- **Interactive grid** — contacts grouped alphabetically, with instant search
- **Two display modes** — compact clickable cards or expanded cards showing all fields inline
- **Detail page** — click any contact to see full info with a photo lightbox
- **Typed fields** — phones and emails shown with labels: Mobile, Home, Work, Fax …
- **Rich filter bar** — one-click filters: Photo, Mobile, Email, Website, Address, Note, Birthday, Social, Category
- **Organization dropdown** — filter all contacts by company
- **Export to VCF** — download any single contact back as a `.vcf` file
- **Fully self-contained** — one `.html` file, no external dependencies, works offline

### Parser
- vCard 2.1 and 3.0 / 4.0
- UTF-8, UTF-16-LE and Latin-1 encoded files
- Quoted-Printable encoded fields, including multi-line values
- Inline Base64 photos
- Phone / email / address type labels (HOME, WORK, CELL, FAX …)
- Websites (`URL` field)
- Social & IM profiles — Skype, Telegram, WhatsApp, ICQ, AIM, MSN, Jabber, Viber, Twitter, LinkedIn, Facebook, Instagram and more (`X-*` and `IMPP` fields)
- Role, Anniversary, Categories
- Catch-all for any custom field — nothing is silently lost

### Duplicate handling
- **Delete** — keep the richest copy (most filled fields), discard the rest
- **Merge** — combine all copies into one contact (union of all phones, emails, etc.)
- Detection based on: same name + same phones + same emails

## Requirements

Python 3.10+, [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter):

```bash
pip install customtkinter
```

## Usage

```bash
python main.py
```

1. Click **Browse** to select a `.vcf` file — contact count is shown immediately
2. Choose output destination
3. Configure options (export mode, grid style, field selection, duplicate handling)
4. Click **Convert** — optionally open the result automatically

## Project structure

| File | Purpose |
|---|---|
| `main.py` | GUI entry point (CustomTkinter) |
| `vcf_parser.py` | vCard parser — folding, QP encoding, typed fields, X-* |
| `html_export.py` | Generates the interactive HTML with filters |
| `dedup.py` | Duplicate detection and merging logic |
| `CHANGELOG.md` | Version history |

## Platforms

Tested on macOS (Apple Silicon). Should work on Windows and Linux with Python 3.10+.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
