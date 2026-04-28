# VCF → HTML Converter

A cross-platform desktop app that converts vCard contact files (`.vcf`) into a beautiful, self-contained interactive HTML file.

## Features

- **Interactive grid** — contacts grouped alphabetically, with search
- **Two display modes** — compact clickable cards or expanded cards showing all fields
- **Detail page** — click any contact to see full info, with photo lightbox
- **Export to VCF** — download any single contact back as a `.vcf` file
- **Duplicate handling** — detect, delete or merge duplicate contacts intelligently
- **Field selection** — export all fields or choose a custom set
- **Fully self-contained output** — one `.html` file, no external dependencies, works offline

## Supported vCard features

- vCard 2.1 and 3.0
- UTF-8 and UTF-16-LE encoded files
- Quoted-Printable encoded fields (including multi-line values)
- Inline Base64 photos

## Requirements

- Python 3.10+
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)

```bash
pip install customtkinter
```

## Usage

```bash
python main.py
```

1. Click **Browse** to select a `.vcf` file
2. Choose output destination
3. Configure options (export mode, fields, duplicate handling)
4. Click **Convert**

## Project structure

| File | Purpose |
|---|---|
| `main.py` | GUI entry point (CustomTkinter) |
| `vcf_parser.py` | vCard parser — handles folding, QP encoding, UTF-16 |
| `html_export.py` | Generates the interactive HTML output |
| `dedup.py` | Duplicate detection and merging logic |

## Platforms

Tested on macOS. Should work on Windows and Linux with Python 3.10+.
