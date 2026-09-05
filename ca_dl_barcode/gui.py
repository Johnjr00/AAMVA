"""
Tkinter desktop GUI for the California DL/ID PDF417 barcode generator.

Presents every AAMVA data element as a labelled field (dropdowns for the
enumerated ones), validates input against the standard, renders a live PDF417
preview, and exports to PNG or SVG.  The raw AAMVA payload and a decoded view
are available for verification.

Run with ``python run.py`` (or ``python -m ca_dl_barcode``).
"""

from __future__ import annotations

import io
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import barcode as bc
from . import constants as C
from . import encoder, parser
from .model import LicenseData, ZCSubfile
from .validation import validate

APP_TITLE = "California DL/ID PDF417 Barcode Generator (AAMVA v09)"

COMPLIANCE_NOTICE = (
    "For testing and development of barcode-reading / ID-verification software. "
    "Generates AAMVA data payloads only - not a government document and not for "
    "producing fraudulent identification."
)

PAD = 6


def _combo_values(mapping: dict) -> list:
    """Turn a {code: label} mapping into 'code - label' combo entries."""
    return [f"{code} - {label}" for code, label in mapping.items()]


def _code_from_combo(value: str) -> str:
    """Extract the leading code from a 'code - label' combo selection."""
    return (value or "").split(" - ", 1)[0].strip()


