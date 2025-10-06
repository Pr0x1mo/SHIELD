# -*- coding: utf-8 -*-
# ============================================================================
# BEGINNER-FRIENDLY, FULLY COMMENTED VERSION
# File: cibc_parser_commented.py
# Created: 2025-09-16T13:04:03
#
# WHAT THIS PROGRAM DOES (Plain English):
# - Reads your CIBC PDF/CSV statements (loans, credit cards, payoffs, etc.).
# - Extracts useful info (like dates, amounts, names) using text matching and optional NLP.
# - Organizes that info into clean tables (pandas DataFrames).
# - Saves the results to easy-to-open files (like Excel) in an output folder.
#
# HOW TO RUN (from a terminal/command prompt):
# 1) Make sure Python 3.9+ is installed.
# 2) (Optional but recommended) Create a virtual environment:
#       python -m venv .venv
#       .venv\Scripts\activate    (Windows)   OR   source .venv/bin/activate (macOS/Linux)
# 3) Install required packages (examples; your script may need some of these):
#       pip install pandas pdfplumber regex openpyxl python-dateutil spacy
#    If the script uses spaCy name-finding (PERSON names):
#       python -m spacy download en_core_web_sm
# 4) Run:
#       python cibc_parser_commented.py --input <folder_with_statements> --output <where_to_save>
#
# READING THE COMMENTS:
# - Every important line explains itself in plain English above it.
# - If a comment mentions "DataFrame": think "Excel sheet in memory".
# - If a comment mentions "regex": think "magic pattern matching for text".
# - If a comment mentions "NLP/spaCy": think "find names in text like 'John Smith' automatically".
# ============================================================================

# Shebang: tells the OS this is a Python script when run directly on Unix-like systems.
#!/usr/bin/env python3
"""
Combined CIBC Bank Statement Parser with Optional spaCy Enhancement
Processes all document types from a single input file:
1. LOAN STATEMENT (BILL) R-06090-002
2. REV. CREDIT STATEMENT R-06088-001
3. ADVICE OF RATE CHANGE R-06061-001
4. PAYOFF NOTICE TO PAYEE R-07362-001
5. PAST DUE NOTICE R-06385-00x
"""

# Importing Python modules (re) so we can use their ready-made tools and functions below.
import re
# Importing Python modules (csv) so we can use their ready-made tools and functions below.
import csv
# Bringing in specific parts (Path) from the 'pathlib' module so we can call them directly.
from pathlib import Path

# Try to import spaCy for enhanced NLP capabilities (optional)
# Try to run some code. If it errors, we can handle it without crashing.
try:
# Importing Python modules (spacy) so we can use their ready-made tools and functions below.
    import spacy
    # Save a value into a variable named 'nlp' so we can use it later.
    nlp = spacy.load("en_core_web_sm")
    # Save a value into a variable named 'HAVE_SPACY' so we can use it later.
    HAVE_SPACY = True
    print("spaCy loaded successfully - enhanced extraction available")
# If an error happens in the 'try' block, this 'except' block runs to handle it.
except:
    # Save a value into a variable named 'HAVE_SPACY' so we can use it later.
    HAVE_SPACY = False
    print("Note: spaCy not installed. Using regex-only extraction (still works fine!)")

# ============= CONFIGURATION =============
# Save a value into a variable named 'INPUT_PATH' so we can use it later.
INPUT_PATH = Path(r"C:\Source\Obfuscate\Python\FF Parser\input\SampleFileSTMT.txt") #change this

# Output paths for all document types
# Save a value into a variable named 'OUTPUT_DIR' so we can use it later.
OUTPUT_DIR = Path(r"C:\Source\Obfuscate\Python\FF Parser\output") #change this 

# Loan Statement outputs

OUT_LOAN_HDR_TSV = OUTPUT_DIR / "loan_bill_header.tsv"
OUT_LOAN_SUM_TSV = OUTPUT_DIR / "loan_bill_summary.tsv"
OUT_LOAN_HIST_TSV = OUTPUT_DIR / "loan_bill_history.tsv"
OUT_LOAN_HDR_XLSX = OUTPUT_DIR / "loan_bill_header.xlsx"
OUT_LOAN_SUM_XLSX = OUTPUT_DIR / "loan_bill_summary.xlsx"
OUT_LOAN_HIST_XLSX = OUTPUT_DIR / "loan_bill_history.xlsx"

# Rev Credit Statement outputs

OUT_REV_HDR_TSV = OUTPUT_DIR / "rev_credit_statement.tsv"
OUT_REV_TXN_TSV = OUTPUT_DIR / "rev_credit_transactions.tsv"
OUT_REV_HDR_XLSX = OUTPUT_DIR / "rev_credit_statement.xlsx"
OUT_REV_TXN_XLSX = OUTPUT_DIR / "rev_credit_transactions.xlsx"

# Advice of Rate Change outputs
OUT_ADVICE_TSV = OUTPUT_DIR / "adviceOfRateChange.tsv"
OUT_ADVICE_XLSX = OUTPUT_DIR / "adviceOfRateChange.xlsx"

# Payoff Notice outputs
OUT_PAYOFF_TSV = OUTPUT_DIR / "payoff_notice_only.tsv"
OUT_PAYOFF_XLSX = OUTPUT_DIR / "payoff_notice_only.xlsx"

# Past Due Notice outputs

OUT_PAST_DUE_TSV = OUTPUT_DIR / "past_due_notice_only.tsv"
OUT_PAST_DUE_XLSX = OUTPUT_DIR / "past_due_notice_only.xlsx"

# Try Excel support if xcel isn't downloaded then these will be saved as tsv 
# Try to run some code. If it errors, we can handle it without crashing.
try:
# Bringing in specific parts (Workbook) from the 'openpyxl' module so we can call them directly.
    from openpyxl import Workbook
    # Save a value into a variable named 'HAVE_XLSX' so we can use it later.
    HAVE_XLSX = True
# If an error happens in the 'try' block, this 'except' block runs to handle it.
except Exception:
    # Save a value into a variable named 'HAVE_XLSX' so we can use it later.
    HAVE_XLSX = False
    print("Note: openpyxl not installed. Excel output will be skipped.")

# ============= COMMON UTILITIES =============
def read_text(path: Path) -> str:
    """Read and normalize (means make the text consistent so the program doesn’t get confused by differences in how files are saved.) text file."""
    # Send this value back to whoever called the function ('return' ends the function).
    return path.read_text(errors="ignore").replace("\r\n", "\n").replace("\r", "\n") #replace window's ending and old mac endings into \n

# Define a function named 'm2f'. Inputs: s: str. These are values the function expects when you call it.
# A function is a reusable mini-program you can run by its name.
def m2f(s: str):
    """Convert money string to float."""
    # Check a condition. If it's True, run the block under this 'if'.
    if not s:
        # Send this value back to whoever called the function ('return' ends the function).
        return None
    # Try to run some code. If it errors, we can handle it without crashing.
    try:
        # Send this value back to whoever called the function ('return' ends the function).
        return float(s.replace(",", "").replace("$", "").strip())
    # If an error happens in the 'try' block, this 'except' block runs to handle it.
    except:
        # Send this value back to whoever called the function ('return' ends the function).
        return None

# Common regex patterns
# Save a value into a variable named 'ZIP_RE' so we can use it later.
# This regex looks for a US-style address fragment: "STATE ZIPCODE"
# - \b            = word boundary (ensures we start at a word edge)
# - [A-Z]{2}      = exactly two letters (intended for state code, e.g. "IL")
# - [,\s]+        = one or more commas or spaces after the state
# - \d{5}         = exactly five digits (basic ZIP code, e.g. "60602")
# - (?:-\d{4})?   = optional part: a dash and four more digits (ZIP+4)
# - \b            = another word boundary (ensures clean ending)
# With re.IGNORECASE, the state letters can be uppercase or lowercase.
ZIP_RE = re.compile(r"\b[A-Z]{2}[,\s]+\d{5}(?:-\d{4})?\b", re.IGNORECASE)
# Save a value into a variable named 'MONEY_RE' so we can use it later.
# This regex looks for money amounts written like "$1,234.56"
# - \$        = a dollar sign (the backslash escapes it so regex sees "$" literally)
# - [0-9]     = the first digit (so it always starts with at least one number)
# - [0-9,]*   = then zero or more digits or commas (commas allow thousands like "1,234")
# - \.        = a literal decimal point
# - \d{2}     = exactly two digits after the decimal (for cents, like ".56")
MONEY_RE = r"\$[0-9][0-9,]*\.\d{2}"

# Remittance ZIP patterns to exclude
# Save a value into a variable named 'REM_ZIP_PATTS' so we can use it later.
REM_ZIP_PATTS = (r"\bCHICAGO\s+IL\s+60603\b", r"\bWORTH[,\s]+IL\s+60482\b")

# ============= SPACY ENHANCEMENT FUNCTIONS =============
# Define a function named 'extract_names_with_spacy'. Inputs: text_block, max_names=5. These are values the function expects when you call it.
# A function is a reusable mini-program you can run by its name.
def extract_names_with_spacy(text_block, max_names=5):
    """
    Use spaCy NER (Named Entity Recognition) to pull out people’s names from text.
    Returns a list of up to max_names names.
    """

    # If spaCy wasn’t successfully loaded earlier, just stop here and return an empty list.
    if not HAVE_SPACY:
        return []

    try:
        # nlp() is spaCy’s main function: it takes text and breaks it down into tokens (words, punctuation),
        # and also tags them with info like "this is a PERSON", "this is a DATE", etc.
        # [:1000] means "take only the first 1000 characters of the text_block" — this keeps it fast.
        doc = nlp(text_block[:1000])

        # names will be a list where we store any valid person names we find.
        names = []

        # seen is a "set" — kind of like a list, but it can’t contain duplicates.
        # We use this to keep track of names we’ve already added, so we don’t repeat them.
        seen = set()

        # Loop through each entity (ent) that spaCy identified in the text.
        for ent in doc.ents:
            # If this entity is labeled as a PERSON and we haven’t hit the limit yet…
            if ent.label_ == "PERSON" and len(names) < max_names:
                # Clean up the text of the name (remove extra spaces).
                name = ent.text.strip()

                # Filter out junk: skip known company names, skip duplicates, skip very short names.
                if (name.upper() not in ("CIBC BANK USA", "LASALLE", "CHICAGO", "CIBC")
                    and name not in seen
                    and len(name) > 2):
                    names.append(name)   # add to the list
                    seen.add(name)       # mark it as already used

        # Return the final list of names.
        return names

    except Exception as e:
        # If spaCy throws an error, don’t crash — just return an empty list.
        return []


# Define a function named 'extract_address_with_spacy'. Inputs: text_block. These are values the function expects when you call it.
# A function is a reusable mini-program you can run by its name.
def extract_address_with_spacy(text_block):
    """
    Use spaCy to help extract address components.
    Returns a tuple: (street, city_state_zip).
    For example: ("123 Main St", "Chicago, IL 60602")
    """

    # If spaCy wasn’t loaded earlier, stop and return two empty strings.
    if not HAVE_SPACY:
        return "", ""
    
    try:
        # Split the text into separate lines, so we can examine them one by one.
        lines = text_block.splitlines()
        
        # Look at each line (with its index i) to try to find the line that contains a ZIP code.
        for i, line in enumerate(lines):
            # Does this line match the ZIP code regex (like "IL 60602" or "CA, 94105-1234")?
            if ZIP_RE.search(line):

                # If this line is one of the "remittance" addresses we don’t care about, skip it.
                # any(...) runs the inner test for each pattern in REM_ZIP_PATTS.
                if any(re.search(p, line, re.IGNORECASE) for p in REM_ZIP_PATTS):
                    continue
                    
                # We found a line with a ZIP code. Now check the line *above* it to see if that’s the street.
                if i > 0:
                    # Grab the text from the line before and strip off spaces.
                    street = lines[i-1].strip()

                    # Verify this really looks like a street:
                    # - either it has a digit (house/building number), OR
                    # - it contains "P.O. BOX" in some form.
                    if re.search(r"\d", street) or re.search(r"\bP\.?O\.?\s*BOX\b", street, re.IGNORECASE):
                        # If it looks good, return a tuple:
                        # (the street line, the current line with city/state/zip).
                        return street, line.strip()
        
        # If we didn’t find anything, return two empty strings.
        return "", ""

    except:
        # If something went wrong (like bad input), return two empty strings instead of crashing.
        return "", ""


