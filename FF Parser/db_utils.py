# -*- coding: utf-8 -*-
"""
db_utils.py - Database utilities for CIBC Parser
Handles all SQL Server connections and operations
"""

import pyodbc
from typing import List, Dict, Any, Optional
from datetime import datetime
# SQL Server Connection Configuration
SERVER = 'jmplabsv04'
DATABASE = 'terrorbytesDB'
USERNAME = 'Proximo'
PASSWORD = 'Serpahim25'

# Connection string for SQL Server
CONNECTION_STRING = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}'

def get_db_connection():
    """Create and return a database connection."""
    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise

def table_exists(conn, table_name: str, schema: str = 'dbo') -> bool:
    """Check if a table exists in the database."""
    cursor = conn.cursor()
    query = """
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
    """
    cursor.execute(query, (schema, table_name))
    return cursor.fetchone()[0] > 0

def create_schema_if_not_exists(conn, schema_name: str):
    """Create a schema if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute(f"""
    IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = '{schema_name}')
    BEGIN
        EXEC('CREATE SCHEMA {schema_name}')
    END
    """)
    conn.commit()

def clear_table(conn, table_name: str, schema: str = 'dbo'):
    """Clear existing data from table."""
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM [{schema}].[{table_name}]")
    conn.commit()
    print(f"Cleared existing data from {schema}.{table_name}")

from datetime import datetime
# ...

def insert_to_table(conn, table_name: str, rows: List[Dict[str, Any]], schema: str = 'dbo') -> int:
    """Generic function to insert rows into a table, auto-setting inserted_datetime when available."""
    if not rows:
        return 0

    cursor = conn.cursor()

    # Get destination columns
    dest_cols_info = get_table_columns(conn, table_name, schema)  # uses INFORMATION_SCHEMA
    dest_cols = [c['name'] for c in dest_cols_info]
    dest_cols_lower = {c.lower() for c in dest_cols}
    has_inserted_dt = 'inserted_datetime' in dest_cols_lower

    # Build columns list from row keys (skip identity), and add inserted_datetime if needed
    excluded = {'id'}
    base_cols = [col for col in rows[0].keys() if col.lower() not in excluded and col in dest_cols]
    columns = base_cols[:]
    if has_inserted_dt and 'inserted_datetime' not in {c.lower() for c in columns}:
        columns.append('inserted_datetime')

    placeholders = ', '.join(['?' for _ in columns])
    columns_str = ', '.join([f'[{col}]' for col in columns])

    insert_query = f"INSERT INTO [{schema}].[{table_name}] ({columns_str}) VALUES ({placeholders})"

    inserted = 0
    for row in rows:
        try:
            values = [
                (datetime.now() if col.lower() == 'inserted_datetime' else row.get(col))
                for col in columns
            ]
            cursor.execute(insert_query, values)
            inserted += 1
        except Exception as e:
            print(f"Error inserting row into {schema}.{table_name}: {e}")
            clean_row = {k: v for k, v in row.items() if k.lower() not in excluded and k.lower() != 'inserted_datetime'}
            print(f"Row data (without id/inserted_datetime): {clean_row}")

    conn.commit()
    return inserted


def fetch_all_from_table(conn, table_name: str, schema: str = 'dbo', 
                         columns: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Fetch all rows from a table as list of dictionaries."""
    cursor = conn.cursor()
    
    if columns:
        columns_str = ', '.join([f'[{col}]' for col in columns])
    else:
        columns_str = '*'
    
    query = f"SELECT {columns_str} FROM [{schema}].[{table_name}]"
    cursor.execute(query)
    
    # Get column names
    col_names = [desc[0] for desc in cursor.description]
    
    # Fetch all rows and convert to dictionaries
    rows = []
    for row in cursor.fetchall():
        rows.append(dict(zip(col_names, row)))
    
    return rows

def copy_table_structure(conn, source_table: str, dest_table: str, 
                        source_schema: str = 'dbo', dest_schema: str = 'dbo'):
    """Copy table structure from source to destination (no data)."""
    cursor = conn.cursor()
    
    # Create schema if needed
    if dest_schema != 'dbo':
        create_schema_if_not_exists(conn, dest_schema)
    
    # Drop destination table if exists
    cursor.execute(f"""
    IF EXISTS (SELECT * FROM sys.tables t 
               JOIN sys.schemas s ON t.schema_id = s.schema_id 
               WHERE s.name = '{dest_schema}' AND t.name = '{dest_table}')
        DROP TABLE [{dest_schema}].[{dest_table}]
    """)
    
    # Copy structure
    cursor.execute(f"""
    SELECT TOP 0 * 
    INTO [{dest_schema}].[{dest_table}]
    FROM [{source_schema}].[{source_table}]
    """)
    
    conn.commit()
    print(f"Created table {dest_schema}.{dest_table} from {source_schema}.{source_table} structure")

def execute_query(conn, query: str, params: Optional[tuple] = None):
    """Execute a custom query."""
    cursor = conn.cursor()
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    conn.commit()

def get_table_columns(conn, table_name: str, schema: str = 'dbo') -> List[Dict[str, Any]]:
    """Get column information for a table."""
    cursor = conn.cursor()
    query = """
    SELECT 
        COLUMN_NAME,
        DATA_TYPE,
        CHARACTER_MAXIMUM_LENGTH,
        IS_NULLABLE,
        COLUMN_DEFAULT
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
    ORDER BY ORDINAL_POSITION
    """
    cursor.execute(query, (schema, table_name))
    
    columns = []
    for row in cursor.fetchall():
        columns.append({
            'name': row[0],
            'type': row[1],
            'max_length': row[2],
            'nullable': row[3] == 'YES',
            'default': row[4]
        })
    
    return columns