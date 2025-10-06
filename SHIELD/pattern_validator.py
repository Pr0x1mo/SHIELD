# pattern_validator.py
import yaml
import re

def validate_patterns(path="config/field_patterns.yaml"):
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    fields = config.get("fields", {})

    print("Validating regex patterns:\n")
    for label, patterns in fields.items():
        for pattern in patterns:
            try:
                re.compile(pattern)
                print(f"{label}: {pattern}")
            except re.error as e:
                print(f"{label}: {pattern} - Invalid regex: {e}")

if __name__ == "__main__":
    validate_patterns()
