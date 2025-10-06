# -*- coding: utf-8 -*-
"""
cibc_parser_sql.py - Main CIBC Parser Script with SQL Server Output
Coordinates parsing and database insertion
"""

from pathlib import Path
from datetime import datetime
import sys

# Import our modules
from common_utils import read_text, print_spacy_status, HAVE_SPACY
from db_utils import (
    get_db_connection, 
    insert_to_table, 
    clear_table,
    table_exists,
    execute_query
)
from processors import (
    LoanStatementProcessor,
    RevCreditProcessor,
    AdviceOfRateChangeProcessor,
    PayoffNoticeProcessor,
    PastDueNoticeProcessor
)

# ============= CONFIGURATION =============
INPUT_PATH = Path(r"C:\Users\Proximus\Desktop\Obfuscate\Python\FF Parser\input\SampleFileSTMT.txt")

# Table mappings
TABLE_MAPPINGS = {
    'loan_header': 'loan_bill_header',
    'loan_summary': 'loan_bill_summary',
    'loan_history': 'loan_bill_history',
    'rev_header': 'rev_credit_statement',
    'rev_transactions': 'rev_credit_transactions',
    'advice': 'adviceOfRateChange',
    'payoff': 'payoff_notice_only',
    'past_due': 'past_due_notice_only'
}

