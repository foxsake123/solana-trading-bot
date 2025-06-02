# check_db_columns.py
import sqlite3
import pandas as pd

def check_database_schema():
    """Check what columns are available in the database"""
    
    conn = sqlite3.connect('data/sol_bot.db')
    
    print("🔍 Checking database schema...\n")
    
    # Check tokens table columns
    print("TOKENS table columns:")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(tokens)")
    token_columns = cursor.fetchall()
    for col in token_columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Check trades table columns
    print("\nTRADES table columns:")
    cursor.execute("PRAGMA table_info(trades)")
    trade_columns = cursor.fetchall()
    for col in trade_columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Get sample token data to see what's actually stored
    print("\nSample token data:")
    tokens_df = pd.read_sql_query("SELECT * FROM tokens LIMIT 1", conn)
    if not tokens_df.empty:
        for col in tokens_df.columns:
            print(f"  - {col}: {tokens_df[col].iloc[0]}")
    else:
        print("  No tokens found in database")
    
    conn.close()

if __name__ == "__main__":
    check_database_schema()