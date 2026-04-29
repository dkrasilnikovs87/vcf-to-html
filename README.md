# VCF → HTML Converter

A cross-platform desktop app that converts vCard contact files (`.vcf`) into a beautiful, self-contained interactive HTML file. Also available as a command-line tool for automation.

## Features

### HTML Output
- **Interactive grid** — contacts grouped alphabetically with instant search
- **Two display modes** — compact clickable cards or expanded cards showing all fields inline
- **Detail page** — click any contact to see full info with a photo lightbox
- **Typed fields** — phones and emails shown with labels: Mobile, Home, Work, Fax …
- **Rich filter bar** — one-click filters: Photo, Mobile, Email, Website, Address, Note, Birthday, Social, Category
- **Organization dropdown** — filter all contacts by company
- **Export to VCF** — download any single contact back as a `.vcf` file
- **Fully self-contained** — one `.html` file, no external dependencies, works offline

### Parser
- vCard 2.1, 3.0 and 4.0
- Automatic encoding detection via `charset-normalizer` — UTF-8, UTF-16, Latin-1, Windows-1251 and more
- Quoted-Printable encoded fields, including multi-line soft-break values
- Inline Base64 photos
- Phone / email / address type labels (HOME, WORK, CELL, FAX …)
- Websites (`URL` field)
- Social & IM profiles — Skype, Telegram, WhatsApp, ICQ, AIM, MSN, Jabber, Viber, Twitter, LinkedIn, Facebook, Instagram and more (`X-*` and `IMPP` fields)
- Role, Anniversary, Categories
- Catch-all for any unknown field — nothing is silently lost

### Duplicate Handling
- **Delete** — keep the richest copy (most filled fields), discard the rest
- **Merge** — combine all copies into one contact (union of all phones, emails, etc.)
- **Fuzzy name matching** — treats "Anna Maria" and "Maria Anna" as the same person
- Detection based on: same name + same phones + same emails

### Photo Compression
- Resize photos before embedding using Pillow: Original / Large (1024 px) / Medium (640 px) / Small (320 px) / Strip all
- Dramatically reduces output file size for large contact books with photos

### Persistent Settings
- All options (paths, export mode, field selection, dedup mode) are saved automatically and restored on next launch

### Command-Line Interface
```bash
python cli.py contacts.vcf output.html
python cli.py contacts.vcf output.html --dedup merge --grid expanded --photo 640
python cli.py contacts.vcf output/ --mode multiple --quiet
```

## Requirements

Python 3.10+:

```bash
pip install -r requirements.txt
```

Dependencies: `customtkinter`, `charset-normalizer`, `Pillow`

## Usage

```bash
python main.py
```

1. Click **Browse** to select a `.vcf` file — contact count is shown immediately
2. Choose the output destination
3. Configure options: export mode, grid style, photo compression, field selection, duplicate handling
4. Click **Convert** — optionally open the result automatically

## CLI Usage

```
python cli.py input.vcf output.html [options]

Options:
  --mode {single,multiple}   single HTML file or one per contact (default: single)
  --grid {compact,expanded}  card style (default: compact)
  --dedup {none,delete,merge} duplicate handling (default: none)
  --fuzzy                    fuzzy name matching for dedup
  --photo MAX_PX             max photo size in px; 0=original, -1=strip (default: 0)
  --fields FIELD,...         comma-separated list of fields to include
  --title TITLE              custom HTML page title
  --quiet, -q                suppress progress output
```

## Project Structure

| File | Purpose |
|---|---|
| `main.py` | GUI entry point (CustomTkinter) |
| `cli.py` | Command-line interface (argparse) |
| `vcf_parser.py` | vCard parser — folding, QP, charset detection, typed fields, X-* |
| `html_export.py` | Generates the interactive HTML with filters and photo compression |
| `dedup.py` | Duplicate detection, merging logic, fuzzy name matching |
| `tests/` | pytest test suite — parser and dedup coverage |
| `CHANGELOG.md` | Version history |

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

## Platforms

Tested on macOS (Apple Silicon). Should work on Windows and Linux with Python 3.10+.

## Building a Standalone App

```bash
pip install pyinstaller
pyinstaller --windowed --name "VCF Converter" --collect-all customtkinter main.py
```

Output: `dist/VCF Converter.app` (macOS) or `dist/VCF Converter.exe` (Windows).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