# Define a function named 'classify_transaction_with_spacy'. Inputs: description. These are values the function expects when you call it.
# A function is a reusable mini-program you can run by its name.
def classify_transaction_with_spacy(description):
    """
    Use spaCy to figure out what kind of transaction this is.
    Returns a category string like 'payment', 'fee', 'interest', 'transfer', or 'advance'.
    If it doesn’t match any, returns 'other'.
    """

    # If spaCy wasn’t loaded OR the description text is empty, just return an empty string.
    if not HAVE_SPACY or not description:
        return ""
    
    try:
        # Feed the transaction description into spaCy’s nlp() processor.
        # .lower() makes the text all lowercase so "PAYMENT" and "payment" match the same.
        doc = nlp(description.lower())
        
        # Define sets (groups) of keywords that indicate different categories.
        # If any of these words appear in the description, we’ll classify accordingly.

        payment_words  = {'payment', 'pmt', 'paid', 'pay', 'remittance', 'credit'}
        fee_words      = {'fee', 'charge', 'penalty', 'cost', 'fine'}
        interest_words = {'interest', 'int', 'apr', 'finance charge'}
        transfer_words = {'transfer', 'xfer', 'wire', 'ach'}
        advance_words  = {'advance', 'withdrawal', 'draw', 'debit'}
        
        # Convert the description into a set of tokens (individual words).
        # {token.text for token in doc} builds a set, so duplicates are removed.
        tokens = {token.text for token in doc}
        
        # Now check which keyword set overlaps with the tokens.
        # "&" means “set intersection”: are there any words in common?

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
            # If none of the categories matched, call it "other".
            return "other"

    except:
        # If anything goes wrong (e.g. spaCy fails), return an empty string instead of crashing.
        return ""


# Define a function named 'enhance_customer_extraction'. Inputs: names_regex, street_regex, csz_regex, content. These are values the function expects when you call it.
# A function is a reusable mini-program you can run by its name.
def enhance_customer_extraction(names_regex, street_regex, csz_regex, content):
    """
    Try spaCy first for name extraction, fall back to regex results.
    Combines the best of both approaches.
    """
    # Check a condition. If it's True, run the block under this 'if'.
    if not HAVE_SPACY:
        # Send this value back to whoever called the function ('return' ends the function).
        return names_regex, street_regex, csz_regex
    
    # Try to run some code. If it errors, we can handle it without crashing.
    try:
        # Extract names with spaCy from the area around the address
        # Save a value into a variable named 'search_window' so we can use it later.
        search_window = content[:1500]  # Customer info usually in first part
        # Save a value into a variable named 'spacy_names' so we can use it later.
        spacy_names = extract_names_with_spacy(search_window)
        
        # If spaCy found good names and we have address from regex, combine them
        # Check a condition. If it's True, run the block under this 'if'.
        if len(spacy_names) >= 1 and street_regex and csz_regex:
            # Pad spacy names to 5
            # Start a loop that repeats while a condition stays True.
            while len(spacy_names) < 5:
                spacy_names.append("")
            # Send this value back to whoever called the function ('return' ends the function).
            return spacy_names[:5], street_regex, csz_regex
        
        # Otherwise return regex results
        # Send this value back to whoever called the function ('return' ends the function).
        return names_regex, street_regex, csz_regex
    # If an error happens in the 'try' block, this 'except' block runs to handle it.
    except:
        # Send this value back to whoever called the function ('return' ends the function).
        return names_regex, street_regex, csz_regex

# ============= LOAN STATEMENT PROCESSING =============
# Create a Class named 'LoanStatementProcessor'. If you didn't know, a Class is a blueprint for objects (bundles of data + functions).
# We'll make objects from this Class to organize related behavior and state.
class LoanStatementProcessor:
    # Save a value into a variable named 'HDR' so we can use it later.
    HDR = re.compile(
        r"^\s*\d{3}-\d{7}\s+CIBC BANK USA\s+LOAN STATEMENT \(BILL\)\s+"
        r"(R-06090-002)\s+(\d{2}-\d{2}-\d{2})\s+PAGE\s+(\d+)\s*$",
        re.MULTILINE
    )
    
    # Save a value into a variable named 'FIELD_STARTS' so we can use it later.
    FIELD_STARTS = (
        r"ACCOUNT/NOTE\s*NUMBER", r"ACCOUNT\s*NUMBER", r"NOTE\s*NUMBER",
        r"STATEMENT\s*DATE", r"PAYMENT\s*DUE\s*DATE",
        r"OFFICER", r"BRANCH\s*NUMBER", r"CURRENT\s*BALANCE", r"AMOUNT\s*DUE",
        r"RATE\s+INFORMATION", r"SUMMARY", r"YEAR-TO-DATE\s+SUMMARY",
        r"LOAN\s+HISTORY", r"PAGE\s+\d+\s+OF\s+\d+",
        r"PLEASE\s+REMIT", r"PLEASE\s+SEND\s+YOUR\s+PAYMENT\s+TO",
        r"CIBC\s+BANK\s+USA", r"LASALLE", r"LOAN\s+OPERATIONS",
        r"AMOUNT\s+ENCLOSED", r"A\s+LATE\s+FEE\s+OF",
        r"YOUR\s+CHECKING\s+ACCOUNT\s+WILL\s+BE\s+CHARGED",
        r"RETAIN\s+THIS\s+STATEMENT", r"FOR\s+CUSTOMER\s+ASSISTANCE",
        r"YOUR\s+ACCOUNT\s+NUMBER", r"CALL\s+\d"
    )
    
    # Save a value into a variable named 'RIGHT_COL' so we can use it later.
    RIGHT_COL = re.compile(
        r"\s{2,}(?:ACCOUNT/NOTE\s*NUMBER|ACCOUNT\s*NUMBER|NOTE\s*NUMBER|"
        r"STATEMENT\s*DATE|PAYMENT\s*DUE\s*DATE|OFFICER|BRANCH\s*NUMBER|"
        r"CURRENT\s*BALANCE|AMOUNT\s*DUE|AMOUNT\s+ENCLOSED|A\s+LATE\s+FEE\s+OF|"
        r"PLEASE\s+REMIT|PLEASE\s+SEND\s+YOUR\s+PAYMENT|YOUR\s+CHECKING\s+ACCOUNT|"
        r"RETAIN\s+THIS\s+STATEMENT|FOR\s+CUSTOMER\s+ASSISTANCE)\b.*$",
        re.IGNORECASE
    )
    
    @classmethod
    def clean_left_column(cls, ln: str) -> str:
        # Save a value into a variable named 'ln' so we can use it later.
        ln = re.sub(cls.RIGHT_COL, "", ln)
        # Save a value into a variable named 'ln' so we can use it later.
        ln = re.sub(r"\s+\b\d{3}\b$", "", ln)
        # Send this value back to whoever called the function ('return' ends the function).
        return ln.strip()
    
    @classmethod
    def looks_like_field(cls, ln: str) -> bool:
        # Save a value into a variable named 'up' so we can use it later.
        up = ln.upper().strip()
        # Check a condition. If it's True, run the block under this 'if'.
        if ":" in up and not re.search(r"\bP\.?O\.?\s*BOX\b", up):
            # Send this value back to whoever called the function ('return' ends the function).
            return True
        # Start a loop: repeat these steps once for each item in a collection.
        for p in cls.FIELD_STARTS:
            # Check a condition. If it's True, run the block under this 'if'.
            if re.search(r"^\s*" + p + r"\b", up, re.IGNORECASE):
                # Send this value back to whoever called the function ('return' ends the function).
                return True
        # Check a condition. If it's True, run the block under this 'if'.
        if any(re.search(p, up, re.IGNORECASE) for p in REM_ZIP_PATTS):
            # Send this value back to whoever called the function ('return' ends the function).
            return True
        # Send this value back to whoever called the function ('return' ends the function).
        return False
    
    @classmethod
    # Define a function named 'find_acct_note'. Inputs: cls, block: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def find_acct_note(cls, block: str):
        # Save a value into a variable named 'm' so we can use it later.
        m = re.search(r"Account/Note\s*Number\s*([0-9]+)\s*-\s*([0-9]+)", block, re.IGNORECASE)
        # Check a condition. If it's True, run the block under this 'if'.
        if m:
            # Send this value back to whoever called the function ('return' ends the function).
            return m.group(1), m.group(2)
        # Save a value into a variable named 'm_acc' so we can use it later.
        m_acc = re.search(r"\bAccount\s*Number\s*[: ]+\s*([0-9]+)\b", block, re.IGNORECASE)
        # Save a value into a variable named 'm_note' so we can use it later.
        m_note = re.search(r"\bNote\s*Number\s*[: ]+\s*([0-9]+)\b", block, re.IGNORECASE)
        # Send this value back to whoever called the function ('return' ends the function).
        return (m_acc.group(1) if m_acc else ""), (m_note.group(1) if m_note else "")
    
    @classmethod
    # Define a function named 'split_pages'. Inputs: cls, text: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def split_pages(cls, text: str):
        # Save a value into a variable named 'ms' so we can use it later.
        ms = list(cls.HDR.finditer(text))
        # Save a value into a variable named 'pages' so we can use it later.
        pages = []
        # Start a loop: repeat these steps once for each item in a collection.
        for i, m in enumerate(ms):
            # Save a value into a variable named 'start' so we can use it later.
            start = m.end()
            # Save a value into a variable named 'end' so we can use it later.
            end = ms[i+1].start() if i+1 < len(ms) else len(text)
            pages.append({
                "code": m.group(1),
                "hdate": m.group(2),
                "page": int(m.group(3)),
                "body": text[start:end]
            })
        # Send this value back to whoever called the function ('return' ends the function).
        return pages
    
    @classmethod
    # Define a function named 'group_statements_in_order'. Inputs: cls, pages. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def group_statements_in_order(cls, pages):
        statements, current = [], None
        # Start a loop: repeat these steps once for each item in a collection.
        for p in pages:
            acct, note = cls.find_acct_note(p["body"])
            # Check a condition. If it's True, run the block under this 'if'.
            if acct and note:
                # Check a condition. If it's True, run the block under this 'if'.
                if current:
                    statements.append(current)
                # Save a value into a variable named 'current' so we can use it later.
                current = {
                    "code": p["code"],
                    "hdate": p["hdate"],
                    "acct": acct,
                    "note": note,
                    "parts": [p["body"]]
                }
            # If none of the above conditions were True, do this 'else' part.
            else:
                # Check a condition. If it's True, run the block under this 'if'.
                if current:
                    current["parts"].append(p["body"])
        # Check a condition. If it's True, run the block under this 'if'.
        if current:
            statements.append(current)
        # Start a loop: repeat these steps once for each item in a collection.
        for st in statements:
