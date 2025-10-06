# ff_dataset_extractor.py
# Split an AS/400 spool text into per-dataset files, preserving bytes exactly.
# Datasets are grouped by page header (Title + Code). Output pages are joined
# with the same form-feed (FF, \x0c) page breaks. Nothing is added/changed.

import os, re, sys, argparse
from typing import Dict, List, Tuple, Optional

# ---------------------------
# Header regex (flexible)
# ---------------------------
PAGE_HDR_RE = re.compile(r"""
^[^\S\r\n]*                                  # leading spaces/tabs
(?P<acct>\d{2,10}(?:-\d{3,9})?)              # 992  OR  123-1234567
[^\S\r\n]+
(?:
    (?P<org>.+?)                             # Variant A: has org
    [^\S\r\n]{2,}
    (?P<title>.+?)                           # title
  |
    (?P<title_only>.+?)                      # Variant B: no org; this is the title
)
[^\S\r\n]{2,}
(?P<code>
      [A-Z]{1,3}-\d{5}-\d{3}                 # classic: R-06088-001 / RC-06088-001
    | [A-Z]{1,3}-\d{3,6}[^\S\r\n]+[A-Z]{2,}-\d{3,6}  # split: R-8101 SET-001
    | [A-Z0-9]{4,16}                         # compact: LN4CSUMM, ABC123XY, etc.
)
[^\S\r\n]+
(?P<date>\d{2}[-/]\d{2}[-/]\d{2}|\d{4}-\d{2}-\d{2})
[^\S\r\n]+
(?:PAGE|Page)[^\S\r\n]*[:#]?[^\S\r\n]*       # PAGE / PAGE: / PAGE#
(?P<page>\d+)
(?:[^\S\r\n]+of[^\S\r\n]+(?P<pages>\d+))?    # optional "of N"
[^\S\r\n]*$
""", re.VERBOSE | re.MULTILINE)

# ---------------------------
# Core functions
# ---------------------------
def split_pages_bytes(data: bytes) -> List[bytes]:
    """Split by form-feed (0x0c). Keep first chunk as page 1 even if no leading FF."""
    parts = data.split(b"\x0c")
    return [p for p in parts if p.strip(b"\r\n\t \x00") != b""]

def find_header_key(page_bytes: bytes) -> Optional[Tuple[str, str]]:
    """
    Look for the page header in the first few non-empty lines.
    Return (title, code) if found, else None.
    Decode with latin-1 so bytes map 1:1 to codepoints (no changes).
    """
    try:
        text = page_bytes.decode("latin-1", errors="ignore")
    except Exception:
        return None
    lines = text.splitlines()
    seen = 0
    for ln in lines[:12]:  # first dozen lines is plenty for AS/400 headers
        if not ln.strip():
            continue
        seen += 1
        m = PAGE_HDR_RE.search(ln)
        if m:
            gd = m.groupdict()
            title = (gd.get("title") or gd.get("title_only") or "").strip()
            code  = gd.get("code", "").strip()
            return (title, code)
        if seen >= 6:
            break
    return None

def sanitize_filename(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)

def write_dataset_files(pages_by_ds: Dict[Tuple[str,str], List[bytes]], outdir: str) -> List[str]:
    os.makedirs(outdir, exist_ok=True)
    written: List[str] = []
    for (title, code), pages in pages_by_ds.items():
        base = f"{title}_{code}.txt".lower()
        path = os.path.join(outdir, sanitize_filename(base))
        # Join original pages with FF so page boundaries are preserved.
        blob = b"\x0c".join(p.rstrip(b"\x0c") for p in pages)
        with open(path, "wb") as f:
            f.write(blob)
        written.append(path)
    return written

def run_split(input_path: str, outdir: str, unmatched_path: Optional[str]) -> Tuple[List[str], int]:
    with open(input_path, "rb") as f:
        data = f.read()

    pages = split_pages_bytes(data)
    pages_by_ds: Dict[Tuple[str,str], List[bytes]] = {}
    unmatched: List[bytes] = []

    for pg in pages:
        key = find_header_key(pg)
        if key is None:
            unmatched.append(pg)
            continue
        pages_by_ds.setdefault(key, []).append(pg)

    written = write_dataset_files(pages_by_ds, outdir)

    if unmatched_path and unmatched:
        os.makedirs(os.path.dirname(unmatched_path) or ".", exist_ok=True)
        with open(unmatched_path, "wb") as f:
            f.write(b"\x0c".join(unmatched))

    return written, len(unmatched)

