"""
VCF → HTML Converter — main GUI entry point.

Built with CustomTkinter for a modern cross-platform look.
Runs on macOS, Windows and Linux (requires Python 3.10+).
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from vcf_parser  import parse_file
from html_export import export_single, export_multiple
from dedup       import deduplicate

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

# Field definitions: (key, display label)
FIELD_DEFS = [
    ("nickname",     "Nickname"),
    ("organization", "Organization / Company"),
    ("title",        "Job Title"),
    ("phones",       "Phone Numbers"),
    ("emails",       "Email Addresses"),
    ("addresses",    "Addresses"),
    ("birthday",     "Birthday"),
    ("note",         "Notes"),
]


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VCF → HTML Converter")
        self.geometry("540x760")
        self.resizable(True, True)
        self.minsize(480, 640)

        # ── State variables ──────────────────────────────────────────────────
        self._vcf_path    = tk.StringVar()
        self._out_path    = tk.StringVar()
        self._export_mode = tk.StringVar(value="single")   # single | multiple
        self._grid_style  = tk.StringVar(value="compact")  # compact | expanded
        self._fields_mode = tk.StringVar(value="all")      # all | custom
        self._dedup_mode  = tk.StringVar(value="none")     # none | delete | merge
        self._field_vars  = {k: tk.BooleanVar(value=True) for k, _ in FIELD_DEFS}
        self._contacts    = []   # parsed Contact objects

        self._build_ui()

    # ── UI helpers ────────────────────────────────────────────────────────────

    def _section(self, parent, text):
        """Render a bold section label."""
        ctk.CTkLabel(
            parent, text=text, anchor="w",
            font=ctk.CTkFont(weight="bold"), text_color="#555"
        ).pack(fill="x", padx=20, pady=(16, 4))

    def _hrow(self, parent) -> ctk.CTkFrame:
        """Create and pack a transparent horizontal row frame."""
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

        # ── Grid display style (single mode only) ────────────────────────────
        self._section(self, "Grid Display Style")
        ctk.CTkLabel(
            self, text="Applies to single HTML mode only",
            text_color="#bbb", font=ctk.CTkFont(size=11), anchor="w"
        ).pack(fill="x", padx=20)
        grow = self._hrow(self)
        self._radio_compact = ctk.CTkRadioButton(
            grow, text="Compact cards  (click card to open)",
            variable=self._grid_style, value="compact"
        )
        self._radio_compact.pack(side="left", padx=(0, 16))
        self._radio_expanded = ctk.CTkRadioButton(
            grow, text="Expanded  (all fields visible on card)",
            variable=self._grid_style, value="expanded"
        )
        self._radio_expanded.pack(side="left")

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

        # Checkboxes container — shown only when "Custom selection" is active
        self._check_frame = ctk.CTkFrame(self)
        for i, (key, label) in enumerate(FIELD_DEFS):
            ctk.CTkCheckBox(
                self._check_frame, text=label,
                variable=self._field_vars[key]
            ).grid(row=i // 2, column=i % 2, sticky="w", padx=14, pady=4)

        # ── Duplicate handling ────────────────────────────────────────────────
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
        ctk.CTkLabel(
            self,
            text="Duplicates: same name + same phones + same emails → treated as one",
            text_color="#bbb", font=ctk.CTkFont(size=11), anchor="w"
        ).pack(fill="x", padx=20, pady=(2, 0))

        # ── Status + Convert button ──────────────────────────────────────────
        self._status = ctk.CTkLabel(self, text="", text_color="gray")
        self._status.pack(pady=(18, 0), padx=20)

        self._btn = ctk.CTkButton(
            self, text="Convert", height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._convert
        )
        self._btn.pack(pady=14, padx=20, fill="x")

    # ── Event handlers ─────────────────────────────────────────────────────────

    def _on_export_mode_change(self):
        """Disable grid style options when 'one file per contact' is selected."""
        state = "normal" if self._export_mode.get() == "single" else "disabled"
        self._radio_compact.configure(state=state)
        self._radio_expanded.configure(state=state)

    def _on_fields_mode_change(self):
        """Show or hide the field checkboxes based on fields mode selection."""
        if self._fields_mode.get() == "custom":
            self._check_frame.pack(fill="x", padx=20, pady=(6, 0),
                                   before=self._status)
        else:
            self._check_frame.pack_forget()

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
        threading.Thread(target=self._run_export, daemon=True).start()

    def _run_export(self):
        try:
            # Build field selection dict
            if self._fields_mode.get() == "all":
                fields = {k: True for k, _ in FIELD_DEFS}
            else:
                fields = {k: v.get() for k, v in self._field_vars.items()}

            contacts = self._contacts

            # Apply deduplication if requested
            dedup = self._dedup_mode.get()
            if dedup in ('delete', 'merge'):
                contacts, removed = deduplicate(contacts, dedup)
                dedup_msg = f" ({removed} duplicate{'s' if removed != 1 else ''} {'removed' if dedup == 'delete' else 'merged'})"
            else:
                dedup_msg = ""

            grid_style = self._grid_style.get()
            out        = self._out_path.get()
            title      = os.path.splitext(os.path.basename(self._vcf_path.get()))[0]

            if self._export_mode.get() == "single":
                export_single(contacts, out, fields, grid_style, title)
                msg = f"Saved {len(contacts)} contacts → {os.path.basename(out)}{dedup_msg}"
            else:
                export_multiple(contacts, out, fields, grid_style)
                msg = f"Saved {len(contacts)} HTML files → {os.path.basename(out)}/{dedup_msg}"

            self.after(0, lambda: self._done(msg, out, success=True))

        except Exception as e:
            self.after(0, lambda: self._done(f"Error: {e}", "", success=False))

    def _done(self, msg: str, target: str, success: bool):
        self._btn.configure(state="normal", text="Convert")
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
