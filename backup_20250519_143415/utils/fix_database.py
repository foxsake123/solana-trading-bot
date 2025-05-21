import os
import sys
import logging
import sqlite3
from config import BotConfiguration

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('db_fix')

def reset_database():
    """
    Reset the database completely by deleting the file and recreating it
    """
    db_path = BotConfiguration.DB_PATH
    
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Delete the existing database file if it exists
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            logger.info(f"Deleted existing database file: {db_path}")
        except Exception as e:
            logger.error(f"Failed to delete database file: {e}")
            return False
    
    # Create a new database with the correct schema
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        
        # Create tokens table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            contract_address TEXT PRIMARY KEY,
            ticker TEXT,
            name TEXT,
            launch_date TEXT,
            safety_score REAL,
            volume_24h REAL,
            price_usd REAL,
            liquidity_usd REAL,
            mcap REAL,
            holders INTEGER,
            liquidity_locked BOOLEAN,
            last_updated TEXT
        )
        ''')
        
        # Create trades table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_address TEXT,
            action TEXT,
            amount REAL,
            price REAL,
            timestamp TEXT,
            tx_hash TEXT
        )
        ''')
        
        # Create social_mentions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS social_mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_address TEXT,
            platform TEXT,
            post_id TEXT,
            author TEXT,
            content TEXT,
            timestamp TEXT,
            engagement_score REAL
        )
        ''')
        
        conn.commit()
        logger.info("Database reset successfully with correct schema")
        return True
    
    except Exception as e:
        logger.error(f"Error creating new database: {e}")
        return False
    
    finally:
        conn.close()

def fix_database_schema():
    """
    Fix database schema without deleting existing data
    """
    db_path = BotConfiguration.DB_PATH
    
    # Check if the database exists
    if not os.path.exists(db_path):
        logger.info("Database doesn't exist. Creating new database...")
        return reset_database()
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        
        # Check if the tokens table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tokens'")
        if not cursor.fetchone():
            logger.info("Tokens table doesn't exist. Recreating tables...")
            return reset_database()
        
        # Check for required columns in tokens table
        cursor.execute("PRAGMA table_info(tokens)")
        columns = [info[1] for info in cursor.fetchall()]
        
        # Add missing columns
        if 'price_usd' not in columns:
            logger.info("Adding price_usd column to tokens table")
            cursor.execute("ALTER TABLE tokens ADD COLUMN price_usd REAL DEFAULT 0.0")
        
        if 'liquidity_usd' not in columns:
            logger.info("Adding liquidity_usd column to tokens table")
            cursor.execute("ALTER TABLE tokens ADD COLUMN liquidity_usd REAL DEFAULT 0.0")
            
        if 'mcap' not in columns:
            logger.info("Adding mcap column to tokens table")
            cursor.execute("ALTER TABLE tokens ADD COLUMN mcap REAL DEFAULT 0.0")
            
        if 'holders' not in columns:
            logger.info("Adding holders column to tokens table")
            cursor.execute("ALTER TABLE tokens ADD COLUMN holders INTEGER DEFAULT 0")
        
        conn.commit()
        logger.info("Database schema fixed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error fixing database schema: {e}")
        return False
    
    finally:
        conn.close()

if __name__ == "__main__":
    # Check if user wants to reset or just fix
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        logger.info("Resetting database completely...")
        if reset_database():
            logger.info("Database reset successfully!")
        else:
            logger.error("Failed to reset database.")
    else:
        logger.info("Fixing database schema...")
        if fix_database_schema():
            logger.info("Database schema fixed successfully!")
        else:
            logger.error("Failed to fix database schema. Try running with --reset flag.")
