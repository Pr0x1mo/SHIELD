# regex_extractor.py
import re
import yaml

def load_regex_patterns(path="config/field_patterns.yaml"):
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    return config.get("fields", {})

def extract_fields(text, patterns):
    results = []
    for label, regex_list in patterns.items():
        for pattern in regex_list:
            try:
                for match in re.finditer(pattern, text):
                    results.append({
                        "label": label,
                        "text": match.group(),
                        "start": match.start(),
                        "end": match.end()
                    })
            except re.error as e:
                print(f"Invalid pattern for {label}: {pattern} => {e}")
    return results
