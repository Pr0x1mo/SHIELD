import spacy
from spacy.cli import download
import shutil
import os

# Step 1: Download the model if not already present
model_name = "en_core_web_lg"
download(model_name)

# Step 2: Load the model
nlp = spacy.load(model_name)

# Step 3: (Optional) Strip unused pipeline components to reduce size
components_to_keep = {"ner", "tokenizer"}
components_to_remove = set(nlp.pipe_names) - components_to_keep
for pipe in components_to_remove:
    nlp.remove_pipe(pipe)

# Step 4: Save to a portable directory for on-premise use
on_premise_path = os.path.abspath("./on_prem_nlp_model")
if os.path.exists(on_premise_path):
    shutil.rmtree(on_premise_path)

nlp.to_disk(on_premise_path)
print(f"On-premise SpaCy model saved successfully to: {on_premise_path}")

# Example of reloading later
# from spacy import load
# nlp = load("./on_prem_nlp_model")

