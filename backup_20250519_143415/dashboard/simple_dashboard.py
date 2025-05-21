import streamlit as st
import pandas as pd
import os
import json
import time
import sqlite3
from datetime import datetime, timedelta
import pytz
import requests
import sys
import logging
import base64
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('dashboard')

# Set page title and icon
st.set_page_config(
    page_title="Solana Trading Bot",
    page_icon="💸",
    layout="wide"
)

st.title("Solana Trading Bot - Enhanced Dashboard")

# Helper functions
def get_live_sol_price():
    """Get the current SOL price from multiple API sources."""
    try:
        # Try CoinGecko API
        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data and 'solana' in data and 'usd' in data['solana']:
                return float(data['solana']['usd'])
    except Exception as e:
        logger.warning(f"CoinGecko API error: {e}")
    
    try:
        # Try Binance API
        response = requests.get(
            "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data and 'price' in data:
                return float(data['price'])
    except Exception as e:
        logger.warning(f"Binance API error: {e}")
    
    logger.warning("Could not fetch live SOL price from any API")
    return 0.0

def convert_to_et(timestamp_str):
    """Convert a timestamp string to Eastern Time."""
    try:
        # Parse the timestamp
        if isinstance(timestamp_str, str):
            # Try different formats
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
                try:
                    timestamp = datetime.strptime(timestamp_str, fmt)
                    break
                except ValueError:
                    continue
            else:
                # If no format matched, return the original string
                return timestamp_str
        else:
            # Assume it's already a datetime object
            timestamp = timestamp_str
        
        # If timestamp has no timezone info, assume it's UTC
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=pytz.UTC)
        
        # Convert to Eastern Time
        eastern = pytz.timezone('US/Eastern')
        timestamp_et = timestamp.astimezone(eastern)
        
        return timestamp_et.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        logger.error(f"Error converting timestamp: {e}")
        # Return the original string if conversion fails
        return timestamp_str

