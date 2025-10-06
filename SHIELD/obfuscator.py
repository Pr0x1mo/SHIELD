# obfuscator.py
import re
from faker import Faker

fake = Faker()

def pad_or_trim(value: str, length: int) -> str:
    """Return value padded with spaces (rjust/ljust) or trimmed so result length == length."""
    if length <= 0:
        return value
    if len(value) == length:
        return value
    if len(value) < length:
        return value.ljust(length)
    # too long -> trim
    return value[:length]


# Helper: try several common date patterns and return a strftime format
def detect_date_format(original: str) -> str | None:
    s = original.strip()
    # pattern -> strftime
    patterns = [
        (r'^\d{4}-\d{2}-\d{2}$', '%Y-%m-%d'),        # 2023-09-27
        (r'^\d{2}-\d{2}-\d{4}$', '%m-%d-%Y'),        # 09-27-2023 or 12-31-2023
        (r'^\d{2}/\d{2}/\d{4}$', '%m/%d/%Y'),        # 09/27/2023
        (r'^\d{1,2}/\d{1,2}/\d{2}$', '%m/%d/%y'),    # 9/27/23 or 09/27/23
        (r'^\d{2}-\d{2}-\d{2}$', '%y-%m-%d'),        # 23-09-27
        (r'^\d{4}/\d{2}/\d{2}$', '%Y/%m/%d'),        # 2023/09/27
        (r'^\d{2}\.\d{2}\.\d{4}$', '%d.%m.%Y'),      # 27.09.2023
        (r'^[A-Za-z]{3} \d{1,2}, \d{4}$', '%b %d, %Y'), # Sep 27, 2023
        (r'^[A-Za-z]{3} \d{1,2} \d{4}$', '%b %d %Y'), # Sep 27 2023
        (r'^\d{1,2} [A-Za-z]{3} \d{4}$', '%d %b %Y'), # 27 Sep 2023
        (r'^[A-Za-z]{4,9} \d{1,2}, \d{4}$', '%B %d, %Y'), # September 27, 2023
        (r'^\d{4}$', '%Y'),                          # 2023
        # Add more patterns if your data uses other formats
    ]
    for regex, fmt in patterns:
        if re.match(regex, s):
            return fmt
    # If nothing matched, attempt a heuristic parse with known formats
    trial_formats = ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M', '%Y.%m.%d']
    for fmt in trial_formats:
        try:
            datetime.datetime.strptime(s, fmt)
            return fmt
        except Exception:
            continue
    return None

def generate_date_like_original(original: str) -> str:
    original_length = len(original or "")
    fmt = detect_date_format(original)
    # create a fake date object - use recent past by default
    try:
        fake_date_obj = fake.date_between(start_date='-20y', end_date='today')
    except Exception:
        fake_date_obj = fake.past_date()  # fallback

    if fmt:
        # Some detected formats may include time; for safety, only format the date part.
        # If fmt contains a time directive, we keep date-only formatting (unless you want time).
        try:
            # If fmt includes time tokens but original didn't include time (rare), this still works.
            formatted = fake_date_obj.strftime(fmt)
        except Exception:
            # fallback to reasonable ISO-like format
            formatted = fake_date_obj.strftime('%Y-%m-%d')
        return pad_or_trim(formatted, original_length)
    else:
        # fallback to your previous behavior (20%y-%m-%d)
        try:
            formatted = fake_date_obj.strftime("20%y-%m-%d")
        except Exception:
            formatted = fake_date_obj.strftime('%Y-%m-%d')
        return pad_or_trim(formatted, original_length)

# Example: Replacement within your generate_synthetic_data or obfuscation function:
# elif pii_type == "DATE":
#     return generate_date_like_original(original)
#
# or if you keep the same function structure:

