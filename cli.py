"""
VCF → HTML Converter — command-line interface.

Examples:
  python cli.py contacts.vcf output.html
  python cli.py contacts.vcf output/ --mode multiple
  python cli.py contacts.vcf output.html --dedup merge --grid expanded --photo 640
  python cli.py contacts.vcf output.html --fields phones,emails,addresses
"""

import argparse
import sys
from pathlib import Path

from vcf_parser  import parse_file
from html_export import export_single, export_multiple
from dedup       import deduplicate

ALL_FIELDS = [
    "nickname", "organization", "title", "role", "phones",
    "emails", "addresses", "urls", "birthday", "anniversary",
    "note", "custom_fields",
]


def _progress_bar(value: float, width: int = 40) -> str:
    filled = int(width * value)
    bar = "█" * filled + "░" * (width - filled)
    return f"\r[{bar}] {int(value * 100):3d}%"


def main():
    parser = argparse.ArgumentParser(
        prog="vcf2html",
        description="Convert VCF contacts to interactive HTML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input",  help="Input .vcf file")
    parser.add_argument("output", help="Output .html file, or folder when --mode=multiple")

    parser.add_argument(
        "--mode", choices=["single", "multiple"], default="single",
        help="single: one HTML file (default) | multiple: one file per contact"
    )
    parser.add_argument(
        "--grid", choices=["compact", "expanded"], default="compact",
        help="Grid style for single mode (default: compact)"
    )
    parser.add_argument(
        "--dedup", choices=["none", "delete", "merge"], default="none",
        help="Duplicate handling (default: none)"
    )
    parser.add_argument(
        "--photo", type=int, default=0, metavar="MAX_PX",
        help="Max photo dimension in pixels (0=original, -1=strip all photos)"
    )
    parser.add_argument(
        "--fields", metavar="FIELD,...",
        help=f"Comma-separated fields to include. Default: all. "
             f"Available: {', '.join(ALL_FIELDS)}"
    )
    parser.add_argument(
        "--title", default="",
        help="HTML page title (default: input filename without extension)"
    )
    parser.add_argument(
        "--fuzzy", action="store_true",
        help="Fuzzy name matching for dedup (Иван Иванов = Иванов Иван)"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress progress output"
    )

    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print(f"Parsing {args.input}…")
    contacts = parse_file(args.input)
    if not contacts:
        print("Error: no contacts found in file.", file=sys.stderr)
        sys.exit(1)
    if not args.quiet:
        print(f"  Loaded {len(contacts)} contacts")

    if args.dedup in ("delete", "merge"):
        contacts, removed = deduplicate(contacts, args.dedup, fuzzy=args.fuzzy)
        if not args.quiet:
            fuzzy_note = " fuzzy" if args.fuzzy else ""
            print(f"  Dedup ({args.dedup}{fuzzy_note}): {removed} removed, {len(contacts)} remaining")

    # Build fields dict
    if args.fields:
        requested = {f.strip() for f in args.fields.split(",")}
        unknown = requested - set(ALL_FIELDS)
        if unknown:
            print(f"Warning: unknown fields ignored: {', '.join(unknown)}", file=sys.stderr)
        fields = {k: (k in requested) for k in ALL_FIELDS}
    else:
        fields = {k: True for k in ALL_FIELDS}

    title = args.title or Path(args.input).stem

    def progress_cb(v: float):
        if not args.quiet:
            print(_progress_bar(v), end="", flush=True)

    if not args.quiet:
        print(f"Exporting → {args.output}…")

    if args.mode == "single":
        export_single(contacts, args.output, fields, args.grid, title,
                      photo_max_size=args.photo, progress_cb=progress_cb)
    else:
        export_multiple(contacts, args.output, fields, args.grid,
                        photo_max_size=args.photo, progress_cb=progress_cb)

    if not args.quiet:
        print()  # newline after progress bar
        print(f"Done. Saved {len(contacts)} contacts → {args.output}")


if __name__ == "__main__":
    main()