class BarcodeApp(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master, padding=PAD)
        self.master = master
        master.title(APP_TITLE)
        master.geometry("1120x820")
        master.minsize(940, 640)

        self.vars: dict[str, tk.Variable] = {}
        self._preview_photo = None      # keep a reference so Tk doesn't GC it
        self._current_payload: str | None = None

        self._build_styles()
        self._build_layout()
        self.load_sample()

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def _build_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Notice.TLabel", foreground="#7a5a00",
                        background="#fff4cc", padding=6)
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Generate.TButton", font=("Segoe UI", 10, "bold"))

    def _build_layout(self) -> None:
        self.pack(fill="both", expand=True)

        notice = ttk.Label(self, text=COMPLIANCE_NOTICE, style="Notice.TLabel",
                          anchor="center", wraplength=1080)
        notice.pack(fill="x", pady=(0, PAD))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        # Left: scrollable form.  Right: preview + actions.
        left = ttk.Frame(body)
        left.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(body, width=420)
        right.pack(side="right", fill="both", padx=(PAD, 0))
        right.pack_propagate(False)

        self._build_form(left)
        self._build_side(right)

        self.status = tk.StringVar(value="Ready.")
        status_bar = ttk.Label(self, textvariable=self.status, relief="sunken",
                              anchor="w", padding=4)
        status_bar.pack(fill="x", pady=(PAD, 0))

    def _build_form(self, parent: ttk.Frame) -> None:
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        form = ttk.Frame(canvas)
        form.bind("<Configure>",
                 lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        window = canvas.create_window((0, 0), window=form, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mouse-wheel scrolling (Windows / macOS / Linux).
        def _on_wheel(event):
            delta = -1 if getattr(event, "num", None) == 5 or event.delta < 0 else 1
            canvas.yview_scroll(-delta, "units")
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            canvas.bind_all(seq, _on_wheel)

        self._build_name_section(form)
        self._build_dates_section(form)
        self._build_physical_section(form)
        self._build_address_section(form)
        self._build_license_section(form)
        self._build_realid_section(form)
        self._build_zc_section(form)
        self._build_advanced_section(form)

    # -- field helpers -------------------------------------------------- #
    def _section(self, parent, title) -> ttk.LabelFrame:
        frame = ttk.Labelframe(parent, text=title, style="Section.TLabelframe",
                              padding=PAD)
        frame.pack(fill="x", padx=PAD, pady=PAD)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)
        return frame

    def _entry(self, parent, key, label, row, col=0, width=24, hint=""):
        var = tk.StringVar()
        self.vars[key] = var
        ttk.Label(parent, text=label).grid(row=row, column=col * 2, sticky="w",
                                          padx=(0, 4), pady=3)
        entry = ttk.Entry(parent, textvariable=var, width=width)
        entry.grid(row=row, column=col * 2 + 1, sticky="ew", pady=3)
        if hint:
            self._add_tip(entry, hint)
        return var

    def _combo(self, parent, key, label, values, row, col=0, width=22, hint=""):
        var = tk.StringVar()
        self.vars[key] = var
        ttk.Label(parent, text=label).grid(row=row, column=col * 2, sticky="w",
                                          padx=(0, 4), pady=3)
        combo = ttk.Combobox(parent, textvariable=var, values=values,
                            state="readonly", width=width)
        combo.grid(row=row, column=col * 2 + 1, sticky="ew", pady=3)
        if hint:
            self._add_tip(combo, hint)
        return var

    def _check(self, parent, key, label, row, col=0):
        var = tk.BooleanVar()
        self.vars[key] = var
        ttk.Checkbutton(parent, text=label, variable=var).grid(
            row=row, column=col * 2, columnspan=2, sticky="w", pady=3)
        return var

    def _add_tip(self, widget, text):
        """Very small tooltip implementation."""
        tip = {"win": None}

        def show(_):
            if tip["win"] or not text:
                return
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + widget.winfo_height() + 2
            win = tk.Toplevel(widget)
            win.wm_overrideredirect(True)
            win.wm_geometry(f"+{x}+{y}")
            ttk.Label(win, text=text, background="#ffffe0", relief="solid",
                     borderwidth=1, padding=4, wraplength=320).pack()
            tip["win"] = win

        def hide(_):
            if tip["win"]:
                tip["win"].destroy()
                tip["win"] = None

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)

    # -- sections ------------------------------------------------------- #
    def _build_name_section(self, parent):
        f = self._section(parent, "Name")
        self._entry(f, "family_name", "Family name (DCS) *", 0, 0)
        self._entry(f, "first_name", "First name (DAC) *", 0, 1)
        self._entry(f, "middle_name", "Middle name(s) (DAD)", 1, 0)
        self._entry(f, "name_suffix", "Suffix (DCU)", 1, 1,
                   hint="JR, SR, III ...")
        trunc = _combo_values(C.TRUNCATION_CODES)
        self._combo(f, "family_truncation", "Family truncated (DDE)", trunc, 2, 0)
        self._combo(f, "first_truncation", "First truncated (DDF)", trunc, 2, 1)
        self._combo(f, "middle_truncation", "Middle truncated (DDG)", trunc, 3, 0)

    def _build_dates_section(self, parent):
        f = self._section(parent, "Dates  (enter as MM/DD/YYYY)")
        self._entry(f, "issue_date", "Issue date (DBD) *", 0, 0,
                   hint="Encoded as MMDDCCYY")
        self._entry(f, "expiry_date", "Expiration date (DBA) *", 0, 1)
        self._entry(f, "dob", "Date of birth (DBB) *", 1, 0)

    def _build_physical_section(self, parent):
        f = self._section(parent, "Physical description")
        self._combo(f, "sex", "Sex (DBC) *", _combo_values(C.SEX_CODES), 0, 0)
        self._combo(f, "eye_color", "Eye colour (DAY) *",
                   _combo_values(C.EYE_COLORS), 0, 1)
        self._combo(f, "hair_color", "Hair colour (ZCB)",
                   [""] + _combo_values(C.HAIR_COLORS), 1, 0,
                   hint="California stores hair colour in the ZC subfile (ZCB)")
        self._entry(f, "height_value", "Height (DAU) *", 1, 1,
                   hint="Number only, e.g. 68")
        self._combo(f, "height_unit", "Height unit",
                   [C.HEIGHT_UNIT_INCHES, C.HEIGHT_UNIT_CM], 2, 0, width=10)
        self._entry(f, "weight_lb", "Weight lb (DAW)", 2, 1)

    def _build_address_section(self, parent):
        f = self._section(parent, "Address")
        self._entry(f, "street1", "Street (DAG) *", 0, 0)
        self._entry(f, "street2", "Street 2 (DAH)", 0, 1)
        self._entry(f, "city", "City (DAI) *", 1, 0)
        self._combo(f, "state", "State (DAJ) *", C.US_JURISDICTIONS, 1, 1,
                   width=8)
        self._entry(f, "postal_code", "ZIP (DAK) *", 2, 0,
                   hint="5 or 9 digits; padded to 9")

    def _build_license_section(self, parent):
        f = self._section(parent, "License / document")
        self._entry(f, "dl_number", "DL/ID number (DAQ) *", 0, 0)
        self._entry(f, "vehicle_class", "Vehicle class (DCA) *", 0, 1,
                   hint="California class, e.g. C")
        self._entry(f, "restrictions", "Restrictions (DCB)", 1, 0,
                   hint="NONE if none")
        self._entry(f, "endorsements", "Endorsements (DCD)", 1, 1,
                   hint="NONE if none")
        self._entry(f, "document_discriminator", "Doc discriminator (DCF) *", 2, 0)
        self._entry(f, "inventory_control", "Inventory control (DCK)", 2, 1)

    def _build_realid_section(self, parent):
        f = self._section(parent, "REAL ID / DHS  (optional)")
        self._combo(f, "compliance_type", "Compliance (DDA)",
                   [""] + _combo_values(C.COMPLIANCE_TYPES), 0, 0, width=30)
        self._entry(f, "card_revision_date", "Card revision date (DDB)", 0, 1)
        self._check(f, "limited_duration", "Limited duration (DDD)", 1, 0)
        self._check(f, "organ_donor", "Organ donor (DDK)", 1, 1)
        self._check(f, "veteran", "Veteran (DDL)", 2, 0)

    def _build_zc_section(self, parent):
        f = self._section(parent, "California jurisdiction subfile (ZC)")
        note = ("California's ZC subfile has no ZCA. ZCB carries the hair "
                "colour (set it in Physical description above); ZCC and ZCD "
                "are present but blank on issued cards. The ZC subfile is "
                "emitted whenever a hair colour is set.")
        ttk.Label(f, text=note, wraplength=760, foreground="#555").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))
        self._entry(f, "zcc", "ZCC (usually blank)", 1, 0)
        self._entry(f, "zcd", "ZCD (usually blank)", 1, 1)

    def _build_advanced_section(self, parent):
        f = self._section(parent, "Advanced  (header & symbol)")
        self._entry(f, "iin", "IIN", 0, 0, width=12,
                   hint="California = 636014")
        self._entry(f, "aamva_version", "AAMVA version", 0, 1, width=8,
                   hint="California 2017-2025 = 09")
        self._entry(f, "jurisdiction_version", "Jurisdiction version", 1, 0,
                   width=8)
        self._entry(f, "columns", "PDF417 columns", 1, 1, width=8,
                   hint="Symbol width; default 13")
        self._entry(f, "security_level", "Error-correction level", 2, 0,
                   width=8, hint="PDF417 EC level 0-8; default 5")
        # sensible defaults for the header/symbol fields
        self.vars["iin"].set(C.CALIFORNIA_IIN)
        self.vars["aamva_version"].set(C.DEFAULT_AAMVA_VERSION)
        self.vars["jurisdiction_version"].set(C.DEFAULT_JURISDICTION_VERSION)
        self.vars["columns"].set(str(bc.DEFAULT_COLUMNS))
        self.vars["security_level"].set(str(bc.DEFAULT_SECURITY_LEVEL))

    def _build_side(self, parent):
        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(0, PAD))
        ttk.Button(actions, text="Generate / Preview", style="Generate.TButton",
                  command=self.generate).pack(fill="x", pady=2)
        row1 = ttk.Frame(actions); row1.pack(fill="x")
        ttk.Button(row1, text="Save PNG", command=self.save_png).pack(
            side="left", fill="x", expand=True, padx=(0, 2), pady=2)
        ttk.Button(row1, text="Save SVG", command=self.save_svg).pack(
            side="left", fill="x", expand=True, padx=(2, 0), pady=2)
        row2 = ttk.Frame(actions); row2.pack(fill="x")
        ttk.Button(row2, text="Raw payload", command=self.show_raw).pack(
            side="left", fill="x", expand=True, padx=(0, 2), pady=2)
        ttk.Button(row2, text="Decoded view", command=self.show_decoded).pack(
            side="left", fill="x", expand=True, padx=(2, 0), pady=2)
        row3 = ttk.Frame(actions); row3.pack(fill="x")
        ttk.Button(row3, text="Load sample", command=self.load_sample).pack(
            side="left", fill="x", expand=True, padx=(0, 2), pady=2)
        ttk.Button(row3, text="Clear", command=self.clear_form).pack(
            side="left", fill="x", expand=True, padx=(2, 0), pady=2)

        preview_box = ttk.Labelframe(parent, text="PDF417 preview", padding=PAD)
        preview_box.pack(fill="both", expand=True)
        self.preview = tk.Canvas(preview_box, background="white",
                               highlightthickness=1, highlightbackground="#ccc")
        self.preview.pack(fill="both", expand=True)
        self.preview.bind("<Configure>", lambda e: self._draw_preview())

    # ------------------------------------------------------------------ #
    # Data <-> form
    # ------------------------------------------------------------------ #
    def collect(self) -> LicenseData:
        g = lambda k: (self.vars[k].get() or "").strip()
        return LicenseData(
            iin=g("iin"),
            aamva_version=g("aamva_version"),
            jurisdiction_version=g("jurisdiction_version"),
            family_name=g("family_name"),
            first_name=g("first_name"),
            middle_name=g("middle_name"),
            name_suffix=g("name_suffix"),
            family_truncation=_code_from_combo(g("family_truncation")) or "N",
            first_truncation=_code_from_combo(g("first_truncation")) or "N",
            middle_truncation=_code_from_combo(g("middle_truncation")) or "N",
            issue_date=g("issue_date"),
            expiry_date=g("expiry_date"),
            dob=g("dob"),
            sex=_code_from_combo(g("sex")),
            eye_color=_code_from_combo(g("eye_color")),
            hair_color=_code_from_combo(g("hair_color")),
            height_value=g("height_value"),
            height_unit=g("height_unit") or C.HEIGHT_UNIT_INCHES,
            weight_lb=g("weight_lb"),
            street1=g("street1"),
            street2=g("street2"),
            city=g("city"),
            state=g("state"),
            postal_code=g("postal_code"),
            dl_number=g("dl_number"),
            vehicle_class=g("vehicle_class"),
            restrictions=g("restrictions"),
            endorsements=g("endorsements"),
            document_discriminator=g("document_discriminator"),
            inventory_control=g("inventory_control"),
            compliance_type=_code_from_combo(g("compliance_type")),
            card_revision_date=g("card_revision_date"),
            limited_duration=bool(self.vars["limited_duration"].get()),
            organ_donor=bool(self.vars["organ_donor"].get()),
            veteran=bool(self.vars["veteran"].get()),
            zc=ZCSubfile(zcc=g("zcc"), zcd=g("zcd")),
        )

    def _symbol_options(self):
        try:
            columns = int(self.vars["columns"].get())
        except ValueError:
            columns = bc.DEFAULT_COLUMNS
        try:
            security = int(self.vars["security_level"].get())
        except ValueError:
            security = bc.DEFAULT_SECURITY_LEVEL
        return max(1, min(columns, 30)), max(0, min(security, 8))

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #
    def _validated_payload(self):
        data = self.collect()
        result = validate(data)
        if result.warnings:
            self.status.set("Warning: " + " ".join(result.warnings))
        if not result.ok:
            messagebox.showerror(
                "Cannot generate barcode",
                "Please fix the following:\n\n- " + "\n- ".join(result.errors),
            )
            return None
        try:
            return encoder.encode(data)
        except Exception as exc:  # pragma: no cover - defensive
            messagebox.showerror("Encoding error", str(exc))
            return None

    def generate(self):
        payload = self._validated_payload()
        if payload is None:
            return
        self._current_payload = payload
        self._draw_preview()
        if not self.status.get().startswith("Warning"):
            self.status.set(f"Generated - payload is {len(payload)} bytes, "
                          f"{self.collect().iin} v{self.collect().aamva_version}.")

    def _draw_preview(self):
        if not self._current_payload:
            return
        columns, security = self._symbol_options()
        try:
            image = bc.render_png_image(self._current_payload, columns=columns,
                                       security_level=security, scale=3)
        except Exception as exc:
            self.status.set(f"Preview error: {exc}")
            return
        cw = max(self.preview.winfo_width(), 10)
        ch = max(self.preview.winfo_height(), 10)
        scale = min(cw / image.width, ch / image.height, 1.0)
        if scale < 1.0:
            image = image.resize((max(1, int(image.width * scale)),
                                 max(1, int(image.height * scale))))
        self._preview_photo = self._pil_to_photo(image)
        self.preview.delete("all")
        self.preview.create_image(cw // 2, ch // 2, image=self._preview_photo)

    @staticmethod
    def _pil_to_photo(image):
        """Convert a PIL image to a Tk PhotoImage without extra dependencies."""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return tk.PhotoImage(data=buffer.getvalue())

    def save_png(self):
        payload = self._validated_payload()
        if payload is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("PNG image", "*.png")],
            initialfile="ca_dl_barcode.png")
        if not path:
            return
        columns, security = self._symbol_options()
        bc.save_png(payload, path, columns=columns, security_level=security)
        self._current_payload = payload
        self._draw_preview()
        self.status.set(f"Saved PNG: {path}")

    def save_svg(self):
        payload = self._validated_payload()
        if payload is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".svg", filetypes=[("SVG vector", "*.svg")],
            initialfile="ca_dl_barcode.svg")
        if not path:
            return
        columns, security = self._symbol_options()
        bc.save_svg(payload, path, columns=columns, security_level=security,
                   description="California DL/ID AAMVA PDF417")
        self._current_payload = payload
        self._draw_preview()
        self.status.set(f"Saved SVG: {path}")

    def show_raw(self):
        payload = self._validated_payload()
        if payload is None:
            return
        printable = (payload.replace(C.DATA_ELEMENT_SEPARATOR, "<LF>\n")
                            .replace(C.RECORD_SEPARATOR, "<RS>")
                            .replace(C.SEGMENT_TERMINATOR, "<CR>\n"))
        self._text_window("Raw AAMVA payload", printable, payload)

    def show_decoded(self):
        payload = self._validated_payload()
        if payload is None:
            return
        self._text_window("Decoded barcode", parser.to_readable(payload), payload)

    def _text_window(self, title, text, copy_value):
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("640x560")
        box = tk.Text(win, wrap="word", font=("Consolas", 10))
        box.insert("1.0", text)
        box.configure(state="disabled")
        box.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        def copy():
            self.clipboard_clear()
            self.clipboard_append(copy_value)
            self.status.set("Copied raw payload to clipboard.")
        ttk.Button(win, text="Copy raw payload", command=copy).pack(pady=(0, PAD))

    # ------------------------------------------------------------------ #
    # Sample / clear
    # ------------------------------------------------------------------ #
    def clear_form(self):
        for key, var in self.vars.items():
            if isinstance(var, tk.BooleanVar):
                var.set(False)
            else:
                var.set("")
        self.vars["iin"].set(C.CALIFORNIA_IIN)
        self.vars["aamva_version"].set(C.DEFAULT_AAMVA_VERSION)
        self.vars["jurisdiction_version"].set(C.DEFAULT_JURISDICTION_VERSION)
        self.vars["columns"].set(str(bc.DEFAULT_COLUMNS))
        self.vars["security_level"].set(str(bc.DEFAULT_SECURITY_LEVEL))
        self.vars["state"].set("CA")
        self.vars["height_unit"].set(C.HEIGHT_UNIT_INCHES)
        self._current_payload = None
        self.preview.delete("all")
        self.status.set("Form cleared.")

    def load_sample(self):
        sample = {
            "family_name": "CARDHOLDER", "first_name": "JANE",
            "middle_name": "QUINCY", "name_suffix": "",
            "family_truncation": "N - Not truncated",
            "first_truncation": "N - Not truncated",
            "middle_truncation": "N - Not truncated",
            "issue_date": "01/15/2020", "expiry_date": "03/22/2028",
            "dob": "05/12/1985", "sex": "2 - Female", "eye_color": "BRN - Brown",
            "hair_color": "BRN - Brown", "height_value": "65",
            "height_unit": "in", "weight_lb": "130",
            "street1": "1234 MAIN ST", "street2": "", "city": "LOS ANGELES",
            "state": "CA", "postal_code": "90001", "dl_number": "D1234567",
            "vehicle_class": "C", "restrictions": "NONE", "endorsements": "NONE",
            "document_discriminator": "ABCD1234567890", "inventory_control": "",
            "compliance_type": "F - REAL ID compliant",
            "card_revision_date": "01/01/2018",
            "zcc": "", "zcd": "",
        }
        for key, value in sample.items():
            if key in self.vars:
                self.vars[key].set(value)
        for key in ("limited_duration", "veteran"):
            self.vars[key].set(False)
        self.vars["organ_donor"].set(True)
        self.status.set("Loaded sample data. Click Generate / Preview.")
        self.generate()


def run() -> None:
    root = tk.Tk()
    BarcodeApp(root)
    root.mainloop()


if __name__ == "__main__":
    run()