# ============= TABLE CREATION =============
def ensure_tables_exist(conn):
    """Create all necessary tables if they don't exist."""
    cursor = conn.cursor()
    
    # Create loan_bill_header table
    if not table_exists(conn, 'loan_bill_header'):
        print("  Creating table: loan_bill_header")
        cursor.execute("""
        CREATE TABLE [dbo].[loan_bill_header] (
            id INT IDENTITY(1,1) PRIMARY KEY,
            Notice_Type NVARCHAR(50),
            Notice_Code NVARCHAR(20),
            Header_Date NVARCHAR(10),
            Account_Number NVARCHAR(20),
            Note_Number NVARCHAR(20),
            Total_Pages NVARCHAR(10),
            Statement_Date NVARCHAR(20),
            Officer NVARCHAR(100),
            Branch_Number NVARCHAR(10),
            Customer_Name_1 NVARCHAR(100),
            Customer_Name_2 NVARCHAR(100),
            Customer_Name_3 NVARCHAR(100),
            Customer_Name_4 NVARCHAR(100),
            Customer_Name_5 NVARCHAR(100),
            Address_Street NVARCHAR(200),
            Address_CityStateZip NVARCHAR(200),
            Current_Balance DECIMAL(18,2),
            Payment_Due_Date NVARCHAR(20),
            Amount_Due DECIMAL(18,2),
            Rate_Type NVARCHAR(50),
            Rate_Margin NVARCHAR(20),
            YTD_Interest_Paid DECIMAL(18,2),
            YTD_Escrow_Interest_Paid DECIMAL(18,2),
            YTD_Unapplied_Funds DECIMAL(18,2),
            YTD_Escrow_Balance DECIMAL(18,2),
            YTD_Taxes_Disbursed DECIMAL(18,2),
            inserted_datetime DATETIME DEFAULT GETDATE()
        )
        """)
    
    # Create loan_bill_summary table
    if not table_exists(conn, 'loan_bill_summary'):
        print("  Creating table: loan_bill_summary")
        cursor.execute("""
        CREATE TABLE [dbo].[loan_bill_summary] (
            id INT IDENTITY(1,1) PRIMARY KEY,
            Account_Number NVARCHAR(20),
            Note_Number NVARCHAR(20),
            Header_Date NVARCHAR(10),
            Note_Category NVARCHAR(50),
            Current_Balance DECIMAL(18,2),
            Interest_Rate FLOAT,
            Maturity_Date NVARCHAR(20),
            Description NVARCHAR(500),
            Amount DECIMAL(18,2),
            inserted_datetime DATETIME DEFAULT GETDATE()
        )
        """)
    
    # Create loan_bill_history table
    if not table_exists(conn, 'loan_bill_history'):
        print("  Creating table: loan_bill_history")
        cursor.execute("""
        CREATE TABLE [dbo].[loan_bill_history] (
            id INT IDENTITY(1,1) PRIMARY KEY,
            Account_Number NVARCHAR(20),
            Note_Number NVARCHAR(20),
            Header_Date NVARCHAR(10),
            Customer_Name_1 NVARCHAR(100),
            Hist_Note NVARCHAR(20),
            Posting_Date NVARCHAR(10),
            Effective_Date NVARCHAR(10),
            Transaction_Description NVARCHAR(500),
            Transaction_Category NVARCHAR(50),
            Principal DECIMAL(18,2),
            Interest DECIMAL(18,2),
            LateFees_Others DECIMAL(18,2),
            Escrow DECIMAL(18,2),
            Insurance DECIMAL(18,2),
            inserted_datetime DATETIME DEFAULT GETDATE()
        )
        """)
    
    # Create rev_credit_statement table
    if not table_exists(conn, 'rev_credit_statement'):
        print("  Creating table: rev_credit_statement")
        cursor.execute("""
        CREATE TABLE [dbo].[rev_credit_statement] (
            id INT IDENTITY(1,1) PRIMARY KEY,
            Notice_Type NVARCHAR(50),
            Notice_Code NVARCHAR(20),
            Header_Date NVARCHAR(10),
            Account_Number NVARCHAR(20),
            Note_Number NVARCHAR(20),
            Statement_Date NVARCHAR(20),
            Payment_Due_Date NVARCHAR(20),
            Customer_Name_1 NVARCHAR(100),
            Customer_Name_2 NVARCHAR(100),
            Customer_Name_3 NVARCHAR(100),
            Customer_Name_4 NVARCHAR(100),
            Customer_Name_5 NVARCHAR(100),
            Address_Street NVARCHAR(200),
            Address_CityStateZip NVARCHAR(200),
            New_Statement_Balance DECIMAL(18,2),
            Fees_Charged_Unpaid_top DECIMAL(18,2),
            Past_Due_Amount_top DECIMAL(18,2),
            Minimum_Payment_Due_top DECIMAL(18,2),
            Available_Credit DECIMAL(18,2),
            Fees_Charged_Unpaid DECIMAL(18,2),
            Current_Amount_Due DECIMAL(18,2),
            Past_Due_Amount DECIMAL(18,2),
            Minimum_Payment_Due DECIMAL(18,2),
            Period_Fees_Total DECIMAL(18,2),
            Period_Interest_Total DECIMAL(18,2),
            YTD_Fees DECIMAL(18,2),
            YTD_Interest DECIMAL(18,2),
            Total_Interest_Charges_Paid_YTD DECIMAL(18,2),
            Previous_Statement_Balance DECIMAL(18,2),
            Advances_Debits DECIMAL(18,2),
            Payments_Credits DECIMAL(18,2),
            Interest_Charge DECIMAL(18,2),
            Other_Charges DECIMAL(18,2),
            Current_Statement_Balance DECIMAL(18,2),
            inserted_datetime DATETIME DEFAULT GETDATE()
        )
        """)
    
    # Create rev_credit_transactions table
    if not table_exists(conn, 'rev_credit_transactions'):
        print("  Creating table: rev_credit_transactions")
        cursor.execute("""
        CREATE TABLE [dbo].[rev_credit_transactions] (
            id INT IDENTITY(1,1) PRIMARY KEY,
            Account_Number NVARCHAR(20),
            Note_Number NVARCHAR(20),
            Header_Date NVARCHAR(10),
            Trans_Date NVARCHAR(10),
            Post_Date NVARCHAR(10),
            Description NVARCHAR(500),
            Transaction_Category NVARCHAR(50),
            Advances_Debits_or_IntCharge DECIMAL(18,2),
            Payments_Credits DECIMAL(18,2),
            Balance_Subject_to_IntRate DECIMAL(18,2),
            inserted_datetime DATETIME DEFAULT GETDATE()
        )
        """)
    
    # Create adviceOfRateChange table
    if not table_exists(conn, 'adviceOfRateChange'):
        print("  Creating table: adviceOfRateChange")
        cursor.execute("""
        CREATE TABLE [dbo].[adviceOfRateChange] (
            id INT IDENTITY(1,1) PRIMARY KEY,
            Notice_Type NVARCHAR(50),
            Notice_Code NVARCHAR(20),
            Header_Date NVARCHAR(10),
            Page INT,
            Customer_Name_1 NVARCHAR(100),
            Customer_Name_2 NVARCHAR(100),
            Customer_Name_3 NVARCHAR(100),
            Customer_Name_4 NVARCHAR(100),
            Customer_Name_5 NVARCHAR(100),
            Address_Street NVARCHAR(200),
            Address_CityStateZip NVARCHAR(200),
            Account_Number NVARCHAR(20),
            Note_Number NVARCHAR(20),
            Previous_Rate FLOAT,
            Current_Rate FLOAT,
            Date_of_RateChange NVARCHAR(10),
            inserted_datetime DATETIME DEFAULT GETDATE()
        )
        """)
    
    # Create payoff_notice_only table
    if not table_exists(conn, 'payoff_notice_only'):
        print("  Creating table: payoff_notice_only")
        cursor.execute("""
        CREATE TABLE [dbo].[payoff_notice_only] (
            id INT IDENTITY(1,1) PRIMARY KEY,
            Notice_Type NVARCHAR(50),
            Notice_Code NVARCHAR(20),
            Header_Date NVARCHAR(10),
            Page INT,
            Notice_Date NVARCHAR(10),
            County_Name NVARCHAR(200),
            County_Address NVARCHAR(500),
            Notice_Comment NVARCHAR(MAX),
            Ref_No NVARCHAR(100),
            Account NVARCHAR(20),
            Note NVARCHAR(20),
            Issue_Date NVARCHAR(10),
            Acct_Name NVARCHAR(200),
            Property_At NVARCHAR(500),
            inserted_datetime DATETIME DEFAULT GETDATE()
        )
        """)
    
    # Create past_due_notice_only table
    if not table_exists(conn, 'past_due_notice_only'):
        print("  Creating table: past_due_notice_only")
        cursor.execute("""
        CREATE TABLE [dbo].[past_due_notice_only] (
            id INT IDENTITY(1,1) PRIMARY KEY,
            Notice_Type NVARCHAR(50),
            Notice_Code NVARCHAR(20),
            Header_Date NVARCHAR(10),
            Page INT,
            Customer_Name_1 NVARCHAR(100),
            Customer_Name_2 NVARCHAR(100),
            Customer_Name_3 NVARCHAR(100),
            Customer_Name_4 NVARCHAR(100),
            Customer_Name_5 NVARCHAR(100),
            Address_Street NVARCHAR(200),
            Address_CityStateZip NVARCHAR(200),
            Notice_Date NVARCHAR(10),
            Account_Number NVARCHAR(20),
            Note_Number NVARCHAR(20),
            Officer NVARCHAR(100),
            Branch NVARCHAR(100),
            Loan_Type NVARCHAR(100),
            Due_Date NVARCHAR(10),
            Principal DECIMAL(18,2),
            Interest DECIMAL(18,2),
            Late_Fees DECIMAL(18,2),
            Total_Due DECIMAL(18,2),
            inserted_datetime DATETIME DEFAULT GETDATE()
        )
        """)
    
    conn.commit()

