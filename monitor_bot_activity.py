# monitor_bot_activity.py
import sqlite3
import time
import os
from datetime import datetime
import pandas as pd

def monitor_activity():
    """Monitor bot trading activity"""
    db_path = 'data/sol_bot.db'
    
    if not os.path.exists(db_path):
        print("❌ Database not found")
        return
    
    print("\n📊 Solana Trading Bot Monitor")
    print("=" * 60)
    
    while True:
        try:
            conn = sqlite3.connect(db_path)
            
            # Get recent trades
            recent_trades = pd.read_sql_query(
                "SELECT * FROM trades ORDER BY id DESC LIMIT 10", 
                conn
            )
            
            # Get active positions
            active_positions_query = """
            SELECT contract_address, 
                   SUM(CASE WHEN action='BUY' THEN amount ELSE 0 END) - 
                   SUM(CASE WHEN action='SELL' THEN amount ELSE 0 END) as holding
            FROM trades 
            GROUP BY contract_address
            HAVING holding > 0
            """
            active_positions = pd.read_sql_query(active_positions_query, conn)
            
            # Clear screen
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print(f"\n📊 Bot Activity Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
            
            print("\n🔄 Recent Trades:")
            if not recent_trades.empty:
                for _, trade in recent_trades.head(5).iterrows():
                    action = trade['action']
                    token = trade['contract_address'][:12] + "..."
                    amount = trade['amount']
                    price = trade['price']
                    
                    emoji = "🟢" if action == "BUY" else "🔴"
                    print(f"{emoji} {action}: {amount:.4f} SOL of {token} @ ${price:.8f}")
            else:
                print("No trades yet")
            
            print(f"\n💼 Active Positions: {len(active_positions)}")
            if not active_positions.empty:
                for _, pos in active_positions.iterrows():
                    token = pos['contract_address'][:12] + "..."
                    holding = pos['holding']
                    print(f"  - {token}: {holding:.4f} SOL")
            
            conn.close()
            
            # Wait 5 seconds before refreshing
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor_activity()