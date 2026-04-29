"""
VCF → HTML Converter — main GUI entry point.

Built with CustomTkinter for a modern cross-platform look.
Runs on macOS, Windows and Linux (requires Python 3.10+).
"""

import os
import sys
import json
import logging
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from vcf_parser  import parse_file
from html_export import export_single, export_multiple
from dedup       import deduplicate

# ── Logging setup ─────────────────────────────────────────────────────────────
_LOG_PATH = Path.home() / ".vcf_converter.log"
logging.basicConfig(
    filename=str(_LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Persistent config ─────────────────────────────────────────────────────────
_CONFIG_PATH = Path.home() / ".vcf_converter_config.json"

def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding='utf-8'))
    except Exception:
        return {}

def _save_config(data: dict) -> None:
    try:
        _CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as e:
        log.warning("Could not save config: %s", e)

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

# Field definitions: (key, display label)
FIELD_DEFS = [
    ("nickname",      "Nickname"),
    ("organization",  "Organization / Company"),
    ("title",         "Job Title"),
    ("role",          "Role"),
    ("phones",        "Phone Numbers"),
    ("emails",        "Email Addresses"),
    ("addresses",     "Addresses"),
    ("urls",          "Websites"),
    ("birthday",      "Birthday"),
    ("anniversary",   "Anniversary"),
    ("note",          "Notes"),
    ("custom_fields", "Social / IM / Custom"),
]