# ============= PROCESSING FUNCTIONS =============
def process_loan_statements(text: str, conn, clear_existing: bool = False) -> dict:
    """Process loan statements and insert to database."""
    print("\n" + "-" * 40)
    print("Processing LOAN STATEMENTS...")
    
    loan_hdr, loan_sum, loan_hist = LoanStatementProcessor.process(text)
    
    stats = {
        'headers': 0,
        'summary': 0,
        'history': 0
    }
    
    if loan_hdr:
        # Create tables if they don't exist
        ensure_tables_exist(conn)
        
        if clear_existing:
            if table_exists(conn, TABLE_MAPPINGS['loan_header']):
                clear_table(conn, TABLE_MAPPINGS['loan_header'])
            if table_exists(conn, TABLE_MAPPINGS['loan_summary']):
                clear_table(conn, TABLE_MAPPINGS['loan_summary'])
            if table_exists(conn, TABLE_MAPPINGS['loan_history']):
                clear_table(conn, TABLE_MAPPINGS['loan_history'])
        
        stats['headers'] = insert_to_table(conn, TABLE_MAPPINGS['loan_header'], loan_hdr)
        print(f"  Inserted {stats['headers']} header records")
        
        stats['summary'] = insert_to_table(conn, TABLE_MAPPINGS['loan_summary'], loan_sum)
        print(f"  Inserted {stats['summary']} summary records")
        
        stats['history'] = insert_to_table(conn, TABLE_MAPPINGS['loan_history'], loan_hist)
        print(f"  Inserted {stats['history']} history records")
        
        if HAVE_SPACY:
            print("  ✓ Enhanced with spaCy NER and classification")
    else:
        print("  No loan statements found")
    
    return stats