# Combining two tables (DataFrames) together based on shared columns (like a database join).
            st["content"] = "\n".join(st["parts"])
        # Send this value back to whoever called the function ('return' ends the function).
        return statements
    
    @classmethod
    # Define a function named 'extract_customer_block'. Inputs: cls, content: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def extract_customer_block(cls, content: str):
        # Save a value into a variable named 'raw_lines' so we can use it later.
        raw_lines = [ln.rstrip() for ln in content.splitlines()]
        # Save a value into a variable named 'lines' so we can use it later.
        lines = [cls.clean_left_column(ln) for ln in raw_lines]
        
        # Start a loop: repeat these steps once for each item in a collection.
        for i in range(len(lines)-2):
            # Save a value into a variable named 'name' so we can use it later.
            name = lines[i].strip()
            # Save a value into a variable named 'street' so we can use it later.
            street = lines[i+1].strip()
            # Save a value into a variable named 'csz' so we can use it later.
            csz = lines[i+2].strip()
            # Check a condition. If it's True, run the block under this 'if'.
            if not name or not street or not csz:
                continue
            # Check a condition. If it's True, run the block under this 'if'.
            if cls.looks_like_field(name) or cls.looks_like_field(street) or cls.looks_like_field(csz):
                continue
            # Check a condition. If it's True, run the block under this 'if'.
            if not (re.search(r"\d", street) or re.search(r"\bP\.?O\.?\s*BOX\b", street, re.IGNORECASE)):
                continue
            # Check a condition. If it's True, run the block under this 'if'.
            if not ZIP_RE.search(csz):
                continue
            # Check a condition. If it's True, run the block under this 'if'.
            if any(re.search(p, csz, re.IGNORECASE) for p in REM_ZIP_PATTS):
                continue
            
            # Save a value into a variable named 'names' so we can use it later.
            names = [name]
            # Save a value into a variable named 'k' so we can use it later.
            k = i-1
            # Start a loop that repeats while a condition stays True.
            while k >= 0 and len(names) < 5:
                # Save a value into a variable named 'prev' so we can use it later.
                prev = cls.clean_left_column(raw_lines[k]).strip()
                # Check a condition. If it's True, run the block under this 'if'.
                if not prev or cls.looks_like_field(prev) or ZIP_RE.search(prev):
                    break
                names.insert(0, prev)
                k -= 1
            
            # Start a loop that repeats while a condition stays True.
            while len(names) < 5:
                names.append("")
            
            # Try to enhance with spaCy
            names, street, csz = enhance_customer_extraction(names[:5], street, csz, content)
            
            # Send this value back to whoever called the function ('return' ends the function).
            return (names, street, csz)
        
        # Send this value back to whoever called the function ('return' ends the function).
        return (["","","","",""], "", "")
    
    @classmethod
    # Define a function named 'pull_header_fields'. Inputs: cls, content: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def pull_header_fields(cls, content: str):
        # Define a function named 'grab'. Inputs: pattern: str. These are values the function expects when you call it.
        # A function is a reusable mini-program you can run by its name.
        def grab(pattern: str):
            # Save a value into a variable named 'm' so we can use it later.
            m = re.search(pattern, content, re.IGNORECASE)
            # Send this value back to whoever called the function ('return' ends the function).
            return m.group(1).strip() if m else ""
        
        # Define a function named 'grab_money'. Inputs: pattern: str. These are values the function expects when you call it.
        # A function is a reusable mini-program you can run by its name.
        def grab_money(pattern: str):
            # Save a value into a variable named 'm' so we can use it later.
            m = re.search(pattern, content, re.IGNORECASE)
            # Send this value back to whoever called the function ('return' ends the function).
            return m2f(m.group(1)) if m else None
        
        # Save a value into a variable named 'stmt_date' so we can use it later.
        stmt_date = grab(r"Statement\s*Date\s*[: ]+\s*([0-9/]{8}|[A-Za-z]{3}\s+\d{2},\s+\d{4})")
        # Save a value into a variable named 'officer' so we can use it later.
        officer = grab(r"\bOfficer\s*[: ]+\s*([^\n]+)")
        # Save a value into a variable named 'branch' so we can use it later.
        branch = grab(r"\bBranch\s*Number\s*[: ]+\s*([0-9]+)")
        # Save a value into a variable named 'curr_bal' so we can use it later.
        curr_bal = grab_money(r"Current\s*Balance\s*(" + MONEY_RE + r")")
        # Save a value into a variable named 'due_date' so we can use it later.
        due_date = grab(r"Payment\s*Due\s*Date\s*[: ]+\s*([0-9/]{8}|[A-Za-z]{3}\s+\d{2},\s+\d{4})")
        # Save a value into a variable named 'amt_due' so we can use it later.
        amt_due = grab_money(r"Amount\s*Due\s*(" + MONEY_RE + r")")
        
        # Save a value into a variable named 'page_info' so we can use it later.
        page_info = re.findall(r"\bPage\s+(\d+)\s+of\s+(\d+)\b", content, re.IGNORECASE)
        # Save a value into a variable named 'total_pages' so we can use it later.
        total_pages = max((int(y) for _, y in page_info), default=None)
        
        # Save a value into a variable named 'rate_type' so we can use it later.
        rate_type = margin = ""
        # Save a value into a variable named 'mrate' so we can use it later.
        mrate = re.search(r"\*\*\s*([A-Za-z ]+)\+\s*([0-9.]+%)\s*\*\*", content)
        # Check a condition. If it's True, run the block under this 'if'.
        if mrate:
            # Save a value into a variable named 'rate_type' so we can use it later.
            rate_type = mrate.group(1).strip()
            # Save a value into a variable named 'margin' so we can use it later.
            margin = mrate.group(2).strip()
        
        # Define a function named 'grab_num'. Inputs: pattern: str. These are values the function expects when you call it.
        # A function is a reusable mini-program you can run by its name.
        def grab_num(pattern: str):
            # Save a value into a variable named 'm' so we can use it later.
            m = re.search(pattern, content, re.IGNORECASE)
            # Send this value back to whoever called the function ('return' ends the function).
            return m2f(m.group(1)) if m else None
        
        # Save a value into a variable named 'y_interest' so we can use it later.
        y_interest = grab_num(r"\bInterest\s+Paid\s+([0-9.,]+)")
        # Save a value into a variable named 'y_escrow_int' so we can use it later.
        y_escrow_int = grab_num(r"\bEscrow\s+Interest\s+Paid\s+([0-9.,]+)")
        # Save a value into a variable named 'y_unapplied' so we can use it later.
        y_unapplied = grab_num(r"\bUnapplied\s+Funds\s+([0-9.,]+)")
        # Save a value into a variable named 'y_escrow_bal' so we can use it later.
        y_escrow_bal = grab_num(r"\bEscrow\s+Balance\s+([0-9.,]+)")
        # Save a value into a variable named 'y_taxes_disb' so we can use it later.
        y_taxes_disb = grab_num(r"\bTaxes\s+Disbursed\s+([0-9.,]+)")
        
        # Send this value back to whoever called the function ('return' ends the function).
        return {
            "Statement_Date": stmt_date,
            "Officer": officer,
            "Branch_Number": branch,
            "Current_Balance": curr_bal,
            "Payment_Due_Date": due_date,
            "Amount_Due": amt_due,
            "Total_Pages": total_pages if total_pages is not None else "",
            "Rate_Type": rate_type,
            "Rate_Margin": margin,
            "YTD_Interest_Paid": y_interest,
            "YTD_Escrow_Interest_Paid": y_escrow_int,
            "YTD_Unapplied_Funds": y_unapplied,
            "YTD_Escrow_Balance": y_escrow_bal,
            "YTD_Taxes_Disbursed": y_taxes_disb,
        }
    
    @classmethod
    # Define a function named 'parse_summary_block'. Inputs: cls, content: str, acct: str, note: str, hdate: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def parse_summary_block(cls, content: str, acct: str, note: str, hdate: str):
        # Save a value into a variable named 'rows' so we can use it later.
        rows = []
        # Save a value into a variable named 'm_sum' so we can use it later.
        m_sum = re.search(r"^\s*SUMMARY\s*$", content, re.IGNORECASE | re.MULTILINE)
        # Check a condition. If it's True, run the block under this 'if'.
        if not m_sum:
            # Send this value back to whoever called the function ('return' ends the function).
            return rows
        # Save a value into a variable named 'after' so we can use it later.
        after = content[m_sum.end():]
        # Save a value into a variable named 'stop' so we can use it later.
        stop = re.search(r"^\s*YEAR-TO-DATE\s+SUMMARY|^\s*RATE\s+INFORMATION", after, re.IGNORECASE | re.MULTILINE)
        # Save a value into a variable named 'block' so we can use it later.
        block = after[:stop.start()] if stop else after
        
        # Start a loop: repeat these steps once for each item in a collection.
        for ln in block.splitlines():
            # Save a value into a variable named 's' so we can use it later.
            s = ln.rstrip()
            # Check a condition. If it's True, run the block under this 'if'.
            if not s.strip():
                continue
            # Save a value into a variable named 'm' so we can use it later.
            m = re.match(
                r"^\s*([0-9]{5}/[A-Z])\s+([0-9,]+\.\d{2})\s+([0-9.]+)\s+([0-9/]{8}|00/00/00)\s+(.*?)\s+([0-9,$][0-9,]*\.\d{2})\s*$",
                s
            )
            # Check a condition. If it's True, run the block under this 'if'.
            if m:
                rows.append({
                    "Account_Number": acct,
                    "Note_Number": note,
                    "Header_Date": hdate,
                    "Note_Category": m.group(1),
                    "Current_Balance": m2f(m.group(2)),
                    "Interest_Rate": float(m.group(3)),
                    "Maturity_Date": m.group(4),
                    "Description": m.group(5).strip(),
                    "Amount": m2f(m.group(6)),
                })
                continue
            # Save a value into a variable named 'm2' so we can use it later.
            m2 = re.match(
# This is a long line. It likely chains several steps together to do work in one go.
                r"^\s*(Interest\s+To\s+\d{2}/\d{2}/\d{2}|Total\s+Due\s+On\s+\d{2}/\d{2}/\d{2}|Principal\s+Payment)\s+([0-9,$][0-9,]*\.\d{2})\s*$",
                s, re.IGNORECASE
            )
            # Check a condition. If it's True, run the block under this 'if'.
            if m2:
                rows.append({
                    "Account_Number": acct,
                    "Note_Number": note,
                    "Header_Date": hdate,
                    "Note_Category": "",
                    "Current_Balance": None,
                    "Interest_Rate": None,
                    "Maturity_Date": "",
                    "Description": m2.group(1).strip(),
                    "Amount": m2f(m2.group(2)),
                })
        # Send this value back to whoever called the function ('return' ends the function).
        return rows
    
    @classmethod
    # Define a function named 'parse_history_block'. Inputs: cls, content: str, acct: str, note: str, hdate: str, cust_name_1: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def parse_history_block(cls, content: str, acct: str, note: str, hdate: str, cust_name_1: str):
        # Save a value into a variable named 'rows' so we can use it later.
        rows = []
        # Save a value into a variable named 'm_hist' so we can use it later.
        m_hist = re.search(r"^\s*LOAN\s+HISTORY\s*$", content, re.IGNORECASE | re.MULTILINE)
        # Check a condition. If it's True, run the block under this 'if'.
        if not m_hist:
            # Send this value back to whoever called the function ('return' ends the function).
            return rows
        # Save a value into a variable named 'after' so we can use it later.
        after = content[m_hist.end():]
        # Start a loop: repeat these steps once for each item in a collection.
        for ln in after.splitlines():
            # Save a value into a variable named 's' so we can use it later.
            s = ln.rstrip()
            # Check a condition. If it's True, run the block under this 'if'.
            if not s.strip():
                continue
            # Save a value into a variable named 'm' so we can use it later.
            m = re.match(
# This is a long line. It likely chains several steps together to do work in one go.
                r"^\s*([0-9]{5})\s+([0-9/]{8})\s+([0-9/]{8})\s+(.+?)\s+([0-9,]+\.\d{2})\s+([0-9,]+\.\d{2})\s+([0-9,]+\.\d{2})\s+([0-9,]+\.\d{2})\s+([0-9,]+\.\d{2})\s*$",
                s
            )
            # Check a condition. If it's True, run the block under this 'if'.
            if m:
                # Save a value into a variable named 'desc' so we can use it later.
                desc = m.group(4).strip()
                rows.append({
                    "Account_Number": acct,
                    "Note_Number": note,
                    "Header_Date": hdate,
                    "Customer_Name_1": cust_name_1,
                    "Hist_Note": m.group(1),
                    "Posting_Date": m.group(2),
                    "Effective_Date": m.group(3),
                    "Transaction_Description": desc,
                    "Transaction_Category": classify_transaction_with_spacy(desc),
                    "Principal": m2f(m.group(5)),
                    "Interest": m2f(m.group(6)),
                    "LateFees_Others": m2f(m.group(7)),
                    "Escrow": m2f(m.group(8)),
                    "Insurance": m2f(m.group(9)),
                })
            # Check a condition. If it's True, run the block under this 'if'.
            if cls.HDR.search(s):
                break
        # Send this value back to whoever called the function ('return' ends the function).
        return rows
    
    @classmethod
    # Define a function named 'process'. Inputs: cls, text: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def process(cls, text: str):
        # Save a value into a variable named 'pages' so we can use it later.
        pages = cls.split_pages(text)
        # Save a value into a variable named 'statements' so we can use it later.
        statements = cls.group_statements_in_order(pages)
        
        hdr_rows, sum_rows, hist_rows = [], [], []
        
        # Start a loop: repeat these steps once for each item in a collection.
        for st in statements:
            acct, note, hdate, content = st["acct"], st["note"], st["hdate"], st["content"]
            
            names, street, csz = cls.extract_customer_block(content)
            n1, n2, n3, n4, n5 = (names + ["","","","",""])[:5]
            
            # Save a value into a variable named 'hdr' so we can use it later.
            hdr = cls.pull_header_fields(content)
            
            sum_rows.extend(cls.parse_summary_block(content, acct, note, hdate))
            hist_rows.extend(cls.parse_history_block(content, acct, note, hdate, n1))
            
            hdr_rows.append({
                "Notice_Type": "LOAN STATEMENT",
                "Notice_Code": "R-06090-002",
                "Header_Date": hdate,
                "Account_Number": acct,
                "Note_Number": note,
                "Total_Pages": hdr["Total_Pages"],
                "Statement_Date": hdr["Statement_Date"],
                "Officer": hdr["Officer"],
                "Branch_Number": hdr["Branch_Number"],
                "Customer_Name_1": n1,
                "Customer_Name_2": n2,
                "Customer_Name_3": n3,
                "Customer_Name_4": n4,
                "Customer_Name_5": n5,
                "Address_Street": street,
                "Address_CityStateZip": csz,
                "Current_Balance": hdr["Current_Balance"],
                "Payment_Due_Date": hdr["Payment_Due_Date"],
                "Amount_Due": hdr["Amount_Due"],
                "Rate_Type": hdr["Rate_Type"],
                "Rate_Margin": hdr["Rate_Margin"],
                "YTD_Interest_Paid": hdr["YTD_Interest_Paid"],
                "YTD_Escrow_Interest_Paid": hdr["YTD_Escrow_Interest_Paid"],
                "YTD_Unapplied_Funds": hdr["YTD_Unapplied_Funds"],
                "YTD_Escrow_Balance": hdr["YTD_Escrow_Balance"],
                "YTD_Taxes_Disbursed": hdr["YTD_Taxes_Disbursed"],
            })
        
        # Send this value back to whoever called the function ('return' ends the function).
        return hdr_rows, sum_rows, hist_rows

