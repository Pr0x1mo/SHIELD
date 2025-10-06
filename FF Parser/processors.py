# -*- coding: utf-8 -*-
"""
processors.py - Document processors for CIBC Parser
Contains all document type processing classes
"""

import re
from typing import List, Dict, Tuple, Any
from common_utils import (
    m2f, ZIP_RE, MONEY_RE, REM_ZIP_PATTS,
    enhance_customer_extraction, classify_transaction_with_spacy
)

# ============= LOAN STATEMENT PROCESSOR =============
class LoanStatementProcessor:
    HDR = re.compile(
        r"^\s*\d{3}-\d{7}\s+CIBC BANK USA\s+LOAN STATEMENT \(BILL\)\s+"
        r"(R-06090-002)\s+(\d{2}-\d{2}-\d{2})\s+PAGE\s+(\d+)\s*$",
        re.MULTILINE
    )
    
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
        ln = re.sub(cls.RIGHT_COL, "", ln)
        ln = re.sub(r"\s+\b\d{3}\b$", "", ln)
        return ln.strip()
    
    @classmethod
    def looks_like_field(cls, ln: str) -> bool:
        up = ln.upper().strip()
        if ":" in up and not re.search(r"\bP\.?O\.?\s*BOX\b", up):
            return True
        for p in cls.FIELD_STARTS:
            if re.search(r"^\s*" + p + r"\b", up, re.IGNORECASE):
                return True
        if any(re.search(p, up, re.IGNORECASE) for p in REM_ZIP_PATTS):
            return True
        return False
    
    @classmethod
    def find_acct_note(cls, block: str) -> Tuple[str, str]:
        m = re.search(r"Account/Note\s*Number\s*([0-9]+)\s*-\s*([0-9]+)", block, re.IGNORECASE)
        if m:
            return m.group(1), m.group(2)
        m_acc = re.search(r"\bAccount\s*Number\s*[: ]+\s*([0-9]+)\b", block, re.IGNORECASE)
        m_note = re.search(r"\bNote\s*Number\s*[: ]+\s*([0-9]+)\b", block, re.IGNORECASE)
        return (m_acc.group(1) if m_acc else ""), (m_note.group(1) if m_note else "")
    
    @classmethod
    def split_pages(cls, text: str) -> List[Dict[str, Any]]:
        ms = list(cls.HDR.finditer(text))
        pages = []
        for i, m in enumerate(ms):
            start = m.end()
            end = ms[i+1].start() if i+1 < len(ms) else len(text)
            pages.append({
                "code": m.group(1),
                "hdate": m.group(2),
                "page": int(m.group(3)),
                "body": text[start:end]
            })
        return pages
    
    @classmethod
    def group_statements_in_order(cls, pages: List[Dict]) -> List[Dict]:
        statements, current = [], None
        for p in pages:
            acct, note = cls.find_acct_note(p["body"])
            if acct and note:
                if current:
                    statements.append(current)
                current = {
                    "code": p["code"],
                    "hdate": p["hdate"],
                    "acct": acct,
                    "note": note,
                    "parts": [p["body"]]
                }
            else:
                if current:
                    current["parts"].append(p["body"])
        if current:
            statements.append(current)
        for st in statements:
            st["content"] = "\n".join(st["parts"])
        return statements
    
    @classmethod
    def extract_customer_block(cls, content: str) -> Tuple[List[str], str, str]:
        raw_lines = [ln.rstrip() for ln in content.splitlines()]
        lines = [cls.clean_left_column(ln) for ln in raw_lines]
        
        for i in range(len(lines)-2):
            name = lines[i].strip()
            street = lines[i+1].strip()
            csz = lines[i+2].strip()
            if not name or not street or not csz:
                continue
            if cls.looks_like_field(name) or cls.looks_like_field(street) or cls.looks_like_field(csz):
                continue
            if not (re.search(r"\d", street) or re.search(r"\bP\.?O\.?\s*BOX\b", street, re.IGNORECASE)):
                continue
            if not ZIP_RE.search(csz):
                continue
            if any(re.search(p, csz, re.IGNORECASE) for p in REM_ZIP_PATTS):
                continue
            
            names = [name]
            k = i-1
            while k >= 0 and len(names) < 5:
                prev = cls.clean_left_column(raw_lines[k]).strip()
                if not prev or cls.looks_like_field(prev) or ZIP_RE.search(prev):
                    break
                names.insert(0, prev)
                k -= 1
            
            while len(names) < 5:
                names.append("")
            
            names, street, csz = enhance_customer_extraction(names[:5], street, csz, content)
            
            return (names, street, csz)
        
        return (["","","","",""], "", "")
    
    @classmethod
    def pull_header_fields(cls, content: str) -> Dict[str, Any]:
        def grab(pattern: str):
            m = re.search(pattern, content, re.IGNORECASE)
            return m.group(1).strip() if m else ""
        
        def grab_money(pattern: str):
            m = re.search(pattern, content, re.IGNORECASE)
            return m2f(m.group(1)) if m else None
        
        stmt_date = grab(r"Statement\s*Date\s*[: ]+\s*([0-9/]{8}|[A-Za-z]{3}\s+\d{2},\s+\d{4})")
        officer = grab(r"\bOfficer\s*[: ]+\s*([^\n]+)")
        branch = grab(r"\bBranch\s*Number\s*[: ]+\s*([0-9]+)")
        curr_bal = grab_money(r"Current\s*Balance\s*(" + MONEY_RE + r")")
        due_date = grab(r"Payment\s*Due\s*Date\s*[: ]+\s*([0-9/]{8}|[A-Za-z]{3}\s+\d{2},\s+\d{4})")
        amt_due = grab_money(r"Amount\s*Due\s*(" + MONEY_RE + r")")
        
        page_info = re.findall(r"\bPage\s+(\d+)\s+of\s+(\d+)\b", content, re.IGNORECASE)
        total_pages = max((int(y) for _, y in page_info), default=None)
        
        rate_type = margin = ""
        mrate = re.search(r"\*\*\s*([A-Za-z ]+)\+\s*([0-9.]+%)\s*\*\*", content)
        if mrate:
            rate_type = mrate.group(1).strip()
            margin = mrate.group(2).strip()
        
        def grab_num(pattern: str):
            m = re.search(pattern, content, re.IGNORECASE)
            return m2f(m.group(1)) if m else None
        
        y_interest = grab_num(r"\bInterest\s+Paid\s+([0-9.,]+)")
        y_escrow_int = grab_num(r"\bEscrow\s+Interest\s+Paid\s+([0-9.,]+)")
        y_unapplied = grab_num(r"\bUnapplied\s+Funds\s+([0-9.,]+)")
        y_escrow_bal = grab_num(r"\bEscrow\s+Balance\s+([0-9.,]+)")
        y_taxes_disb = grab_num(r"\bTaxes\s+Disbursed\s+([0-9.,]+)")
        
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
    def parse_summary_block(cls, content: str, acct: str, note: str, hdate: str) -> List[Dict]:
        rows = []
        m_sum = re.search(r"^\s*SUMMARY\s*$", content, re.IGNORECASE | re.MULTILINE)
        if not m_sum:
            return rows
        after = content[m_sum.end():]
        stop = re.search(r"^\s*YEAR-TO-DATE\s+SUMMARY|^\s*RATE\s+INFORMATION", after, re.IGNORECASE | re.MULTILINE)
        block = after[:stop.start()] if stop else after
        
        for ln in block.splitlines():
            s = ln.rstrip()
            if not s.strip():
                continue
            m = re.match(
                r"^\s*([0-9]{5}/[A-Z])\s+([0-9,]+\.\d{2})\s+([0-9.]+)\s+([0-9/]{8}|00/00/00)\s+(.*?)\s+([0-9,$][0-9,]*\.\d{2})\s*$",
                s
            )
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
            m2 = re.match(
                r"^\s*(Interest\s+To\s+\d{2}/\d{2}/\d{2}|Total\s+Due\s+On\s+\d{2}/\d{2}/\d{2}|Principal\s+Payment)\s+([0-9,$][0-9,]*\.\d{2})\s*$",
                s, re.IGNORECASE
            )
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
        return rows
    
    @classmethod
    def parse_history_block(cls, content: str, acct: str, note: str, hdate: str, cust_name_1: str) -> List[Dict]:
        rows = []
        m_hist = re.search(r"^\s*LOAN\s+HISTORY\s*$", content, re.IGNORECASE | re.MULTILINE)
        if not m_hist:
            return rows
        after = content[m_hist.end():]
        for ln in after.splitlines():
            s = ln.rstrip()
            if not s.strip():
                continue
            m = re.match(
                r"^\s*([0-9]{5})\s+([0-9/]{8})\s+([0-9/]{8})\s+(.+?)\s+([0-9,]+\.\d{2})\s+([0-9,]+\.\d{2})\s+([0-9,]+\.\d{2})\s+([0-9,]+\.\d{2})\s+([0-9,]+\.\d{2})\s*$",
                s
            )
            if m:
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
            if cls.HDR.search(s):
                break
        return rows
    
    @classmethod
    def process(cls, text: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        pages = cls.split_pages(text)
        statements = cls.group_statements_in_order(pages)
        
        hdr_rows, sum_rows, hist_rows = [], [], []
        
        for st in statements:
            acct, note, hdate, content = st["acct"], st["note"], st["hdate"], st["content"]
            
            names, street, csz = cls.extract_customer_block(content)
            n1, n2, n3, n4, n5 = (names + ["","","","",""])[:5]
            
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
        
        return hdr_rows, sum_rows, hist_rows


# ============= REV CREDIT STATEMENT PROCESSOR =============
class RevCreditProcessor:
    HDR = re.compile(
        r"^\s*\d{3}-\d{7}\s+CIBC BANK USA\s+REV\. CREDIT STATEMENT\s+"
        r"(R-06088-001)\s+(\d{2}-\d{2}-\d{2})\s+PAGE\s+(\d+)\s*$",
        re.MULTILINE
    )
    
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
        up = ln.upper()
        if any(re.search(p, up, re.IGNORECASE) for p in cls.DROP_PATTS):
            return True
        if any(re.search(p, up, re.IGNORECASE) for p in REM_ZIP_PATTS):
            return True
        return False
    
    @classmethod
    def strip_inline_noise(cls, s: str) -> str:
        s = re.sub(r"\s{2,}AMOUNT\s+ENCLOSED.*$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s{2,}A\s+late\s+fee\s+of.*$", "", s, flags=re.IGNORECASE)
        return s.strip()
    
    @classmethod
    def find_acct_note(cls, block: str) -> Tuple[str, str]:
        m = re.search(r"Account/Note\s*Number\s*([0-9]+)\s*-\s*([0-9]+)", block, re.IGNORECASE)
        if m:
            return m.group(1), m.group(2)
        m = re.search(r"\bAccount\s*Number\s*:\s*([0-9]+)\s+([0-9]+)", block, re.IGNORECASE)
        if m:
            return m.group(1), m.group(2)
        m = re.search(r"\bAccount\s*Number\s*:\s*([0-9 ]+)", block, re.IGNORECASE)
        if m:
            p = m.group(1).split()
            if len(p) == 2:
                return p[0], p[1]
        return "", ""
    
    @classmethod
    def split_pages(cls, text: str) -> List[Dict]:
        ms = list(cls.HDR.finditer(text))
        pages = []
        for i, m in enumerate(ms):
            start = m.end()
            end = ms[i+1].start() if i+1 < len(ms) else len(text)
            pages.append({
                "code": m.group(1),
                "hdate": m.group(2),
                "page": int(m.group(3)),
                "body": text[start:end]
            })
        return pages
    
    @classmethod
    def group_statements(cls, pages: List[Dict]) -> Dict:
        groups = {}
        for p in pages:
            acct, note = cls.find_acct_note(p["body"])
            key = (acct, note, p["hdate"])
            groups.setdefault(key, {"code": "R-06088-001", "hdate": p["hdate"], "parts": []})
            groups[key]["parts"].append((p["page"], p["body"]))
        for k, g in groups.items():
            g["parts"].sort(key=lambda x: x[0])
            g["content"] = "\n".join(b for _, b in g["parts"])
        return groups
    
    @classmethod
    def extract_customer_from_first_page(cls, content: str) -> Tuple[List[str], str, str]:
        m_acc = re.search(r"\bAccount\s*Number\s*:", content, re.IGNORECASE)
        if not m_acc:
            return (["","","","",""], "", "")
        window = content[:m_acc.start()]
        
        lines = [ln.rstrip() for ln in window.splitlines()]
        lines = lines[-50:] if len(lines) > 50 else lines
        
        cleaned = []
        for ln in lines:
            ln2 = cls.strip_inline_noise(ln)
            if not ln2.strip():
                cleaned.append("")
                continue
            if cls.is_drop(ln2):
                cleaned.append("")
                continue
            cleaned.append(ln2)
        
        zi = -1
        for i in range(len(cleaned)-1, -1, -1):
            ln = cleaned[i]
            if ZIP_RE.search(ln):
                if any(re.search(p, ln, re.IGNORECASE) for p in REM_ZIP_PATTS):
                    continue
                zi = i
                break
        if zi <= 0:
            return (["","","","",""], "", "")
        
        street_line = cleaned[zi-1].strip() if zi-1 >= 0 else ""
        if not (re.search(r"\d", street_line) or re.search(r"\bP\.?O\.?\s*BOX\b", street_line, re.IGNORECASE)):
            j = zi-1
            street_line = ""
            while j >= 0:
                cand = cleaned[j].strip()
                if re.search(r"\d", cand) or re.search(r"\bP\.?O\.?\s*BOX\b", cand, re.IGNORECASE):
                    street_line = cand
                    break
                j -= 1
            if not street_line:
                return (["","","","",""], "", "")
        
        csz = cleaned[zi].strip()
        
        names = []
        k = zi-1
        while k >= 0 and cleaned[k].strip() != street_line:
            k -= 1
        k -= 1
        while k >= 0 and len(names) < 5:
            raw = cleaned[k].strip()
            if not raw:
                break
            if ZIP_RE.search(raw):
                k -= 1
                continue
            raw = re.sub(r"\s+\b\d{3}\b$", "", raw).strip()
            if not raw or cls.is_drop(raw):
                break
            names.insert(0, raw)
            k -= 1
        
        while len(names) < 5:
            names.append("")
        
        names, street_line, csz = enhance_customer_extraction(names[:5], street_line, csz, content)
        
        return (names[:5], street_line, csz)
    
    @classmethod
    def pull_top_fields(cls, content: str) -> Tuple:
        stmt = (re.search(r"Statement\s*Date\s+([A-Za-z]{3}\s+\d{2},\s+\d{4})", content, re.IGNORECASE) or
                re.search(r"Statement\s*Date\s*:\s*(\d{2}/\d{2}/\d{2})", content, re.IGNORECASE))
        due = (re.search(r"Payment\s*Due\s*Date\s+([A-Za-z]{3}\s+\d{2},\s+\d{4})", content, re.IGNORECASE) or
               re.search(r"Payment\s*Due\s*Date\s*:\s*(\d{2}/\d{2}/\d{2})", content, re.IGNORECASE))
        stmt_date = stmt.group(1) if stmt else ""
        due_date = due.group(1) if due else ""
        
        new_bal = m2f((re.search(r"New\s*Statement\s*Balance\s*\$([0-9,]+\.\d{2})", content, re.IGNORECASE) or [None,None])[1])
        fees_unpd = m2f((re.search(r"Fees\s*Charged/Unpaid\s*\$([0-9,]+\.\d{2})", content, re.IGNORECASE) or [None,None])[1])
        past_due = m2f((re.search(r"Past\s*Due\s*Amount\s*\$([0-9,]+\.\d{2})", content, re.IGNORECASE) or [None,None])[1])
        min_pay = m2f((re.search(r"Minimum\s*Payment\s*Due\s*\$([0-9,]+\.\d{2})", content, re.IGNORECASE) or [None,None])[1])
        
        def grab(pattern: str):
            m = re.search(pattern, content, re.IGNORECASE)
            return m2f(m.group(1)) if m else None
        
        pfees = grab(r"TOTAL\s+FEES\s+FOR\s+THIS\s+PERIOD\s*(" + MONEY_RE + r")")
        pint = grab(r"TOTAL\s+INTEREST\s+FOR\s+THIS\s+PERIOD\s*(" + MONEY_RE + r")")
        yfees = grab(r"Total\s+fees\s+charged\s+in\s+\d{4}\s*(" + MONEY_RE + r")")
        yint = grab(r"Total\s+interest\s+charged\s+in\s+\d{4}\s*(" + MONEY_RE + r")")
        tip = grab(r"Total\s+Interest\s+Charges\s+Paid\s+In\s+\d{4}:\s*(" + MONEY_RE + r")")
        
        prev=adv=pay=intr=other=curr=None
        mh = re.search(r"Previous\s+Statement.*?Equals\s+Current\s+Statement\s+Balance", content, re.IGNORECASE|re.DOTALL)
        if mh:
            tail = "\n".join(content[mh.end():].splitlines()[:4])
            nums = re.findall(MONEY_RE, tail)
            if len(nums) >= 6:
                prev,adv,pay,intr,other,curr = [m2f(x) for x in nums[:6]]
        
        ac=fcu=cad=pda=mpd=None
        m5 = re.search(r"Available\s+Credit.*?Minimum\s+Payment\s+Due\s*\n([^\n]+)", content, re.IGNORECASE|re.DOTALL)
        if m5:
            amts = re.findall(MONEY_RE, m5.group(1))
            if len(amts) >= 5:
                ac,fcu,cad,pda,mpd = [m2f(x) for x in amts[:5]]
        
        return (stmt_date,due_date,new_bal,fees_unpd,past_due,min_pay,
                ac,fcu,cad,pda,mpd,
                pfees,pint,yfees,yint,tip,
                prev,adv,pay,intr,other,curr)
    
    @classmethod
    def parse_transactions(cls, content: str, acct: str, note: str, hdate: str) -> List[Dict]:
        mstart = re.search(r"^\s*\|\s*Transactions\s*\|\s*$", content, re.IGNORECASE | re.MULTILINE)
        if not mstart:
            mstart = re.search(r"\bTransactions\b", content, re.IGNORECASE)
        if not mstart:
            return []
        start_idx = mstart.end()
        
        mend = re.search(r"TOTAL\s+FEES\s+FOR\s+THIS\s+PERIOD", content[start_idx:], re.IGNORECASE)
        if mend:
            end_idx = start_idx + mend.start()
        else:
            mfees = re.search(r"^\s*\|\s*Fees\s*\|\s*$", content[start_idx:], re.IGNORECASE | re.MULTILINE)
            end_idx = start_idx + (mfees.start() if mfees else len(content) - start_idx)
        
        block = content[start_idx:end_idx]
        lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
        txns = []
        last = None
        
        for raw in lines:
            s = raw
            m = re.match(r"^\s*(\d{2}/\d{2})?\s*(\d{2}/\d{2})?\s*(.*?)\s*("
                        + MONEY_RE + r"(?:\s+" + MONEY_RE + r"){0,2})?\s*$", s)
            if m:
                d1 = (m.group(1) or "").strip()
                d2 = (m.group(2) or "").strip()
                desc = (m.group(3) or "").strip()
                amts = re.findall(MONEY_RE, m.group(4) or "")
                adv=pay=bal=None
                if len(amts) == 3:
                    adv, pay, bal = [m2f(x) for x in amts]
                elif len(amts) == 2:
                    if re.search(r"payment|credit", desc, re.IGNORECASE):
                        pay, bal = [m2f(x) for x in amts]
                    else:
                        adv, bal = [m2f(x) for x in amts]
                elif len(amts) == 1:
                    bal = m2f(amts[0])
                
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
                last = row
            else:
                cont = s.strip()
                if cont and last:
                    last["Description"] = (last["Description"] + " " + cont).strip()
                    last["Transaction_Category"] = classify_transaction_with_spacy(last["Description"])
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
                    last = txns[-1]
        return txns
    
    @classmethod
    def process(cls, text: str) -> Tuple[List[Dict], List[Dict]]:
        pages = cls.split_pages(text)
        groups = cls.group_statements(pages)
        
        header_rows, txn_rows = [], []
        
        for (acct, note, hdate), g in groups.items():
            if not acct and not note:
                continue
            content = g["content"]
            
            names, street, csz = cls.extract_customer_from_first_page(content)
            n1, n2, n3, n4, n5 = (names + ["", "", "", "", ""])[:5]
            
            (stmt_date, due_date, new_bal, fees_unpd, past_due, min_pay,
             ac, fcu, cad, pda, mpd,
             pfees, pint, yfees, yint, tip,
             prev, adv, pay, intr, other, curr) = cls.pull_top_fields(content)
            
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
        
        return header_rows, txn_rows


# ============= ADVICE OF RATE CHANGE PROCESSOR =============
class AdviceOfRateChangeProcessor:
    HDR = re.compile(
        r"^\s*\d{3}-\d{7}\s+CIBC BANK USA\s+ADVICE OF RATE CHANGE\s+(R-\d{5}-\d{3})\s+(\d{2}-\d{2}-\d{2})\s+PAGE\s+(\d+)\s*$",
        re.MULTILINE
    )
    
    @staticmethod
    def clean_tail(s: str) -> str:
        s = re.sub(r"\s+Account\s*Number\s*:.*$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+Note\s*Number\s*:.*$", "", s, flags=re.IGNORECASE)
        return s.strip()
    
    @classmethod
    def extract_names_address(cls, page_body: str) -> Tuple[List[str], str, str]:
        lines = [ln.rstrip() for ln in page_body.splitlines()]
        zi = next((i for i, ln in enumerate(lines) if ZIP_RE.search(ln)), -1)
        if zi <= 0:
            return [], "", ""
        street = cls.clean_tail(lines[zi - 1].strip())
        csz = cls.clean_tail(lines[zi].strip())
        start = max(0, (zi - 1) - 7)
        candidates = [cls.clean_tail(ln) for ln in lines[start:zi-1] if ln.strip()]
        noise = ("CIBC BANK USA", "ADVICE OF RATE CHANGE", "PAGE")
        names = [ln for ln in candidates if not any(n in ln.upper() for n in noise)][-5:]
        
        names, street, csz = enhance_customer_extraction(names, street, csz, page_body)
        
        return names, street, csz
    
    @classmethod
    def process(cls, text: str) -> List[Dict]:
        records = []
        matches = list(cls.HDR.finditer(text))
        
        for i, m in enumerate(matches):
            code, hdr_date, page_no = m.group(1), m.group(2), int(m.group(3))
            if code != "R-06061-001":
                continue
            
            start = m.end()
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            body = text[start:end]
            
            names, street, csz = cls.extract_names_address(body)
            
            acct_m = re.search(r"Account\s*Number\s*:\s*([0-9 ]+)", body, re.IGNORECASE)
            note_m = re.search(r"Note\s*Number\s*:\s*([0-9 ]+)", body, re.IGNORECASE)
            acct_num = acct_m.group(1).replace(" ","") if acct_m else ""
            note_num = note_m.group(1).replace(" ","") if note_m else ""
            
            rate = re.search(r"from\s+([0-9.]+)%\s+to\s+([0-9.]+)%\s+on\s+(\d{2}-\d{2}-\d{2})", body, re.IGNORECASE)
            prev_rate = float(rate.group(1)) if rate else None
            curr_rate = float(rate.group(2)) if rate else None
            rate_date = rate.group(3) if rate else ""
            
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
        
        return records


# ============= PAYOFF NOTICE PROCESSOR =============
class PayoffNoticeProcessor:
    HDR = re.compile(
        r"^\s*\d{3}-\d{7}\s+CIBC BANK USA\s+PAYOFF NOTICE TO PAYEE\s+"
        r"(R-07362-001)\s+(\d{2}-\d{2}-\d{2})\s+PAGE\s+(\d+)\s*$",
        re.MULTILINE
    )
    
    @staticmethod
    def clean_tail(s: str) -> str:
        s = re.sub(r"\s+Ref\s*No\..*$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+Account\s*:.*$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+Note\s*:.*$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+Issue\s*Date\s*:.*$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+Acct\s*Name\s*:.*$", "", s, flags=re.IGNORECASE)
        return s.strip()
    
    @classmethod
    def extract_payee_address(cls, page_body: str) -> Tuple[str, str]:
        lines = [ln.rstrip() for ln in page_body.splitlines() if ln.strip()]
        for i, ln in enumerate(lines):
            if ZIP_RE.search(ln):
                csz = cls.clean_tail(ln.strip())
                street = cls.clean_tail(lines[i-1].strip()) if i-1 >= 0 else ""
                name = cls.clean_tail(lines[i-2].strip()) if i-2 >= 0 else ""
                
                return name, (street + ("\n" if street and csz else "") + csz).strip()
        return "", ""
    
    @staticmethod
    def get_between(body: str, start_pat: str, end_pat: str) -> str:
        s = re.search(start_pat, body, re.IGNORECASE | re.DOTALL)
        if not s:
            return ""
        start_idx = s.start()
        e = re.search(end_pat, body[start_idx:], re.IGNORECASE | re.DOTALL)
        if not e:
            chunk = body[start_idx:]
        else:
            chunk = body[start_idx:start_idx + e.start()]
        lines = [ln.rstrip() for ln in chunk.splitlines()]
        return "\n".join([ln for ln in lines if ln.strip()]).strip()
    
    @staticmethod
    def first_group(rx, body, flags=0, default=""):
        m = re.search(rx, body, flags)
        return m.group(1).strip() if m else default
    
    @classmethod
    def process(cls, text: str) -> List[Dict]:
        records = []
        matches = list(cls.HDR.finditer(text))
        
        for i, m in enumerate(matches):
            code, header_date, page_no = m.group(1), m.group(2), int(m.group(3))
            if code != "R-07362-001":
                continue
            
            start = m.end()
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            body = text[start:end]
            
            notice_date = cls.first_group(r"\bDate\s*:\s*([0-9/]{8})", body)
            county_name, county_addr = cls.extract_payee_address(body)
            
            notice_comment = cls.get_between(
                body,
                r"The loan shown below.+?(?=\n)",
                r"\n\s*Ref\s*No\.\s"
            )
            
            ref_no = cls.first_group(r"Ref\s*No\.\s+([^\n]+)", body, re.IGNORECASE)
            account = cls.first_group(r"\bAccount\s*:\s*([0-9 ]+)", body, re.IGNORECASE).replace(" ","")
            note = cls.first_group(r"\bNote\s*:\s*([0-9 ]+)", body, re.IGNORECASE).replace(" ","")
            issue_date = cls.first_group(r"Issue\s*Date\s*:\s*([0-9/]{8})", body, re.IGNORECASE)
            acct_name = cls.first_group(r"Acct\s*Name\s*:\s*(.+)", body, re.IGNORECASE)
            
            prop_m = re.search(r"Property\s*At\s*:\s*\n\s*(.+)\n\s*(.+)", body, re.IGNORECASE)
            property_at = ""
            if prop_m:
                line1 = prop_m.group(1).strip()
                line2 = prop_m.group(2).strip()
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
        
        return records


# ============= PAST DUE NOTICE PROCESSOR =============
class PastDueNoticeProcessor:
    HDR = re.compile(
        r"^\s*\d{3}-\d{7}\s+CIBC BANK USA\s+PAST DUE NOTICE\s+"
        r"(R-06385-\d{3})\s+(\d{2}-\d{2}-\d{2})\s+PAGE\s+(\d+)\s*$",
        re.MULTILINE
    )
    
    NOISE = ("CIBC BANK USA","PAST DUE NOTICE","PAST DUE LOAN NOTICE","PAGE")
    
    @staticmethod
    def clean_tail(s: str) -> str:
        s = re.sub(r"\s+Notice\s*Date\s*:.*$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+Account\s*Number\s*:.*$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+Note\s*Number\s*:.*$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+Officer\s*:.*$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+Branch\s*:.*$", "", s, flags=re.IGNORECASE)
        return s.strip()
    
    @classmethod
    def extract_names_address(cls, page_body: str) -> Tuple[List[str], str, str]:
        lines = [ln.rstrip() for ln in page_body.splitlines()]
        zi = next((i for i, ln in enumerate(lines) if ZIP_RE.search(ln)), -1)
        if zi <= 0:
            return [], "", ""
        street = cls.clean_tail(lines[zi - 1].strip())
        csz = cls.clean_tail(lines[zi].strip())
        start = max(0, (zi - 1) - 7)
        candidates = [cls.clean_tail(ln) for ln in lines[start:zi-1] if ln.strip()]
        names = [ln for ln in candidates if not any(n in ln.upper() for n in cls.NOISE)][-5:]
        
        names, street, csz = enhance_customer_extraction(names, street, csz, page_body)
        
        return names, street, csz
    
    @classmethod
    def process(cls, text: str) -> List[Dict]:
        records = []
        matches = list(cls.HDR.finditer(text))
        
        for i, m in enumerate(matches):
            code, hdr_date, page_no = m.group(1), m.group(2), int(m.group(3))
            start = m.end()
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            body = text[start:end]
            
            names, street, csz = cls.extract_names_address(body)
            
            notice_date = re.search(r"Notice\s*Date\s*:\s*(\d{2}/\d{2}/\d{2})", body, re.IGNORECASE)
            acct_m = re.search(r"Account\s*Number\s*:\s*([0-9 ]+)", body, re.IGNORECASE)
            note_m = re.search(r"Note\s*Number\s*:\s*([0-9 ]+)", body, re.IGNORECASE)
            officer_m = re.search(r"Officer\s*:\s*([A-Z0-9 &]+)", body)
            branch_m = re.search(r"Branch\s*:\s*([A-Z0-9 &]+)", body)
            
            loan_type_m = re.search(
                r"^\s*(Revolving Credit Loan|Installment Loan|Commercial Loan)\s*$",
                body, re.IGNORECASE | re.MULTILINE
            )
            due_date_m = re.search(
                r"Your\s+loan\s+payment\s+was\s+due\s+(\d{2}/\d{2}/\d{2})",
                body, re.IGNORECASE
            )
            
            pr = re.search(r"Principal\s*:\s*\$?([0-9,]+\.\d{2})", body, re.IGNORECASE)
            it = re.search(r"Interest\s*:\s*\$?([0-9,]+\.\d{2})", body, re.IGNORECASE)
            lf = re.search(r"Late\s*Fees\s*:\s*\$?([0-9,]+\.\d{2})", body, re.IGNORECASE)
            td = re.search(r"Total\s*Due\s*:\s*\$?([0-9,]+\.\d{2})", body, re.IGNORECASE)
            
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
        
        return records