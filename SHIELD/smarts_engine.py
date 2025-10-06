
# smarts_v2_engine.py

import json
import re

def load_smarts_rules(path="config/smarts_rules.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def evaluate_conditions(entity, text_lines, rule_conditions):
    ent_text, ent_label, start, end = entity
    line_num = text_lines["map"].get((start, end), -1)
    line = text_lines["lines"][line_num] if line_num >= 0 else ""
    offset_start = line.find(ent_text) if ent_text in line else -1

    for cond in rule_conditions:
        ctype = cond.get("type")
        op = cond.get("operator")
        val = cond.get("value")

        if ctype == "LABEL":
            if not compare(ent_label, op, val):
                return False

        elif ctype == "VALUE":
            if not compare(ent_text, op, val):
                return False

        elif ctype == "VALUE_REGEX":
            if not re.search(cond.get("pattern", ""), ent_text):
                return False

        elif ctype == "LINE_OFFSET":
            start_col = cond.get("start", 0)
            end_col = cond.get("end", 999)
            if not (start_col <= offset_start <= end_col):
                return False

    return True

def compare(a, op, b):
    if op == "==": return a == b
    if op == "!=": return a != b
    if op == "contains": return b in a
    if op == ">": return float(a) > float(b)
    if op == "<": return float(a) < float(b)
    return False

def apply_actions(entity, actions):
    ent_text, ent_label, start, end = entity
    keep = True
    flags = []
    color = None

    for action in actions:
        atype = action.get("type")
        val = action.get("value")
        if atype == "RENAME_LABEL":
            ent_label = val
        elif atype == "EXCLUDE":
            keep = False
        elif atype == "FLAG":
            flags.append(val)
        elif atype == "HIGHLIGHT":
            color = action.get("color", "yellow")

    return (ent_text, ent_label, start, end, keep, flags, color)

def build_text_line_map(text):
    lines = text.splitlines()
    mapping = {}
    offset = 0
    for i, line in enumerate(lines):
        for j in range(len(line)):
            mapping[(offset + j, offset + j + 1)] = i
        offset += len(line) + 1  # +1 for newline
    return {"lines": lines, "map": mapping}

def apply_smarts_rules(entities, text, rules):
    text_lines = build_text_line_map(text)
    output = []

    sorted_rules = sorted(
        [r for r in rules.values() if r.get("enabled", True)],
        key=lambda r: r.get("priority", 1)
    )
    print("Entities before SMARTS:", len(entities))

    for entity in entities:
        modified = entity
        keep = True
        flags = []
        highlight = None

        for rule in sorted_rules:
            if evaluate_conditions(modified, text_lines, rule.get("conditions", [])):
                result = apply_actions(modified, rule.get("actions", []))
                modified = result[:4]
                keep = keep and result[4]
                flags.extend(result[5])
                highlight = result[6] or highlight

        if keep:
            output.append(modified + (flags, highlight))
    return output