# ============= REV CREDIT STATEMENT PROCESSING =============
# Create a Class named 'RevCreditProcessor'. A Class is a blueprint for objects (bundles of data + functions).
# We'll make objects from this Class to organize related behavior and state.
class RevCreditProcessor:
    # Save a value into a variable named 'HDR' so we can use it later.
    HDR = re.compile(
        r"^\s*\d{3}-\d{7}\s+CIBC BANK USA\s+REV\. CREDIT STATEMENT\s+"
        r"(R-06088-001)\s+(\d{2}-\d{2}-\d{2})\s+PAGE\s+(\d+)\s*$",
        re.MULTILINE
    )
    
    # Save a value into a variable named 'DROP_PATTS' so we can use it later.
    DROP_PATTS = [
        r"PLEASE\s+SEND\s+YOUR\s+PAYMENT\s+TO",
        r"\bCIBC\s+BANK\s+USA\b",
        r"LASALLE", r"LOAN\s+OPERATIONS",
        r"\bAMOUNT\s+ENCLOSED\b",
        r"\bA\s+late\s+fee\s+of\b",
        r"\bYOUR\s+CHECKING\s+ACCOUNT\s+WILL\s+BE\s+CHARGED\b",
        r"\bRETAIN\s+THIS\s+STATEMENT\b",
        r"\bFOR\s+CUSTOMER\s+ASSISTANCE\b",
        r"^\s*Page\s+\d+\s+of\s+\d+\s*$",
    ]
    
    @classmethod
    def is_drop(cls, ln: str) -> bool:
        # Save a value into a variable named 'up' so we can use it later.
        up = ln.upper()
        # Check a condition. If it's True, run the block under this 'if'.
        if any(re.search(p, up, re.IGNORECASE) for p in cls.DROP_PATTS):
            # Send this value back to whoever called the function ('return' ends the function).
            return True
        # Check a condition. If it's True, run the block under this 'if'.
        if any(re.search(p, up, re.IGNORECASE) for p in REM_ZIP_PATTS):
            # Send this value back to whoever called the function ('return' ends the function).
            return True
        # Send this value back to whoever called the function ('return' ends the function).
        return False
    
    @classmethod
    def strip_inline_noise(cls, s: str) -> str:
        # Save a value into a variable named 's' so we can use it later.
        s = re.sub(r"\s{2,}AMOUNT\s+ENCLOSED.*$", "", s, flags=re.IGNORECASE)
        # Save a value into a variable named 's' so we can use it later.
        s = re.sub(r"\s{2,}A\s+late\s+fee\s+of.*$", "", s, flags=re.IGNORECASE)
        # Send this value back to whoever called the function ('return' ends the function).
        return s.strip()
    
    @classmethod
    # Define a function named 'find_acct_note'. Inputs: cls, block: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def find_acct_note(cls, block: str):
        # Save a value into a variable named 'm' so we can use it later.
        m = re.search(r"Account/Note\s*Number\s*([0-9]+)\s*-\s*([0-9]+)", block, re.IGNORECASE)
        # Check a condition. If it's True, run the block under this 'if'.
        if m:
            # Send this value back to whoever called the function ('return' ends the function).
            return m.group(1), m.group(2)
        # Save a value into a variable named 'm' so we can use it later.
        m = re.search(r"\bAccount\s*Number\s*:\s*([0-9]+)\s+([0-9]+)", block, re.IGNORECASE)
        # Check a condition. If it's True, run the block under this 'if'.
        if m:
            # Send this value back to whoever called the function ('return' ends the function).
            return m.group(1), m.group(2)
        # Save a value into a variable named 'm' so we can use it later.
        m = re.search(r"\bAccount\s*Number\s*:\s*([0-9 ]+)", block, re.IGNORECASE)
        # Check a condition. If it's True, run the block under this 'if'.
        if m:
            # Save a value into a variable named 'p' so we can use it later.
            p = m.group(1).split()
            # Check a condition. If it's True, run the block under this 'if'.
            if len(p) == 2:
                # Send this value back to whoever called the function ('return' ends the function).
                return p[0], p[1]
        # Send this value back to whoever called the function ('return' ends the function).
        return "", ""
    
    @classmethod
    # Define a function named 'split_pages'. Inputs: cls, text: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def split_pages(cls, text: str):
        # Save a value into a variable named 'ms' so we can use it later.
        ms = list(cls.HDR.finditer(text))
        # Save a value into a variable named 'pages' so we can use it later.
        pages = []
        # Start a loop: repeat these steps once for each item in a collection.
        for i, m in enumerate(ms):
            # Save a value into a variable named 'start' so we can use it later.
            start = m.end()
            # Save a value into a variable named 'end' so we can use it later.
            end = ms[i+1].start() if i+1 < len(ms) else len(text)
            pages.append({
                "code": m.group(1),
                "hdate": m.group(2),
                "page": int(m.group(3)),
                "body": text[start:end]
            })
        # Send this value back to whoever called the function ('return' ends the function).
        return pages
    
    @classmethod
    # Define a function named 'group_statements'. Inputs: cls, pages. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def group_statements(cls, pages):
        # Save a value into a variable named 'groups' so we can use it later.
        groups = {}
        # Start a loop: repeat these steps once for each item in a collection.
        for p in pages:
            acct, note = cls.find_acct_note(p["body"])
            # Save a value into a variable named 'key' so we can use it later.
            key = (acct, note, p["hdate"])
            groups.setdefault(key, {"code": "R-06088-001", "hdate": p["hdate"], "parts": []})
            groups[key]["parts"].append((p["page"], p["body"]))
        # Start a loop: repeat these steps once for each item in a collection.
        for k, g in groups.items():
            g["parts"].sort(key=lambda x: x[0])
