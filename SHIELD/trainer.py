# trainer.py
import os
import json
from typing import Iterable, List, Tuple, Dict, Any
from pathlib import Path
import shutil
import tempfile

import spacy
from spacy.training.example import Example
from spacy.util import minibatch

MODEL_PATH = "model/on_prem_nlp_model"
FEEDBACK_BACKUP_DIR = "data/backups"  # optional: extra backups of feedback.json


# ---------------------------
# Utility helpers
# ---------------------------

def compute_line_position(text: str, start: int, end: int) -> Tuple[int, int, int]:
    """Return (line_number [1-based], left, right) for a char span."""
    lines = text.splitlines()
    offset = 0
    for i, line in enumerate(lines):
        line_len = len(line) + 1  # include newline
        if offset + line_len > start:
            left = start - offset
            right = end - offset
            return i + 1, left, right  # 1-based line numbers
        offset += line_len
    return -1, -1, -1


def _ensure_lexeme_norm(nlp):
    """Best-effort safety net in case vocab lookups are missing."""
    try:
        _ = nlp.vocab.lookups.get_table("lexeme_norm")
    except KeyError:
        try:
            nlp.vocab.lookups.add_table("lexeme_norm", {})
        except Exception:
            from spacy.lookups import Lookups
            lks = Lookups()
            lks.add_table("lexeme_norm", {})
            nlp.vocab.lookups = lks


def _within(text: str, s: int, e: int) -> bool:
    return 0 <= s < e <= len(text)


def _align_entities(nlp, text: str, raw_entities: Iterable[Tuple[int, int, str]]) -> Tuple[List[Tuple[int, int, str]], int]:
    """
    Convert raw (start, end, label) into token-aligned spans using alignment_mode='contract'.
    Returns (aligned_entities, dropped_count).
    """
    doc = nlp.make_doc(text)
    aligned: List[Tuple[int, int, str]] = []
    dropped = 0
    for s, e, label in raw_entities:
        span = doc.char_span(s, e, label=label, alignment_mode="contract")
        if span is None:
            dropped += 1
        else:
            aligned.append((span.start_char, span.end_char, label))
    return aligned, dropped


def _dedupe_overlaps(ents: List[Tuple[int, int, str]]) -> List[Tuple[int, int, str]]:
    """
    Drop exact duplicates; prefer longer span when overlapping with same label.
    """
    ents = sorted(ents, key=lambda x: (x[0], -x[1]))
    out: List[Tuple[int, int, str]] = []
    for s, e, lbl in ents:
        # exact dup
        if any(s == os_ and e == oe and lbl == ol for os_, oe, ol in out):
            continue
        # same-label overlap: keep widest
        clashes = [(i, o) for i, o in enumerate(out) if not (e <= o[0] or s >= o[1]) and o[2] == lbl]
        if clashes:
            widest = max([(s, e, lbl)] + [o for _, o in clashes], key=lambda z: z[1] - z[0])
            # remove all clashing, then add widest if not already
            keep_idx = {i for i, _ in clashes}
            out = [o for j, o in enumerate(out) if j not in keep_idx]
            if widest not in out:
                out.append(widest)
        else:
            out.append((s, e, lbl))
    return out


def _sanitize_label(lbl: str) -> str:
    """Normalize labels to UPPER_SNAKE_CASE."""
    return (lbl or "").replace(" ", "_").replace("-", "_").upper()


