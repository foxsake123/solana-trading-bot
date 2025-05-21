
# Fix Balance and Position Calculations
import sqlite3
import json
import logging
from datetime import datetime, timezone
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fix_balance')

# Database path - will try multiple possible paths
DEFAULT_DB_PATH = "solana_trader.db"
POSSIBLE_DB_PATHS = [
    "solana_trader.db",
    "./solana_trader.db",
    "../solana_trader.db",
    "data/solana_trader.db",
    "./data/solana_trader.db"
]
BOT_CONTROL_FILE = "bot_control.json"

def diagnose_database():
    """
    Diagnose database issues
    """
    # Check current directory
    current_dir = os.getcwd()
    logger.info(f"Current working directory: {current_dir}")
    
    # List files in current directory
    files = os.listdir(current_dir)
    db_files = [f for f in files if f.endswith('.db')]
    logger.info(f"Database files in current directory: {db_files}")
    
    # Try to locate database file
    db_path = None
    
    for path in POSSIBLE_DB_PATHS:
        if os.path.exists(path):
            db_path = path
            logger.info(f"Found database at: {db_path}")
            break
    
    if not db_path and db_files:
        # Use the first .db file found
        db_path = db_files[0]
        logger.info(f"Using first available database: {db_path}")
    
    if not db_path:
        logger.error("No database file found!")
        return False
    
    # Try to connect to database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if database has tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if tables:
            table_names = [table[0] for table in tables]
            logger.info(f"Tables in database {db_path}: {table_names}")
            
            # Check each table
            for table in table_names:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]
                logger.info(f"Table {table} columns: {column_names}")
                
                # Check row count
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"Table {table} has {count} rows")
                
                # Sample data if there are rows
                if count > 0:
                    cursor.execute(f"SELECT * FROM {table} LIMIT 1")
                    sample = cursor.fetchone()
                    logger.info(f"Sample data from {table}: {sample}")
        else:
            logger.warning(f"Database {db_path} exists but contains no tables")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error connecting to database {db_path}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def fix_wallet_balance():
    """
    Fix wallet balance and position calculations
    """
    logger.info("Starting wallet balance and position fix...")
    
    # Run diagnostics first
    diagnose_database()
    
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
            logger.error(f"Database {db_path} exists but contains no tables. Is this the correct database?")
            
            # Check if we need to create tables
            logger.info("Would you like to create necessary tables for the wallet balance? (y/n)")
            choice = input().lower()
            
            if choice == 'y' or choice == 'yes':
                # Create basic tables for the trading bot
                logger.info("Creating basic tables...")
                
                # Create wallet balance table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS wallet_balance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    balance_sol REAL NOT NULL,
                    last_updated TEXT NOT NULL
                )
                """)
                
                # Create active orders table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_address TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    name TEXT,
                    amount REAL NOT NULL,
                    buy_price REAL NOT NULL,
                    entry_time TEXT NOT NULL,
                    current_price_usd REAL,
                    token_quantity REAL,
                    invested_usd REAL,
                    current_value_usd REAL,
                    pnl_usd REAL,
                    pnl_percent REAL,
                    multiple REAL
                )
                """)
                
                # Create trading history table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_address TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    action TEXT NOT NULL,
                    amount REAL NOT NULL,
                    price REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    tx_hash TEXT,
                    gain_loss_sol REAL,
                    percentage_change REAL,
                    price_multiple REAL
                )
                """)
                
                # Insert initial wallet balance
                cursor.execute("""
                INSERT INTO wallet_balance (balance_sol, last_updated)
                VALUES (?, ?)
                """, (1.0, datetime.now(timezone.utc).isoformat()))
                
                conn.commit()
                logger.info("Basic tables created successfully")
                
                # Get table names again
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
            else:
                logger.info("Skipping table creation")
                return False
        
        table_names = [table['name'] for table in tables]
        logger.info(f"Found tables in database: {table_names}")
        
        # Locate the active positions table
        positions_table = None
        for table in table_names:
            if 'active' in table.lower() or 'position' in table.lower() or 'order' in table.lower():
                # This might be our positions table, check its schema
                try:
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = cursor.fetchall()
                    column_names = [col['name'] for col in columns]
                    
                    # Check if this table has position-like columns
                    if 'amount' in column_names and ('contract_address' in column_names or 'ticker' in column_names):
                        positions_table = table
                        logger.info(f"Found active positions table: {positions_table}")
                        break
                except:
                    continue
        
        if not positions_table:
            logger.error("Could not find active positions table in database")
            return False
        
        # Get starting balance for simulation mode
        starting_balance = 1.0  # Default starting balance is 1.0 SOL
        
        # Load bot control settings to get simulation mode
        simulation_mode = True  # Default to simulation mode
        if os.path.exists(BOT_CONTROL_FILE):
            try:
                with open(BOT_CONTROL_FILE, 'r') as f:
                    control = json.load(f)
                    simulation_mode = control.get('simulation_mode', True)
            except Exception as e:
                logger.error(f"Error loading bot control file: {e}")
        
        # If in simulation mode, verify the wallet balance
        if simulation_mode:
            logger.info("Operating in simulation mode, checking wallet balance...")
            
            # Get active positions
            cursor.execute(f"SELECT * FROM {positions_table}")
            active_positions = cursor.fetchall()
            
            if active_positions:
                # Calculate total invested in active positions
                total_invested = 0.0
                for position in active_positions:
                    amount = float(position['amount']) if 'amount' in position else 0.0
                    total_invested += amount
                
                logger.info(f"Found {len(active_positions)} active positions totaling {total_invested} SOL")
                
                # Calculate remaining balance
                remaining_balance = starting_balance - total_invested
                
                # Check if wallet_balance table exists
                wallet_table = None
                for table in table_names:
                    if 'wallet' in table.lower() or 'balance' in table.lower():
                        wallet_table = table
                        break
                
                if wallet_table:
                    # Check if we need to update the wallet balance table
                    cursor.execute(f"SELECT * FROM {wallet_table} LIMIT 1")
                    balance_row = cursor.fetchone()
                    
                    if balance_row:
                        # Find the balance column
                        balance_col = None
                        for key in balance_row.keys():
                            if 'balance' in key.lower() and 'sol' in key.lower():
                                balance_col = key
                                break
                        
                        if not balance_col:
                            # Just use the first column that might be a balance
                            for key in balance_row.keys():
                                if 'balance' in key.lower() or 'sol' in key.lower() or 'amount' in key.lower():
                                    balance_col = key
                                    break
                        
                        if balance_col:
                            current_balance = float(balance_row[balance_col])
                            
                            # If current stored balance is not correctly accounting for positions
                            if abs(current_balance - remaining_balance) > 0.001:  # Small epsilon for float comparison
                                logger.info(f"Updating wallet balance from {current_balance} to {remaining_balance}")
                                
                                # Update the wallet balance - find the update column
                                update_col = None
                                for key in balance_row.keys():
                                    if 'updated' in key.lower() or 'timestamp' in key.lower() or 'time' in key.lower():
                                        update_col = key
                                        break
                                
                                if update_col:
                                    cursor.execute(
                                        f"UPDATE {wallet_table} SET {balance_col} = ?, {update_col} = ?",
                                        (remaining_balance, datetime.now(timezone.utc).isoformat())
                                    )
                                else:
                                    cursor.execute(
                                        f"UPDATE {wallet_table} SET {balance_col} = ?",
                                        (remaining_balance,)
                                    )
                                
                                logger.info("Wallet balance updated successfully")
                            else:
                                logger.info(f"Wallet balance is already correct: {current_balance}")
                        else:
                            logger.warning("Could not identify balance column in wallet table")
                    else:
                        logger.warning(f"No records in wallet balance table {wallet_table}")
                else:
                    logger.warning("No wallet balance table found in database")
            else:
                logger.info(f"No active positions found in {positions_table}")
        else:
            logger.info("Operating in real trading mode, not modifying wallet balance")
        
        # Commit changes
        conn.commit()
        
        # Verify position calculations
        cursor.execute(f"SELECT * FROM {positions_table}")
        positions = cursor.fetchall()
        
        if positions:
            logger.info(f"Verifying calculations for {len(positions)} active positions")
            
            for position in positions:
                position_id = position['id'] if 'id' in position else 'unknown'
                ticker = position['ticker'] if 'ticker' in position else position['contract_address'] if 'contract_address' in position else 'unknown'
                
                # Check for investment amount
                amount = float(position['amount']) if 'amount' in position else 0.0
                logger.info(f"Position {position_id} ({ticker}): {amount} SOL invested")
        
        # Close connection
        conn.close()
        
        logger.info("Wallet balance and position fix completed")
        return True
    
    except Exception as e:
        logger.error(f"Error fixing wallet balance: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    fix_wallet_balance()


