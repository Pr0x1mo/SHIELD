# SHIELD = spaCy-powered Handling, Ingestion & Entity-Level De-identification

A Python-based data processing pipeline that imports unstructured financial documents, structures them using NLP, stores them in SQL Server, and applies data obfuscation for privacy compliance.

## Overview

SHIELD is designed to process CIBC bank statements and other financial documents by:
1. **Importing** unstructured text data from fixed-width format files
2. **Parsing** and structuring the data using SpaCy NLP for enhanced extraction
3. **Storing** structured data in SQL Server tables
4. **Obfuscating** sensitive information using Faker for test/development environments

## Features

- **Multi-document Support**: Processes loan statements, credit statements, rate change notices, payoff notices, and past due notices
- **NLP Enhancement**: Uses SpaCy for improved name recognition, address extraction, and transaction classification
- **Deterministic Pseudonymization**: Maintains referential integrity across tables while masking sensitive data
- **GUI Dashboard**: Central control panel for all processing operations
- **Modular Architecture**: Separate processors for each document type

## Prerequisites

### Required Software
- Python 3.8 or higher
- SQL Server (tested with SQL Server 2019)
- ODBC Driver 17 for SQL Server

### Python Dependencies
pip install pyodbc
pip install faker
pip install spacy
pip install tkinter
python -m spacy download en_core_web_sm

## Installation

1. Clone the repository:
git clone https://github.com/Pr0x1mo/SHIELD.git
cd SHIELD

2. Install dependencies:
pip install -r requirements.txt
python -m spacy download en_core_web_sm

3. Configure database connection in db_utils.py:
SERVER = 'your_server'
DATABASE = 'your_database'
USERNAME = 'your_username'
PASSWORD = 'your_password'

4. Set environment variable for deterministic pseudonymization (optional):
Windows: setx SHIELD_PSEUDO_KEY "your-long-random-secret-key"
Linux/Mac: export SHIELD_PSEUDO_KEY="your-long-random-secret-key"

## Usage

### Quick Start

Run the main dashboard GUI:
python shield_dashboard_gui.py

The dashboard provides buttons for:
- **Core Pipeline**: Detection & Obfuscation, Feedback Loop Monitor, Reports/Analytics
- **Proximus' Pipeline**: Import unstructured data, Obfuscate data
- **Configuration**: Various configuration and testing tools
- **Model Training**: SpaCy model training utilities
- **Utilities**: Additional parsing tools

### Manual Processing

#### 1. Import and Structure Data
python "FF Parser/cibc_parser_sql.py"

This will:
- Read from input/SampleFileSTMT.txt
- Parse all document types
- Create necessary SQL tables
- Insert structured data to database

#### 2. Obfuscate Data
python "FF Parser/data_obfuscator.py"

This will:
- Read from production tables
- Apply masking rules to sensitive fields
- Write to Masked schema in SQL Server
- Maintain referential integrity with deterministic pseudonymization

## Project Structure

SHIELD/
├── shield_dashboard_gui.py     # Main GUI application
├── FF Parser/
│   ├── cibc_parser_sql.py     # Main parser script
│   ├── data_obfuscator.py     # Data masking script
│   ├── processors.py          # Document type processors
│   ├── db_utils.py            # Database utilities
│   ├── common_utils.py        # Shared utilities & NLP
│   └── input/                 # Input files directory
│       └── SampleFileSTMT.txt # Sample input file
└── SHIELD/                     # Additional SHIELD modules

## Database Schema

### Production Tables (dbo schema)
- **loan_bill_header**: Loan statement headers with customer info
- **loan_bill_summary**: Loan summary details
- **loan_bill_history**: Transaction history for loans
- **rev_credit_statement**: Revolving credit statements
- **rev_credit_transactions**: Credit card transactions
- **adviceOfRateChange**: Rate change notifications
- **payoff_notice_only**: Payoff notices
- **past_due_notice_only**: Past due notices

### Masked Tables (Masked schema)
- Same structure as production tables but with obfuscated data
- Maintains referential integrity through deterministic pseudonymization

## Obfuscation Rules

### Fields Obfuscated:
- **Names**: Replaced with realistic fake names (Faker)
- **Addresses**: Replaced with fake addresses
- **Account/Note Numbers**: Deterministically pseudonymized (last 4 digits preserved)
- **SSNs**: Deterministically masked (last 4 preserved)
- **Monetary Amounts**: +/- 10% random variance
- **Dates**: Shifted by random days (-30 to +30)
- **Interest Rates**: +/- 0.5% variance
- **Descriptions**: Generalized to category types

### Deterministic Pseudonymization
- Uses HMAC-SHA256 for consistent mapping
- Same input always produces same output
- Preserves format and separators
- Optionally preserves last N digits for support/debugging

## Configuration

### Environment Variables
- `SHIELD_PSEUDO_KEY`: Secret key for deterministic pseudonymization

### File Paths
Update paths in `shield_dashboard_gui.py`:
- `FF_PARSER_DIR`: Path to FF Parser directory
- `CIBC_PARSER`: Path to cibc_parser_sql.py
- `DATA_OBFUSCATOR`: Path to data_obfuscator.py

### Input File Location
Default: `FF Parser/input/SampleFileSTMT.txt`
Update in `cibc_parser_sql.py` if needed

## Supported Document Types

1. **Loan Statements (R-06090-002)**
   - Header information with customer details
   - Summary of notes/balances
   - Transaction history

2. **Revolving Credit Statements (R-06088-001)**
   - Statement summary
   - Transaction details
   - Fee and interest calculations

3. **Advice of Rate Change (R-06061-001)**
   - Rate change notifications
   - Previous and new rates

4. **Payoff Notices (R-07362-001)**
   - Payoff details
   - Property information

5. **Past Due Notices (R-06385-XXX)**
   - Past due amounts
   - Payment details

## Troubleshooting

### SpaCy Not Loading
If you see "spaCy not installed" message:
1. Install spacy: pip install spacy
2. Download model: python -m spacy download en_core_web_sm
3. The system will still work with regex-only extraction

### Database Connection Issues
1. Verify SQL Server is running
2. Check credentials in db_utils.py
3. Ensure ODBC Driver 17 is installed
4. Test connection with SQL Server Management Studio

### Missing Tables
Tables are auto-created on first run. If issues persist:
1. Check user has CREATE TABLE permissions
2. Verify database exists
3. Run with --clear flag to reset: python cibc_parser_sql.py --clear

## Security Considerations

1. **Never commit real credentials** - Use environment variables
2. **Set strong SHIELD_PSEUDO_KEY** - Critical for secure pseudonymization
3. **Restrict database access** - Use principle of least privilege
4. **Audit masked data** - Verify no sensitive data leaks
5. **Separate environments** - Never run obfuscation on production database


## Authors

- Proximus

## Acknowledgments

- SpaCy for NLP capabilities
- Faker for realistic test data generation
- pyodbc for SQL Server connectivity
