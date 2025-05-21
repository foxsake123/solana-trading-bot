import asyncio
import sqlite3
import pandas as pd
import os
import argparse
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('check_trades')

def check_trades(show_all=False, limit=20):
    """Check recent trades and active positions in the database"""
    # Connect to database
    conn = sqlite3.connect('data/sol_bot.db')
    
    try:
        print("\n===== RECENT TRADES =====")
        
        # Query to get recent trades
        if show_all:
            query = f"""
            SELECT * FROM trades 
            ORDER BY timestamp DESC 
            LIMIT {limit}
            """
        else:
            # Only show non-simulation trades by default
            query = f"""
            SELECT * FROM trades 
            WHERE (is_simulation = 0 OR is_simulation IS NULL AND contract_address NOT LIKE 'Sim%')
            ORDER BY timestamp DESC 
            LIMIT {limit}
            """
        
        trades = pd.read_sql_query(query, conn)
        
        if not trades.empty:
            # Format the output
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            print(trades)
            
            # Count by action
            buy_count = len(trades[trades['action'] == 'BUY'])
            sell_count = len(trades[trades['action'] == 'SELL'])
            print(f"\nTotal: {len(trades)} trades ({buy_count} buys, {sell_count} sells)")
        else:
            print("No trades found.")
        
        print("\n===== ACTIVE POSITIONS =====")
        
        # Calculate positions by finding tokens where buy amount > sell amount
        buy_trades = pd.read_sql("""
            SELECT contract_address, SUM(amount) as bought,
                   CASE 
                       WHEN is_simulation IS NULL THEN 
                           CASE WHEN contract_address LIKE 'Sim%' THEN 1 ELSE 0 END
                       ELSE is_simulation 
                   END as is_simulation
            FROM trades 
            WHERE action='BUY' 
            GROUP BY contract_address
            """, conn)
        
        sell_trades = pd.read_sql("""
            SELECT contract_address, SUM(amount) as sold 
            FROM trades 
            WHERE action='SELL' 
            GROUP BY contract_address
            """, conn)
        
        if not buy_trades.empty:
            # Merge buy and sell data
            positions = pd.merge(buy_trades, sell_trades, on='contract_address', how='left')
            positions['sold'] = positions['sold'].fillna(0)
            positions['holding'] = positions['bought'] - positions['sold']
            
            # Filter for active positions (holding > 0)
            active = positions[positions['holding'] > 0]
            
            # Filter for non-simulation if not showing all
            if not show_all:
                active = active[~active['is_simulation']]
            
            if not active.empty:
                # Try to add token ticker and name
                try:
                    # Get token info for all active positions
                    token_addresses = tuple(active['contract_address'].tolist())
                    if len(token_addresses) == 1:
                        # Handle single item tuple syntax
                        token_query = f"SELECT contract_address, ticker, name FROM tokens WHERE contract_address = '{token_addresses[0]}'"
                    else:
                        token_query = f"SELECT contract_address, ticker, name FROM tokens WHERE contract_address IN {token_addresses}"
                    
                    token_info = pd.read_sql(token_query, conn)
                    
                    # Merge token info with active positions
                    if not token_info.empty:
                        active = pd.merge(active, token_info, on='contract_address', how='left')
                except Exception as e:
                    logger.warning(f"Could not get token info: {e}")
                
                # Display the active positions
                print(active)
                
                # Count by type
                real_count = len(active[~active['is_simulation']])
                sim_count = len(active[active['is_simulation']])
                print(f"\nTotal: {len(active)} active positions ({real_count} real, {sim_count} simulation)")
            else:
                print("No active positions found.")
        else:
            print("No buy trades found.")
    
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Check trading activity in the database.')
    parser.add_argument('-a', '--all', action='store_true', help='Show all trades including simulations')
    parser.add_argument('-l', '--limit', type=int, default=20, help='Limit number of trades to show')
    
    args = parser.parse_args()
    
    check_trades(show_all=args.all, limit=args.limit)