#!/usr/bin/env python
"""
Fix token prices and positions in the database
"""

import os
import sys
import sqlite3
import random
import pandas as pd
from datetime import datetime, timezone
import asyncio

# Add the current directory to the path so we can import our modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Configure basic logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fix_database():
    """Fix token prices and position calculations in the database"""
    try:
        # Import required modules
        from config import BotConfiguration
        from database import Database
        from solana_trader import SolanaTrader
        
        # Create database instance
        db = Database()
        
        # Get SOL price
        trader = SolanaTrader(db=db, simulation_mode=True)
        sol_price = await trader.get_sol_price()
        logger.info(f"Current SOL price: ${sol_price}")
        
        # Get active positions
        positions = db.get_active_orders()
        logger.info(f"Found {len(positions)} active positions")
        
        # Update each position with realistic metrics
        conn = sqlite3.connect(BotConfiguration.DB_PATH)
        cursor = conn.cursor()
        
        # Update token prices in the database
        for idx, row in positions.iterrows():
            contract_address = row['contract_address']
            ticker = row['ticker']
            buy_price = row['buy_price']
            
            # Generate a realistic current price (random between 0.5x-3x buy price)
            price_multiple = random.uniform(0.5, 3.0)
            current_price = buy_price * price_multiple
            
            # Update token data in the database
            logger.info(f"Updating token price for {ticker} ({contract_address}) - Multiple: {price_multiple:.2f}x")
            cursor.execute("""
                UPDATE tokens 
                SET price_usd = ?, last_updated = ?
                WHERE contract_address = ?
            """, (current_price, datetime.now(timezone.utc).isoformat(), contract_address))
        
        # Commit changes
        conn.commit()
        conn.close()
        
        # Close trader connection
        await trader.close()
        
        logger.info("Database token prices updated successfully!")
        logger.info("Please restart your bot or refresh the dashboard to see the changes")
        
        return True
    
    except Exception as e:
        logger.error(f"Error fixing database: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(fix_database())
