# Fix Timestamp Format in Database
import sqlite3
import logging
from datetime import datetime, timezone
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fix_timestamps')

# Try multiple possible database paths
POSSIBLE_DB_PATHS = [
    "solana_trader.db",
    "./solana_trader.db",
    "../solana_trader.db",
    "data/solana_trader.db",
    "./data/solana_trader.db"
]

def fix_timestamp_formats():
    """
    Fix timestamp formats in the database
    """
    logger.info("Starting timestamp format fix...")
    
    # Find the database
    db_path = None
    for path in POSSIBLE_DB_PATHS:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        # Check for any .db file
        files = os.listdir('.')
        db_files = [f for f in files if f.endswith('.db')]
        if db_files:
            db_path = db_files[0]
    
    if not db_path:
        logger.error("Cannot find database file. Please check the file exists and try again.")
        return False
    
    logger.info(f"Using database: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Use dictionary cursor
        cursor = conn.cursor()
        
        # Check table names first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            logger.error("No tables found in database")
            return False
            
        table_names = [table['name'] for table in tables]
        logger.info(f"Found tables in database: {table_names}")
        
        # Check each table for timestamp columns
        timestamp_columns_found = False
        
        for table in table_names:
            # Get column info
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            column_names = [col['name'] for col in columns]
            
            # Find timestamp-like columns
            timestamp_columns = []
            for col in column_names:
                if 'time' in col.lower() or 'date' in col.lower() or 'timestamp' in col.lower():
                    timestamp_columns.append(col)
            
            if timestamp_columns:
                # Sample data to check format
                cursor.execute(f"SELECT * FROM {table} LIMIT 10")
                rows = cursor.fetchall()
                
                if rows:
                    # Check each timestamp column in sampled rows
                    for col in timestamp_columns:
                        for row in rows:
                            if col in row.keys() and row[col]:
                                timestamp_value = row[col]
                                logger.info(f"Found timestamp in {table}.{col}: {timestamp_value}")
                                timestamp_columns_found = True
                                
                                # Check if timestamp needs fixing (contains ET but is not ISO format)
                                if " ET" in str(timestamp_value) and "T" not in str(timestamp_value):
                                    logger.info(f"Table {table}, column {col} has timestamps that need fixing")
                                    
                                    # Update the table to convert all timestamps to ISO format
                                    try:
                                        # Get all rows with ET timestamps
                                        cursor.execute(f"SELECT * FROM {table} WHERE {col} LIKE '% ET'")
                                        et_rows = cursor.fetchall()
                                        
                                        for et_row in et_rows:
                                            row_id = et_row['id']
                                            et_timestamp = et_row[col]
                                            
                                            # Convert to ISO format
                                            try:
                                                # Remove ET suffix
                                                clean_ts = et_timestamp.replace(' ET', '')
                                                
                                                # Parse with appropriate format
                                                if 'AM' in clean_ts or 'PM' in clean_ts:
                                                    dt = datetime.strptime(clean_ts, "%Y-%m-%d %I:%M:%S %p")
                                                else:
                                                    dt = datetime.strptime(clean_ts, "%Y-%m-%d %H:%M:%S")
                                                
                                                # Convert to ISO format
                                                iso_timestamp = dt.isoformat()
                                                
                                                # Update the row
                                                cursor.execute(f"UPDATE {table} SET {col} = ? WHERE id = ?", 
                                                              (iso_timestamp, row_id))
                                                
                                                logger.info(f"Converted timestamp: {et_timestamp} -> {iso_timestamp}")
                                            except Exception as e:
                                                logger.error(f"Error converting timestamp {et_timestamp}: {e}")
                                        
                                        # Commit changes
                                        conn.commit()
                                        logger.info(f"Updated timestamps in {table}.{col}")
                                    except Exception as e:
                                        logger.error(f"Error updating timestamps in {table}.{col}: {e}")
                
        if not timestamp_columns_found:
            logger.info("No timestamp columns found that need fixing")
        
        # Close connection
        conn.close()
        
        logger.info("Timestamp format fix completed")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing timestamp formats: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    fix_timestamp_formats()
