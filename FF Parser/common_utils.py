# -*- coding: utf-8 -*-
"""
common_utils.py - Common utilities for CIBC Parser
Shared functions and regex patterns
"""

import re
from pathlib import Path
from typing import Optional, Tuple, List

# Try to import spaCy for enhanced NLP capabilities

try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    HAVE_SPACY = True
    print("✓ spaCy loaded successfully")
except Exception as e:
    HAVE_SPACY = False
    nlp = None
    print(f"spaCy error: {e}")
    
# ============= COMMON REGEX PATTERNS =============
ZIP_RE = re.compile(r"\b[A-Z]{2}[,\s]+\d{5}(?:-\d{4})?\b", re.IGNORECASE)
MONEY_RE = r"\$[0-9][0-9,]*\.\d{2}"
REM_ZIP_PATTS = (r"\bCHICAGO\s+IL\s+60603\b", r"\bWORTH[,\s]+IL\s+60482\b")

# ============= BASIC UTILITIES =============
def read_text(path: Path) -> str:
    """Read and normalize text file."""
    return path.read_text(errors="ignore").replace("\r\n", "\n").replace("\r", "\n")

def m2f(s: str) -> Optional[float]:
    """Convert money string to float."""
    if not s:
        return None
    try:
        return float(s.replace(",", "").replace("$", "").strip())
    except:
        return None

# ============= SPACY ENHANCEMENT FUNCTIONS =============
def extract_names_with_spacy(text_block: str, max_names: int = 5) -> List[str]:
    """Use spaCy NER to extract person names."""
    if not HAVE_SPACY or not nlp:
        return []
    
    try:
        doc = nlp(text_block[:1000])
        names = []
        seen = set()
        
        for ent in doc.ents:
            if ent.label_ == "PERSON" and len(names) < max_names:
                name = ent.text.strip()
                if (name.upper() not in ("CIBC BANK USA", "LASALLE", "CHICAGO", "CIBC")
                    and name not in seen
                    and len(name) > 2):
                    names.append(name)
                    seen.add(name)
        
        return names
    except Exception:
        return []

def extract_address_with_spacy(text_block: str) -> Tuple[str, str]:
    """Use spaCy to help extract address components."""
    if not HAVE_SPACY or not nlp:
        return "", ""
    
    try:
        lines = text_block.splitlines()
        
        for i, line in enumerate(lines):
            if ZIP_RE.search(line):
                if any(re.search(p, line, re.IGNORECASE) for p in REM_ZIP_PATTS):
                    continue
                
                if i > 0:
                    street = lines[i-1].strip()
                    if re.search(r"\d", street) or re.search(r"\bP\.?O\.?\s*BOX\b", street, re.IGNORECASE):
                        return street, line.strip()
        
        return "", ""
    except:
        return "", ""

def classify_transaction_with_spacy(description: str) -> str:
    """Use spaCy to classify transaction type."""
    if not HAVE_SPACY or not nlp or not description:
        return ""
    
    try:
        doc = nlp(description.lower())
        
        payment_words = {'payment', 'pmt', 'paid', 'pay', 'remittance', 'credit'}
        fee_words = {'fee', 'charge', 'penalty', 'cost', 'fine'}
        interest_words = {'interest', 'int', 'apr', 'finance charge'}
        transfer_words = {'transfer', 'xfer', 'wire', 'ach'}
        advance_words = {'advance', 'withdrawal', 'draw', 'debit'}
        
        tokens = {token.text for token in doc}
        
        if tokens & payment_words:
            return "payment"
        elif tokens & fee_words:
            return "fee"
        elif tokens & interest_words:
            return "interest"
        elif tokens & transfer_words:
            return "transfer"
        elif tokens & advance_words:
            return "advance"
        else:
            return "other"
    except:
        return ""

def enhance_customer_extraction(names_regex: List[str], street_regex: str, 
                               csz_regex: str, content: str) -> Tuple[List[str], str, str]:
    """Try spaCy first for name extraction, fall back to regex results."""
    if not HAVE_SPACY or not nlp:
        return names_regex, street_regex, csz_regex
    
    try:
        search_window = content[:1500]
        spacy_names = extract_names_with_spacy(search_window)
        
        if len(spacy_names) >= 1 and street_regex and csz_regex:
            while len(spacy_names) < 5:
                spacy_names.append("")
            return spacy_names[:5], street_regex, csz_regex
        
        return names_regex, street_regex, csz_regex
    except:
        return names_regex, street_regex, csz_regex

def print_spacy_status():
    """Print spaCy status message."""
    if HAVE_SPACY:
        print("✓ spaCy loaded successfully - enhanced extraction available")
    else:
        print("Note: spaCy not installed. Using regex-only extraction (still works fine!)")
        print("To enable ML enhancements:")
        print("  pip install spacy")
        print("  python -m spacy download en_core_web_sm")