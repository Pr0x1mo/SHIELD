# test_pattern.py
import re
import yaml
import argparse

def load_patterns(path="config/field_patterns.yaml"):
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    return config.get("fields", {})

def test_label_pattern(label, text):
    patterns = load_patterns()
    matches = []
    if label not in patterns:
        print(f"Label '{label}' not found in config.")
        return

    print(f"\n Testing patterns for label: {label}")
    for pattern in patterns[label]:
        try:
            for match in re.finditer(pattern, text):
                matches.append((match.group(), match.start(), match.end()))
                print(f" Match: '{match.group()}' at ({match.start()}, {match.end()})")
        except re.error as e:
            print(f" Pattern error: {pattern} - {e}")

    if not matches:
        print(" No matches found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True, help="Pattern label from YAML")
    parser.add_argument("--text", required=True, help="Text to test against")
    args = parser.parse_args()

    test_label_pattern(args.label, args.text)