def generate_synthetic_data(original: str, pii_type: str) -> str:
    """
    Create a synthetic replacement for `original` based on `pii_type`.
    Follows the behavior you supplied: uses specific faker calls and pads
    to the original length where shown in your snippet.
    """
    original_length = len(original or "")
    if pii_type == "PERSON":
        fake_name = fake.name()
        return pad_or_trim(fake_name, original_length)
    elif pii_type == "ORG":
        fake_org = fake.company()
        return pad_or_trim(fake_org, original_length)
    elif pii_type in ("ACCT", "ACCOUNT_NUMBER"):
        # Your snippet used fake.aba() for routing; for acct you used fake.aba() for ACCT — keep ACCT -> aba? 
        # Here we produce a 10-digit numeric account as safer default if detection uses ACCOUNT_NUMBER.
        fake_acct = fake.aba() if hasattr(fake, "aba") and pii_type == "ACCT" else str(fake.random_number(digits=10))
        return pad_or_trim(fake_acct, original_length)
    elif pii_type == "MONEY" or pii_type == "CHECK_AMOUNT":
        fake_money = f"{fake.random_int(min=1, max=999)},{fake.random_int(min=1, max=999)}.00"
        return pad_or_trim(fake_money, original_length)
    elif pii_type == "ROUTING_NUMBER":
        # your snippet returned raw fake.aba() (no padding). We follow that:
        return fake.aba() if hasattr(fake, "aba") else str(fake.random_number(digits=9))
    elif pii_type == "ADDRESS_NUMBER" or pii_type == "ADDRESS":
        fake_address = fake.address()
        return pad_or_trim(fake_address, original_length)
    elif pii_type == "SSN_NUMBER" or pii_type == "SSN":
        fake_ssn = fake.ssn()
        return pad_or_trim(fake_ssn, original_length)
    elif pii_type == "PHONE_NUMBER" or pii_type == "PHONE":
        # use basic_phone_number if available (your snippet used basic_phone_number)
        fake_phone = fake.basic_phone_number() if hasattr(fake, "basic_phone_number") else fake.phone_number()
        return pad_or_trim(fake_phone, original_length)
    elif pii_type == "DATE":
        return generate_date_like_original(original)
    elif pii_type == "GPE" or pii_type == "CITY":
        fake_city = fake.city()
        return pad_or_trim(fake_city, original_length)
    elif pii_type == "BANK":
        # return a string of random letters same length as original
        if original_length <= 0:
            return ""
        # Faker has random_letters in some providers; else use Python
        try:
            letters = fake.random_letters(length=original_length)
            return "".join(letters)
        except Exception:
            import random, string
            return "".join(random.choice(string.ascii_letters) for _ in range(original_length))
    else:
        # default: return original unchanged (as in your snippet)
        return original

# Normalization: map labels produced by detection pipeline into the types expected above.
LABEL_NORMALIZATION = {
    # common labels used in your repo -> map to the snippet-style names
    "PERSON": "PERSON",
    "ORG": "ORG",
    "ACCOUNT_NUMBER": "ACCOUNT_NUMBER",
    "ACCT": "ACCT",
    "CREDIT_CARD": "CREDIT_CARD",
    "CHECK_AMOUNT": "CHECK_AMOUNT",
    "MONEY": "MONEY",
    "ROUTING_NUMBER": "ROUTING_NUMBER",
    "SSN": "SSN_NUMBER",
    "SSN_NUMBER": "SSN_NUMBER",
    "PHONE": "PHONE_NUMBER",
    "PHONE_NUMBER": "PHONE_NUMBER",
    "ADDRESS": "ADDRESS",
    "ADDRESS_NUMBER": "ADDRESS_NUMBER",
    "DATE": "DATE",
    "IP_ADDRESS": "IP_ADDRESS",
    "GPE": "GPE",
    "CITY": "CITY",
    "BANK": "BANK",
    # add more as your detectors produce other labels
}

def obfuscate_text(text: str, entities):
    """
    Entities expected as an iterable of (start, end, label) tuples (same as your other code).
    Replacement preserves position logic by performing replacements from the end to start.
    """
    replacements = []
    # sort by start (and by length if needed) to process in deterministic order
    for start, end, label in sorted(entities, key=lambda x: (x[0], -x[1] + x[0])):
        original = text[start:end]
        normalized_label = LABEL_NORMALIZATION.get(label, label)
        replacement = generate_synthetic_data(original, normalized_label)
        # ensure replacement yields at least something (fallback)
        if replacement is None:
            replacement = "[REDACTED]"
        replacements.append((start, end, replacement))

    # apply replacements in reverse so offsets don't shift earlier spans
    for start, end, replacement in reversed(replacements):
        text = text[:start] + replacement + text[end:]
    return text
