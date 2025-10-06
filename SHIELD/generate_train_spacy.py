import json
from pathlib import Path
import spacy
from spacy.tokens import DocBin


def extract_entities(config_path, text_path):
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    with open(text_path, encoding="utf-8") as f:
        raw_lines = f.read().splitlines()

    header_skip = int(config.get("header_skip", 0) or 0)
    footer_skip = int(config.get("footer_skip", 0) or 0)

    # IMPORTANT: avoid lines[:-0] which returns [] in Python
    if footer_skip > 0:
        lines = raw_lines[header_skip:len(raw_lines) - footer_skip]
    else:
        lines = raw_lines[header_skip:]

    full_text = "\n".join(lines)

    entities = []
    for field in config.get("fields", []):
        label = field["label"]
        line = int(field["line"])
        left = int(field["left"])
        right = int(field["right"])

        if 0 <= line < len(lines):
            line_text = lines[line]

            # Clamp to line bounds to avoid IndexErrors and negative widths
            L = max(0, min(left, len(line_text)))
            R = max(L, min(right, len(line_text)))

            slice_text = line_text[L:R]  # do NOT strip for offsets

            # Absolute start of this line within full_text (+1 for '\n' per previous lines)
            line_start = sum(len(ln) + 1 for ln in lines[:line])
            start = line_start + L
            end = line_start + R  # fixed-width => stable end

            # Only keep non-empty (ignoring whitespace-only) spans
            if slice_text.strip():
                entities.append((start, end, label))

    return full_text, entities


def build_docbin(file_pairs, out_path="train.spacy"):
    # Use a blank English tokenizer; no dependency on your custom model
    nlp = spacy.blank("en")
    doc_bin = DocBin()

    total_spans = 0
    aligned_spans = 0

    for config_file, text_file in file_pairs:
        text, spans = extract_entities(config_file, text_file)
        total_spans += len(spans)

        doc = nlp.make_doc(text)
        ents = []
        for s, e, label in spans:
            # Contract alignment turns slightly off char spans into token-aligned spans
            span = doc.char_span(s, e, label=label, alignment_mode="contract")
            if span is not None:
                ents.append(span)
        aligned_spans += len(ents)
        doc.ents = ents
        doc_bin.add(doc)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    doc_bin.to_disk(out_path)
    print(f"✅ {out_path} saved — aligned {aligned_spans}/{total_spans} spans")


if __name__ == "__main__":
    file_pairs = [
        (r"C:\Users\salda\source\repos\Shield Application\config\ACCT_DETAIL.json",
         r"C:\Users\salda\source\repos\Shield Application\data\Samples\SamplePIIData_ACCT_DETAIL.txt"),
        (r"C:\Users\salda\source\repos\Shield Application\config\ACCT_LOAN.json",
         r"C:\Users\salda\source\repos\Shield Application\data\Samples\SamplePIIData_ACCT_LOAN.txt"),
        (r"C:\Users\salda\source\repos\Shield Application\config\ACCT_STATUS.json",
         r"C:\Users\salda\source\repos\Shield Application\data\Samples\SamplePIIData_ACCT_STATUS.txt"),
        (r"C:\Users\salda\source\repos\Shield Application\config\EMPLYE_EXPNSE_STM.json",
         r"C:\Users\salda\source\repos\Shield Application\data\Samples\SamplePIIData_EMPLYE_EXPNSE_STM.txt"),
    ]

    build_docbin(file_pairs, out_path="train.spacy")
