# Add this script to calculate P&L for existing trades to fix your statistics

import sqlite3
import json
import logging
from datetime import datetime, timezone

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fix_trades')

# Database path
DB_PATH = "solana_trader.db"

def fix_trade_calculations():
    """
    Fix P&L calculations for existing trades
    """
    logger.info("Starting trade P&L calculation fix...")
    
    try:
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get all completed trades (SELL)
        cursor.execute("SELECT * FROM trading_history WHERE action = 'SELL'")
        sell_trades = cursor.fetchall()
        
        if not sell_trades:
            logger.info("No SELL trades found to fix.")
            return False
        
        # Get column names
        cursor.execute("PRAGMA table_info(trading_history)")
        columns = [col[1] for col in cursor.fetchall()]
        
        logger.info(f"Found {len(sell_trades)} SELL trades to update")
        
        # Process each SELL trade
        for sell_trade in sell_trades:
            # Convert to dict
            sell_dict = dict(zip(columns, sell_trade))
            sell_id = sell_dict['id']
            contract_address = sell_dict['contract_address']
            ticker = sell_dict.get('ticker', 'Unknown')
            
            # Find corresponding BUY trade
            cursor.execute(
                "SELECT * FROM trading_history WHERE contract_address = ? AND action = 'BUY' ORDER BY timestamp ASC LIMIT 1", 
                (contract_address,)
            )
            buy_trade = cursor.fetchone()
            
            if not buy_trade:
                logger.warning(f"No BUY trade found for SELL ID {sell_id} ({ticker}). Skipping.")
                continue
            
            # Convert BUY trade to dict
            buy_dict = dict(zip(columns, buy_trade))
            
            # Calculate P&L metrics
            sell_amount = float(sell_dict['amount'])
            sell_price = float(sell_dict['price'])
            buy_amount = float(buy_dict['amount'])
            buy_price = float(buy_dict['price'])
            
            # Calculate gain/loss in SOL terms
            buy_value = buy_amount * buy_price
            sell_value = sell_amount * sell_price
            gain_loss_sol = sell_value - buy_value
            
            # Calculate percentage change and price multiple
            percentage_change = ((sell_price / buy_price) - 1) * 100
            price_multiple = sell_price / buy_price
            
            logger.info(f"Trade {sell_id} ({ticker}): Calculated P&L = {gain_loss_sol:.4f} SOL ({percentage_change:.2f}%)")
            
            # Update the SELL trade with calculated metrics
            cursor.execute(
                """
                UPDATE trading_history 
                SET gain_loss_sol = ?,
                    percentage_change = ?,
                    price_multiple = ?
                WHERE id = ?
                """,
                (gain_loss_sol, percentage_change, price_multiple, sell_id)
            )
        
        # Commit changes
        conn.commit()
        logger.info(f"Successfully updated P&L metrics for {len(sell_trades)} trades")
        
        # Close connection
        conn.close()
        return True
    
    except Exception as e:
        logger.error(f"Error fixing trade calculations: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    fix_trade_calculations()
