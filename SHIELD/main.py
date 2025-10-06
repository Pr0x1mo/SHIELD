# main.py - SHIELD CLI Pipeline
import argparse
import os
from file_loader import get_file_text
from regex_extractor import extract_fields, load_regex_patterns
from pii_detection import detect_entities, load_model
from feedback_loop import collect_user_feedback
from obfuscator import obfuscate_text
from trainer import train_model

DEFAULT_FEEDBACK_FILE = "data/feedback.json"
DEFAULT_OUTPUT_DIR = "data/obfuscated"


def run_detection(
    filepath,
    nlp_model=None,
    use_spacy=True,
    use_regex=True,
    use_smarts=False,
    smarts_config_path="config/smarts_report_configs.json",
):
    """
    Returns:
      content (str),
      entities_gui (list of tuples):
        (value, label, "start-end", line_number, left, right, record, "", start, end)
    """
    import json, os
    from utils import extract_spans_from_smart_config
    content = get_file_text(filepath)
    filename = os.path.basename(filepath)

    def compute_line_position(text, start, end):
        lines = text.splitlines()
        offset = 0
        for i, line in enumerate(lines):
            ln = len(line) + 1
            if offset + ln > start:
                return i, start - offset, end - offset
            offset += ln
        return -1, -1, -1

    entities_char = []  # (value, label, start, end, record)

    # spaCy
    if use_spacy and nlp_model is not None:
        try:
            spacy_ents = detect_entities(content, nlp_model)  # (text,label,start,end)
            entities_char += [(t, l, s, e, "") for (t, l, s, e) in spacy_ents]
        except Exception as e:
            print(f"[WARN] spaCy extraction failed: {e}")

    # Regex
    if use_regex:
        try:
            patterns = load_regex_patterns()
            regex_results = extract_fields(content, patterns)
            entities_char += [(r["text"], r["label"], int(r["start"]), int(r["end"]), "") for r in regex_results]
        except Exception as e:
            print(f"[WARN] Regex extraction failed: {e}")

    # SMARTS (fixed-width via report config)
    if use_smarts:
        try:
            with open(smarts_config_path, "r", encoding="utf-8") as f:
                configs = json.load(f)
            matched = None
            for cfg in configs:
                rn = (cfg.get("report_name") or "").lower()
                if rn and rn in filename.lower():
                    matched = cfg
                    break
            if matched:
                smarts_ents = extract_spans_from_smart_config(content, matched)
                # returns (value, label, start, end, record)
                entities_char += smarts_ents
            else:
                print(f"[INFO] No SMARTS report config matched for '{filename}'.")
        except Exception as e:
            print(f"[WARN] SMARTS extraction failed: {e}")

    # Build GUI/feedback-friendly rows with line/left/right
    entities_gui = []
    for (value, label, start, end, record) in entities_char:
        try:
            start = int(start); end = int(end)
            line, left, right = compute_line_position(content, start, end)
            span = f"{start}-{end}"
            entities_gui.append((value, label, span, line, left, right, record or "", "", start, end))
        except Exception:
            continue

    print("\nDetected Entities:")
    for v, l, span, *_ in entities_gui:
        print(f"- {v} ({l}) @ {span}")

    return content, entities_gui



def run_obfuscation(filepath, nlp_model=None, feedback_file=DEFAULT_FEEDBACK_FILE, output_dir=DEFAULT_OUTPUT_DIR):
    # Use the new switches below (see argparse section)
    text, all_entities = run_detection(
        filepath,
        nlp_model=nlp_model,
        use_spacy=not args.nospacy,
        use_regex=not args.noregex,
        use_smarts=args.smarts,
        smarts_config_path=args.smarts_config,
    )

    updated = collect_user_feedback(text, all_entities)  # list of dicts
    if not updated:
        print("\nNo changes made. Nothing to obfuscate.")
        return

    # Build (start,end,label) for obfuscation
    obfus_spans = [(e["start"], e["end"], e["label"]) for e in updated]

    # Train model — if you’ve applied the “trainer accepts dicts or tuples” fix,
    # you can pass `updated` directly. If not, pass obfus_spans.
    try:
        train_model(text, updated, feedback_file)   # preferred (dict-aware trainer)
    except Exception:
        train_model(text, obfus_spans, feedback_file)

    obfuscated = obfuscate_text(text, obfus_spans)

    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.basename(filepath)
    output_path = os.path.join(output_dir, f"obfuscated_{filename}")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(obfuscated)

    print(f"\nObfuscated file saved: {output_path}")



def main():
    parser = argparse.ArgumentParser(description="SHIELD: PII Detection and Obfuscation Pipeline")
    parser.add_argument("--mode", choices=["detect", "obfuscate"], required=True, help="Run mode")
    parser.add_argument("--file", required=True, help="Path to input file")
    parser.add_argument("--feedback", default=DEFAULT_FEEDBACK_FILE, help="Path to feedback.json")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Output directory for obfuscated files")
    parser.add_argument("--noregex", action="store_true", help="Disable regex-based extraction")
    parser.add_argument("--nospacy", action="store_true", help="Disable spaCy-based extraction")
    parser.add_argument("--smarts", action="store_true", help="Enable SMARTS (fixed-width) extraction")
    parser.add_argument("--smarts-config", default="config/smarts_report_configs.json", help="Path to SMARTS report configs")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"File not found: {args.file}")
        return

    nlp = None if args.nospacy else load_model()

    if args.mode == "detect":
        run_detection(
            args.file,
            nlp_model=nlp,
            use_spacy=not args.nospacy,
            use_regex=not args.noregex,
            use_smarts=args.smarts,
            smarts_config_path=args.smarts_config,
        )
    elif args.mode == "obfuscate":
        run_obfuscation(args.file, nlp_model=nlp, feedback_file=args.feedback, output_dir=args.output)



if __name__ == "__main__":
    main()
