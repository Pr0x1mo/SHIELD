
import json
import spacy

def load_expected(config_path, text_path):
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    with open(text_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    header_skip = config.get("header_skip", 0)
    footer_skip = config.get("footer_skip", 0)
    lines = lines[header_skip:len(lines) - footer_skip]
    expected = []
    for field in config["fields"]:
        label = field["label"]
        line = int(field["line"])
        left = int(field["left"])
        right = int(field["right"])
        if 0 <= line < len(lines):
            value = lines[line][left:right].strip()
            start = sum(len(ln)+1 for ln in lines[:line]) + left
            end = start + len(value)
            expected.append({"label": label, "value": value, "start": start, "end": end})
    return expected

def load_predictions(model_path, text_path):
    nlp = spacy.load(model_path)
    text = open(text_path, encoding="utf-8").read()
    doc = nlp(text)
    return [{"label": ent.label_, "value": ent.text.strip(), "start": ent.start_char, "end": ent.end_char} for ent in doc.ents]

def compare(expected, predicted):
    results = []
    for exp in expected:
        match = next((p for p in predicted if abs(p["start"] - exp["start"]) <= 5 and p["label"] == exp["label"]), None)
        results.append({
            "label": exp["label"],
            "expected": exp["value"],
            "predicted": match["value"] if match else "",
            "match": match is not None and match["value"] == exp["value"]
        })
    return results

if __name__ == "__main__":
    model_dir = "model/on_prem_nlp_model"
    config_path = r"C:\Users\salda\source\repos\Shield Application\config\R-07362-001.json"
    text_path = r"C:\Users\salda\source\repos\Shield Application\data\Samples\payoff_notice_to_payee_r-07362-001.txt"

    expected = load_expected(config_path, text_path)
    predicted = load_predictions(model_dir, text_path)
    results = compare(expected, predicted)

    print(f"{'Label':20} | {'Expected':30} | {'Predicted':30} | Match")
    print("-" * 90)
    for r in results:
        print(f"{r['label']:20} | {r['expected']:<30} | {r['predicted']:<30} | {'✅' if r['match'] else '❌'}")

