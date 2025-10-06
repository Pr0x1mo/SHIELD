import spacy
import os

# Step 1: Define model path
model_path = os.path.abspath("./model/on_prem_nlp_model")

# Step 2: Validate model directory
if not os.path.exists(model_path):
    raise FileNotFoundError(f"Model path not found: {model_path}")
if not os.path.exists(os.path.join(model_path, "config.cfg")):
    raise FileNotFoundError(f"config.cfg missing in: {model_path}")

# Step 3: Load model
nlp = spacy.load(model_path)
print("Model loaded successfully.")

# Step 4: Run test inference
doc = nlp("John Doe lives at 123 Main Street and works at Acme Corp.")
for ent in doc.ents:
    print(f"{ent.text} ({ent.label_})")
