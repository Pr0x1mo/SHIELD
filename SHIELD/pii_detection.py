# pii_detection.py
from __future__ import annotations
from pathlib import Path
import spacy

# import your regex extractor utilities
from regex_extractor import load_regex_patterns, extract_fields

DEFAULT_MODEL_ROOT = Path("model/on_prem_nlp_model")
DEFAULT_REGEX_CONFIG = "config/field_patterns.yaml"

# Global cache
_nlp = None
_loaded_from: Path | str | None = None

# ---------- helpers ----------

def _candidate_paths(root: Path) -> list[Path]:
    # Try promoted active model first, then trainer outputs, then root (in case it's a model dir)
    return [root / "active", root / "model-best", root / "model-last", root]

def _sanitize_label(lbl: str) -> str:
    return (lbl or "").replace(" ", "_").replace("-", "_").upper()

def _within(text: str, s: int, e: int) -> bool:
    return 0 <= s < e <= len(text)

def _merge_and_dedupe(text: str, *lists):
    """
    Merge lists of (value,label,start,end) and dedupe:
      - drop invalid spans
      - prefer longer span on same-label overlaps
      - drop exact duplicates
    """
    # Flatten
    ents = []
    for L in lists:
        for t in L:
            try:
                val, lbl, s, e = t
                s, e = int(s), int(e)
                lbl = _sanitize_label(str(lbl))
                if not _within(text, s, e):
                    continue
                ents.append((val, lbl, s, e))
            except Exception:
                continue

    # sort by (start asc, end desc) so wider spans come first for same start
    ents.sort(key=lambda x: (x[2], -x[3]))

    out = []
    for val, lbl, s, e in ents:
        # exact duplicate?
        if any(s == os and e == oe and lbl == ol for _, ol, os, oe in out):
            continue
        # same-label overlap: keep widest
        overlaps = [i for i, (_, l2, s2, e2) in enumerate(out) if l2 == lbl and not (e <= s2 or s >= e2)]
        if overlaps:
            # Keep widest between current and each overlapping; remove the narrower ones
            keep_current = True
            to_remove = []
            for i in overlaps:
                _, l2, s2, e2 = out[i]
                if (e2 - s2) >= (e - s):  # existing is wider or equal
                    keep_current = False
                else:
                    to_remove.append(i)
            if to_remove:
                out = [o for idx, o in enumerate(out) if idx not in to_remove]
            if keep_current:
                out.append((val, lbl, s, e))
        else:
            out.append((val, lbl, s, e))
    return out

# ---------- model loading ----------

def load_model(root: Path | None = None, *, force_reload: bool = False):
    """
    Load the on-prem model with fallbacks:
      <root>/active -> model-best -> model-last -> root
    If none load, fallback to en_core_web_lg; if that fails, blank('en') with NER pipe.
    (Regex extraction runs separately, so detection still works even if model is blank.)
    """
    global _nlp, _loaded_from
    if _nlp is not None and not force_reload:
        return _nlp

    root = Path(root) if root else DEFAULT_MODEL_ROOT

    for p in _candidate_paths(root):
        try:
            if p.exists():
                _nlp = spacy.load(str(p))
                _loaded_from = p
                print(f"[PII] Loaded model: {p}")
                return _nlp
        except Exception as e:
            print(f"[PII] Failed to load {p}: {e}")

    # Packaged fallback
    try:
        _nlp = spacy.load("en_core_web_lg")
        _loaded_from = "en_core_web_lg"
        print("[PII] Loaded fallback model: en_core_web_lg")
        return _nlp
    except Exception:
        pass

    # Minimal blank pipeline so doc.ents exists (regex will still extract)
    _nlp = spacy.blank("en")
    if "ner" not in _nlp.pipe_names:
        _nlp.add_pipe("ner")
    _loaded_from = "blank_en"
    print("[PII] Using blank('en') pipeline.")
    return _nlp

def reload_model(root: Path | None = None):
    """Force reload after training/promotion without restarting the app."""
    return load_model(root, force_reload=True)

# ---------- detection ----------

def _spacy_detect(text: str):
    nlp = load_model()
    doc = nlp(text)
    return [(ent.text, _sanitize_label(ent.label_), ent.start_char, ent.end_char) for ent in doc.ents]

def _regex_detect(text: str, config_path: str = DEFAULT_REGEX_CONFIG):
    try:
        patterns = load_regex_patterns(config_path)
    except FileNotFoundError:
        print(f"[PII] Regex config missing at {config_path}")
        patterns = {}
    except Exception as e:
        print(f"[PII] Error loading regex config: {e}")
        patterns = {}

    results = extract_fields(text, patterns) if patterns else []
    # Convert to unified tuple shape
    return [(r["text"], _sanitize_label(r["label"]), int(r["start"]), int(r["end"])) for r in results]

def detect_entities(text: str, *, use_spacy: bool = True, use_regex: bool = True, regex_config_path: str = DEFAULT_REGEX_CONFIG):
    """
    Unified detector:
      - spaCy model (if available)
      - regex extractor using YAML patterns
    Returns list[(value, label, start, end)]
    """
    spacy_ents = _spacy_detect(text) if use_spacy else []
    regex_ents = _regex_detect(text, regex_config_path) if use_regex else []
    return _merge_and_dedupe(text, spacy_ents, regex_ents)

# ---------- CLI test ----------

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pii_detection.py <input_file> [regex_config_path]")
    else:
        with open(sys.argv[1], encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if len(sys.argv) > 2:
            cfg = sys.argv[2]
            ents = detect_entities(content, regex_config_path=cfg)
        else:
            ents = detect_entities(content)
        for val, lbl, s, e in ents:
            print(f"{lbl} | {val} | {s}-{e}")