# Combining two tables (DataFrames) together based on shared columns (like a database join).
            g["content"] = "\n".join(b for _, b in g["parts"])
        # Send this value back to whoever called the function ('return' ends the function).
        return groups
    
    @classmethod
    # Define a function named 'extract_customer_from_first_page'. Inputs: cls, content: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def extract_customer_from_first_page(cls, content: str):
        # Save a value into a variable named 'm_acc' so we can use it later.
        m_acc = re.search(r"\bAccount\s*Number\s*:", content, re.IGNORECASE)
        # Check a condition. If it's True, run the block under this 'if'.
        if not m_acc:
            # Send this value back to whoever called the function ('return' ends the function).
            return (["","","","",""], "", "")
        # Save a value into a variable named 'window' so we can use it later.
        window = content[:m_acc.start()]
        
        # Save a value into a variable named 'lines' so we can use it later.
        lines = [ln.rstrip() for ln in window.splitlines()]
        # Save a value into a variable named 'lines' so we can use it later.
        lines = lines[-50:] if len(lines) > 50 else lines
        
        # Save a value into a variable named 'cleaned' so we can use it later.
        cleaned = []
        # Start a loop: repeat these steps once for each item in a collection.
        for ln in lines:
            # Save a value into a variable named 'ln2' so we can use it later.
            ln2 = cls.strip_inline_noise(ln)
            # Check a condition. If it's True, run the block under this 'if'.
            if not ln2.strip():
                cleaned.append("")
                continue
            # Check a condition. If it's True, run the block under this 'if'.
            if cls.is_drop(ln2):
                cleaned.append("")
                continue
            cleaned.append(ln2)
        
        # Save a value into a variable named 'zi' so we can use it later.
        zi = -1
        # Start a loop: repeat these steps once for each item in a collection.
        for i in range(len(cleaned)-1, -1, -1):
            # Save a value into a variable named 'ln' so we can use it later.
            ln = cleaned[i]
            # Check a condition. If it's True, run the block under this 'if'.
            if ZIP_RE.search(ln):
                # Check a condition. If it's True, run the block under this 'if'.
                if any(re.search(p, ln, re.IGNORECASE) for p in REM_ZIP_PATTS):
                    continue
                # Save a value into a variable named 'zi' so we can use it later.
                zi = i
                break
        # Check a condition. If it's True, run the block under this 'if'.
        if zi <= 0:
            # Send this value back to whoever called the function ('return' ends the function).
            return (["","","","",""], "", "")
        
        street_line = cleaned[zi-1].strip() if zi-1 >= 0 else ""
        # Check a condition. If it's True, run the block under this 'if'.
        if not (re.search(r"\d", street_line) or re.search(r"\bP\.?O\.?\s*BOX\b", street_line, re.IGNORECASE)):
            # Save a value into a variable named 'j' so we can use it later.
            j = zi-1
            # Save a value into a variable named 'street_line' so we can use it later.
            street_line = ""
            # Start a loop that repeats while a condition stays True.
            while j >= 0:
                # Save a value into a variable named 'cand' so we can use it later.
                cand = cleaned[j].strip()
                # Check a condition. If it's True, run the block under this 'if'.
                if re.search(r"\d", cand) or re.search(r"\bP\.?O\.?\s*BOX\b", cand, re.IGNORECASE):
                    # Save a value into a variable named 'street_line' so we can use it later.
                    street_line = cand
                    break
                j -= 1
            # Check a condition. If it's True, run the block under this 'if'.
            if not street_line:
                # Send this value back to whoever called the function ('return' ends the function).
                return (["","","","",""], "", "")
        
        # Save a value into a variable named 'csz' so we can use it later.
        csz = cleaned[zi].strip()
        
        # Save a value into a variable named 'names' so we can use it later.
        names = []
        # Save a value into a variable named 'k' so we can use it later.
        k = zi-1
        # Start a loop that repeats while a condition stays True.
        while k >= 0 and cleaned[k].strip() != street_line:
            k -= 1
        k -= 1
        # Start a loop that repeats while a condition stays True.
        while k >= 0 and len(names) < 5:
            # Save a value into a variable named 'raw' so we can use it later.
            raw = cleaned[k].strip()
            # Check a condition. If it's True, run the block under this 'if'.
            if not raw:
                break
            # Check a condition. If it's True, run the block under this 'if'.
            if ZIP_RE.search(raw):
                k -= 1
                continue
            # Save a value into a variable named 'raw' so we can use it later.
            raw = re.sub(r"\s+\b\d{3}\b$", "", raw).strip()
            # Check a condition. If it's True, run the block under this 'if'.
            if not raw or cls.is_drop(raw):
                break
            names.insert(0, raw)
            k -= 1
        
        # Start a loop that repeats while a condition stays True.
        while len(names) < 5:
            names.append("")
        
        # Try to enhance with spaCy
        names, street_line, csz = enhance_customer_extraction(names[:5], street_line, csz, content)
        
        # Send this value back to whoever called the function ('return' ends the function).
        return (names[:5], street_line, csz)
    
    @classmethod
    # Define a function named 'pull_top_fields'. Inputs: cls, content: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def pull_top_fields(cls, content: str):
        # Save a value into a variable named 'stmt' so we can use it later.
        stmt = (re.search(r"Statement\s*Date\s+([A-Za-z]{3}\s+\d{2},\s+\d{4})", content, re.IGNORECASE) or
# Using Regular Expressions (regex) to find or clean patterns in text (like dates, amounts, IDs).
                re.search(r"Statement\s*Date\s*:\s*(\d{2}/\d{2}/\d{2})", content, re.IGNORECASE))
        # Save a value into a variable named 'due' so we can use it later.
        due = (re.search(r"Payment\s*Due\s*Date\s+([A-Za-z]{3}\s+\d{2},\s+\d{4})", content, re.IGNORECASE) or
# Using Regular Expressions (regex) to find or clean patterns in text (like dates, amounts, IDs).
               re.search(r"Payment\s*Due\s*Date\s*:\s*(\d{2}/\d{2}/\d{2})", content, re.IGNORECASE))
        # Save a value into a variable named 'stmt_date' so we can use it later.
        stmt_date = stmt.group(1) if stmt else ""
        # Save a value into a variable named 'due_date' so we can use it later.
        due_date = due.group(1) if due else ""
        
        # Save a value into a variable named 'new_bal' so we can use it later.
        new_bal = m2f((re.search(r"New\s*Statement\s*Balance\s*\$([0-9,]+\.\d{2})", content, re.IGNORECASE) or [None,None])[1])
        # Save a value into a variable named 'fees_unpd' so we can use it later.
        fees_unpd = m2f((re.search(r"Fees\s*Charged/Unpaid\s*\$([0-9,]+\.\d{2})", content, re.IGNORECASE) or [None,None])[1])
        # Save a value into a variable named 'past_due' so we can use it later.
        past_due = m2f((re.search(r"Past\s*Due\s*Amount\s*\$([0-9,]+\.\d{2})", content, re.IGNORECASE) or [None,None])[1])
        # Save a value into a variable named 'min_pay' so we can use it later.
        min_pay = m2f((re.search(r"Minimum\s*Payment\s*Due\s*\$([0-9,]+\.\d{2})", content, re.IGNORECASE) or [None,None])[1])
        
        # Define a function named 'grab'. Inputs: pattern: str. These are values the function expects when you call it.
        # A function is a reusable mini-program you can run by its name.
        def grab(pattern: str):
            # Save a value into a variable named 'm' so we can use it later.
            m = re.search(pattern, content, re.IGNORECASE)
            # Send this value back to whoever called the function ('return' ends the function).
            return m2f(m.group(1)) if m else None
        
        # Save a value into a variable named 'pfees' so we can use it later.
        pfees = grab(r"TOTAL\s+FEES\s+FOR\s+THIS\s+PERIOD\s*(" + MONEY_RE + r")")
        # Save a value into a variable named 'pint' so we can use it later.
        pint = grab(r"TOTAL\s+INTEREST\s+FOR\s+THIS\s+PERIOD\s*(" + MONEY_RE + r")")
        # Save a value into a variable named 'yfees' so we can use it later.
        yfees = grab(r"Total\s+fees\s+charged\s+in\s+\d{4}\s*(" + MONEY_RE + r")")
        # Save a value into a variable named 'yint' so we can use it later.
        yint = grab(r"Total\s+interest\s+charged\s+in\s+\d{4}\s*(" + MONEY_RE + r")")
        # Save a value into a variable named 'tip' so we can use it later.
        tip = grab(r"Total\s+Interest\s+Charges\s+Paid\s+In\s+\d{4}:\s*(" + MONEY_RE + r")")
        
        # Save a value into a variable named 'prev' so we can use it later.
        prev=adv=pay=intr=other=curr=None
        # Save a value into a variable named 'mh' so we can use it later.
        mh = re.search(r"Previous\s+Statement.*?Equals\s+Current\s+Statement\s+Balance", content, re.IGNORECASE|re.DOTALL)
        # Check a condition. If it's True, run the block under this 'if'.
        if mh:
            # Save a value into a variable named 'tail' so we can use it later.
            tail = "\n".join(content[mh.end():].splitlines()[:4])
            # Save a value into a variable named 'nums' so we can use it later.
            nums = re.findall(MONEY_RE, tail)
            # Check a condition. If it's True, run the block under this 'if'.
            if len(nums) >= 6:
                prev,adv,pay,intr,other,curr = [m2f(x) for x in nums[:6]]
        
        # Save a value into a variable named 'ac' so we can use it later.
        ac=fcu=cad=pda=mpd=None
        # Save a value into a variable named 'm5' so we can use it later.
        m5 = re.search(r"Available\s+Credit.*?Minimum\s+Payment\s+Due\s*\n([^\n]+)", content, re.IGNORECASE|re.DOTALL)
        # Check a condition. If it's True, run the block under this 'if'.
        if m5:
            # Save a value into a variable named 'amts' so we can use it later.
            amts = re.findall(MONEY_RE, m5.group(1))
            # Check a condition. If it's True, run the block under this 'if'.
            if len(amts) >= 5:
                ac,fcu,cad,pda,mpd = [m2f(x) for x in amts[:5]]
        
        # Send this value back to whoever called the function ('return' ends the function).
        return (stmt_date,due_date,new_bal,fees_unpd,past_due,min_pay,
                ac,fcu,cad,pda,mpd,
                pfees,pint,yfees,yint,tip,
                prev,adv,pay,intr,other,curr)
    
    @classmethod
    # Define a function named 'parse_transactions'. Inputs: cls, content: str, acct: str, note: str, hdate: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def parse_transactions(cls, content: str, acct: str, note: str, hdate: str):
        # Save a value into a variable named 'mstart' so we can use it later.
        mstart = re.search(r"^\s*\|\s*Transactions\s*\|\s*$", content, re.IGNORECASE | re.MULTILINE)
        # Check a condition. If it's True, run the block under this 'if'.
        if not mstart:
            # Save a value into a variable named 'mstart' so we can use it later.
            mstart = re.search(r"\bTransactions\b", content, re.IGNORECASE)
        # Check a condition. If it's True, run the block under this 'if'.
        if not mstart:
            # Send this value back to whoever called the function ('return' ends the function).
            return []
        # Save a value into a variable named 'start_idx' so we can use it later.
        start_idx = mstart.end()
        
        # Save a value into a variable named 'mend' so we can use it later.
        mend = re.search(r"TOTAL\s+FEES\s+FOR\s+THIS\s+PERIOD", content[start_idx:], re.IGNORECASE)
        # Check a condition. If it's True, run the block under this 'if'.
        if mend:
            # Save a value into a variable named 'end_idx' so we can use it later.
            end_idx = start_idx + mend.start()
        # If none of the above conditions were True, do this 'else' part.
        else:
            # Save a value into a variable named 'mfees' so we can use it later.
            mfees = re.search(r"^\s*\|\s*Fees\s*\|\s*$", content[start_idx:], re.IGNORECASE | re.MULTILINE)
            # Save a value into a variable named 'end_idx' so we can use it later.
            end_idx = start_idx + (mfees.start() if mfees else len(content) - start_idx)
        
        # Save a value into a variable named 'block' so we can use it later.
        block = content[start_idx:end_idx]
        # Save a value into a variable named 'lines' so we can use it later.
        lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
        # Save a value into a variable named 'txns' so we can use it later.
        txns = []
        # Save a value into a variable named 'last' so we can use it later.
        last = None
        
        # Start a loop: repeat these steps once for each item in a collection.
        for raw in lines:
            # Save a value into a variable named 's' so we can use it later.
            s = raw
            # Save a value into a variable named 'm' so we can use it later.
            m = re.match(r"^\s*(\d{2}/\d{2})?\s*(\d{2}/\d{2})?\s*(.*?)\s*("
                        + MONEY_RE + r"(?:\s+" + MONEY_RE + r"){0,2})?\s*$", s)
            # Check a condition. If it's True, run the block under this 'if'.
            if m:
                # Save a value into a variable named 'd1' so we can use it later.
                d1 = (m.group(1) or "").strip()
                # Save a value into a variable named 'd2' so we can use it later.
                d2 = (m.group(2) or "").strip()
                # Save a value into a variable named 'desc' so we can use it later.
                desc = (m.group(3) or "").strip()
                # Save a value into a variable named 'amts' so we can use it later.
                amts = re.findall(MONEY_RE, m.group(4) or "")
                # Save a value into a variable named 'adv' so we can use it later.
                adv=pay=bal=None
                # Check a condition. If it's True, run the block under this 'if'.
                if len(amts) == 3:
                    adv, pay, bal = [m2f(x) for x in amts]
                # If the earlier 'if' was False, check another condition here with 'elif'.
                elif len(amts) == 2:
                    # Check a condition. If it's True, run the block under this 'if'.
                    if re.search(r"payment|credit", desc, re.IGNORECASE):
                        pay, bal = [m2f(x) for x in amts]
                    # If none of the above conditions were True, do this 'else' part.
                    else:
                        adv, bal = [m2f(x) for x in amts]
                # If the earlier 'if' was False, check another condition here with 'elif'.
                elif len(amts) == 1:
                    # Save a value into a variable named 'bal' so we can use it later.
                    bal = m2f(amts[0])
                
                # Save a value into a variable named 'row' so we can use it later.
                row = {
                    "Account_Number": acct,
                    "Note_Number": note,
                    "Header_Date": hdate,
                    "Trans_Date": d1,
                    "Post_Date": d2,
                    "Description": desc,
                    "Transaction_Category": classify_transaction_with_spacy(desc),
                    "Advances_Debits_or_IntCharge": adv,
                    "Payments_Credits": pay,
                    "Balance_Subject_to_IntRate": bal
                }
                txns.append(row)
                # Save a value into a variable named 'last' so we can use it later.
                last = row
            # If none of the above conditions were True, do this 'else' part.
            else:
                # Save a value into a variable named 'cont' so we can use it later.
                cont = s.strip()
                # Check a condition. If it's True, run the block under this 'if'.
                if cont and last:
                    last["Description"] = (last["Description"] + " " + cont).strip()
                    # Re-classify with updated description
                    last["Transaction_Category"] = classify_transaction_with_spacy(last["Description"])
                # If the earlier 'if' was False, check another condition here with 'elif'.
                elif cont:
                    txns.append({
                        "Account_Number": acct,
                        "Note_Number": note,
                        "Header_Date": hdate,
                        "Trans_Date": "",
                        "Post_Date": "",
                        "Description": cont,
                        "Transaction_Category": classify_transaction_with_spacy(cont),
                        "Advances_Debits_or_IntCharge": None,
                        "Payments_Credits": None,
                        "Balance_Subject_to_IntRate": None
                    })
                    # Save a value into a variable named 'last' so we can use it later.
                    last = txns[-1]
        # Send this value back to whoever called the function ('return' ends the function).
        return txns
    
    @classmethod
    # Define a function named 'process'. Inputs: cls, text: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def process(cls, text: str):
        # Save a value into a variable named 'pages' so we can use it later.
        pages = cls.split_pages(text)
        # Save a value into a variable named 'groups' so we can use it later.
        groups = cls.group_statements(pages)
        
        header_rows, txn_rows = [], []
        
        # Start a loop: repeat these steps once for each item in a collection.
        for (acct, note, hdate), g in groups.items():
            # Check a condition. If it's True, run the block under this 'if'.
            if not acct and not note:
                continue
            # Save a value into a variable named 'content' so we can use it later.
            content = g["content"]
            
            names, street, csz = cls.extract_customer_from_first_page(content)
            n1, n2, n3, n4, n5 = (names + ["", "", "", "", ""])[:5]
            
            (stmt_date, due_date, new_bal, fees_unpd, past_due, min_pay,
             ac, fcu, cad, pda, mpd,
             pfees, pint, yfees, yint, tip,
             prev, adv, pay, intr, other, curr) = cls.pull_top_fields(content)
            
            # Save a value into a variable named 'txns' so we can use it later.
            txns = cls.parse_transactions(content, acct, note, hdate)
            txn_rows.extend(txns)
            
            header_rows.append({
                "Notice_Type": "REV. CREDIT STATEMENT",
                "Notice_Code": "R-06088-001",
                "Header_Date": hdate,
                "Account_Number": acct,
                "Note_Number": note,
                "Statement_Date": stmt_date,
                "Payment_Due_Date": due_date,
                "Customer_Name_1": n1,
                "Customer_Name_2": n2,
                "Customer_Name_3": n3,
                "Customer_Name_4": n4,
                "Customer_Name_5": n5,
                "Address_Street": street,
                "Address_CityStateZip": csz,
                "New_Statement_Balance": new_bal,
                "Fees_Charged_Unpaid_top": fees_unpd,
                "Past_Due_Amount_top": past_due,
                "Minimum_Payment_Due_top": min_pay,
                "Available_Credit": ac,
                "Fees_Charged_Unpaid": fcu,
                "Current_Amount_Due": cad,
                "Past_Due_Amount": pda,
                "Minimum_Payment_Due": mpd,
                "Period_Fees_Total": pfees,
                "Period_Interest_Total": pint,
                "YTD_Fees": yfees,
                "YTD_Interest": yint,
                "Total_Interest_Charges_Paid_YTD": tip,
                "Previous_Statement_Balance": prev,
                "Advances_Debits": adv,
                "Payments_Credits": pay,
                "Interest_Charge": intr,
                "Other_Charges": other,
                "Current_Statement_Balance": curr,
            })
        
        # Send this value back to whoever called the function ('return' ends the function).
        return header_rows, txn_rows

