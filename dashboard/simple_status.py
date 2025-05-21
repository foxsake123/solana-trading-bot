# Create this as simple_status.py
import sqlite3
import pandas as pd
from datetime import datetime
import time
import os

def get_status():
    """Get and display the current status of the trading bot"""
    # Connect to database
    conn = sqlite3.connect('data/sol_bot.db')
    
    try:
        # Clear the screen for better visibility
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("\n===== SOLANA TRADING BOT STATUS =====")
        print(f"Status Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get recent trades
        recent_trades = pd.read_sql("SELECT * FROM trades ORDER BY timestamp DESC LIMIT 20", conn)
        
        # Count trades by type
        total_trades = len(recent_trades)
        real_trades = sum(1 for addr in recent_trades['contract_address'] if not str(addr).startswith('Sim'))
        sim_trades = total_trades - real_trades
        
        print(f"\nTrade Statistics:")
        print(f"- Total trades in database: {total_trades}")
        print(f"- Real token trades: {real_trades}")
        print(f"- Simulation token trades: {sim_trades}")
        
        # Get most recent real trade
        if real_trades > 0:
            real_trades_df = recent_trades[~recent_trades['contract_address'].astype(str).str.startswith('Sim')]
            if not real_trades_df.empty:
                last_real = real_trades_df.iloc[0]
                print(f"\nMost Recent Real Trade:")
                print(f"- Token: {last_real['contract_address']}")
                print(f"- Action: {last_real['action']}")
                print(f"- Amount: {last_real['amount']} SOL")
                print(f"- Price: {last_real['price']}")
                print(f"- Time: {last_real['timestamp']}")
        else:
            print("\nNo real trades found yet")
        
        # Get most recent trade (including simulations)
        if not recent_trades.empty:
            last_trade = recent_trades.iloc[0]
            is_sim = str(last_trade['contract_address']).startswith('Sim')
            
            print(f"\nMost Recent Trade ({('SIMULATION' if is_sim else 'REAL')}):")
            print(f"- Token: {last_trade['contract_address']}")
            print(f"- Action: {last_trade['action']}")
            print(f"- Amount: {last_trade['amount']} SOL")
            print(f"- Price: {last_trade['price']}")
            print(f"- Time: {last_trade['timestamp']}")
        
        # Get active positions
        buy_trades = pd.read_sql(
            "SELECT contract_address, SUM(amount) as bought FROM trades WHERE action='BUY' GROUP BY contract_address", 
            conn
        )
        sell_trades = pd.read_sql(
            "SELECT contract_address, SUM(amount) as sold FROM trades WHERE action='SELL' GROUP BY contract_address", 
            conn
        )
        
        # Merge buy and sell data
        active_positions = []
        if not buy_trades.empty:
            # Create a complete dataframe with bought and sold amounts
            positions = pd.merge(buy_trades, sell_trades, on='contract_address', how='left')
            positions['sold'] = positions['sold'].fillna(0)
            positions['holding'] = positions['bought'] - positions['sold']
            active = positions[positions['holding'] > 0]
            
            # Count active positions
            total_active = len(active)
            real_active = sum(1 for addr in active['contract_address'] if not str(addr).startswith('Sim'))
            sim_active = total_active - real_active
            
            print(f"\nActive Positions:")
            print(f"- Total active positions: {total_active}")
            print(f"- Real token positions: {real_active}")
            print(f"- Simulation token positions: {sim_active}")
            
            # List real active positions
            if real_active > 0:
                real_positions = active[~active['contract_address'].astype(str).str.startswith('Sim')]
                
                print("\nActive Real Token Positions:")
                for idx, row in real_positions.iterrows():
                    print(f"- {row['contract_address']}: {row['holding']:.6f} SOL")
                    
                    # Try to get additional token info if available
                    try:
                        token_info = pd.read_sql(f"SELECT * FROM tokens WHERE contract_address='{row['contract_address']}'", conn)
                        if not token_info.empty:
                            ticker = token_info['ticker'].iloc[0] if 'ticker' in token_info.columns else 'UNKNOWN'
                            name = token_info['name'].iloc[0] if 'name' in token_info.columns else 'Unknown Token'
                            print(f"  {ticker} - {name}")
                    except:
                        pass
        else:
            print("\nNo active positions found")
        
        # Check bot control settings
        try:
            with open('bot_control.json', 'r') as f:
                import json
                settings = json.load(f)
                
                print("\nBot Control Settings:")
                print(f"- Running: {settings.get('running', False)}")
                print(f"- Simulation Mode: {settings.get('simulation_mode', True)}")
                print(f"- Take Profit Target: {settings.get('take_profit_target', 'N/A')}%")
                print(f"- Stop Loss: {settings.get('stop_loss_percentage', 'N/A')}%")
                print(f"- Max Investment: {settings.get('max_investment_per_token', 'N/A')} SOL")
        except:
            print("\nUnable to read bot control settings")
            
        print("\n====================================")
        
    except Exception as e:
        print(f"Error getting status: {e}")
    finally:
        # Close connection
        conn.close()

# Show initial status
get_status()

# Keep updating
print("\nPress Ctrl+C to exit. Status will update every 30 seconds...")
try:
    while True:
        time.sleep(30)
        get_status()
except KeyboardInterrupt:
    print("\nStatus monitoring stopped")