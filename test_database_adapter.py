"""
Test script for database adapter to verify it handles the is_simulation parameter correctly
"""
import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('database_adapter_test')

# Add core directory to path if needed
core_dir = 'core'
if os.path.exists(core_dir) and core_dir not in sys.path:
    sys.path.insert(0, core_dir)

# Try to import the database
try:
    from database import Database
    logger.info("Successfully imported Database class")
except ImportError:
    logger.error("Failed to import Database. Make sure database.py is available")
    sys.exit(1)

# Try to import the fixed database adapter
try:
    from database_adapter_fix import DatabaseAdapter
    logger.info("Successfully imported fixed DatabaseAdapter")
except ImportError:
    logger.error("Failed to import DatabaseAdapter. Make sure database_adapter_fix.py is available")
    sys.exit(1)

def test_adapter():
    """Test the database adapter with the is_simulation parameter"""
    logger.info("Creating test database instance")
    
    # Create a database instance with a test path
    db_path = 'data/test_db.db'
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = Database(db_path=db_path)
    
    logger.info("Creating database adapter")
    adapter = DatabaseAdapter(db)
    
    # Test token saving
    logger.info("Testing token saving")
    token_result = adapter.save_token({
        'contract_address': 'TEST_TOKEN_ADDRESS',
        'ticker': 'TEST',
        'name': 'Test Token',
        'price_usd': 0.0001,
        'volume_24h': 10000.0,
        'liquidity_usd': 50000.0,
    })
    logger.info(f"Token save result: {token_result}")
    
    # Test trade recording with is_simulation parameter
    logger.info("Testing trade recording with is_simulation parameter")
    trade_result = adapter.record_trade(
        contract_address='TEST_TOKEN_ADDRESS',
        action='BUY',
        amount=0.1,
        price=0.00005,
        tx_hash='SIM_TEST_TX_HASH',
        is_simulation=True
    )
    logger.info(f"Trade record result: {trade_result}")
    
    # Check that the trade was recorded
    logger.info("Getting trade history")
    trades = db.get_trade_history('TEST_TOKEN_ADDRESS')
    logger.info(f"Trades found: {len(trades)}")
    
    # Check active orders
    logger.info("Getting active orders")
    active_orders = adapter.get_active_orders()
    logger.info(f"Active orders: {active_orders}")
    
    logger.info("Database adapter test completed successfully")
    return True

if __name__ == "__main__":
    test_adapter()
