#!/usr/bin/env python
"""Test database connection"""
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2 import OperationalError

# Load environment variables from .env
load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env file")
    exit(1)

print(f"Testing database connection...")
print(f"Database URL: {DATABASE_URL[:50]}...")  # Hide credentials in output

try:
    # Parse the database URL and connect
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Execute a simple query to verify connection
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    
    print(f"\n✅ Database connected successfully!")
    print(f"PostgreSQL Version: {db_version[0]}")
    
    # List tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    
    tables = cursor.fetchall()
    print(f"\nTables in database: {len(tables)}")
    if tables:
        for table in tables:
            print(f"  - {table[0]}")
    else:
        print("  (No tables found)")
    
    cursor.close()
    conn.close()
    
except OperationalError as e:
    print(f"\n❌ Database connection failed!")
    print(f"Error: {e}")
    exit(1)
except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    exit(1)
