# -*- coding: utf-8 -*-
"""
data_obfuscator.py - Data Obfuscation Script
Reads from production tables, masks sensitive data, writes to Masked schema

Deterministic pseudonymization is used for IDs/SSNs/accounts so the same
input always maps to the same fake output while preserving separators and
optionally the last 4 digits (to keep joins/queryability across tables).
"""

import random
import string
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
from faker import Faker
import re
import os
import hmac

from db_utils import (
    get_db_connection,
    fetch_all_from_table,
    insert_to_table,
    create_schema_if_not_exists,
    copy_table_structure,
    clear_table,
    table_exists
)

# ---------- Deterministic numeric pseudonymization ----------

# Secret used for deterministic pseudonymization (set per env/host)
# Example (PowerShell):  setx SHIELD_PSEUDO_KEY "your-long-random-secret"
PSEUDO_KEY = os.getenv("SHIELD_PSEUDO_KEY", "CHANGE-ME-IN-ENV")

SSN_LIKE = re.compile(r"\b\d{3}[ -]?\d{2}[ -]?\d{4}\b")

def _pseudo_digit_stream(key: bytes, seed: str, n: int) -> list[int]:
    """
    Deterministic stream of digits [0-9] of length n using HMAC-SHA256(key, seed|i).
    """
    out, i = [], 0
    while len(out) < n:
        block = hmac.new(key, f"{seed}|{i}".encode("utf-8"), hashlib.sha256).digest()
        out.extend(b % 10 for b in block)
        i += 1
    return out[:n]

def deterministic_numeric_like(value: str, preserve_last: int = 0, key: str = PSEUDO_KEY) -> str:
    """
    Map the digits in `value` to new digits deterministically, preserving separators and optionally
    the last N digits. Works for '563 73 6000', '563-73-6000', '563736000', etc.
    """
    if value is None:
        return value
    s = str(value)
    digits = re.sub(r"\D", "", s)
    if not digits:
        return s
    keep = digits[-preserve_last:] if 0 < preserve_last < len(digits) else ""
    repl_len = len(digits) - len(keep)
    stream = _pseudo_digit_stream(key.encode("utf-8"), digits, repl_len)
    new_digits = "".join(str(d) for d in stream) + keep

    # Reinsert into original format (keep original separators/spacing)
    result, idx = [], 0
    for ch in s:
        if ch.isdigit():
            result.append(new_digits[idx])
            idx += 1
        else:
            result.append(ch)
    return "".join(result)

# Initialize Faker for realistic fake data
fake = Faker()

