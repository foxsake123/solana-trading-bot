import sqlite3
import pandas as pd

# Create and save this as check_trades.py
conn = sqlite3.connect('data/sol_bot.db')
try:
    # Check trades
    print("===== RECENT TRADES =====")
    trades = pd.read_sql("SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10", conn)
    if not trades.empty:
        print(trades)
    else:
        print("No trades found in database.")

    # Check active positions
    print("\n===== ACTIVE POSITIONS =====")
    # Calculate positions by finding tokens where buy amount > sell amount
    buy_trades = pd.read_sql("SELECT contract_address, SUM(amount) as bought FROM trades WHERE action='BUY' GROUP BY contract_address", conn)
    sell_trades = pd.read_sql("SELECT contract_address, SUM(amount) as sold FROM trades WHERE action='SELL' GROUP BY contract_address", conn)
    
    if not buy_trades.empty:
        # Merge buy and sell data
        positions = pd.merge(buy_trades, sell_trades, on='contract_address', how='left')
        positions['sold'] = positions['sold'].fillna(0)
        positions['holding'] = positions['bought'] - positions['sold']
        active = positions[positions['holding'] > 0]
        
        if not active.empty:
            print(active)
        else:
            print("No active positions found.")
    else:
        print("No buy trades found.")

except Exception as e:
    print(f"Error querying database: {e}")
finally:
    conn.close()