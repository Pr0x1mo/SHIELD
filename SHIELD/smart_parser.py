# smart_parser.py — Fixed-width parser for absolute line + group tables
import json, argparse, os, re
from typing import Dict, List, Any, Optional, Tuple

def parse_fixed_width(text, config):
    """
    Build a list of dict records by treating each line at group=1 as a row start,
    then attaching fields from subsequent groups (2, 3, ...) relative to that line.
    No lines are skipped; we iterate over the full window each time.
    """
    lines = text.splitlines()
    header_skip = int(config.get("header_skip", 0) or 0)
    footer_skip = int(config.get("footer_skip", 0) or 0)
    win = lines[header_skip: len(lines) - footer_skip]

    # group fields by group id
    groups = {}
    for f in config.get("fields", []):
        g = int(f.get("group", 1))
        groups.setdefault(g, []).append(f)

    records = []

    # If there’s no group 1, nothing to iterate
    if 1 not in groups:
        return records

    # Walk every physical line; treat each as potential group-1 row start
    for i in range(len(win)):
        row1 = win[i]
        rec = {}

        # group 1 on this line
        for f in groups[1]:
            left, right = int(f["left"]), int(f["right"])
            rec[f["label"]] = row1[left:right].strip() if left < len(row1) else ""

        # groups 2..N, relative to the same starting line
        g_id = 2
        while g_id in groups:
            rel_idx = i + (g_id - 1)
            if rel_idx >= len(win):
                break
            row_g = win[rel_idx]
            for f in groups[g_id]:
                left, right = int(f["left"]), int(f["right"])
                rec[f["label"]] = row_g[left:right].strip() if left < len(row_g) else ""
            g_id += 1

        records.append(rec)

    return records

def slice_safe(line: str, left: int, right: Optional[int]) -> str:
    if left is None: left = 0
    if right is None or right > len(line): right = len(line)
    if left < 0: left = 0
    if left >= len(line): return ""
    return line[left:right]

def select_config(config_data: Any, report_name: Optional[str]) -> Dict[str, Any]:
    if isinstance(config_data, dict):
        return config_data
    if isinstance(config_data, list):
        if report_name:
            for rule in config_data:
                if isinstance(rule, dict) and rule.get("report_name") == report_name:
                    return rule
            names = [r.get("report_name") for r in config_data if isinstance(r, dict)]
            raise ValueError(f"Report '{report_name}' not found. Available: {names}")
        for rule in config_data:
            if isinstance(rule, dict) and "fields" in rule:
                return rule
        raise ValueError("No usable rule with 'fields' found in config list.")
    raise TypeError("Config must be a dict or list of dicts.")

def compute_relevant_lines(lines: List[str], cfg: Dict[str, Any]) -> List[str]:
    header_skip = int(cfg.get("header_skip", 0))
    footer_skip = int(cfg.get("footer_skip", 0))
    return lines[header_skip: len(lines) - footer_skip if footer_skip > 0 else None]

def is_separator(ln: str) -> bool:
    s = ln.strip()
    return (not s) or set(s) <= {"-"}  # blank or dashed line

def group_fields_by_group(cfg: Dict[str, Any]) -> Dict[int, List[Dict[str, Any]]]:
    groups: Dict[int, List[Dict[str, Any]]] = {}
    for f in cfg.get("fields", []):
        g = int(f.get("group", 1))
        groups.setdefault(g, []).append(f)
    return groups

def group_start_lines(groups: Dict[int, List[Dict[str, Any]]]) -> Dict[int, int]:
    # For each group, use the minimum 'line' as the group's starting row (0-based within relevant_lines)
    starts: Dict[int, int] = {}
    for g, fields in groups.items():
        lines = [int(f.get("line", 0)) for f in fields]
        starts[g] = min(lines) if lines else 0
    return starts

def parse_absolute_group_tables(text: str, cfg: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
    """
    Parse using absolute line numbers per group:
    - For each group g, start at its min(line).
    - Extract rows until the next group's start line (exclusive) or EOF.
    - Within a row, fields may come from line offsets (field.line - group_start_line).
    """
    all_lines = text.splitlines()
    lines = compute_relevant_lines(all_lines, cfg)
    groups = group_fields_by_group(cfg)
    if not groups:
        return {}

    starts = group_start_lines(groups)
    # Order groups by their start line in the file
    ordered_groups: List[Tuple[int, int]] = sorted(starts.items(), key=lambda x: x[1])

    result: Dict[str, List[Dict[str, str]]] = {}

    for idx, (g, g_start) in enumerate(ordered_groups):
        next_start = ordered_groups[idx + 1][1] if idx + 1 < len(ordered_groups) else len(lines)
        # safety: bounds
        g_start = max(0, g_start)
        next_start = min(len(lines), max(next_start, g_start))

        # Fields for this group
        g_fields = groups[g]
        base = g_start
        rows: List[Dict[str, str]] = []

        i = base
        while i < next_start:
            # Skip separators
            if is_separator(lines[i]):
                i += 1
                continue

            row: Dict[str, str] = {}
            any_value = False
            for f in g_fields:
                fld_line_abs = int(f.get("line", g_start))
                offset = fld_line_abs - g_start
                line_index = i + offset
                if line_index >= next_start or line_index >= len(lines):
                    continue
                ln = lines[line_index]
                left = int(f.get("left", 0))
                right = f.get("right")
                right = int(right) if right is not None else None
                label = f.get("label", f"Group{g}_{left}_{right}")
                val = slice_safe(ln, left, right).strip()
                row[label] = val
                if val:
                    any_value = True

            if any_value:
                rows.append(row)
                # Advance to the next *physical* row for this table.
                # If your group spans multiple physical lines per record,
                # you can set all field.line = g_start and increment below by 1 per record.
                i += 1
            else:
                # If we got an entirely empty row, likely reached whitespace/gap before next section.
                i += 1

        result[f"group_{g}"] = rows

    return result

def main():
    ap = argparse.ArgumentParser(description="Parse fixed-width AS/400-style text using absolute line + group tables.")
    ap.add_argument("--config", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--report-name", default=None)
    ap.add_argument("--out", default="parsed_bygroup.json")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg_data = json.load(f)
    rule = select_config(cfg_data, args.report_name)
    with open(args.report, "r", encoding="utf-8") as f:
        text = f.read()

    recs_by_group = parse_absolute_group_tables(text, rule)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(recs_by_group, f, indent=2)
    print(f"✅ Parsed → {args.out}")

if __name__ == "__main__":
    main()