def process_rev_credit(text: str, conn, clear_existing: bool = False) -> dict:
    """Process rev credit statements and insert to database."""
    print("\n" + "-" * 40)
    print("Processing REV. CREDIT STATEMENTS...")
    
    rev_hdr, rev_txn = RevCreditProcessor.process(text)
    
    stats = {
        'statements': 0,
        'transactions': 0
    }
    
    if rev_hdr:
        # Create tables if they don't exist
        ensure_tables_exist(conn)
        
        if clear_existing:
            if table_exists(conn, TABLE_MAPPINGS['rev_header']):
                clear_table(conn, TABLE_MAPPINGS['rev_header'])
            if table_exists(conn, TABLE_MAPPINGS['rev_transactions']):
                clear_table(conn, TABLE_MAPPINGS['rev_transactions'])
        
        stats['statements'] = insert_to_table(conn, TABLE_MAPPINGS['rev_header'], rev_hdr)
        print(f"  Inserted {stats['statements']} statement records")
        
        stats['transactions'] = insert_to_table(conn, TABLE_MAPPINGS['rev_transactions'], rev_txn)
        print(f"  Inserted {stats['transactions']} transaction records")
        
        if HAVE_SPACY:
            print("  ✓ Transaction categories added via spaCy")
    else:
        print("  No rev credit statements found")
    
    return stats

def process_advice_rate_change(text: str, conn, clear_existing: bool = False) -> dict:
    """Process advice of rate change notices and insert to database."""
    print("\n" + "-" * 40)
    print("Processing ADVICE OF RATE CHANGE...")
    
    advice_records = AdviceOfRateChangeProcessor.process(text)
    
    stats = {'notices': 0}
    
    if advice_records:
        # Create tables if they don't exist
        ensure_tables_exist(conn)
        
        if clear_existing:
            if table_exists(conn, TABLE_MAPPINGS['advice']):
                clear_table(conn, TABLE_MAPPINGS['advice'])
        
        stats['notices'] = insert_to_table(conn, TABLE_MAPPINGS['advice'], advice_records)
        print(f"  Inserted {stats['notices']} rate change notices")
    else:
        print("  No advice of rate change notices found")
    
    return stats

def process_payoff_notices(text: str, conn, clear_existing: bool = False) -> dict:
    """Process payoff notices and insert to database."""
    print("\n" + "-" * 40)
    print("Processing PAYOFF NOTICES...")
    
    payoff_records = PayoffNoticeProcessor.process(text)
    
    stats = {'notices': 0}
    
    if payoff_records:
        # Create tables if they don't exist
        ensure_tables_exist(conn)
        
        if clear_existing:
            if table_exists(conn, TABLE_MAPPINGS['payoff']):
                clear_table(conn, TABLE_MAPPINGS['payoff'])
        
        stats['notices'] = insert_to_table(conn, TABLE_MAPPINGS['payoff'], payoff_records)
        print(f"  Inserted {stats['notices']} payoff notices")
    else:
        print("  No payoff notices found")
    
    return stats

