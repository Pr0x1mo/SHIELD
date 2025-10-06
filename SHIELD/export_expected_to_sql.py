# export_expected_to_sql.py
# Expected → CSV, one row per PAGE (split on form feed `\f`) or whole doc.
# No predictions. SQL-friendly wide format. Duplicate labels get _2, _3...

import argparse, csv, hashlib, json, os, re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

SAFE_COL_RE = re.compile(r"[^A-Za-z0-9_]")

def sanitize_col(name: str) -> str:
    name = name.strip().upper().replace(" ", "_")
    name = SAFE_COL_RE.sub("_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "FIELD"

def slice_safe(line: str, left: int, right: int) -> str:
    left = max(0, int(left)); right = max(left, int(right))
    return line[left:right]

def split_pages(text: str, page_header_regex: Optional[str] = None) -> List[str]:
    """Prefer form-feed split; if not found and regex is provided, split by header pattern."""
    if "\f" in text:
        parts = text.split("\f")
        return [p.strip("\n") for p in parts if p.strip()]
    if page_header_regex:
        lines = text.splitlines()
        starts = [i for i, ln in enumerate(lines) if re.search(page_header_regex, ln)]
        if not starts:
            return [text]
        starts.append(len(lines))
        pages = []
        for i in range(len(starts) - 1):
            chunk = "\n".join(lines[starts[i]:starts[i+1]]).strip("\n")
            if chunk.strip():
                pages.append(chunk)
        return pages
    return [text]

def load_expected_from_lines(lines: List[str], cfg: Dict) -> List[Dict]:
    header_skip = int(cfg.get("header_skip", 0))
    footer_skip = int(cfg.get("footer_skip", 0))
    lines = lines[header_skip : len(lines) - footer_skip if footer_skip > 0 else None]

    out: List[Dict] = []
    for field in cfg.get("fields", []):
        lbl  = str(field["label"])
        line = int(field["line"]); left = int(field["left"]); right = int(field["right"])
        if 0 <= line < len(lines):
            out.append({"label": lbl, "value": slice_safe(lines[line], left, right)})
    return out  # preserves config order

def build_row(expected: List[Dict], keep_empty: bool, collapse_space: bool) -> Dict[str, str]:
    def clean(v: str) -> str:
        v = v.strip()
        if collapse_space:
            v = re.sub(r"\s+", " ", v)
        return v
    counts: Dict[str, int] = {}
    row: Dict[str, str] = {}
    for e in expected:
        val = clean(e["value"])
        if not keep_empty and val == "":
            continue
        base = sanitize_col(e["label"])
        counts[base] = counts.get(base, 0) + 1
        col = f"{base}_{counts[base]}" if counts[base] > 1 else base
        row[col] = val
    return row

def hash_doc(text: bytes) -> str:
    return hashlib.md5(text).hexdigest()

def export_rows(rows: List[Dict[str,str]], text_path: str, out_csv: str,
                add_bom: bool, include_meta: bool, page_numbers: List[int]):
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    enc = "utf-8-sig" if add_bom else "utf-8"
    with open(text_path, "rb") as fb:
        doc_hash = hash_doc(fb.read())
    now = datetime.utcnow().isoformat(timespec="seconds")

    # union of columns, preserving first-seen order
    cols: List[str] = []
    for r in rows:
        for k in r.keys():
            if k not in cols:
                cols.append(k)

    meta_cols = []
    if include_meta:
        meta_cols = ["DOC_ID", "SOURCE_FILE", "LOADED_UTC", "PAGE_INDEX"]
        cols = meta_cols + cols

    with open(out_csv, "w", newline="", encoding=enc) as f:
        w = csv.writer(f)
        w.writerow(cols)
        for idx, r in enumerate(rows):
            if include_meta:
                prefix = [doc_hash, os.path.abspath(text_path), now, page_numbers[idx]]
                w.writerow(prefix + [r.get(c, "") for c in cols[len(meta_cols):]])
            else:
                w.writerow([r.get(c, "") for c in cols])

def main():
    ap = argparse.ArgumentParser(description="Export Expected values to SQL-friendly CSV (multi-page).")
    ap.add_argument("--config", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", default="data/sql_exports/expected_wide.csv")
    ap.add_argument("--split-pages", action="store_true",
                    help="Split one file into multiple CSV rows (one per page). Splits on FF \\f; optionally use --page-header-regex.")
    ap.add_argument("--page-header-regex", default=None,
                    help="Regex that marks the start of a page when no FF present.")
    ap.add_argument("--keep-empty", action="store_true", help="Keep empty values (default: drop).")
    ap.add_argument("--no-collapse", action="store_true", help="Do NOT collapse inner whitespace.")
    ap.add_argument("--bom", action="store_true", help="Write UTF-8 with BOM (useful for SQL Server).")
    ap.add_argument("--no-meta", action="store_true", help="Do NOT include DOC_ID/SOURCE_FILE/LOADED_UTC/PAGE_INDEX.")
    args = ap.parse_args()

    # Load config + text
    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    with open(args.text, "r", encoding="utf-8") as f:
        full_text = f.read()

    # Split into pages if requested
    if args.split_pages:
        pages = split_pages(full_text, page_header_regex=args.page_header_regex)
    else:
        pages = [full_text]

    rows: List[Dict[str,str]] = []
    page_numbers: List[int] = []
    for i, page_text in enumerate(pages, start=1):
        lines = page_text.splitlines()
        expected = load_expected_from_lines(lines, cfg)
        row = build_row(expected, keep_empty=args.keep_empty, collapse_space=not args.no_collapse)
        rows.append(row)
        page_numbers.append(i)

    export_rows(rows, args.text, args.out, add_bom=args.bom, include_meta=not args.no_meta, page_numbers=page_numbers)
    print(f"Wrote {args.out} ({len(rows)} row(s))")

if __name__ == "__main__":
    main()