PHOTO_OPTIONS = {
    "Original (no resize)": 0,
    "Large  (max 1024 px)":  1024,
    "Medium (max 640 px)":   640,
    "Small  (max 320 px)":   320,
    "Strip all photos":      -1,
}


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VCF → HTML Converter")
        self.resizable(True, True)

        cfg = _load_config()

        # ── State variables ──────────────────────────────────────────────────
        self._vcf_path    = tk.StringVar(value=cfg.get("vcf_path", ""))
        self._out_path    = tk.StringVar(value=cfg.get("out_path", ""))
        self._export_mode = tk.StringVar(value=cfg.get("export_mode", "single"))
        self._grid_style  = tk.StringVar(value=cfg.get("grid_style", "compact"))
        self._fields_mode = tk.StringVar(value=cfg.get("fields_mode", "all"))
        self._dedup_mode  = tk.StringVar(value=cfg.get("dedup_mode", "none"))
        self._fuzzy_dedup = tk.BooleanVar(value=cfg.get("fuzzy_dedup", False))
        self._photo_opt   = tk.StringVar(value=cfg.get("photo_opt", list(PHOTO_OPTIONS)[0]))
        saved_fields      = cfg.get("field_vars", {})
        self._field_vars  = {
            k: tk.BooleanVar(value=saved_fields.get(k, True))
            for k, _ in FIELD_DEFS
        }
        self._contacts    = []
        self._base_height = 0   # natural window height without checkboxes

        self._build_ui()

        # Lock minimum size to natural content height after layout is computed
        self.update_idletasks()
        self._base_height = self.winfo_reqheight()
        self.minsize(520, self._base_height)
        self.geometry(f"560x{self._base_height}")

        # If config had custom fields open, show them now
        if self._fields_mode.get() == "custom":
            self._show_checkboxes(animate=False)

        log.info("App started")

    # ── UI helpers ────────────────────────────────────────────────────────────

    def _section(self, parent, text):
        ctk.CTkLabel(
            parent, text=text, anchor="w",
            font=ctk.CTkFont(weight="bold"), text_color="#555"
        ).pack(fill="x", padx=20, pady=(16, 4))

    def _hrow(self, parent) -> ctk.CTkFrame:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=0)
        return row

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # Title
        ctk.CTkLabel(
            self, text="VCF → HTML Converter",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(22, 2))
        ctk.CTkLabel(
            self, text="Convert vCard contacts to an interactive HTML file",
            text_color="gray"
        ).pack(pady=(0, 6))

        # ── Input file ───────────────────────────────────────────────────────
        self._section(self, "Input VCF File")
        row = self._hrow(self)
        ctk.CTkEntry(
            row, textvariable=self._vcf_path, state="readonly",
            placeholder_text="No file selected..."
        ).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="Browse", width=80,
                      command=self._browse_input).pack(side="left", padx=(8, 0))

        # ── Output destination ───────────────────────────────────────────────
        self._section(self, "Output Destination")
        row2 = self._hrow(self)
        ctk.CTkEntry(
            row2, textvariable=self._out_path, state="readonly",
            placeholder_text="No destination selected..."
        ).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row2, text="Browse", width=80,
                      command=self._browse_output).pack(side="left", padx=(8, 0))

        # ── Export mode ──────────────────────────────────────────────────────
        self._section(self, "Export Mode")
        mrow = self._hrow(self)
        ctk.CTkRadioButton(
            mrow, text="Single HTML file (all contacts)",
            variable=self._export_mode, value="single",
            command=self._on_export_mode_change
        ).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(
            mrow, text="One file per contact",
            variable=self._export_mode, value="multiple",
            command=self._on_export_mode_change
        ).pack(side="left")

        # ── Grid display style ───────────────────────────────────────────────
        self._section(self, "Grid Display Style")
        ctk.CTkLabel(
            self, text="Applies to single HTML mode only",
            text_color="#bbb", font=ctk.CTkFont(size=11), anchor="w"
        ).pack(fill="x", padx=20)
        grow = self._hrow(self)
        self._radio_compact = ctk.CTkRadioButton(
            grow, text="Compact  (click card to open)",
            variable=self._grid_style, value="compact"
        )
        self._radio_compact.pack(side="left", padx=(0, 16))
        self._radio_expanded = ctk.CTkRadioButton(
            grow, text="Expanded  (all fields on card)",
            variable=self._grid_style, value="expanded"
        )
        self._radio_expanded.pack(side="left")

        # ── Photo compression ────────────────────────────────────────────────
        self._section(self, "Photo Compression")
        prow = self._hrow(self)
        ctk.CTkLabel(prow, text="Resize photos:", anchor="w",
                     font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))
        ctk.CTkOptionMenu(
            prow, variable=self._photo_opt,
            values=list(PHOTO_OPTIONS.keys()), width=220
        ).pack(side="left")

        # ── Fields to include ────────────────────────────────────────────────
        self._section(self, "Fields to Include")
        frow = self._hrow(self)
        ctk.CTkRadioButton(
            frow, text="All fields",
            variable=self._fields_mode, value="all",
            command=self._on_fields_mode_change
        ).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(
            frow, text="Custom selection",
            variable=self._fields_mode, value="custom",
            command=self._on_fields_mode_change
        ).pack(side="left")

        # Checkboxes — hidden initially, window grows when shown
        self._check_frame = ctk.CTkFrame(self)
        for i, (key, label) in enumerate(FIELD_DEFS):
            ctk.CTkCheckBox(
                self._check_frame, text=label,
                variable=self._field_vars[key]
            ).grid(row=i // 2, column=i % 2, sticky="w", padx=14, pady=4)

        # ── Duplicate handling ───────────────────────────────────────────────
        self._section(self, "Duplicate Handling")
        drow = self._hrow(self)
        ctk.CTkRadioButton(
            drow, text="Keep all",
            variable=self._dedup_mode, value="none"
        ).pack(side="left", padx=(0, 12))
        ctk.CTkRadioButton(
            drow, text="Delete duplicates",
            variable=self._dedup_mode, value="delete"
        ).pack(side="left", padx=(0, 12))
        ctk.CTkRadioButton(
            drow, text="Merge duplicates",
            variable=self._dedup_mode, value="merge"
        ).pack(side="left")
        ctk.CTkCheckBox(
            self, text="Fuzzy name matching  (Иван Иванов = Иванов Иван)",
            variable=self._fuzzy_dedup, font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=20, pady=(6, 0))
        ctk.CTkLabel(
            self,
            text="Duplicates: same name + same phones + same emails → treated as one",
            text_color="#bbb", font=ctk.CTkFont(size=11), anchor="w"
        ).pack(fill="x", padx=20, pady=(2, 0))

        # ── Status + progress + Convert button ───────────────────────────────
        self._status = ctk.CTkLabel(self, text="", text_color="gray")
        self._status.pack(pady=(18, 4), padx=20)

        self._progress = ctk.CTkProgressBar(self, height=6)
        self._progress.set(0)
        # hidden until conversion starts

        self._btn = ctk.CTkButton(
            self, text="Convert", height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._convert
        )
        self._btn.pack(pady=(4, 18), padx=20, fill="x")

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_export_mode_change(self):
        state = "normal" if self._export_mode.get() == "single" else "disabled"
        self._radio_compact.configure(state=state)
        self._radio_expanded.configure(state=state)

    def _on_fields_mode_change(self):
        if self._fields_mode.get() == "custom":
            self._show_checkboxes()
        else:
            self._hide_checkboxes()

    def _show_checkboxes(self, animate=True):
        self._check_frame.pack(fill="x", padx=20, pady=(6, 0), before=self._status)
        self.update_idletasks()
        needed = self.winfo_reqheight()
        current = self.winfo_height()
        if needed > current:
            self.geometry(f"{self.winfo_width()}x{needed}")
        self.minsize(520, needed)

    def _hide_checkboxes(self):
        self._check_frame.pack_forget()
        self.update_idletasks()
        self.geometry(f"{self.winfo_width()}x{self._base_height}")
        self.minsize(520, self._base_height)

    def _browse_input(self):
        path = filedialog.askopenfilename(
            title="Select VCF file",
            filetypes=[("vCard files", "*.vcf"), ("All files", "*.*")]
        )
        if not path:
            return
        self._vcf_path.set(path)
        contacts = parse_file(path)
        self._contacts = contacts
        self._status.configure(
            text=f"Loaded {len(contacts)} contact{'s' if len(contacts) != 1 else ''}",
            text_color="#50C878"
        )

    def _browse_output(self):
        if self._export_mode.get() == "single":
            path = filedialog.asksaveasfilename(
                title="Save HTML file as",
                defaultextension=".html",
                filetypes=[("HTML files", "*.html")]
            )
        else:
            path = filedialog.askdirectory(title="Select output folder")
        if path:
            self._out_path.set(path)

    # ── Conversion ────────────────────────────────────────────────────────────

    def _convert(self):
        if not self._vcf_path.get():
            messagebox.showerror("Error", "Please select a VCF input file first.")
            return
        if not self._out_path.get():
            messagebox.showerror("Error", "Please choose an output destination.")
            return
        if not self._contacts:
            messagebox.showerror("Error", "No contacts loaded. Check the input file.")
            return

        self._btn.configure(state="disabled", text="Converting…")
        self._progress.set(0)
        self._progress.pack(pady=(0, 4), padx=20, fill="x", before=self._btn)
        threading.Thread(target=self._run_export, daemon=True).start()

    def _set_progress(self, value: float):
        self._progress.set(value)

    def _run_export(self):
        try:
            if self._fields_mode.get() == "all":
                fields = {k: True for k, _ in FIELD_DEFS}
            else:
                fields = {k: v.get() for k, v in self._field_vars.items()}

            contacts = self._contacts

            dedup = self._dedup_mode.get()
            if dedup in ('delete', 'merge'):
                contacts, removed = deduplicate(contacts, dedup,
                                                fuzzy=self._fuzzy_dedup.get())
                dedup_msg = f" ({removed} duplicate{'s' if removed != 1 else ''} {'removed' if dedup == 'delete' else 'merged'})"
            else:
                dedup_msg = ""

            photo_max_size = PHOTO_OPTIONS.get(self._photo_opt.get(), 0)
            grid_style = self._grid_style.get()
            out        = self._out_path.get()
            title      = os.path.splitext(os.path.basename(self._vcf_path.get()))[0]

            def progress_cb(v):
                self.after(0, lambda val=v: self._set_progress(val))

            if self._export_mode.get() == "single":
                export_single(contacts, out, fields, grid_style, title,
                              photo_max_size=photo_max_size, progress_cb=progress_cb)
                msg = f"Saved {len(contacts)} contacts → {os.path.basename(out)}{dedup_msg}"
            else:
                export_multiple(contacts, out, fields, grid_style,
                                photo_max_size=photo_max_size, progress_cb=progress_cb)
                msg = f"Saved {len(contacts)} HTML files → {os.path.basename(out)}/{dedup_msg}"

            log.info("Export complete: %s", msg)
            _save_config({
                "vcf_path":    self._vcf_path.get(),
                "out_path":    self._out_path.get(),
                "export_mode": self._export_mode.get(),
                "grid_style":  self._grid_style.get(),
                "fields_mode": self._fields_mode.get(),
                "dedup_mode":  self._dedup_mode.get(),
                "fuzzy_dedup": self._fuzzy_dedup.get(),
                "photo_opt":   self._photo_opt.get(),
                "field_vars":  {k: v.get() for k, v in self._field_vars.items()},
            })
            self.after(0, lambda: self._done(msg, out, success=True))

        except Exception as e:
            log.exception("Export failed")
            self.after(0, lambda: self._done(f"Error: {e}", "", success=False))

    def _done(self, msg: str, target: str, success: bool):
        self._btn.configure(state="normal", text="Convert")
        self._progress.pack_forget()
        self._status.configure(
            text=msg,
            text_color="#50C878" if success else "#FF6B6B"
        )
        if success and messagebox.askyesno("Done", f"{msg}\n\nOpen the result?"):
            import subprocess
            if sys.platform == "darwin":
                subprocess.Popen(["open", target])
            elif sys.platform == "win32":
                os.startfile(target)
            else:
                subprocess.Popen(["xdg-open", target])


if __name__ == "__main__":
    app = App()
    app.mainloop()