# ============= CONFIGURATION =============
# Define which fields to obfuscate and how
OBFUSCATION_RULES = {
    # Customer names - replace with fake names
    'name_fields': [
        'Customer_Name_1', 'Customer_Name_2', 'Customer_Name_3',
        'Customer_Name_4', 'Customer_Name_5', 'County_Name', 'Acct_Name'
    ],

    # Addresses - replace with fake addresses
    'address_fields': [
        'Address_Street', 'Address_CityStateZip', 'County_Address', 'Property_At'
    ],

    # Account/Note numbers / identifiers — deterministic pseudonymization (keep joins)
    'account_fields': ['Account_Number', 'Account'],
    'note_fields':    ['Note_Number', 'Note', 'Hist_Note'],
    'id_fields':      ['Customer_ID', 'Customer_Number'],
    'ssn_fields':     ['SSN', 'Social_Security_Number', 'Customer_SSN'],

    # Officer names - replace with fake names
    'officer_fields': ['Officer'],

    # Branch numbers - randomize
    'branch_fields': ['Branch_Number', 'Branch'],

    # Reference numbers - hash
    'reference_fields': ['Ref_No'],

    # Monetary amounts - apply random variance
    'money_fields': [
        'Current_Balance', 'Amount_Due', 'Amount', 'Principal', 'Interest',
        'LateFees_Others', 'Escrow', 'Insurance', 'YTD_Interest_Paid',
        'YTD_Escrow_Interest_Paid', 'YTD_Unapplied_Funds', 'YTD_Escrow_Balance',
        'YTD_Taxes_Disbursed', 'New_Statement_Balance', 'Fees_Charged_Unpaid_top',
        'Past_Due_Amount_top', 'Minimum_Payment_Due_top', 'Available_Credit',
        'Fees_Charged_Unpaid', 'Current_Amount_Due', 'Past_Due_Amount',
        'Minimum_Payment_Due', 'Period_Fees_Total', 'Period_Interest_Total',
        'YTD_Fees', 'YTD_Interest', 'Total_Interest_Charges_Paid_YTD',
        'Previous_Statement_Balance', 'Advances_Debits', 'Payments_Credits',
        'Interest_Charge', 'Other_Charges', 'Current_Statement_Balance',
        'Advances_Debits_or_IntCharge', 'Balance_Subject_to_IntRate',
        'Late_Fees', 'Total_Due'
    ],

    # Dates - shift by random days
    'date_fields': [
        'Statement_Date', 'Payment_Due_Date', 'Header_Date', 'Posting_Date',
        'Effective_Date', 'Maturity_Date', 'Trans_Date', 'Post_Date',
        'Notice_Date', 'Issue_Date', 'Due_Date', 'Date_of_RateChange'
    ],

    # Rates - apply small variance
    'rate_fields': ['Interest_Rate', 'Previous_Rate', 'Current_Rate'],

    # Descriptions - generalize
    'description_fields': ['Description', 'Transaction_Description', 'Notice_Comment']
}

# ============= OBFUSCATION FUNCTIONS =============

