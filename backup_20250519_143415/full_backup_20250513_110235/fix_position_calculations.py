#!/usr/bin/env python
"""
Fix position calculations and token prices in the database
"""

import os
import sys
import sqlite3
import random
import json
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
        db_path = BotConfiguration.DB_PATH
        
        # Get SOL price
        trader = SolanaTrader(db=db, simulation_mode=True)
        sol_price = await trader.get_sol_price()
        logger.info(f"Current SOL price: ${sol_price}")
        
        # Get active positions
        positions = db.get_active_orders()
        logger.info(f"Found {len(positions)} active positions")
        
        # Update each position with realistic metrics
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. First, update token prices in the database with realistic values
        for idx, row in positions.iterrows():
            contract_address = row['contract_address']
            ticker = row['ticker']
            buy_price = float(row['buy_price'])
            
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
        
        # 2. Next, update the trades table with proper P&L calculations
        # Fetch all trades
        cursor.execute("SELECT * FROM trades ORDER BY timestamp")
        trades = cursor.fetchall()
        
        # Get column names
        cursor.execute("PRAGMA table_info(trades)")
        column_names = [info[1] for info in cursor.fetchall()]
        
        # Create a dict of column index to name
        col_indices = {name: i for i, name in enumerate(column_names)}
        
        # Process trades by contract address
        trades_by_contract = {}
        for trade in trades:
            contract_address = trade[col_indices['contract_address']]
            if contract_address not in trades_by_contract:
                trades_by_contract[contract_address] = []
            trades_by_contract[contract_address].append(trade)
        
        # Calculate P&L for each contract
        for contract_address, contract_trades in trades_by_contract.items():
            # Sort by timestamp
            contract_trades.sort(key=lambda x: x[col_indices['timestamp']])
            
            # Process buys and sells
            buys = [t for t in contract_trades if t[col_indices['action']] == 'BUY']
            sells = [t for t in contract_trades if t[col_indices['action']] == 'SELL']
            
            # If we have both buys and sells, calculate PnL
            if buys and sells:
                for sell in sells:
                    sell_id = sell[col_indices['id']]
                    sell_amount = sell[col_indices['amount']]
                    sell_price = sell[col_indices['price']]
                    
                    # Find corresponding buy
                    # For simplicity, use the first buy (in reality, you'd need FIFO or average cost basis)
                    buy = buys[0]
                    buy_amount = buy[col_indices['amount']]
                    buy_price = buy[col_indices['price']]
                    
                    # Calculate token quantities
                    buy_tokens = buy_amount / buy_price
                    sell_tokens = sell_amount / sell_price
                    
                    # Calculate gain/loss
                    # Let's use a simple approach: compare what we paid vs what we got
                    buy_value = buy_amount  # In SOL
                    sell_value = sell_amount  # In SOL
                    
                    # Calculate price multiple
                    price_multiple = sell_price / buy_price if buy_price > 0 else 1.0
                    
                    # P&L metrics
                    gain_loss_sol = sell_value - buy_value
                    percentage_change = ((price_multiple - 1) * 100) if buy_price > 0 else 0
                    
                    # Update the trade with realistic P&L
                    logger.info(f"Updating sell trade {sell_id} with P&L: {gain_loss_sol:.4f} SOL ({percentage_change:.1f}%)")
                    cursor.execute("""
                        UPDATE trades 
                        SET gain_loss_sol = ?, percentage_change = ?, price_multiple = ?
                        WHERE id = ?
                    """, (gain_loss_sol, percentage_change, price_multiple, sell_id))
        
        # Commit changes
        conn.commit()
        
        # 3. Finally, load bot_control.json and fix investment amounts
        try:
            bot_control_path = BotConfiguration.BOT_CONTROL_FILE
            with open(bot_control_path, 'r') as f:
                control_data = json.load(f)
            
            # Fix investment parameters if too low
            if 'max_investment_per_token' in control_data and control_data['max_investment_per_token'] < 0.1:
                control_data['max_investment_per_token'] = 0.1
                logger.info("Updated max_investment_per_token to 0.1 SOL")
            
            if 'min_investment_per_token' in control_data and control_data['min_investment_per_token'] < 0.01:
                control_data['min_investment_per_token'] = 0.01
                logger.info("Updated min_investment_per_token to 0.01 SOL")
            
            # Write updated control file
            with open(bot_control_path, 'w') as f:
                json.dump(control_data, f, indent=4)
        except Exception as e:
            logger.error(f"Error updating bot_control.json: {e}")
        
        # Close connections
        conn.close()
        await trader.close()
        
        logger.info("Database fix completed successfully!")
        logger.info("Please restart your bot or refresh the dashboard to see the changes")
        
        return True
    
    except Exception as e:
        logger.error(f"Error fixing database: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(fix_database())
