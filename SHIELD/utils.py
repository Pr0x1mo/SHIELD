# utils.py

import re


def clean_entity_spans(entities):
    """
    Removes duplicates and overlapping spans.
    Accepts:
      - (text, label, start, end)
      - or (start, end, label)
    Returns:
      - (text, label, start, end)
    """

    seen = set()
    cleaned = []

    for ent in entities:
        try:
            if len(ent) == 5:
                text, label, start, end, record = ent
            else:
                text, label, start, end = ent
                record = ""
            start = int(start)
            end = int(end)
            if (start, end) in seen:
                continue
            if any(not (end <= s or start >= e) for _, _, s, e, *_ in cleaned):
                continue
            cleaned.append((text, label, start, end, record))
            seen.add((start, end))
        except:
            continue

    return cleaned



def highlight_entities_in_text(text, entities, style_func=None):
    """
    Inject highlight markers into the text based on entity spans.

    Args:
        text (str): Original text.
        entities (list): List of (start, end, label).
        style_func (func): Optional function(label) => (prefix, suffix)

    Returns:
        str: Highlighted text.
    """
    entities = sorted(entities, key=lambda x: x[0], reverse=True)

    for start, end, label in entities:
        prefix, suffix = style_func(label) if style_func else ("[", f"]({label})")
        text = text[:start] + prefix + text[start:end] + suffix + text[end:]
    return text


def default_style(label):
    return ("[", f"]<{label}>")


def convert_char_spans_to_tokens(doc, char_spans):
    """
    Convert character spans to token spans (start_token, end_token, label).

    Args:
        doc (spacy.Doc): Processed document.
        char_spans (list): List of (start_char, end_char, label).

    Returns:
        list: List of (start_token_idx, end_token_idx, label)
    """
    token_spans = []
    for start, end, label in char_spans:
        span = doc.char_span(start, end, label=label, alignment_mode="contract")
        if span:
            token_spans.append((span.start, span.end, label))
    return token_spans


def hybrid_entity_extraction(text, nlp, regex_patterns=None, smarts_rules=None, apply_smarts_func=None):
    """
    Combines spaCy NER, regex patterns, and SMARTS rule logic.

    Args:
        text (str): Input document text.
        nlp (spacy.Language): spaCy model.
        regex_patterns (list): List of compiled regex patterns.
        smarts_rules (dict): SMARTS rules loaded from JSON.
        apply_smarts_func (func): Optional function for applying SMARTS rules.

    Returns:
        list: Final merged entity list (text, label, start, end)
    """
    from regex_extractor import extract_fields
    from smarts_engine import apply_smarts_rules

    regex_entities = []
    if regex_patterns:
        regex_entities = [
            (r["text"], r["label"], r["start"], r["end"])
            for r in extract_fields(text, regex_patterns)
        ]

    doc = nlp(text)
    spacy_entities = [(ent.text, ent.label_, ent.start_char, ent.end_char) for ent in doc.ents]

    merged = spacy_entities + regex_entities

    # SMARTS filtering (optional)
    if smarts_rules and apply_smarts_func:
        merged = apply_smarts_func(merged, text, smarts_rules)

    return merged


# utils.py
def extract_spans_from_smart_config(text: str, config: dict):
    """
    Iterate all rows for each group in a SMARTS JSON (no 'repeat' flag required).
    For a group:
      - Start at min(line) among that group's fields (0-based).
      - Skip any leading dashed/blank/header lines that produce no field values.
      - Extract values row-by-row until we hit a dashed/blank line *after* rows started,
        or we get a row that yields no field values (end of block).
    Returns: list of (value, label, start, end).
    """

    def is_break_line(s: str) -> bool:
        t = s.strip()
        return (t == "") or all(ch in "---" for ch in t)

    lines = text.splitlines()
    n = len(lines)

    header_skip = int(config.get("header_skip", 0) or 0)
    footer_skip = int(config.get("footer_skip", 0) or 0)

    # Build cumulative offsets to map (line, col) -> absolute char index
    offsets = [0] * (n + 1)
    acc = 0
    for i, ln in enumerate(lines):
        offsets[i] = acc
        acc += len(ln) + 1  # +1 for '\n'
    offsets[n] = acc

    def abs_pos(line_idx: int, col: int) -> int:
        return offsets[line_idx] + col

    # Active window after header/footer trim
    win_first = max(0, header_skip)
    win_last  = n - max(0, footer_skip)  # exclusive

    # Group fields by 'group'
    groups = {}
    for f in config.get("fields", []):
        try:
            g = int(f.get("group", 0))
        except Exception:
            g = 0
        groups.setdefault(g, []).append(f)

    entities = []

    for g, fields in sorted(groups.items()):
        if not fields:
            continue

        # Base relative line for this group (0-based within window)
        try:
            base_rel = min(int(f["line"]) for f in fields)
        except Exception:
            continue

        row = win_first + base_rel
        if row < win_first or row >= win_last:
            continue

        started = False

        while row < win_last:
            # Try to extract all fields for this "row block"
            row_added_any = False
            broken_here = is_break_line(lines[row])

            # Map each field's relative line to the current physical row
            for f in fields:
                try:
                    label = str(f["label"]).strip()
                    rel_line = int(f["line"]) - base_rel
                    line_idx = row + rel_line
                    if line_idx < win_first or line_idx >= win_last:
                        continue

                    left  = int(f["left"])
                    right = int(f["right"])

                    src = lines[line_idx]
                    if left >= len(src):
                        continue
                    r = min(max(right, left), len(src))
                    raw = src[left:r]
                    if not raw:
                        continue

                    # Trim while preserving absolute span
                    lead  = len(raw) - len(raw.lstrip())
                    value = raw.strip()
                    if not value:
                        continue

                    start_abs = abs_pos(line_idx, left + lead)
                    end_abs   = start_abs + len(value)
                    entities.append((value, label, start_abs, end_abs))
                    row_added_any = True
                except Exception:
                    # skip malformed field & continue
                    pass

            if row_added_any:
                started = True
                row += 1
                continue

            # If we didn't add anything on this row:
            if not started:
                # We're still before data: skip dashed/blank/header-ish rows
                if broken_here:
                    row += 1
                    continue
                else:
                    # No values and not a break line — likely header text; skip it
                    row += 1
                    continue
            else:
                # We already started collecting rows — a non-producing or break row ends the block
                break

    return entities







