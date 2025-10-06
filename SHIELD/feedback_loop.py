def compute_line_position(text: str, start: int, end: int):
    # 1-based line_number; left/right are offsets in the line
    lines = text.splitlines()
    offset = 0
    for i, line in enumerate(lines):
        line_len = len(line) + 1
        if offset + line_len > start:
            left = start - offset
            right = end - offset
            return i + 1, left, right
        offset += line_len
    return -1, -1, -1

def sanitize_label(lbl: str) -> str:
    return (lbl or "").strip().replace(" ", "_").replace("-", "_").upper()

def normalize_entity(text: str, ent):
    """
    Returns:
      {"start","end","label","line_number","left","right","value"}
    Accepts:
      - dict with start/end/label (value optional)
      - tuples: (value,label,"s-e") or (value,label,s,e) or (s,e,label)
    """
    try:
        provided_value = None

        if isinstance(ent, dict):
            s = int(ent["start"]); e = int(ent["end"]); lbl = sanitize_label(ent["label"])
            provided_value = ent.get("value")
        else:
            # tuple/list variants
            if isinstance(ent[2], str) and "-" in ent[2]:
                s, e = map(int, ent[2].split("-")); lbl = sanitize_label(ent[1])
                provided_value = ent[0] if isinstance(ent[0], str) else None
            elif len(ent) >= 4 and not isinstance(ent[2], str):
                if isinstance(ent[0], int) and isinstance(ent[1], int):
                    # (start, end, label)
                    s, e, lbl = int(ent[0]), int(ent[1]), sanitize_label(ent[2])
                else:
                    # (value, label, start, end)
                    provided_value = ent[0] if isinstance(ent[0], str) else None
                    s, e, lbl = int(ent[2]), int(ent[3]), sanitize_label(ent[1])
            else:
                return None

        if not (0 <= s < e <= len(text)):
            return None

        ln, lf, rt = compute_line_position(text, s, e)
        value = provided_value if (provided_value and provided_value.strip()) else text[s:e]

        return {
            "start": s, "end": e, "label": lbl,
            "line_number": ln, "left": lf, "right": rt,
            "value": value
        }
    except Exception:
        return None

def dedupe_overlaps(ents):
    # De-dupe by (start,end,label); keep widest on same-label overlaps. 'value' follows the kept span.
    ents = sorted(ents, key=lambda x: (x["start"], -x["end"]))
    out = []
    for e in ents:
        if any(e["start"]==o["start"] and e["end"]==o["end"] and e["label"]==o["label"] for o in out):
            continue
        clashes = [o for o in out if not (e["end"] <= o["start"] or e["start"] >= o["end"]) and o["label"] == e["label"]]
        if clashes:
            widest = max([e] + clashes, key=lambda z: z["end"] - z["start"])
            out = [o for o in out if o not in clashes]
            out.append(widest)
        else:
            out.append(e)
    return out

def collect_user_feedback(text, entities):
    clean = [x for x in (normalize_entity(text, e) for e in entities) if x]
    clean = dedupe_overlaps(clean)

    print("\n=== SHIELD Feedback Review ===")
    print("Enter=confirm | x=exclude | l NEWLABEL | e START END | s=skip\n")

    final = []
    for i, e in enumerate(clean, 1):
        print(f"[{i}/{len(clean)}] '{e['value']}' [{e['label']}] span=({e['start']},{e['end']}) line={e['line_number']}")
        cmd = input(" > ").strip()

        if cmd == "":
            final.append(e); continue
        if cmd.lower() == "x":
            continue
        if cmd.lower().startswith("l "):
            e["label"] = sanitize_label(cmd[2:].strip())
            final.append(e); continue
        if cmd.lower().startswith("e "):
            try:
                _, s, ed = cmd.split(); s, ed = int(s), int(ed)
                if 0 <= s < ed <= len(text):
                    e["start"], e["end"] = s, ed
                    e["line_number"], e["left"], e["right"] = compute_line_position(text, s, ed)
                    e["value"] = text[s:ed]  # <-- refresh value on edit
                    final.append(e)
                else:
                    print("  ! invalid span")
            except Exception:
                print("  ! usage: e START END")
            continue
        if cmd.lower() == "s":
            break

    return dedupe_overlaps(final)