# ============= ADVICE OF RATE CHANGE PROCESSING =============
# Create a Class named 'AdviceOfRateChangeProcessor'. A Class is a blueprint for objects (bundles of data + functions).
# We'll make objects from this Class to organize related behavior and state.
class AdviceOfRateChangeProcessor:
    # Save a value into a variable named 'HDR' so we can use it later.
    HDR = re.compile(
        r"^\s*\d{3}-\d{7}\s+CIBC BANK USA\s+ADVICE OF RATE CHANGE\s+(R-\d{5}-\d{3})\s+(\d{2}-\d{2}-\d{2})\s+PAGE\s+(\d+)\s*$",
        re.MULTILINE
    )
    
    @staticmethod
    def clean_tail(s: str) -> str:
        # Save a value into a variable named 's' so we can use it later.
        s = re.sub(r"\s+Account\s*Number\s*:.*$", "", s, flags=re.IGNORECASE)
        # Save a value into a variable named 's' so we can use it later.
        s = re.sub(r"\s+Note\s*Number\s*:.*$", "", s, flags=re.IGNORECASE)
        # Send this value back to whoever called the function ('return' ends the function).
        return s.strip()
    
    @classmethod
    # Define a function named 'extract_names_address'. Inputs: cls, page_body: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def extract_names_address(cls, page_body: str):
        # Save a value into a variable named 'lines' so we can use it later.
        lines = [ln.rstrip() for ln in page_body.splitlines()]
        # Save a value into a variable named 'zi' so we can use it later.
        zi = next((i for i, ln in enumerate(lines) if ZIP_RE.search(ln)), -1)
        # Check a condition. If it's True, run the block under this 'if'.
        if zi <= 0:
            # Send this value back to whoever called the function ('return' ends the function).
            return [], "", ""
        # Save a value into a variable named 'street' so we can use it later.
        street = cls.clean_tail(lines[zi - 1].strip())
        # Save a value into a variable named 'csz' so we can use it later.
        csz = cls.clean_tail(lines[zi].strip())
        # Save a value into a variable named 'start' so we can use it later.
        start = max(0, (zi - 1) - 7)
        # Save a value into a variable named 'candidates' so we can use it later.
        candidates = [cls.clean_tail(ln) for ln in lines[start:zi-1] if ln.strip()]
        # Save a value into a variable named 'noise' so we can use it later.
        noise = ("CIBC BANK USA", "ADVICE OF RATE CHANGE", "PAGE")
        # Save a value into a variable named 'names' so we can use it later.
        names = [ln for ln in candidates if not any(n in ln.upper() for n in noise)][-5:]
        
        # Try to enhance with spaCy
        names, street, csz = enhance_customer_extraction(names, street, csz, page_body)
        
        # Send this value back to whoever called the function ('return' ends the function).
        return names, street, csz
    
    @classmethod
    # Define a function named 'process'. Inputs: cls, text: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def process(cls, text: str):
        # Save a value into a variable named 'records' so we can use it later.
        records = []
        # Save a value into a variable named 'matches' so we can use it later.
        matches = list(cls.HDR.finditer(text))
        
        # Start a loop: repeat these steps once for each item in a collection.
        for i, m in enumerate(matches):
            code, hdr_date, page_no = m.group(1), m.group(2), int(m.group(3))
            # Check a condition. If it's True, run the block under this 'if'.
            if code != "R-06061-001":
                continue
            
            # Save a value into a variable named 'start' so we can use it later.
            start = m.end()
            # Save a value into a variable named 'end' so we can use it later.
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            # Save a value into a variable named 'body' so we can use it later.
            body = text[start:end]
            
            names, street, csz = cls.extract_names_address(body)
            
            # Save a value into a variable named 'acct_m' so we can use it later.
            acct_m = re.search(r"Account\s*Number\s*:\s*([0-9 ]+)", body, re.IGNORECASE)
            # Save a value into a variable named 'note_m' so we can use it later.
            note_m = re.search(r"Note\s*Number\s*:\s*([0-9 ]+)", body, re.IGNORECASE)
            # Save a value into a variable named 'acct_num' so we can use it later.
            acct_num = acct_m.group(1).replace(" ","") if acct_m else ""
            # Save a value into a variable named 'note_num' so we can use it later.
            note_num = note_m.group(1).replace(" ","") if note_m else ""
            
            # Save a value into a variable named 'rate' so we can use it later.
            rate = re.search(r"from\s+([0-9.]+)%\s+to\s+([0-9.]+)%\s+on\s+(\d{2}-\d{2}-\d{2})", body, re.IGNORECASE)
            # Save a value into a variable named 'prev_rate' so we can use it later.
            prev_rate = float(rate.group(1)) if rate else None
            # Save a value into a variable named 'curr_rate' so we can use it later.
            curr_rate = float(rate.group(2)) if rate else None
            # Save a value into a variable named 'rate_date' so we can use it later.
            rate_date = rate.group(3) if rate else ""
            
            # Save a value into a variable named 'rec' so we can use it later.
            rec = {
                "Notice_Type": "ADVICE OF RATE CHANGE",
                "Notice_Code": code,
                "Header_Date": hdr_date,
                "Page": page_no,
                "Customer_Name_1": names[0] if len(names)>0 else "",
                "Customer_Name_2": names[1] if len(names)>1 else "",
                "Customer_Name_3": names[2] if len(names)>2 else "",
                "Customer_Name_4": names[3] if len(names)>3 else "",
                "Customer_Name_5": names[4] if len(names)>4 else "",
                "Address_Street": street,
                "Address_CityStateZip": csz,
                "Account_Number": acct_num,
                "Note_Number": note_num,
                "Previous_Rate": prev_rate,
                "Current_Rate": curr_rate,
                "Date_of_RateChange": rate_date
            }
            records.append(rec)
        
        # Send this value back to whoever called the function ('return' ends the function).
        return records

# ============= PAYOFF NOTICE PROCESSING =============
# Create a Class named 'PayoffNoticeProcessor'. A Class is a blueprint for objects (bundles of data + functions).
# We'll make objects from this Class to organize related behavior and state.
class PayoffNoticeProcessor:
    # Save a value into a variable named 'HDR' so we can use it later.
    HDR = re.compile(
        r"^\s*\d{3}-\d{7}\s+CIBC BANK USA\s+PAYOFF NOTICE TO PAYEE\s+"
        r"(R-07362-001)\s+(\d{2}-\d{2}-\d{2})\s+PAGE\s+(\d+)\s*$",
        re.MULTILINE
    )
    
    @staticmethod
    def clean_tail(s: str) -> str:
        # Save a value into a variable named 's' so we can use it later.
        s = re.sub(r"\s+Ref\s*No\..*$", "", s, flags=re.IGNORECASE)
        # Save a value into a variable named 's' so we can use it later.
        s = re.sub(r"\s+Account\s*:.*$", "", s, flags=re.IGNORECASE)
        # Save a value into a variable named 's' so we can use it later.
        s = re.sub(r"\s+Note\s*:.*$", "", s, flags=re.IGNORECASE)
        # Save a value into a variable named 's' so we can use it later.
        s = re.sub(r"\s+Issue\s*Date\s*:.*$", "", s, flags=re.IGNORECASE)
        # Save a value into a variable named 's' so we can use it later.
        s = re.sub(r"\s+Acct\s*Name\s*:.*$", "", s, flags=re.IGNORECASE)
        # Send this value back to whoever called the function ('return' ends the function).
        return s.strip()
    
    @classmethod
    # Define a function named 'extract_payee_address'. Inputs: cls, page_body: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def extract_payee_address(cls, page_body: str):
        # Save a value into a variable named 'lines' so we can use it later.
        lines = [ln.rstrip() for ln in page_body.splitlines() if ln.strip()]
        # Start a loop: repeat these steps once for each item in a collection.
        for i, ln in enumerate(lines):
            # Check a condition. If it's True, run the block under this 'if'.
            if ZIP_RE.search(ln):
                # Save a value into a variable named 'csz' so we can use it later.
                csz = cls.clean_tail(ln.strip())
                street = cls.clean_tail(lines[i-1].strip()) if i-1 >= 0 else ""
                name = cls.clean_tail(lines[i-2].strip()) if i-2 >= 0 else ""
                
                # Try spaCy enhancement for county name
                # Check a condition. If it's True, run the block under this 'if'.
                if HAVE_SPACY and name:
                    # Save a value into a variable named 'spacy_names' so we can use it later.
                    spacy_names = extract_names_with_spacy(page_body[:500], max_names=1)
                    # Check a condition. If it's True, run the block under this 'if'.
                    if spacy_names and "COUNTY" in name.upper():
                        # Keep the county designation but maybe improve name extraction
                        pass
                
                # Send this value back to whoever called the function ('return' ends the function).
                return name, (street + ("\n" if street and csz else "") + csz).strip()
        # Send this value back to whoever called the function ('return' ends the function).
        return "", ""
    
    @staticmethod
    def get_between(body: str, start_pat: str, end_pat: str) -> str:
        # Save a value into a variable named 's' so we can use it later.
        s = re.search(start_pat, body, re.IGNORECASE | re.DOTALL)
        # Check a condition. If it's True, run the block under this 'if'.
        if not s:
            # Send this value back to whoever called the function ('return' ends the function).
            return ""
        # Save a value into a variable named 'start_idx' so we can use it later.
        start_idx = s.start()
        # Save a value into a variable named 'e' so we can use it later.
        e = re.search(end_pat, body[start_idx:], re.IGNORECASE | re.DOTALL)
        # Check a condition. If it's True, run the block under this 'if'.
        if not e:
            # Save a value into a variable named 'chunk' so we can use it later.
            chunk = body[start_idx:]
        # If none of the above conditions were True, do this 'else' part.
        else:
            # Save a value into a variable named 'chunk' so we can use it later.
            chunk = body[start_idx:start_idx + e.start()]
        # Save a value into a variable named 'lines' so we can use it later.
        lines = [ln.rstrip() for ln in chunk.splitlines()]
        # Send this value back to whoever called the function ('return' ends the function).
        return "\n".join([ln for ln in lines if ln.strip()]).strip()
    
    @staticmethod
    # Define a function named 'first_group'. Inputs: rx, body, flags=0, default="". These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def first_group(rx, body, flags=0, default=""):
        # Save a value into a variable named 'm' so we can use it later.
        m = re.search(rx, body, flags)
        # Send this value back to whoever called the function ('return' ends the function).
        return m.group(1).strip() if m else default
    
    @classmethod
    # Define a function named 'process'. Inputs: cls, text: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def process(cls, text: str):
        # Save a value into a variable named 'records' so we can use it later.
        records = []
        # Save a value into a variable named 'matches' so we can use it later.
        matches = list(cls.HDR.finditer(text))
        
        # Start a loop: repeat these steps once for each item in a collection.
        for i, m in enumerate(matches):
            code, header_date, page_no = m.group(1), m.group(2), int(m.group(3))
            # Check a condition. If it's True, run the block under this 'if'.
            if code != "R-07362-001":
                continue
            
            # Save a value into a variable named 'start' so we can use it later.
            start = m.end()
            # Save a value into a variable named 'end' so we can use it later.
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            # Save a value into a variable named 'body' so we can use it later.
            body = text[start:end]
            
            # Save a value into a variable named 'notice_date' so we can use it later.
            notice_date = cls.first_group(r"\bDate\s*:\s*([0-9/]{8})", body)
            county_name, county_addr = cls.extract_payee_address(body)
            
            # Save a value into a variable named 'notice_comment' so we can use it later.
            notice_comment = cls.get_between(
                body,
                r"The loan shown below.+?(?=\n)",
                r"\n\s*Ref\s*No\.\s"
            )
            
            # Save a value into a variable named 'ref_no' so we can use it later.
            ref_no = cls.first_group(r"Ref\s*No\.\s+([^\n]+)", body, re.IGNORECASE)
            # Save a value into a variable named 'account' so we can use it later.
            account = cls.first_group(r"\bAccount\s*:\s*([0-9 ]+)", body, re.IGNORECASE).replace(" ","")
            # Save a value into a variable named 'note' so we can use it later.
            note = cls.first_group(r"\bNote\s*:\s*([0-9 ]+)", body, re.IGNORECASE).replace(" ","")
            # Save a value into a variable named 'issue_date' so we can use it later.
            issue_date = cls.first_group(r"Issue\s*Date\s*:\s*([0-9/]{8})", body, re.IGNORECASE)
            # Save a value into a variable named 'acct_name' so we can use it later.
            acct_name = cls.first_group(r"Acct\s*Name\s*:\s*(.+)", body, re.IGNORECASE)
            
            # Save a value into a variable named 'prop_m' so we can use it later.
            prop_m = re.search(r"Property\s*At\s*:\s*\n\s*(.+)\n\s*(.+)", body, re.IGNORECASE)
            # Save a value into a variable named 'property_at' so we can use it later.
            property_at = ""
            # Check a condition. If it's True, run the block under this 'if'.
            if prop_m:
                # Save a value into a variable named 'line1' so we can use it later.
                line1 = prop_m.group(1).strip()
                # Save a value into a variable named 'line2' so we can use it later.
                line2 = prop_m.group(2).strip()
                # Save a value into a variable named 'property_at' so we can use it later.
                property_at = (line1 + "\n" + line2).strip()
            
            records.append({
                "Notice_Type": "PAYOFF NOTICE TO PAYEE",
                "Notice_Code": code,
                "Header_Date": header_date,
                "Page": page_no,
                "Notice_Date": notice_date,
                "County_Name": county_name,
                "County_Address": county_addr,
                "Notice_Comment": notice_comment,
                "Ref_No": ref_no,
                "Account": account,
                "Note": note,
                "Issue_Date": issue_date,
                "Acct_Name": acct_name,
                "Property_At": property_at
            })
        
        # Send this value back to whoever called the function ('return' ends the function).
        return records

