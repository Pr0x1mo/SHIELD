
import json
import spacy
from pathlib import Path

def load_expected_entities(config_path, text_path):
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    with open(text_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    header_skip = config.get("header_skip", 0)
    footer_skip = config.get("footer_skip", 0)
    lines = lines[header_skip:len(lines) - footer_skip]

    expected = []
    for field in config.get("fields", []):
        label = field["label"]
        line = int(field["line"])
        left = int(field["left"])
        right = int(field["right"])

        if 0 <= line < len(lines):
            value = lines[line][left:right].strip()
            char_start = sum(len(ln) + 1 for ln in lines[:line]) + left
            char_end = char_start + len(value)
            expected.append({
                "label": label,
                "value": value,
                "start": char_start,
                "end": char_end
            })
    return expected

def load_model_predictions(model_path, text):
    nlp = spacy.load(model_path)
    doc = nlp(text)
    return [{
        "label": ent.label_,
        "value": ent.text.strip(),
        "start": ent.start_char,
        "end": ent.end_char
    } for ent in doc.ents]

def compare_entities(expected, predicted):
    comparison = []
    for exp in expected:
        match = next((pred for pred in predicted if abs(pred["start"] - exp["start"]) <= 5 and pred["label"] == exp["label"]), None)
        comparison.append({
            "Label": exp["label"],
            "Expected Value": exp["value"],
            "Predicted Value": match["value"] if match else "",
            "Match": "✅" if match and match["value"] == exp["value"] else "❌"
        })
    return comparison

if __name__ == "__main__":
    model_dir = "model/on_prem_nlp_model"
    config_path = r"C:\Users\salda\source\repos\Shield Application\config\R-07362-001.json"
    text_path = r"C:\Users\salda\source\repos\Shield Application\data\Samples\payoff_notice_to_payee_r-07362-001.txt"

    expected = load_expected_entities(config_path, text_path)
    text = Path(text_path).read_text(encoding="utf-8")
    predicted = load_model_predictions(model_dir, text)

    results = compare_entities(expected, predicted)

    print("\n=== SMARTS Config vs. Model Prediction ===")
    for row in results:
        print(f"{row['Label']:20} | Expected: {row['Expected Value']:<30} | Predicted: {row['Predicted Value']:<30} | {row['Match']}")