class DataObfuscator:
    def __init__(self, seed: Optional[int] = None):
        """Initialize obfuscator with optional seed for reproducibility."""
        if seed:
            random.seed(seed)
            Faker.seed(seed)
        self.fake = Faker()
        self.name_cache: Dict[str, str] = {}  # Cache: same name -> same replacement

    def obfuscate_name(self, name: Optional[str]) -> Optional[str]:
        """Replace a real name with a fake one, consistently."""
        if not name or str(name).strip() == "":
            return name

        name_s = str(name)
        if name_s in self.name_cache:
            return self.name_cache[name_s]

        # Generate new fake name
        if "COUNTY" in name_s.upper():
            fake_name = self.fake.city() + " COUNTY"
        elif "&" in name_s or "BANK" in name_s.upper():
            fake_name = self.fake.company()
        else:
            fake_name = self.fake.name()

        self.name_cache[name_s] = fake_name
        return fake_name

    def obfuscate_address(self, address: Optional[str]) -> Optional[str]:
        """Replace address with fake address."""
        if not address or str(address).strip() == "":
            return address

        addr = str(address)
        # Multi-line or complex address
        if any(x in addr.upper() for x in ['APT', 'SUITE', '#', '\n']):
            return self.fake.address()
        # City, State Zip format
        elif any(x in addr.upper() for x in [', IL', ', CA', ', NY']):
            return f"{self.fake.city()}, {self.fake.state_abbr()} {self.fake.zipcode()}"
        # Just street
        else:
            return self.fake.street_address()

    def obfuscate_account(self, account: Optional[str]) -> Optional[str]:
        """
        Deterministically pseudonymize numeric identifiers while preserving separators
        and keeping the last 4 digits (to aid support workflows).
        """
        if account is None:
            return account
        s = str(account).strip()
        if s == "":
            return s
        return deterministic_numeric_like(s, preserve_last=4)

    def obfuscate_officer(self, officer: Optional[str]) -> Optional[str]:
        """Replace officer name/code."""
        if not officer or str(officer).strip() == "":
            return officer

        s = str(officer)
        # If it looks like a code (e.g., "ABC123"), generate similar
        if any(c.isdigit() for c in s):
            return ''.join(random.choices(string.ascii_uppercase, k=3)) + \
                   ''.join(random.choices(string.digits, k=3))
        else:
            return self.fake.name()

    def obfuscate_branch(self, branch: Optional[str]) -> Optional[str]:
        """Randomize branch number/code."""
        if branch is None or str(branch).strip() == "":
            return branch

        s = str(branch)
        if s.isdigit():
            return ''.join(random.choices(string.digits, k=len(s)))
        else:
            return f"BR{random.randint(100, 999)}"

    def obfuscate_reference(self, ref: Optional[str]) -> Optional[str]:
        """Hash reference numbers for consistency (8 hex chars)."""
        if not ref or str(ref).strip() == "":
            return ref
        return hashlib.md5(str(ref).encode()).hexdigest()[:8].upper()

    def obfuscate_money(self, amount: Optional[float]) -> Optional[float]:
        """Apply random variance to monetary amounts (+/- 10%)."""
        if amount is None or amount == 0:
            return amount

        # Convert Decimal to float if needed
        if isinstance(amount, Decimal):
            amount = float(amount)

        variance = random.uniform(0.9, 1.1)
        return round(float(amount) * variance, 2)

    def obfuscate_date(self, date_str: Optional[str]) -> Optional[str]:
        """Shift dates by random number of days."""
        if not date_str or str(date_str).strip() == "" or str(date_str) == "00/00/00":
            return date_str

        s = str(date_str)
        for fmt in ("%m/%d/%y", "%m/%d/%Y", "%Y-%m-%d", "%b %d, %Y"):
            try:
                date_obj = datetime.strptime(s, fmt)
                shift_days = random.randint(-30, 30)
                new_date = date_obj + timedelta(days=shift_days)
                return new_date.strftime(fmt)
            except ValueError:
                continue
        return s

    def obfuscate_rate(self, rate: Optional[float]) -> Optional[float]:
        """Apply small variance to interest rates (+/- 0.5%)."""
        if rate is None:
            return rate
        variance = random.uniform(-0.5, 0.5)
        return round(float(rate) + variance, 2)

    def obfuscate_description(self, desc: Optional[str]) -> Optional[str]:
        """Generalize transaction descriptions."""
        if not desc or str(desc).strip() == "":
            return desc

        desc_upper = str(desc).upper()
        if any(x in desc_upper for x in ['PAYMENT', 'PMT', 'PAID']):
            return "Payment Transaction"
        elif any(x in desc_upper for x in ['FEE', 'CHARGE', 'PENALTY']):
            return "Fee Assessment"
        elif any(x in desc_upper for x in ['INTEREST', 'INT', 'FINANCE']):
            return "Interest Charge"
        elif any(x in desc_upper for x in ['TRANSFER', 'XFER', 'WIRE']):
            return "Fund Transfer"
        elif any(x in desc_upper for x in ['ADVANCE', 'WITHDRAWAL', 'DRAW']):
            return "Cash Advance"
        elif any(x in desc_upper for x in ['DEPOSIT', 'CREDIT']):
            return "Credit Transaction"
        else:
            return "General Transaction"

    def obfuscate_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Obfuscate a single row based on field rules."""
        obfuscated = row.copy()

        for field in list(row.keys()):
            if field in OBFUSCATION_RULES['name_fields']:
                obfuscated[field] = self.obfuscate_name(row[field])
            elif field in OBFUSCATION_RULES['address_fields']:
                obfuscated[field] = self.obfuscate_address(row[field])
            elif (field in OBFUSCATION_RULES['account_fields']
                  or field in OBFUSCATION_RULES['note_fields']
                  or field in OBFUSCATION_RULES['id_fields']
                  or field in OBFUSCATION_RULES['ssn_fields']):
                obfuscated[field] = self.obfuscate_account(row[field])
            elif field in OBFUSCATION_RULES['officer_fields']:
                obfuscated[field] = self.obfuscate_officer(row[field])
            elif field in OBFUSCATION_RULES['branch_fields']:
                obfuscated[field] = self.obfuscate_branch(row[field])
            elif field in OBFUSCATION_RULES['reference_fields']:
                obfuscated[field] = self.obfuscate_reference(row[field])
            elif field in OBFUSCATION_RULES['money_fields']:
                obfuscated[field] = self.obfuscate_money(row[field])
            elif field in OBFUSCATION_RULES['date_fields']:
                obfuscated[field] = self.obfuscate_date(row[field])
            elif field in OBFUSCATION_RULES['rate_fields']:
                obfuscated[field] = self.obfuscate_rate(row[field])
            elif field in OBFUSCATION_RULES['description_fields']:
                obfuscated[field] = self.obfuscate_description(row[field])

            # Replace any inline SSN-like pattern inside string values deterministically
            v = obfuscated.get(field)
            if isinstance(v, str):
                obfuscated[field] = SSN_LIKE.sub(
                    lambda m: deterministic_numeric_like(m.group(0), preserve_last=4),
                    v
                )

        return obfuscated

# ============= MAIN PROCESSING =============

def process_table(conn, source_table: str, dest_table: str,
                  obfuscator: DataObfuscator, clear_existing: bool = False):
    """Process a single table: read, obfuscate, write to masked schema."""
    print(f"\nProcessing {source_table}...")

    # Check if source table exists
    if not table_exists(conn, source_table, 'dbo'):
        print(f"  Source table does not exist, skipping")
        return 0

    # Create destination table if needed
    if not table_exists(conn, dest_table, 'Masked'):
        copy_table_structure(conn, source_table, dest_table, 'dbo', 'Masked')

    # Clear destination if requested
    if clear_existing:
        clear_table(conn, dest_table, 'Masked')

    # Fetch all rows from source
    rows = fetch_all_from_table(conn, source_table, 'dbo')
    print(f"  Found {len(rows)} records")

    if not rows:
        return 0

    # Obfuscate each row
    obfuscated_rows: List[Dict[str, Any]] = []
    for row in rows:
        obfuscated_rows.append(obfuscator.obfuscate_row(row))

    # Insert to destination
    inserted = insert_to_table(conn, dest_table, obfuscated_rows, 'Masked')
    print(f"  Inserted {inserted} obfuscated records to Masked.{dest_table}")

    return inserted

def main():
    """Main obfuscation process."""
    print("=" * 60)
    print("DATA OBFUSCATOR FOR CIBC PARSER")
    print("=" * 60)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Connect to database
    print("\nConnecting to SQL Server...")
    try:
        conn = get_db_connection()
        print("✓ Connected successfully")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return 1

    # Create Masked schema if it doesn't exist
    print("\nCreating Masked schema if needed...")
    create_schema_if_not_exists(conn, 'Masked')

    # Ask about clearing existing masked data
    response = input("\nClear existing masked data before inserting? (y/n): ").lower()
    clear_existing = response == 'y'

    # Ask about seed for reproducibility (Faker/random only)
    response = input("\nUse fixed seed for reproducible obfuscation? (y/n): ").lower()
    seed = 12345 if response == 'y' else None

    # Initialize obfuscator
    obfuscator = DataObfuscator(seed)

    # Process each table
    tables = [
        ('loan_bill_header', 'loan_bill_header'),
        ('loan_bill_summary', 'loan_bill_summary'),
        ('loan_bill_history', 'loan_bill_history'),
        ('rev_credit_statement', 'rev_credit_statement'),
        ('rev_credit_transactions', 'rev_credit_transactions'),
        ('adviceOfRateChange', 'adviceOfRateChange'),
        ('payoff_notice_only', 'payoff_notice_only'),
        ('past_due_notice_only', 'past_due_notice_only')
    ]

    total_records = 0
    for source, dest in tables:
        count = process_table(conn, source, dest, obfuscator, clear_existing)
        total_records += count

    # Close connection
    conn.close()

    # Summary
    print("\n" + "=" * 60)
    print("OBFUSCATION COMPLETE!")
    print("=" * 60)
    print(f"\nTotal records obfuscated: {total_records}")
    print(f"Data written to schema: Masked")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
