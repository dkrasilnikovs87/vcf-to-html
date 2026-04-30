# VCF Converter

A cross-platform desktop app that converts vCard contact files (`.vcf`) into an interactive HTML file or a CSV spreadsheet. Also available as a command-line tool for scripting and automation.

## Download

Pre-built binaries are attached to each [GitHub Release](https://github.com/dkrasilnikovs87/vcf-to-html/releases):

| Platform | File | Notes |
|---|---|---|
| macOS | `VCF-Converter-macOS.zip` | Extract and run `VCF Converter.app`. Gatekeeper may warn on first launch — right-click → Open to bypass. |
| Windows | `VCF-Converter-Windows.zip` | Extract the folder, run `VCF Converter.exe`. SmartScreen may warn — click "More info → Run anyway". |
| Linux | `VCF-Converter-Linux.tar.gz` | Extract, then run the `VCF Converter` executable inside the folder. |

> Binaries are built automatically via GitHub Actions on every release tag — no manual packaging.

## Features

### Export formats
- **Interactive HTML** — self-contained single file, no external dependencies, works offline
- **CSV** — UTF-8 with BOM for correct Excel / Numbers opening on all platforms

### HTML output
- Contacts grouped alphabetically with instant search
- Two grid modes: compact clickable cards or expanded cards with all fields visible
- Rich filter bar — one-click chips: Photo, Mobile, Email, Website, Address, Note, Birthday, Social, Category
- Organization dropdown filter
- Live count ("42 of 150")
- Detail page with photo lightbox and typed field rows (Mobile, Home, Work …)
- Categories shown as tags
- **In-browser editing** — toggle Edit Mode to delete contacts or correct field values, then download the updated HTML

### vCard parser
- vCard 2.1, 3.0 and 4.0
- Automatic encoding detection (`charset-normalizer`) — UTF-8, UTF-16, Latin-1, Windows-1251, CP1252 and more
- RFC 6350 line folding and Quoted-Printable multi-line soft-break joining
- Inline Base64 photos
- Typed phone / email / address labels (CELL→Mobile, HOME→Home, WORK→Work, FAX→Fax …)
- vCard 4.0 `TYPE="work,voice"` quoted params handled correctly
- Websites (`URL`), Social & IM profiles (`X-*` and `IMPP` — Skype, Telegram, WhatsApp, ICQ, Viber, Twitter, LinkedIn, Facebook, Instagram and more)
- Role, Anniversary, Categories
- Catch-all for any unknown field — nothing is silently discarded

### Duplicate handling
- **Delete** — keep the richest copy (most filled fields), discard the rest
- **Merge** — combine all copies into one (union of phones, emails, etc.)
- **Fuzzy name matching** — "Anna Maria" and "Maria Anna" are treated as the same person; phones and emails still required to match

### Photo compression (HTML export)
Resize photos with Pillow before embedding in Base64:

| Option | Max dimension |
|---|---|
| Original (no resize) | — |
| Large | 1024 px |
| Medium | 640 px |
| Small | 320 px |
| Strip all photos | — |

### Persistent settings
All options are saved to `~/.vcf_converter_config.json` and restored on next launch.

### Logging
Structured log at `~/.vcf_converter.log` with timestamps. Full traceback on export errors.

## Requirements

Python 3.10+:

```bash
pip install -r requirements.txt
```

Dependencies: `customtkinter`, `charset-normalizer`, `Pillow`

## GUI usage

```bash
python main.py
```

1. **Browse** — select a `.vcf` file (contact count shown immediately)
2. **Output** — choose destination file or folder
3. Configure: export mode, grid style, photo compression, fields, duplicates
4. **Convert** — progress bar shown during export; optionally open the result

## CLI usage

```bash
python cli.py input.vcf output.html
python cli.py input.vcf output.csv --mode csv
python cli.py input.vcf out/ --mode multiple --dedup merge --grid expanded
python cli.py input.vcf output.html --dedup delete --fuzzy --photo 640 --quiet
```

```
positional:
  input           Input .vcf file
  output          Output path (.html, .csv, or folder for --mode multiple)

options:
  --mode          single | multiple | csv  (default: single)
  --grid          compact | expanded       (default: compact)
  --dedup         none | delete | merge    (default: none)
  --fuzzy         Fuzzy name matching for dedup (Anna Maria = Maria Anna)
  --photo MAX_PX  Max photo size in px; 0 = original, -1 = strip (default: 0)
  --fields        Comma-separated field list (default: all)
  --title         Custom HTML page title
  --quiet, -q     Suppress progress output
```

## Project structure

| File | Purpose |
|---|---|
| `main.py` | GUI entry point (CustomTkinter) |
| `cli.py` | Command-line interface (argparse) |
| `vcf_parser.py` | vCard parser — folding, QP, charset detection, typed fields, X-* |
| `html_export.py` | HTML / CSV export, in-browser edit mode |
| `dedup.py` | Duplicate detection, merge logic, fuzzy name matching |
| `tests/` | pytest test suite with sample fixtures |
| `.github/workflows/build.yml` | CI: builds macOS, Windows, Linux binaries on release tags |

## Running tests

```bash
pip install pytest
pytest tests/ -v
```

34 tests covering the parser (vCard 2.1/3.0, QP encoding, RFC folding, typed fields, social profiles, catch-all) and dedup (delete/merge, richest-copy selection, fuzzy matching).

## Building a standalone app locally

```bash
pip install pyinstaller
pyinstaller --windowed --name "VCF Converter" --collect-all customtkinter --noconfirm main.py
```

Output: `dist/VCF Converter.app` (macOS) · `dist/VCF Converter/VCF Converter.exe` (Windows) · `dist/VCF Converter/VCF Converter` (Linux)

> **macOS note:** Without Apple notarization, Gatekeeper will warn on first launch. Right-click the `.app` → Open to run it anyway.

## Platforms

Tested on macOS 15 (Apple Silicon). Should work on Windows 10+ and Linux with Python 3.10+.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