# ---------------------------
# CLI
# ---------------------------
def main_cli(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Split AS/400 export into per-dataset text files (byte-perfect).")
    ap.add_argument("--input", required=True, help="Path to the original spool text file")
    ap.add_argument("--outdir", default="Output", help="Directory to write per-dataset .txt files")
    ap.add_argument("--unmatched", default="", help="Optional path for pages with no identifiable header (leave empty to skip)")
    args = ap.parse_args(argv)

    written, um_count = run_split(args.input, args.outdir, args.unmatched or None)

    print(f"Done. Wrote {len(written)} dataset file(s) to '{args.outdir}'.")
    if args.unmatched:
        print(f"Unmatched pages: {um_count} → {args.unmatched}")
    else:
        print(f"Unmatched pages: {um_count} (not saved)")
    return 0

# ---------------------------
# GUI (Tkinter)
# ---------------------------
def main_gui() -> int:
    try:
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
    except Exception:
        # Tk isn't available; fall back to CLI usage message
        print("Tkinter not available. Use CLI flags: --input <file> --outdir <dir> [--unmatched <file>]")
        return 2

    root = tk.Tk()
    root.title("AS/400 Dataset Extractor")
    root.geometry("720x260")
    root.resizable(False, False)

    # Vars
    input_var = tk.StringVar()
    outdir_var = tk.StringVar(value="Output")
    save_unmatched_var = tk.BooleanVar(value=True)
    unmatched_var = tk.StringVar(value="")

    # Helpers
    def default_unmatched_path() -> str:
        base_dir = outdir_var.get().strip() or "."
        return os.path.join(base_dir, "unmatched_pages.txt")

    def on_browse_input():
        path = filedialog.askopenfilename(
            title="Select spool text file",
            filetypes=[("Text files", "*.txt *.prn *.lis *.out *.log"), ("All files", "*.*")],
        )
        if path:
            input_var.set(path)
            # if outdir not set or still default, set it next to input
            if not outdir_var.get() or outdir_var.get() == "Output":
                outdir_var.set(os.path.join(os.path.dirname(path), "Output"))
            # set a sensible default unmatched path
            if save_unmatched_var.get() and not unmatched_var.get():
                unmatched_var.set(default_unmatched_path())

    def on_browse_outdir():
        path = filedialog.askdirectory(title="Choose output folder")
        if path:
            outdir_var.set(path)
            if save_unmatched_var.get() and (not unmatched_var.get() or unmatched_var.get().endswith("unmatched_pages.txt")):
                unmatched_var.set(default_unmatched_path())

    def on_browse_unmatched():
        path = filedialog.asksaveasfilename(
            title="Save unmatched pages as...",
            defaultextension=".txt",
            initialfile="unmatched_pages.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            unmatched_var.set(path)
            save_unmatched_var.set(True)

    def on_toggle_unmatched():
        if save_unmatched_var.get():
            if not unmatched_var.get():
                unmatched_var.set(default_unmatched_path())
            unmatched_entry.configure(state="normal")
            unmatched_browse.configure(state="normal")
        else:
            unmatched_entry.configure(state="disabled")
            unmatched_browse.configure(state="disabled")

    def validate() -> Optional[Tuple[str, str, Optional[str]]]:
        in_path = input_var.get().strip()
        out_dir = outdir_var.get().strip() or "Output"
        um_path = unmatched_var.get().strip() if save_unmatched_var.get() else ""
        if not in_path or not os.path.isfile(in_path):
            messagebox.showerror("Missing input", "Please select a valid input file.")
            return None
        if not out_dir:
            messagebox.showerror("Missing output folder", "Please choose an output folder.")
            return None
        if save_unmatched_var.get() and not um_path:
            um_path = default_unmatched_path()
        return in_path, out_dir, (um_path or None)

    # Layout
    pad = {"padx": 10, "pady": 8}

    frm = ttk.Frame(root)
    frm.pack(fill="both", expand=True, **pad)

    # Row 1: Input
    ttk.Label(frm, text="Input file:").grid(row=0, column=0, sticky="w")
    input_entry = ttk.Entry(frm, textvariable=input_var, width=70)
    input_entry.grid(row=0, column=1, sticky="we", padx=(0, 6))
    ttk.Button(frm, text="Browse...", command=on_browse_input).grid(row=0, column=2, sticky="e")

    # Row 2: Outdir
    ttk.Label(frm, text="Output folder:").grid(row=1, column=0, sticky="w")
    outdir_entry = ttk.Entry(frm, textvariable=outdir_var, width=70)
    outdir_entry.grid(row=1, column=1, sticky="we", padx=(0, 6))
    ttk.Button(frm, text="Choose...", command=on_browse_outdir).grid(row=1, column=2, sticky="e")

    # Row 3: Unmatched
    unmatched_chk = ttk.Checkbutton(frm, text="Save unmatched pages", variable=save_unmatched_var, command=on_toggle_unmatched)
    unmatched_chk.grid(row=2, column=0, sticky="w")
    unmatched_entry = ttk.Entry(frm, textvariable=unmatched_var, width=70)
    unmatched_entry.grid(row=2, column=1, sticky="we", padx=(0, 6))
    unmatched_browse = ttk.Button(frm, text="Save As...", command=on_browse_unmatched)
    unmatched_browse.grid(row=2, column=2, sticky="e")

    # Row 4: Buttons + status
    status_var = tk.StringVar(value="")
    status = ttk.Label(frm, textvariable=status_var, foreground="#555")
    status.grid(row=3, column=0, columnspan=3, sticky="w")

    btns = ttk.Frame(frm)
    btns.grid(row=4, column=0, columnspan=3, sticky="e")
    def on_run():
        vals = validate()
        if not vals:
            return
        in_path, out_dir, um_path = vals
        try:
            status_var.set("Processing…")
            root.update_idletasks()
            written, um_count = run_split(in_path, out_dir, um_path)
            msg = f"Wrote {len(written)} dataset file(s) to:\n{out_dir}"
            if um_path:
                msg += f"\nUnmatched pages: {um_count} → {um_path}"
            else:
                msg += f"\nUnmatched pages: {um_count} (not saved)"
            messagebox.showinfo("Done", msg)
            status_var.set("Done.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            status_var.set("Failed.")
    ttk.Button(btns, text="Run", command=on_run).pack(side="right", padx=(6,0))
    ttk.Button(btns, text="Close", command=root.destroy).pack(side="right")

    # Init control states
    on_toggle_unmatched()

    # Make middle column expand
    frm.columnconfigure(1, weight=1)

    root.mainloop()
    return 0

# ---------------------------
# Entrypoint
# ---------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
        raise SystemExit(main_cli())
    else:
        raise SystemExit(main_gui())
