# ff_dataset_extractor.py
# Split an AS/400 spool text into per-dataset files, preserving bytes exactly.
# Datasets are grouped by page header (Title + Code). Output pages are joined
# with the same form-feed (FF, \x0c) page breaks. Nothing is added/changed.

import re, os, argparse
from typing import Dict, List, Tuple, Optional

# Flexible header like:
# XXX- ORG NAME    REPORT NAME   R-00000-001   MM-DD-YY   PAGE#
PAGE_HDR_RE = re.compile(
    r"""^\s*
    (?P<acct>\d{3}-\d{7})\s+
    (?P<org>.+?)\s{2,}
    (?P<title>[A-Z0-9 .()/,&'_-]+?)\s{2,}
    (?P<code>[A-Z]-\d{5}-\d{3})\s{2,}
    (?P<date>\d{2}-\d{2}-\d{2}|\d{4}-\d{2}-\d{2})\s+
    PAGE\s+(?P<page>\d+)
    \s*$""",
    re.VERBOSE
)

def split_pages_bytes(data: bytes) -> List[bytes]:
    """Split by form-feed (0x0c). Keep first chunk as page 1 even if no leading FF."""
    parts = data.split(b"\x0c")
    # Drop empty parts that are pure whitespace
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
            title = gd.get("title", "").strip()
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

def main():
    ap = argparse.ArgumentParser(description="Split AS/400 export into per-dataset text files (byte-perfect).")
    ap.add_argument("--input", required=True, help="Path to the original spool text file")
    ap.add_argument("--outdir", default="data/datasets", help="Directory to write per-dataset .txt files")
    ap.add_argument("--unmatched", default=None, help="Optional path for pages with no identifiable header")
    args = ap.parse_args()

    with open(args.input, "rb") as f:
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

    written = write_dataset_files(pages_by_ds, args.outdir)

    if args.unmatched and unmatched:
        os.makedirs(os.path.dirname(args.unmatched) or ".", exist_ok=True)
        with open(args.unmatched, "wb") as f:
            f.write(b"\x0c".join(unmatched))

    print(f"Done. Wrote {len(written)} dataset file(s) to '{args.outdir}'.")
    if args.unmatched:
        print(f"Unmatched pages: {len(unmatched)} → {args.unmatched}")

if __name__ == "__main__":
    main()
