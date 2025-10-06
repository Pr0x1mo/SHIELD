# file_loader.py
import os
import pandas as pd
import pdfplumber

def read_text_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()

def read_csv_file(filepath):
    df = pd.read_csv(filepath)
    return "\n".join(df.astype(str).apply(lambda x: ' '.join(x), axis=1))

def read_pdf_file(filepath):
    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
    return text

def read_rpg_report(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    return "\n".join([line.strip() for line in lines])

def get_file_text(filepath):
    ext = os.path.splitext(filepath)[-1].lower()
    if ext == '.txt':
        return read_text_file(filepath)
    elif ext == '.csv':
        return read_csv_file(filepath)
    elif ext == '.pdf':
        return read_pdf_file(filepath)
    elif ext in ['.rpg', '.rpgrpt', '.prn']:
        return read_rpg_report(filepath)
    else:
        raise ValueError("Unsupported file format: " + ext)
