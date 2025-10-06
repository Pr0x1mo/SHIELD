import spacy
from spacy.tokens import DocBin

# Load your .spacy file
doc_bin = DocBin().from_disk("train.spacy")
nlp = spacy.load("model/on_prem_nlp_model")
docs = list(doc_bin.get_docs(nlp.vocab))

print(f"Total docs loaded: {len(docs)}\n")

# Loop through all docs
for i, doc in enumerate(docs):
    print(f"\n--- Document {i+1} ---")
    print("Text Preview:",  doc.text)

    if doc.ents:
        print("Entities:")
        for ent in doc.ents:
            print(f"  - {ent.text} [{ent.label_}]")
    else:
        print("No entities found.")