def _normalize_current_entities(text: str, entities: Iterable[Any]) -> List[Dict[str, Any]]:
    """
    Normalize various input shapes into dicts:
      - dict: {"start","end","label", "line_number"?, "left"?, "right"?, "value"?}
      - tuple: (start, end, label) OR (value, label, start, end)
    Attaches fixed-width metadata if missing. Leaves 'value' untouched if present.
    """
    norm: List[Dict[str, Any]] = []
    for item in entities:
        try:
            if isinstance(item, dict):
                s = int(item["start"]); e = int(item["end"]); lbl = _sanitize_label(str(item["label"]))
                ln = int(item.get("line_number", -1))
                lf = int(item.get("left", -1))
                rt = int(item.get("right", -1))
                val = item.get("value")
            else:
                # tuple/list
                val = None
                if len(item) >= 4 and not isinstance(item[2], str):
                    # (value, label, start, end) OR (start, end, label, ?)
                    if isinstance(item[0], int) and isinstance(item[1], int):
                        # (start, end, label)
                        s, e, lbl = int(item[0]), int(item[1]), _sanitize_label(str(item[2]))
                    else:
                        # (value, label, start, end)
                        val = item[0] if isinstance(item[0], str) else None
                        s, e, lbl = int(item[2]), int(item[3]), _sanitize_label(str(item[1]))
                elif len(item) == 3 and isinstance(item[0], int):
                    s, e, lbl = int(item[0]), int(item[1]), _sanitize_label(str(item[2]))
                else:
                    # Unknown shape
                    continue
                ln, lf, rt = compute_line_position(text, s, e)
            if not _within(text, s, e):
                continue
            rec = {"start": s, "end": e, "label": lbl, "line_number": ln, "left": lf, "right": rt}
            if val is not None:
                rec["value"] = val
            norm.append(rec)
        except Exception:
            continue
    return norm


def _backup_feedback_file(feedback_file: str):
    """Optional safety backup of feedback.json."""
    if not os.path.exists(feedback_file):
        return
    try:
        os.makedirs(FEEDBACK_BACKUP_DIR, exist_ok=True)
        base = os.path.basename(feedback_file)
        dst = os.path.join(FEEDBACK_BACKUP_DIR, base)
        shutil.copy2(feedback_file, dst)
    except Exception:
        pass


def _load_feedback_examples(feedback_file: str) -> List[Tuple[str, List[Tuple[int, int, str]]]]:
    """
    Load feedback.json (list of records). Each record:
      { "text": str, "entities": [ {start,end,label, line_number,left,right, value?}, ... ] }
    Returns list of (text, [(start,end,label), ...]) for training.
    """
    if not os.path.exists(feedback_file):
        return []

    with open(feedback_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        return []

    examples: List[Tuple[str, List[Tuple[int, int, str]]]] = []
    for rec in data:
        text = rec.get("text", "")
        ents = rec.get("entities", [])
        triples: List[Tuple[int, int, str]] = []
        for e in ents:
            try:
                s, e2, lbl = int(e["start"]), int(e["end"]), _sanitize_label(str(e["label"]))
                if _within(text, s, e2):
                    triples.append((s, e2, lbl))
            except Exception:
                continue
        triples = _dedupe_overlaps(triples)
        examples.append((text, triples))
    return examples


# ---------------------------
# Model directory helpers (Windows-safe save)
# ---------------------------

def _is_valid_model_dir(path: Path) -> bool:
    """A spaCy model dir must have config.cfg or meta.json."""
    return (path / "config.cfg").exists() or (path / "meta.json").exists()

def _clean_model_dir(path: Path):
    """Remove target dir if it exists as a file or directory (best effort)."""
    if path.exists():
        if path.is_file():
            path.unlink(missing_ok=True)
        else:
            shutil.rmtree(path, ignore_errors=True)

def _atomic_save(nlp, target: Path):
    """Write to temp dir then move into place (atomic-ish)."""
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="shield_spacy_", dir=parent))
    try:
        nlp.to_disk(tmpdir)
        _clean_model_dir(target)
        shutil.move(str(tmpdir), str(target))
    finally:
        if tmpdir.exists():
            shutil.rmtree(tmpdir, ignore_errors=True)

