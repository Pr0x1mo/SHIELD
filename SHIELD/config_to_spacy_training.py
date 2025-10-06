import json
import re
import spacy
from spacy.tokens import DocBin


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_multi_record_config(report_path, config):
    with open(report_path, "r", encoding="utf-8") as f:
        raw_lines = f.read().splitlines()

    header_skip = int(config.get("header_skip", 0) or 0)
    footer_skip = int(config.get("footer_skip", 0) or 0)

    # Avoid lines[:-0] => []
    if footer_skip > 0:
        lines = raw_lines[header_skip:len(raw_lines) - footer_skip]
    else:
        lines = raw_lines[header_skip:]

    # Detect record blocks using anchor pattern (9-digit account number at line start)
    record_start_pattern = re.compile(r"^\d{9}\s+[A-Z]")
    record_starts = [i for i, line in enumerate(lines) if record_start_pattern.match(line)]

    # Use a blank English tokenizer for robust doc creation
    nlp = spacy.blank("en")
    all_docs = []

    # If no record starts found, nothing to do
    if not record_starts:
        return all_docs

    anchor_first = record_starts[0]
    full_text = "\n".join(lines)

    for base_line in record_starts:
        text = full_text  # same underlying text; entities differ per record
        entities = []

        for field in config.get("fields", []):
            label = field.get("label")
            field_line_abs = int(field.get("line", 0))
            left = int(field.get("left", 0))
            right = int(field.get("right", 0))

            # Compute relative offset from the first anchor, then map to current base_line
            line_offset = field_line_abs - anchor_first
            target_line_index = base_line + line_offset

            if 0 <= target_line_index < len(lines):
                line_text = lines[target_line_index]

                # Clamp to line bounds to keep offsets stable
                L = max(0, min(left, len(line_text)))
                R = max(L, min(right, len(line_text)))

                slice_text = line_text[L:R]  # do NOT strip for offsets

                # Absolute char start of this target line within the full text
                line_start = sum(len(ln) + 1 for ln in lines[:target_line_index])
                char_start = line_start + L
                char_end = line_start + R  # fixed-width => stable end

                # Keep only non-empty (ignoring whitespace-only) spans
                if slice_text.strip():
                    entities.append((char_start, char_end, label))

        if entities:
            doc = nlp.make_doc(text)
            # Align spans to token boundaries to avoid W030 warnings
            spans = [
                doc.char_span(s, e, label=lbl, alignment_mode="contract")
                for s, e, lbl in entities
            ]
            spans = [s for s in spans if s is not None]
            if spans:
                doc.ents = spans
                all_docs.append(doc)

    return all_docs


def convert_to_spacy_format(config_path, report_path, output_path="train.spacy"):
    config = load_config(config_path)
    docs = apply_multi_record_config(report_path, config)
    doc_bin = DocBin(docs=docs)
    doc_bin.to_disk(output_path)
    print(f"✅ Saved {len(docs)} training docs to {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to SMARTS config JSON")
    parser.add_argument("--report", required=True, help="Path to raw report text file")
    parser.add_argument("--out", default="train.spacy", help="Output path for spaCy training file")
    args = parser.parse_args()

    convert_to_spacy_format(args.config, args.report, args.out)