# ============= PAST DUE NOTICE PROCESSING =============
# Create a Class named 'PastDueNoticeProcessor'. A Class is a blueprint for objects (bundles of data + functions).
# We'll make objects from this Class to organize related behavior and state.
class PastDueNoticeProcessor:
    # Save a value into a variable named 'HDR' so we can use it later.
    HDR = re.compile(
        r"^\s*\d{3}-\d{7}\s+CIBC BANK USA\s+PAST DUE NOTICE\s+"
        r"(R-06385-\d{3})\s+(\d{2}-\d{2}-\d{2})\s+PAGE\s+(\d+)\s*$",
        re.MULTILINE
    )
    
    # Save a value into a variable named 'NOISE' so we can use it later.
    NOISE = ("CIBC BANK USA","PAST DUE NOTICE","PAST DUE LOAN NOTICE","PAGE")
    
    @staticmethod
    def clean_tail(s: str) -> str:
        # Save a value into a variable named 's' so we can use it later.
        s = re.sub(r"\s+Notice\s*Date\s*:.*$", "", s, flags=re.IGNORECASE)
        # Save a value into a variable named 's' so we can use it later.
        s = re.sub(r"\s+Account\s*Number\s*:.*$", "", s, flags=re.IGNORECASE)
        # Save a value into a variable named 's' so we can use it later.
        s = re.sub(r"\s+Note\s*Number\s*:.*$", "", s, flags=re.IGNORECASE)
        # Save a value into a variable named 's' so we can use it later.
        s = re.sub(r"\s+Officer\s*:.*$", "", s, flags=re.IGNORECASE)
        # Save a value into a variable named 's' so we can use it later.
        s = re.sub(r"\s+Branch\s*:.*$", "", s, flags=re.IGNORECASE)
        # Send this value back to whoever called the function ('return' ends the function).
        return s.strip()
    
    @classmethod
    # Define a function named 'extract_names_address'. Inputs: cls, page_body: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def extract_names_address(cls, page_body: str):
        # Save a value into a variable named 'lines' so we can use it later.
        lines = [ln.rstrip() for ln in page_body.splitlines()]
        # Save a value into a variable named 'zi' so we can use it later.
        zi = next((i for i, ln in enumerate(lines) if ZIP_RE.search(ln)), -1)
        # Check a condition. If it's True, run the block under this 'if'.
        if zi <= 0:
            # Send this value back to whoever called the function ('return' ends the function).
            return [], "", ""
        # Save a value into a variable named 'street' so we can use it later.
        street = cls.clean_tail(lines[zi - 1].strip())
        # Save a value into a variable named 'csz' so we can use it later.
        csz = cls.clean_tail(lines[zi].strip())
        # Save a value into a variable named 'start' so we can use it later.
        start = max(0, (zi - 1) - 7)
        # Save a value into a variable named 'candidates' so we can use it later.
        candidates = [cls.clean_tail(ln) for ln in lines[start:zi-1] if ln.strip()]
        # Save a value into a variable named 'names' so we can use it later.
        names = [ln for ln in candidates if not any(n in ln.upper() for n in cls.NOISE)][-5:]
        
        # Try to enhance with spaCy
        names, street, csz = enhance_customer_extraction(names, street, csz, page_body)
        
        # Send this value back to whoever called the function ('return' ends the function).
        return names, street, csz
    
    @classmethod
    # Define a function named 'process'. Inputs: cls, text: str. These are values the function expects when you call it.
    # A function is a reusable mini-program you can run by its name.
    def process(cls, text: str):
        # Save a value into a variable named 'records' so we can use it later.
        records = []
        # Save a value into a variable named 'matches' so we can use it later.
        matches = list(cls.HDR.finditer(text))
        
        # Start a loop: repeat these steps once for each item in a collection.
        for i, m in enumerate(matches):
            code, hdr_date, page_no = m.group(1), m.group(2), int(m.group(3))
            # Save a value into a variable named 'start' so we can use it later.
            start = m.end()
            # Save a value into a variable named 'end' so we can use it later.
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            # Save a value into a variable named 'body' so we can use it later.
            body = text[start:end]
            
            names, street, csz = cls.extract_names_address(body)
            
            # Save a value into a variable named 'notice_date' so we can use it later.
            notice_date = re.search(r"Notice\s*Date\s*:\s*(\d{2}/\d{2}/\d{2})", body, re.IGNORECASE)
            # Save a value into a variable named 'acct_m' so we can use it later.
            acct_m = re.search(r"Account\s*Number\s*:\s*([0-9 ]+)", body, re.IGNORECASE)
            # Save a value into a variable named 'note_m' so we can use it later.
            note_m = re.search(r"Note\s*Number\s*:\s*([0-9 ]+)", body, re.IGNORECASE)
            # Save a value into a variable named 'officer_m' so we can use it later.
            officer_m = re.search(r"Officer\s*:\s*([A-Z0-9 &]+)", body)
            # Save a value into a variable named 'branch_m' so we can use it later.
            branch_m = re.search(r"Branch\s*:\s*([A-Z0-9 &]+)", body)
            
            # Save a value into a variable named 'loan_type_m' so we can use it later.
            loan_type_m = re.search(
                r"^\s*(Revolving Credit Loan|Installment Loan|Commercial Loan)\s*$",
                body, re.IGNORECASE | re.MULTILINE
            )
            # Save a value into a variable named 'due_date_m' so we can use it later.
            due_date_m = re.search(
                r"Your\s+loan\s+payment\s+was\s+due\s+(\d{2}/\d{2}/\d{2})",
                body, re.IGNORECASE
            )
            
            # Save a value into a variable named 'pr' so we can use it later.
            pr = re.search(r"Principal\s*:\s*\$?([0-9,]+\.\d{2})", body, re.IGNORECASE)
            # Save a value into a variable named 'it' so we can use it later.
            it = re.search(r"Interest\s*:\s*\$?([0-9,]+\.\d{2})", body, re.IGNORECASE)
            # Save a value into a variable named 'lf' so we can use it later.
            lf = re.search(r"Late\s*Fees\s*:\s*\$?([0-9,]+\.\d{2})", body, re.IGNORECASE)
            # Save a value into a variable named 'td' so we can use it later.
            td = re.search(r"Total\s*Due\s*:\s*\$?([0-9,]+\.\d{2})", body, re.IGNORECASE)
            
            # Save a value into a variable named 'rec' so we can use it later.
            rec = {
                "Notice_Type": "PAST DUE NOTICE",
                "Notice_Code": code,
                "Header_Date": hdr_date,
                "Page": page_no,
                "Customer_Name_1": names[0] if len(names)>0 else "",
                "Customer_Name_2": names[1] if len(names)>1 else "",
                "Customer_Name_3": names[2] if len(names)>2 else "",
                "Customer_Name_4": names[3] if len(names)>3 else "",
                "Customer_Name_5": names[4] if len(names)>4 else "",
                "Address_Street": street,
                "Address_CityStateZip": csz,
                "Notice_Date": notice_date.group(1) if notice_date else "",
                "Account_Number": (acct_m.group(1).replace(" ","") if acct_m else ""),
                "Note_Number": (note_m.group(1).replace(" ","") if note_m else ""),
                "Officer": (officer_m.group(1).strip() if officer_m else ""),
                "Branch": (branch_m.group(1).strip() if branch_m else ""),
                "Loan_Type": (loan_type_m.group(1).strip() if loan_type_m else ""),
                "Due_Date": (due_date_m.group(1) if due_date_m else ""),
                "Principal": m2f(pr.group(1)) if pr else None,
                "Interest": m2f(it.group(1)) if it else None,
                "Late_Fees": m2f(lf.group(1)) if lf else None,
                "Total_Due": m2f(td.group(1)) if td else None,
            }
            records.append(rec)
        
        # Send this value back to whoever called the function ('return' ends the function).
        return records

# ============= OUTPUT UTILITIES =============
# Define a function named 'write_tsv'. Inputs: filepath, rows, columns. These are values the function expects when you call it.
# A function is a reusable mini-program you can run by its name.
def write_tsv(filepath, rows, columns):
    """Write rows to TSV file."""
    # Open or manage a resource safely using 'with' (auto-closes files, etc.).
    with filepath.open("w", newline="", encoding="utf-8") as f:
        # Save a value into a variable named 'w' so we can use it later.
        w = csv.DictWriter(f, fieldnames=columns, delimiter="\t")
        w.writeheader()
        # Start a loop: repeat these steps once for each item in a collection.
        for r in rows:
            # Start a loop: repeat these steps once for each item in a collection.
            for c in columns:
                r.setdefault(c, "")
            w.writerow({k: ("" if r[k] is None else r[k]) for k in columns})