def _safe_save_model(nlp, model_path: str):
    """
    Save model atomically and handle Windows vectors edge-case.
    If OSError mentions 'vectors', drop vocab.vectors and retry.
    """
    target = Path(model_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _clean_model_dir(target)
    try:
        _atomic_save(nlp, target)
    except OSError as e:
        if "vectors" in str(e).lower():
            # Remove/clear vectors and retry; not needed for NER weights
            try:
                nlp.vocab.reset_vectors()
            except Exception:
                try:
                    nlp.vocab.vectors = None  # type: ignore[attr-defined]
                except Exception:
                    pass
            _atomic_save(nlp, target)
        else:
            raise


# ---------------------------
# Public API
# ---------------------------

def train_model(text: str, entities: Iterable[Any], feedback_file: str) -> Dict[str, Any]:
    """
    Append the current document + confirmed entities to feedback_file,
    then (re)train/update the model at MODEL_PATH using ALL feedback.

    Returns a summary dict with counts.
    """
    # Ensure feedback dir exists
    dirpath = os.path.dirname(feedback_file)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)

    # Normalize current entities to dict records (keep fixed-width metadata and 'value' if present)
    current_norm = _normalize_current_entities(text, entities)

    # Append to feedback.json
    _backup_feedback_file(feedback_file)
    if os.path.exists(feedback_file):
        with open(feedback_file, "r", encoding="utf-8") as f:
            feedback_data = json.load(f)
        if not isinstance(feedback_data, list):
            feedback_data = []
    else:
        feedback_data = []

    feedback_data.append({
        "text": text,
        "entities": current_norm
    })

    with open(feedback_file, "w", encoding="utf-8") as f:
        json.dump(feedback_data, f, indent=2)

    # Load or create model (tolerate invalid/corrupt dir)
    model_dir = Path(MODEL_PATH)
    new_model = False
    if model_dir.exists() and _is_valid_model_dir(model_dir):
        try:
            nlp = spacy.load(MODEL_PATH)
        except Exception:
            nlp = spacy.blank("en"); nlp.add_pipe("ner"); new_model = True
    else:
        nlp = spacy.blank("en")
        nlp.add_pipe("ner")
        new_model = True

    _ensure_lexeme_norm(nlp)

    # Ensure NER pipe
    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner", last=True)
    else:
        ner = nlp.get_pipe("ner")

    # Build training set from ALL feedback
    all_examples = _load_feedback_examples(feedback_file)

    # Add all labels
    for _, ents in all_examples:
        for _, _, lbl in ents:
            ner.add_label(lbl)

    # Convert to Example objects with safe alignment
    ex_objs: List[Example] = []
    dropped_total = 0
    for txt, ents in all_examples:
        aligned, dropped = _align_entities(nlp, txt, ents)
        dropped_total += dropped
        if not aligned:
            continue
        doc = nlp.make_doc(txt)
        ex_objs.append(Example.from_dict(doc, {"entities": aligned}))

    # If no examples, still persist a minimal valid model to avoid future load warnings
    if not ex_objs:
        try:
            if new_model:
                nlp.initialize(lambda: [])
        except Exception:
            pass
        _safe_save_model(nlp, MODEL_PATH)
        return {
            "status": "no_training_data",
            "model_path": MODEL_PATH,
            "records_in_feedback": len(all_examples),
            "examples_trained": 0,
            "appended_entities": len(current_norm),
            "dropped_misaligned": dropped_total,
            "message": "No valid examples to train; wrote a minimal model to disk."
        }

    # (Re)initialize if new model or labels changed
    if new_model:
        nlp.initialize(get_examples=lambda: ex_objs)

    # Simple update loop (small project-scale)
    n_iter = 5
    for _ in range(n_iter):
        for batch in minibatch(ex_objs, size=8):
            nlp.update(batch)

    # Persist (Windows-safe; avoids vocab\\vectors error)
    _safe_save_model(nlp, MODEL_PATH)

    return {
        "status": "ok",
        "model_path": MODEL_PATH,
        "records_in_feedback": len(all_examples),
        "examples_trained": len(ex_objs),
        "appended_entities": len(current_norm),
        "dropped_misaligned": dropped_total,
    }
