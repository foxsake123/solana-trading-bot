# Create this as status_monitor.py
import sqlite3
import pandas as pd
from datetime import datetime
import time
import os
import json

def get_bot_status():
    """Get and display the current status of the trading bot"""
    # Connect to database
    conn = sqlite3.connect('data/sol_bot.db')
    
    try:
        # Clear the screen for better visibility
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("\n===== SOLANA TRADING BOT STATUS =====")
        print(f"Status Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check bot_control.json
        try:
            with open('bot_control.json', 'r') as f:
                settings = json.load(f)
                
                print("\nBot Configuration:")
                print(f"- Running: {settings.get('running', False)}")
                print(f"- Simulation Mode: {settings.get('simulation_mode', True)}")
                print(f"- Take Profit Target: {settings.get('take_profit_target', 'N/A')}%")
                print(f"- Stop Loss: {settings.get('stop_loss_percentage', 'N/A')}%")
                print(f"- Max Investment: {settings.get('max_investment_per_token', 'N/A')} SOL")
        except:
            print("\nUnable to read bot control settings")
        
        # Get recent trades
        recent_trades = pd.read_sql("""
            SELECT * FROM trades 
            ORDER BY timestamp DESC 
            LIMIT 20
        """, conn)
        
        # Count trades by type
        if 'is_simulation' in recent_trades.columns:
            real_trades = recent_trades[~recent_trades['is_simulation']].shape[0]
            sim_trades = recent_trades[recent_trades['is_simulation']].shape[0]
        else:
            # If is_simulation column doesn't exist, make educated guess
            real_trades = sum(1 for addr in recent_trades['contract_address'] if not str(addr).startswith('Sim'))
            sim_trades = recent_trades.shape[0] - real_trades
        
        print(f"\nTrade Statistics:")
        print(f"- Total trades in database: {len(recent_trades)}")
        print(f"- Real token trades: {real_trades}")
        print(f"- Simulation token trades: {sim_trades}")
        
        # Show most recent trade
        if not recent_trades.empty:
            last_trade = recent_trades.iloc[0]
            is_sim = ('is_simulation' in last_trade and last_trade['is_simulation']) or str(last_trade['contract_address']).startswith('Sim')
            
            print(f"\nMost Recent Trade ({('SIMULATION' if is_sim else 'REAL')}):")
            print(f"- Token: {last_trade['contract_address']}")
            print(f"- Action: {last_trade['action']}")
            print(f"- Amount: {last_trade['amount']} SOL")
            print(f"- Price: {last_trade['price']}")
            print(f"- Time: {last_trade['timestamp']}")
            if 'tx_hash' in last_trade and last_trade['tx_hash']:
                print(f"- TX Hash: {last_trade['tx_hash']}")
                if not is_sim and not last_trade['tx_hash'].startswith(('SIM_', 'REAL_')):
                    print(f"  View on Explorer: https://solscan.io/tx/{last_trade['tx_hash']}")
        
        # Get most recent real trade
        if real_trades > 0:
            if 'is_simulation' in recent_trades.columns:
                real_trades_df = recent_trades[~recent_trades['is_simulation']]
            else:
                real_trades_df = recent_trades[~recent_trades['contract_address'].astype(str).str.startswith('Sim')]
                
            if not real_trades_df.empty:
                last_real = real_trades_df.iloc[0]
                
                print(f"\nMost Recent Real Trade:")
                print(f"- Token: {last_real['contract_address']}")
                print(f"- Action: {last_real['action']}")
                print(f"- Amount: {last_real['amount']} SOL")
                print(f"- Price: {last_real['price']}")
                print(f"- Time: {last_real['timestamp']}")
                if 'tx_hash' in last_real and last_real['tx_hash']:
                    print(f"- TX Hash: {last_real['tx_hash']}")
                    if not last_real['tx_hash'].startswith(('SIM_', 'REAL_')):
                        print(f"  View on Explorer: https://solscan.io/tx/{last_real['tx_hash']}")
        
        # Get active positions
        try:
            print("\nActive Positions:")
            # Calculate positions
            buy_trades = pd.read_sql("""
                SELECT contract_address, SUM(amount) as bought, 
                       CASE 
                           WHEN is_simulation IS NULL THEN 
                               CASE WHEN contract_address LIKE 'Sim%' THEN 1 ELSE 0 END
                           ELSE is_simulation 
                       END as is_simulation
                FROM trades 
                WHERE action='BUY' 
                GROUP BY contract_address, is_simulation
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
                active = positions[positions['holding'] > 0]
                
                # Count positions
                total_active = len(active)
                real_positions = active[~active['is_simulation'].astype(bool)]
                sim_positions = active[active['is_simulation'].astype(bool)]
                
                print(f"- Total active positions: {total_active}")
                print(f"- Real token positions: {len(real_positions)}")
                print(f"- Simulation token positions: {len(sim_positions)}")
                
                # Show real positions detail
                if not real_positions.empty:
                    print("\nActive Real Token Positions:")
                    for idx, row in real_positions.iterrows():
                        print(f"- {row['contract_address']}: {row['holding']:.6f} SOL")
                        # Try to get token info
                        try:
                            token_info = pd.read_sql(f"SELECT * FROM tokens WHERE contract_address='{row['contract_address']}'", conn)
                            if not token_info.empty:
                                ticker = token_info['ticker'].iloc[0] if 'ticker' in token_info else 'UNKNOWN'
                                name = token_info['name'].iloc[0] if 'name' in token_info else 'Unknown'
                                print(f"  {ticker} - {name}")
                        except:
                            pass
            else:
                print("- No active positions found")
        except Exception as e:
            print(f"- Error getting positions: {e}")
            
        print("\n====================================")
        
    except Exception as e:
        print(f"Error getting status: {e}")
    finally:
        # Close connection
        conn.close()

if __name__ == "__main__":
    # Show initial status
    get_bot_status()
    
    # Keep updating
    print("\nPress Ctrl+C to exit. Status will update every 30 seconds...")
    try:
        while True:
            time.sleep(30)
            get_bot_status()
    except KeyboardInterrupt:
        print("\nStatus monitoring stopped")