# Define a function named 'write_xlsx'. Inputs: filepath, rows, columns, sheet_name. These are values the function expects when you call it.
# A function is a reusable mini-program you can run by its name.
def write_xlsx(filepath, rows, columns, sheet_name):
    """Write rows to Excel file."""
    # Check a condition. If it's True, run the block under this 'if'.
    if not HAVE_XLSX:
        # Send this value back to whoever called the function ('return' ends the function).
        return
    # Save a value into a variable named 'wb' so we can use it later.
    wb = Workbook()
    # Save a value into a variable named 'ws' so we can use it later.
    ws = wb.active
    ws.title = sheet_name
    ws.append(columns)
    # Start a loop: repeat these steps once for each item in a collection.
    for r in rows:
        ws.append([r.get(c, "") if r.get(c, "") is not None else "" for c in columns])
    wb.save(filepath)

# ============= MAIN PROCESSING =============
# Define a function named 'main'. This function takes no inputs.
# A function is a reusable mini-program you can run by its name.
def main():
    print("=" * 60)
    print("COMBINED CIBC BANK STATEMENT PARSER")
    print("WITH OPTIONAL SPACY ENHANCEMENT")
    print("=" * 60)
    
    # Read input file once
    print(f"\nReading input file: {INPUT_PATH}")
    # Save a value into a variable named 'text' so we can use it later.
    text = read_text(INPUT_PATH)
    print(f"Total size: {len(text):,} characters")
    
    # Process Loan Statements
    print("\n" + "-" * 40)
    print("Processing LOAN STATEMENTS...")
    loan_hdr, loan_sum, loan_hist = LoanStatementProcessor.process(text)
    
    # Check a condition. If it's True, run the block under this 'if'.
    if loan_hdr:
        # Define columns
        # Save a value into a variable named 'loan_hdr_cols' so we can use it later.
        loan_hdr_cols = [
            "Notice_Type","Notice_Code","Header_Date","Account_Number","Note_Number",
            "Total_Pages","Statement_Date","Officer","Branch_Number",
            "Customer_Name_1","Customer_Name_2","Customer_Name_3","Customer_Name_4","Customer_Name_5",
            "Address_Street","Address_CityStateZip",
            "Current_Balance","Payment_Due_Date","Amount_Due",
            "Rate_Type","Rate_Margin",
            "YTD_Interest_Paid","YTD_Escrow_Interest_Paid","YTD_Unapplied_Funds",
            "YTD_Escrow_Balance","YTD_Taxes_Disbursed"
        ]
        # Save a value into a variable named 'loan_sum_cols' so we can use it later.
        loan_sum_cols = [
            "Account_Number","Note_Number","Header_Date",
            "Note_Category","Current_Balance","Interest_Rate","Maturity_Date","Description","Amount"
        ]
        # Save a value into a variable named 'loan_hist_cols' so we can use it later.
        loan_hist_cols = [
            "Account_Number","Note_Number","Header_Date","Customer_Name_1",
            "Hist_Note","Posting_Date","Effective_Date","Transaction_Description",
            "Transaction_Category",  # Added if spaCy is available
            "Principal","Interest","LateFees_Others","Escrow","Insurance"
        ]
        
        # Write outputs
        write_tsv(OUT_LOAN_HDR_TSV, loan_hdr, loan_hdr_cols)
        write_tsv(OUT_LOAN_SUM_TSV, loan_sum, loan_sum_cols)
        write_tsv(OUT_LOAN_HIST_TSV, loan_hist, loan_hist_cols)
        
        # Check a condition. If it's True, run the block under this 'if'.
        if HAVE_XLSX:
            write_xlsx(OUT_LOAN_HDR_XLSX, loan_hdr, loan_hdr_cols, "loan_header")
            write_xlsx(OUT_LOAN_SUM_XLSX, loan_sum, loan_sum_cols, "summary")
            write_xlsx(OUT_LOAN_HIST_XLSX, loan_hist, loan_hist_cols, "loan_history")
        
        print(f"  Found {len(loan_hdr)} statements")
        print(f"  Wrote {len(loan_sum)} summary rows")
        print(f"  Wrote {len(loan_hist)} history rows")
        # Check a condition. If it's True, run the block under this 'if'.
        if HAVE_SPACY:
            print("  Enhanced with spaCy NER and classification")
    # If none of the above conditions were True, do this 'else' part.
    else:
        print("  No loan statements found")
    
    # Process Rev Credit Statements
    print("\n" + "-" * 40)
    print("Processing REV. CREDIT STATEMENTS...")
    rev_hdr, rev_txn = RevCreditProcessor.process(text)
    
    # Check a condition. If it's True, run the block under this 'if'.
    if rev_hdr:
        # Define columns
        # Save a value into a variable named 'rev_hdr_cols' so we can use it later.
        rev_hdr_cols = [
            "Notice_Type","Notice_Code","Header_Date","Account_Number","Note_Number",
            "Statement_Date","Payment_Due_Date",
            "Customer_Name_1","Customer_Name_2","Customer_Name_3","Customer_Name_4","Customer_Name_5",
            "Address_Street","Address_CityStateZip",
            "New_Statement_Balance","Fees_Charged_Unpaid_top","Past_Due_Amount_top","Minimum_Payment_Due_top",
            "Available_Credit","Fees_Charged_Unpaid","Current_Amount_Due","Past_Due_Amount","Minimum_Payment_Due",
            "Period_Fees_Total","Period_Interest_Total","YTD_Fees","YTD_Interest","Total_Interest_Charges_Paid_YTD",
            "Previous_Statement_Balance","Advances_Debits","Payments_Credits","Interest_Charge",
            "Other_Charges","Current_Statement_Balance"
        ]
        # Save a value into a variable named 'rev_txn_cols' so we can use it later.
        rev_txn_cols = [
            "Account_Number","Note_Number","Header_Date","Trans_Date","Post_Date",
            "Description","Transaction_Category",  # Added if spaCy is available
            "Advances_Debits_or_IntCharge","Payments_Credits","Balance_Subject_to_IntRate"
        ]
        
        # Write outputs
        write_tsv(OUT_REV_HDR_TSV, rev_hdr, rev_hdr_cols)
        write_tsv(OUT_REV_TXN_TSV, rev_txn, rev_txn_cols)
        
        # Check a condition. If it's True, run the block under this 'if'.
        if HAVE_XLSX:
            write_xlsx(OUT_REV_HDR_XLSX, rev_hdr, rev_hdr_cols, "rev_stmt")
            write_xlsx(OUT_REV_TXN_XLSX, rev_txn, rev_txn_cols, "transactions")
        
        print(f"  Found {len(rev_hdr)} statements")
        print(f"  Wrote {len(rev_txn)} transactions")
        # Check a condition. If it's True, run the block under this 'if'.
        if HAVE_SPACY:
            print("  Transaction categories added via spaCy")
    # If none of the above conditions were True, do this 'else' part.
    else:
        print("  No rev credit statements found")
    
    # Process Advice of Rate Change
    print("\n" + "-" * 40)
    print("Processing ADVICE OF RATE CHANGE...")
    # Save a value into a variable named 'advice_records' so we can use it later.
    advice_records = AdviceOfRateChangeProcessor.process(text)
    
    # Check a condition. If it's True, run the block under this 'if'.
    if advice_records:
        # Save a value into a variable named 'advice_cols' so we can use it later.
        advice_cols = [
            "Notice_Type","Notice_Code","Header_Date","Page",
            "Customer_Name_1","Customer_Name_2","Customer_Name_3","Customer_Name_4","Customer_Name_5",
            "Address_Street","Address_CityStateZip",
            "Account_Number","Note_Number",
            "Previous_Rate","Current_Rate","Date_of_RateChange"
        ]
        
        write_tsv(OUT_ADVICE_TSV, advice_records, advice_cols)
        # Check a condition. If it's True, run the block under this 'if'.
        if HAVE_XLSX:
            write_xlsx(OUT_ADVICE_XLSX, advice_records, advice_cols, "advice_only")
        
        print(f"  Found {len(advice_records)} rate change notices")
    # If none of the above conditions were True, do this 'else' part.
    else:
        print("  No advice of rate change notices found")
    
    # Process Payoff Notices
    print("\n" + "-" * 40)
    print("Processing PAYOFF NOTICES...")
    # Save a value into a variable named 'payoff_records' so we can use it later.
    payoff_records = PayoffNoticeProcessor.process(text)
    
    # Check a condition. If it's True, run the block under this 'if'.
    if payoff_records:
        # Save a value into a variable named 'payoff_cols' so we can use it later.
        payoff_cols = [
            "Notice_Type","Notice_Code","Header_Date","Page","Notice_Date",
            "County_Name","County_Address","Notice_Comment",
            "Ref_No","Account","Note","Issue_Date","Acct_Name","Property_At"
        ]
        
        write_tsv(OUT_PAYOFF_TSV, payoff_records, payoff_cols)
        # Check a condition. If it's True, run the block under this 'if'.
        if HAVE_XLSX:
            write_xlsx(OUT_PAYOFF_XLSX, payoff_records, payoff_cols, "payoff_only")
        
        print(f"  Found {len(payoff_records)} payoff notices")
    # If none of the above conditions were True, do this 'else' part.
    else:
        print("  No payoff notices found")
    
    # Process Past Due Notices
    print("\n" + "-" * 40)
    print("Processing PAST DUE NOTICES...")
    # Save a value into a variable named 'past_due_records' so we can use it later.
    past_due_records = PastDueNoticeProcessor.process(text)
    
    # Check a condition. If it's True, run the block under this 'if'.
    if past_due_records:
        # Save a value into a variable named 'past_due_cols' so we can use it later.
        past_due_cols = [
            "Notice_Type","Notice_Code","Header_Date","Page",
            "Customer_Name_1","Customer_Name_2","Customer_Name_3","Customer_Name_4","Customer_Name_5",
            "Address_Street","Address_CityStateZip",
            "Notice_Date","Account_Number","Note_Number","Officer","Branch",
            "Loan_Type","Due_Date","Principal","Interest","Late_Fees","Total_Due",
        ]
        
        write_tsv(OUT_PAST_DUE_TSV, past_due_records, past_due_cols)
        # Check a condition. If it's True, run the block under this 'if'.
        if HAVE_XLSX:
            write_xlsx(OUT_PAST_DUE_XLSX, past_due_records, past_due_cols, "past_due_only")
        
        print(f"  Found {len(past_due_records)} past due notices")
    # If none of the above conditions were True, do this 'else' part.
    else:
        print("  No past due notices found")
    
    # Summary
    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE!")
    print("=" * 60)
    print("\nOutput files created in:", OUTPUT_DIR)
    print("\nSummary:")
    print(f"  - Loan Statements: {len(loan_hdr)} statements")
    print(f"  - Rev Credit Statements: {len(rev_hdr)} statements")
    print(f"  - Advice of Rate Change: {len(advice_records)} notices")
    print(f"  - Payoff Notices: {len(payoff_records)} notices")
    print(f"  - Past Due Notices: {len(past_due_records)} notices")
    
    # Check a condition. If it's True, run the block under this 'if'.
    if HAVE_SPACY:
        print("\n✓ spaCy enhancements applied:")
        print("  - Enhanced name extraction with NER")
        print("  - Transaction categorization")
    # If none of the above conditions were True, do this 'else' part.
    else:
        print("\nTo enable ML enhancements, install spaCy:")
        print("  pip install spacy")
        print("  python -m spacy download en_core_web_sm")
    
    # Check a condition. If it's True, run the block under this 'if'.
    if not HAVE_XLSX:
        print("\nNote: Excel files were skipped (install openpyxl for Excel output)")

# Run the script when executed
# Check a condition. If it's True, run the block under this 'if'.
if __name__ == "__main__":
    main()
# ============================================================================
# TIPS & TROUBLESHOOTING
# - If a PDF doesn't parse, try converting it to text or checking if it's scanned (image-only).
# - If you get a 'ModuleNotFoundError', install the missing package with 'pip install <name>'.
# - If spaCy complains about a model, run: python -m spacy download en_core_web_sm
# - If file paths fail on Windows, use raw strings like r"C:\folder\file.pdf".
# - Print variables (with 'print(variable)') to see what's inside while learning.
# ============================================================================