def process_past_due_notices(text: str, conn, clear_existing: bool = False) -> dict:
    """Process past due notices and insert to database."""
    print("\n" + "-" * 40)
    print("Processing PAST DUE NOTICES...")
    
    past_due_records = PastDueNoticeProcessor.process(text)
    
    stats = {'notices': 0}
    
    if past_due_records:
        # Create tables if they don't exist
        ensure_tables_exist(conn)
        
        if clear_existing:
            if table_exists(conn, TABLE_MAPPINGS['past_due']):
                clear_table(conn, TABLE_MAPPINGS['past_due'])
        
        stats['notices'] = insert_to_table(conn, TABLE_MAPPINGS['past_due'], past_due_records)
        print(f"  Inserted {stats['notices']} past due notices")
    else:
        print("  No past due notices found")
    
    return stats

def main():
    """Main processing function."""
    print("=" * 60)
    print("CIBC BANK STATEMENT PARSER - SQL SERVER VERSION")
    print("=" * 60)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Print spaCy status
    print_spacy_status()
    
    # Check if input file exists
    if not INPUT_PATH.exists():
        print(f"\n✗ Error: Input file not found: {INPUT_PATH}")
        return 1
    
    # Connect to database
    print("\n" + "-" * 40)
    print("Connecting to SQL Server...")
    try:
        conn = get_db_connection()
        print("✓ Connected successfully")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return 1
    
    # Read input file
    print(f"\nReading input file: {INPUT_PATH}")
    text = read_text(INPUT_PATH)
    print(f"Total size: {len(text):,} characters")
    
    # Ask user about clearing existing data
    if len(sys.argv) > 1 and sys.argv[1] == '--clear':
        clear_existing = True
        print("\nClearing existing data (--clear flag provided)")
    else:
        response = input("\nClear existing data from tables before inserting? (y/n): ").lower()
        clear_existing = response == 'y'
    
    # Process all document types
    all_stats = {}
    
    try:
        all_stats['loan'] = process_loan_statements(text, conn, clear_existing)
        all_stats['rev_credit'] = process_rev_credit(text, conn, clear_existing)
        all_stats['advice'] = process_advice_rate_change(text, conn, clear_existing)
        all_stats['payoff'] = process_payoff_notices(text, conn, clear_existing)
        all_stats['past_due'] = process_past_due_notices(text, conn, clear_existing)
        
    except Exception as e:
        print(f"\n✗ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        return 1
    
    # Close connection
    conn.close()
    
    # Print summary
    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE!")
    print("=" * 60)
    
    print("\nSummary of inserted records:")
    print(f"  Loan Statements:")
    print(f"    - Headers: {all_stats['loan']['headers']}")
    print(f"    - Summary: {all_stats['loan']['summary']}")
    print(f"    - History: {all_stats['loan']['history']}")
    print(f"  Rev Credit:")
    print(f"    - Statements: {all_stats['rev_credit']['statements']}")
    print(f"    - Transactions: {all_stats['rev_credit']['transactions']}")
    print(f"  Advice of Rate Change: {all_stats['advice']['notices']}")
    print(f"  Payoff Notices: {all_stats['payoff']['notices']}")
    print(f"  Past Due Notices: {all_stats['past_due']['notices']}")
    
    total_records = (
        all_stats['loan']['headers'] + all_stats['loan']['summary'] + 
        all_stats['loan']['history'] + all_stats['rev_credit']['statements'] + 
        all_stats['rev_credit']['transactions'] + all_stats['advice']['notices'] + 
        all_stats['payoff']['notices'] + all_stats['past_due']['notices']
    )
    
    print(f"\nTotal records inserted: {total_records}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())