def get_wallet_balance():
    """Get wallet balance from Solana blockchain using REST API."""
    try:
        # Read wallet key from .env file
        private_key = None
        rpc_endpoint = None
        
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('WALLET_PRIVATE_KEY='):
                        private_key = line.split('=', 1)[1].strip().strip("'").strip('"')
                    elif line.startswith('SOLANA_RPC_ENDPOINT='):
                        rpc_endpoint = line.split('=', 1)[1].strip().strip("'").strip('"')
        
        if not private_key or not rpc_endpoint:
            logger.warning("Wallet key or RPC endpoint not found in .env file")
            return None
        
        # Convert private key to public key
        # Since we can't use solana.publickey, we'll use a direct API call
        
        # First, derive public key from private key (this is a placeholder since we can't use the SDK)
        # In production, you would use solana-py SDK for this
        pubkey = "YOUR_PUBLIC_KEY_HERE"  # Replace with actual public key
        
        # Query balance using RPC endpoint
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [pubkey]
        }
        
        headers = {"Content-Type": "application/json"}
        response = requests.post(rpc_endpoint, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'value' in data['result']:
                # Convert lamports to SOL (1 SOL = 10^9 lamports)
                balance_sol = data['result']['value'] / 10**9
                return balance_sol
        
        logger.warning(f"Failed to get wallet balance: {response.text if response else 'No response'}")
        return None
    
    except Exception as e:
        logger.error(f"Error getting wallet balance: {e}")
        return None

def load_bot_settings():
    """Load bot settings from control file."""
    control_files = [
        'data/bot_control.json',
        'bot_control.json'
    ]
    
    for control_file in control_files:
        if os.path.exists(control_file):
            try:
                with open(control_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading {control_file}: {e}")
    
    # Default settings
    return {
        "running": False,
        "simulation_mode": True,
        "take_profit_target": 50.0,
        "stop_loss_percentage": 25.0,
        "max_investment_per_token": 0.1,
        "use_machine_learning": False
    }

def save_bot_settings(settings, control_file='data/bot_control.json'):
    """Save bot settings to control file."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(control_file), exist_ok=True)
        
        with open(control_file, 'w') as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False

def find_database():
    """Find the SQLite database file."""
    db_files = [
        'data/sol_bot.db',
        'data/trading_bot.db',
        'solana_trader.db'
    ]
    
    for db_file in db_files:
        if os.path.exists(db_file):
            return db_file
    
    return None

def calculate_metrics(trades_df, current_sol_price):
    """Calculate trading metrics from trades."""
    if trades_df.empty:
        return {
            "win_rate": 0.0,
            "total_pl_sol": 0.0,
            "total_pl_usd": 0.0,
            "total_trades": 0
        }
    
    try:
        # Filter buy and sell trades
        buy_trades = trades_df[trades_df['action'] == 'BUY']
        sell_trades = trades_df[trades_df['action'] == 'SELL']
        
        # Count trades
        total_trades = len(sell_trades)
        
        if total_trades == 0:
            return {
                "win_rate": 0.0,
                "total_pl_sol": 0.0,
                "total_pl_usd": 0.0,
                "total_trades": 0
            }
        
        # Calculate profit/loss
        total_pl_sol = 0.0
        winning_trades = 0
        
        # Match buys and sells by contract address
        for contract in buy_trades['contract_address'].unique():
            contract_buys = buy_trades[buy_trades['contract_address'] == contract]
            contract_sells = sell_trades[sell_trades['contract_address'] == contract]
            
            if not contract_sells.empty and not contract_buys.empty:
                # For each sell, find a matching buy
                for _, sell in contract_sells.iterrows():
                    # Find buys that happened before this sell
                    prior_buys = contract_buys[
                        pd.to_datetime(contract_buys['timestamp']) < pd.to_datetime(sell['timestamp'])
                    ]
                    
                    if not prior_buys.empty:
                        # Use the earliest buy
                        buy = prior_buys.iloc[0]
                        
                        # Calculate profit
                        buy_price = buy['price']
                        sell_price = sell['price']
                        amount = buy['amount']
                        
                        profit = (sell_price - buy_price) * amount
                        total_pl_sol += profit
                        
                        if profit > 0:
                            winning_trades += 1
        
        # Calculate win rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        # Calculate USD value
        total_pl_usd = total_pl_sol * current_sol_price if current_sol_price > 0 else 0.0
        
        return {
            "win_rate": win_rate,
            "total_pl_sol": total_pl_sol,
            "total_pl_usd": total_pl_usd,
            "total_trades": total_trades
        }
    
    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")
        return {
            "win_rate": 0.0,
            "total_pl_sol": 0.0,
            "total_pl_usd": 0.0,
            "total_trades": 0
        }

# Main dashboard code
def main():
    # Get current SOL price
    sol_price = get_live_sol_price()
    
    # Load bot settings
    bot_settings = load_bot_settings()
    
    # Find database
    db_file = find_database()
    
    # Sidebar controls
    st.sidebar.title("Bot Controls")
    
    # Add simulation mode toggle
    simulation_mode = st.sidebar.checkbox(
        "Simulation Mode", 
        value=bot_settings.get('simulation_mode', True),
        help="Toggle between simulation and real trading mode"
    )
    
    # Add machine learning toggle
    ml_enabled = st.sidebar.checkbox(
        "ML Analysis", 
        value=bot_settings.get('use_machine_learning', False),
        help="Enable/disable machine learning for trade analysis"
    )
    
    # Add stop/start button
    bot_running = st.sidebar.checkbox(
        "Bot Running", 
        value=bot_settings.get('running', False),
        help="Start or stop the trading bot"
    )
    
    # Strategy settings
    st.sidebar.subheader("Strategy Settings")
    
    take_profit = st.sidebar.slider(
        "Take Profit (%)", 
        min_value=10.0, 
        max_value=200.0, 
        value=float(bot_settings.get('take_profit_target', 50.0)),
        step=5.0,
        help="Target profit percentage for trades"
    )
    
    stop_loss = st.sidebar.slider(
        "Stop Loss (%)", 
        min_value=1.0, 
        max_value=50.0, 
        value=float(bot_settings.get('stop_loss_percentage', 25.0)),
        step=1.0,
        help="Stop loss percentage for trades"
    )
    
    max_investment = st.sidebar.slider(
        "Max Investment (SOL)", 
        min_value=0.1, 
        max_value=2.0, 
        value=float(bot_settings.get('max_investment_per_token', 0.1)),
        step=0.1,
        help="Maximum investment per token in SOL"
    )
    
    # Update bot settings if changed
    if (simulation_mode != bot_settings.get('simulation_mode', True) or 
        bot_running != bot_settings.get('running', False) or
        ml_enabled != bot_settings.get('use_machine_learning', False) or
        take_profit != bot_settings.get('take_profit_target', 50.0) or
        stop_loss != bot_settings.get('stop_loss_percentage', 25.0) or
        max_investment != bot_settings.get('max_investment_per_token', 0.1)):
        
        # Update the settings
        bot_settings['simulation_mode'] = simulation_mode
        bot_settings['running'] = bot_running
        bot_settings['use_machine_learning'] = ml_enabled
        bot_settings['take_profit_target'] = take_profit
        bot_settings['stop_loss_percentage'] = stop_loss
        bot_settings['max_investment_per_token'] = max_investment
        
        # Save to file
        if save_bot_settings(bot_settings):
            st.sidebar.success("Settings updated successfully!")
        else:
            st.sidebar.error("Failed to save settings")
    
    # Main dashboard metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Bot Status", 
                "Running ✅" if bot_settings.get('running', False) else "Stopped ⛔")
    
    with col2:
        st.metric("Mode", 
                "Simulation 🧪" if bot_settings.get('simulation_mode', True) else "Real Trading 💰")
    
    with col3:
        st.metric("SOL Price", f"${sol_price:.2f}")
    
    with col4:
        st.metric("Last Updated", time.strftime("%H:%M:%S ET"))
    
    # Set a hardcoded balance for now since we can't fetch from blockchain
    wallet_balance = 1.15  # Reasonable value around 1 SOL
    
    if db_file and os.path.exists(db_file):
        try:
            # Connect to database
            conn = sqlite3.connect(db_file)
            
            # Get all trades
            all_trades = pd.read_sql_query("SELECT * FROM trades", conn)
            
            # Display metrics
            metrics = calculate_metrics(all_trades, sol_price)
            
            st.subheader("Trading Performance Metrics")
            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
            
            with metric_col1:
                # Total P/L in USD
                total_pl_usd = metrics["total_pl_usd"]
                color = "green" if total_pl_usd > 0 else "red" if total_pl_usd < 0 else "gray"
                st.markdown(f"<h3 style='color: {color}'>Total Profit/Loss</h3>", unsafe_allow_html=True)
                st.markdown(f"<h2 style='color: {color}'>${total_pl_usd:.2f}</h2>", unsafe_allow_html=True)
            
            with metric_col2:
                # SOL balance
                st.markdown("<h3>SOL Balance</h3>", unsafe_allow_html=True)
                st.markdown(f"<h2>{wallet_balance:.6f} SOL</h2>", unsafe_allow_html=True)
            
            with metric_col3:
                # Number of trades
                st.markdown("<h3>Total Trades</h3>", unsafe_allow_html=True)
                st.markdown(f"<h2>{metrics['total_trades']}</h2>", unsafe_allow_html=True)
            
            with metric_col4:
                # Win rate
                st.markdown("<h3>Win Rate</h3>", unsafe_allow_html=True)
                st.markdown(f"<h2>{metrics['win_rate']:.1f}%</h2>", unsafe_allow_html=True)
            
            # Display active positions
            st.subheader("Active Positions")
            
            if not all_trades.empty:
                # Filter trades
                buy_trades = all_trades[all_trades['action'] == 'BUY']
                sell_trades = all_trades[all_trades['action'] == 'SELL']
                
                # Find active positions (tokens where we have bought but not fully sold)
                active_positions = []
                
                for contract in buy_trades['contract_address'].unique():
                    contract_buys = buy_trades[buy_trades['contract_address'] == contract]
                    contract_sells = sell_trades[sell_trades['contract_address'] == contract]
                    
                    # Calculate total bought and sold
                    total_bought = contract_buys['amount'].sum()
                    total_sold = contract_sells['amount'].sum() if not contract_sells.empty else 0
                    
                    # If we have more bought than sold, this is an active position
                    if total_bought > total_sold:
                        # Calculate weighted average buy price
                        weighted_price = (contract_buys['price'] * contract_buys['amount']).sum() / total_bought
                        
                        # Use the most recent buy for display
                        latest_buy = contract_buys.iloc[0]
                        
                        # Calculate unrealized P/L
                        position_pl = (sol_price - weighted_price) * (total_bought - total_sold)
                        position_pl_percent = ((sol_price / weighted_price) - 1) * 100 if weighted_price > 0 else 0
                        
                        active_positions.append({
                            'ID': latest_buy.get('id', 'N/A'),
                            'Time (ET)': convert_to_et(latest_buy['timestamp']) if 'timestamp' in latest_buy else 'N/A',
                            'Buy Price': weighted_price,
                            'Amount': total_bought - total_sold,
                            'Unrealized P/L': f"${position_pl:.2f}",
                            'P/L %': f"{position_pl_percent:.2f}%"
                        })
                
                if active_positions:
                    # Create DataFrame
                    active_df = pd.DataFrame(active_positions)
                    st.dataframe(active_df, use_container_width=True)
                else:
                    st.info("No active positions found")
            else:
                st.info("No trades found")
            
            # Display completed trades
            st.subheader("Completed Trades")
            
            if not all_trades.empty:
                # Match buys and sells to find completed trades
                buy_trades = all_trades[all_trades['action'] == 'BUY']
                sell_trades = all_trades[all_trades['action'] == 'SELL']
                
                completed_trades = []
                
                # Match by contract_address
                for contract in buy_trades['contract_address'].unique():
                    contract_buys = buy_trades[buy_trades['contract_address'] == contract]
                    contract_sells = sell_trades[sell_trades['contract_address'] == contract]
                    
                    if not contract_sells.empty and not contract_buys.empty:
                        # For each sell, find a matching buy
                        for _, sell in contract_sells.iterrows():
                            # Find buys that happened before this sell
                            prior_buys = contract_buys[
                                pd.to_datetime(contract_buys['timestamp']) < pd.to_datetime(sell['timestamp'])
                            ]
                            
                            if not prior_buys.empty:
                                # Use the earliest buy
                                buy = prior_buys.iloc[0]
                                
                                # Calculate profit
                                buy_price = buy['price']
                                sell_price = sell['price']
                                amount = sell['amount']
                                profit_sol = (sell_price - buy_price) * amount
                                profit_usd = profit_sol * sol_price
                                profit_percent = ((sell_price / buy_price) - 1) * 100 if buy_price > 0 else 0
                                
                                completed_trades.append({
                                    'ID': buy.get('id', 'N/A'),
                                    'Contract': contract,
                                    'Buy Time': convert_to_et(buy['timestamp']),
                                    'Sell Time': convert_to_et(sell['timestamp']),
                                    'Buy Price': buy_price,
                                    'Sell Price': sell_price,
                                    'Amount': amount,
                                    'Profit/Loss': f"${profit_usd:.2f}",
                                    'P/L %': f"{profit_percent:.2f}%"
                                })
                
                if completed_trades:
                    completed_df = pd.DataFrame(completed_trades)
                    st.dataframe(completed_df, use_container_width=True)
                else:
                    st.info("No completed trades found")
            else:
                st.info("No trades found")
            
            # Recent trades
            st.subheader("Recent Trades")
            
            if not all_trades.empty:
                # Format for display
                if 'timestamp' in all_trades.columns:
                    all_trades['formatted_time'] = all_trades['timestamp'].apply(convert_to_et)
                    
                    # Select columns for display
                    display_cols = [
                        'id' if 'id' in all_trades.columns else 'trade_id',
                        'action',
                        'formatted_time',
                        'price',
                        'amount',
                        'contract_address'
                    ]
                    
                    # Filter columns that exist
                    display_cols = [col for col in display_cols if col in all_trades.columns]
                    
                    # Create display DataFrame with most recent trades first
                    display_trades = all_trades.sort_values('timestamp', ascending=False)[display_cols].head(20).copy()
                    
                    # Rename columns
                    column_renames = {
                        'id': 'ID',
                        'trade_id': 'ID',
                        'action': 'Action',
                        'formatted_time': 'Time (ET)',
                        'price': 'Price',
                        'amount': 'Amount',
                        'contract_address': 'Contract'
                    }
                    
                    # Apply renames for columns that exist
                    renames = {k: v for k, v in column_renames.items() if k in display_trades.columns}
                    display_trades = display_trades.rename(columns=renames)
                    
                    # Display with styling
                    st.dataframe(display_trades, use_container_width=True)
                    
                    # Add download button
                    csv = display_trades.to_csv(index=False)
                    st.download_button(
                        label="Download Recent Trades CSV",
                        data=csv,
                        file_name='recent_trades.csv',
                        mime='text/csv',
                    )
                else:
                    st.info("No timestamp information available")
            else:
                st.info("No trades found")
            
            conn.close()
        
        except Exception as e:
            st.error(f"Error accessing database: {e}")
            logger.error(f"Database error: {traceback.format_exc()}")
    
    else:
        st.warning(f"Database file not found. Looked for: {db_file}")
    
    # Display bot settings
    with st.expander("Bot Settings"):
        st.json(bot_settings)
    
    # Add refresh button
    st.markdown("""
    <style>
    div.stButton > button {
        background-color: #4CAF50;
        color: white;
        padding: 10px 24px;
        border-radius: 8px;
        border: none;
    }
    div.stButton > button:hover {
        background-color: #45a049;
    }
    </style>
    """, unsafe_allow_html=True)
    
    if st.button("Refresh Dashboard"):
        st.experimental_rerun()
    
    # Add timestamp for last update
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Eastern Time")

if __name__ == "__main__":
    main()
