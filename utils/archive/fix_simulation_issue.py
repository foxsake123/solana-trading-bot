# fix_simulation_issue.py - Script to fix simulation token trading in real mode

import os
import json
import logging
import sqlite3
from datetime import datetime, timezone

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fix_script')

# Configuration
BOT_CONTROL_FILE = "bot_control.json"
DB_PATH = "solana_trader.db"

def is_simulation_token(contract_address):
    """Check if a token is a simulation token"""
    if not contract_address:
        return False
        
    # Check common simulation token patterns
    sim_patterns = ["sim", "test", "demo", "mock", "fake", "dummy"]
    lower_address = contract_address.lower()
    
    for pattern in sim_patterns:
        if pattern in lower_address:
            return True
            
    # Check for specific simulation token format
    if contract_address.startswith(("Sim0", "Sim1", "Sim2", "Sim3", "Sim4")) and "TopGainer" in contract_address:
        return True
        
    return False

def update_control_file():
    """Update the control file to default to simulation mode"""
    if not os.path.exists(BOT_CONTROL_FILE):
        logger.error(f"Control file {BOT_CONTROL_FILE} not found")
        return False
        
    try:
        # Load current control settings
        with open(BOT_CONTROL_FILE, 'r') as f:
            control = json.load(f)
            
        # Check if already in simulation mode
        if control.get('simulation_mode', True):
            logger.info("Control file already set to simulation mode")
            return True
            
        # Set to simulation mode
        control['simulation_mode'] = True
        
        # Also pause the bot for safety
        control['running'] = False
        
        # Save updated control
        with open(BOT_CONTROL_FILE, 'w') as f:
            json.dump(control, f, indent=4)
            
        logger.info("Updated control file to use simulation mode and paused the bot")
        return True
    except Exception as e:
        logger.error(f"Error updating control file: {e}")
        return False

def fix_active_positions():
    """Fix active positions by marking simulation tokens"""
    if not os.path.exists(DB_PATH):
        logger.error(f"Database file {DB_PATH} not found")
        return False
        
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Find active positions table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%active%' OR name LIKE '%order%' OR name LIKE '%position%'")
        tables = cursor.fetchall()
        
        if not tables:
            logger.error("No active positions table found")
            return False
            
        # Assume first matching table is the active positions table
        active_table = tables[0][0]
        logger.info(f"Found active positions table: {active_table}")
        
        # Get schema to find column names
        cursor.execute(f"PRAGMA table_info({active_table})")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Check if table has necessary columns
        if 'contract_address' not in column_names:
            logger.error(f"Table {active_table} does not have contract_address column")
            return False
            
        # Get active positions
        cursor.execute(f"SELECT * FROM {active_table}")
        positions = cursor.fetchall()
        position_dicts = [dict(zip(column_names, pos)) for pos in positions]
        
        # Find simulation tokens
        sim_tokens = [pos for pos in position_dicts if is_simulation_token(pos.get('contract_address'))]
        
        if not sim_tokens:
            logger.info("No simulation tokens found in active positions")
            return True
            
        logger.info(f"Found {len(sim_tokens)} simulation tokens in active positions")
        
        # Add a is_simulation column if it doesn't exist
        if 'is_simulation' not in column_names:
            try:
                cursor.execute(f"ALTER TABLE {active_table} ADD COLUMN is_simulation INTEGER DEFAULT 0")
                logger.info(f"Added is_simulation column to {active_table}")
            except:
                logger.info("is_simulation column might already exist")
        
        # Mark simulation tokens
        for token in sim_tokens:
            contract_address = token.get('contract_address')
            try:
                cursor.execute(f"UPDATE {active_table} SET is_simulation = 1 WHERE contract_address = ?", (contract_address,))
                logger.info(f"Marked {contract_address} as simulation token")
            except Exception as e:
                logger.error(f"Error marking {contract_address}: {e}")
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        logger.info("Successfully updated active positions")
        return True
    except Exception as e:
        logger.error(f"Error fixing active positions: {e}")
        return False

def main():
    """Main function to fix simulation token issue"""
    logger.info("Starting fix for simulation token trading issue")
    
    # Update control file to default to simulation mode
    update_control_file()
    
    # Fix active positions
    fix_active_positions()
    
    # Output instructions
    print("\n" + "="*60)
    print("FIX APPLIED SUCCESSFULLY")
    print("="*60)
    print("\nActions taken:")
    print("1. Set bot to simulation mode and paused it for safety")
    print("2. Marked simulation tokens in your active positions")
    print("\nNext steps:")
    print("1. Replace the following files with the updated versions:")
    print("   - solana_trader.py")
    print("   - token_scanner.py")
    print("   - trading_bot.py")
    print("\n2. Restart your bot with:")
    print("   python main.py")
    print("\n3. To enable real trading with real tokens, update bot_control.json:")
    print('   {"simulation_mode": false, "running": true, ...}')
    print("\nIMPORTANT: In real trading mode, only real tokens will be traded.")
    print("           Simulation tokens will be filtered out automatically.")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
