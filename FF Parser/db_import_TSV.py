import os
import pandas as pd
from sqlalchemy import create_engine

# Directory path where your TSV files are located
DIRECTORY_PATH = r'C:\Source\Obfuscate\Python\FF Parser\output'  # Update this path to your directory

# Database connection details (SQL Server, using Integrated Security)
DATABASE_URL = 'mssql+pyodbc://@jmplabsv01/terrorbytesDB?driver=ODBC+Driver+17+for+SQL+Server'

# Create SQLAlchemy engine for database connection
engine = create_engine(DATABASE_URL)

# List all TSV files in the directory
tsv_files = [f for f in os.listdir(DIRECTORY_PATH) if f.endswith('.tsv')]

# Loop through all TSV files in the directory
for tsv_file in tsv_files:
    tsv_file_path = os.path.join(DIRECTORY_PATH, tsv_file)

    # Check if the file exists before processing
    if not os.path.exists(tsv_file_path):
        print(f"Error: The file at {tsv_file_path} does not exist.")
        continue  # Skip this file and continue with the next one
    
    print(f"Processing file: {tsv_file_path}")
    
    try:
        # Read the TSV file into a pandas DataFrame
        df = pd.read_csv(tsv_file_path, sep='\t')

        # Extract table name from the filename (without extension)
        table_name = os.path.splitext(tsv_file)[0]

        # Insert data into SQL database table
        try:
            df.to_sql(table_name, engine, if_exists='append', index=False)
            print(f"Data successfully inserted into table '{table_name}' in the 'terrorbytesDB' database.")
        except Exception as e:
            print(f"Error inserting data into table {table_name}: {e}")
    
    except Exception as e:
        print(f"Error reading the file {tsv_file_path}: {e}")
