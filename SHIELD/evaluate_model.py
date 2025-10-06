import spacy
from pathlib import Path

# Load trained model
nlp = spacy.load("model/on_prem_nlp_model")  # or wherever you saved it

# Load report text
with open(r"C:\Users\salda\source\repos\Shield Application\data\Samples\SamplePIIData_ACCT_DETAIL.txt", encoding="utf-8") as f:
    text = f.read()

# Run model
doc = nlp(text)

# Print results
print("Predicted Entities:")
for ent in doc.ents:
    print(f"{ent.label_:20} | {ent.text.strip():40} | Start: {ent.start_char:4} End: {ent.end_char}")
