import asyncio
import pandas as pd
import streamlit as st
import json
import os
import time
from datetime import datetime, timedelta, UTC

# Set page configuration
st.set_page_config(
    page_title="Trading Bot Dashboard",
    page_icon="📊",
    layout="wide"
)

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'trading_bot.db')
BOT_CONTROL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'bot_control.json')

# Create data directory if it doesn't exist
os.makedirs(os.path.dirname(BOT_CONTROL_FILE), exist_ok=True)

# Default control settings
DEFAULT_CONTROL = {
    'running': True,
    'take_profit_target': 1.5,
    'stop_loss_percentage': 0.25,
    'max_investment_per_token': 0.1
}

def get_control_settings():
    """Get bot control settings from file"""
    if not os.path.exists(BOT_CONTROL_FILE):
        # Create default control file
        with open(BOT_CONTROL_FILE, 'w') as f:
            json.dump(DEFAULT_CONTROL, f, indent=4)
        return DEFAULT_CONTROL
    
    try:
        with open(BOT_CONTROL_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error reading control file: {e}")
        return DEFAULT_CONTROL

def update_control_settings(settings):
    """Update bot control settings"""
    try:
        with open(BOT_CONTROL_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception as e:
        st.error(f"Error updating control file: {e}")
        return False

def get_database_data():
    """Get data from SQLite database"""
    try:
        import sqlite3
        
        # Default empty data
        data = {
            'active_orders': pd.DataFrame(),
            'trading_history': pd.DataFrame(),
            'tokens': pd.DataFrame(),
            'wallet_balance': {'sol': 0.0, 'usd': 0.0}
        }
        
        # Check if database exists
        if not os.path.exists(DB_PATH):
            return data
        
        # Connect to database
        with sqlite3.connect(DB_PATH) as conn:
            # Get active orders
            try:
                data['active_orders'] = pd.read_sql_query(
                    """
                    SELECT ao.*, t.ticker, t.name 
                    FROM active_orders ao
                    LEFT JOIN tokens t ON ao.contract_address = t.contract_address
                    """, 
                    conn
                )
            except Exception as e:
                st.error(f"Error reading active orders: {e}")
            
            # Get trading history
            try:
                data['trading_history'] = pd.read_sql_query(
                    """
                    SELECT th.*, t.ticker, t.name 
                    FROM trading_history th
                    LEFT JOIN tokens t ON th.contract_address = t.contract_address
                    ORDER BY th.timestamp DESC
                    LIMIT 100
                    """, 
                    conn
                )
            except Exception as e:
                st.error(f"Error reading trading history: {e}")
            
            # Get tokens
            try:
                data['tokens'] = pd.read_sql_query(
                    """
                    SELECT * FROM tokens
                    ORDER BY last_updated DESC
                    LIMIT 100
                    """, 
                    conn
                )
            except Exception as e:
                st.error(f"Error reading tokens: {e}")
            
            # Get wallet balance (not stored in DB, using placeholder)
            data['wallet_balance'] = {'sol': 3.0, 'usd': 3 * 250}
        
        return data
    
    except Exception as e:
        st.error(f"Database error: {e}")
        return {
            'active_orders': pd.DataFrame(),
            'trading_history': pd.DataFrame(),
            'tokens': pd.DataFrame(),
            'wallet_balance': {'sol': 0.0, 'usd': 0.0}
        }

def main():
    # Set title
    st.title("📊 Solana Trading Bot Dashboard")
    
    # Sidebar controls
    st.sidebar.title("Bot Controls")
    
    # Get control settings
    control = get_control_settings()
    
    # Bot status toggle
    bot_status = "🟢 Running" if control.get('running', True) else "🔴 Stopped"
    
    if st.sidebar.button(f"{'Stop Bot' if control.get('running', True) else 'Start Bot'}"):
        control['running'] = not control.get('running', True)
        update_control_settings(control)
        st.sidebar.success(f"Bot is now {'running' if control['running'] else 'stopped'}")
        time.sleep(1)  # Give time for status to update
        st.rerun()
    
    st.sidebar.write(f"Status: {bot_status}")
    
    # Trading parameters
    st.sidebar.subheader("Trading Parameters")
    
    # Take profit
    tp_value = st.sidebar.number_input(
        "Take Profit Target (x)",
        min_value=1.1,
        max_value=5.0,
        value=float(control.get('take_profit_target', 1.5)),
        step=0.1
    )
    
    # Stop loss
    sl_value = st.sidebar.number_input(
        "Stop Loss (%)",
        min_value=5.0,
        max_value=50.0,
        value=float(control.get('stop_loss_percentage', 0.25)) * 100,
        step=5.0
    ) / 100.0
    
    # Max investment
    max_inv = st.sidebar.number_input(
        "Max Investment per Token (SOL)",
        min_value=0.01,
        max_value=1.0,
        value=float(control.get('max_investment_per_token', 0.1)),
        step=0.01
    )
    
    # Update button
    if st.sidebar.button("Update Trading Parameters"):
        control['take_profit_target'] = tp_value
        control['stop_loss_percentage'] = sl_value
        control['max_investment_per_token'] = max_inv
        update_control_settings(control)
        st.sidebar.success("Trading parameters updated!")
    
    # Auto-refresh
    auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
    refresh_interval = st.sidebar.slider(
        "Refresh interval (seconds)",
        min_value=30,
        max_value=300,
        value=60
    )
    
    # Get data
    data = get_database_data()
    
    # Wallet balance
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Wallet Balance (SOL)", f"{data['wallet_balance']['sol']:.4f}")
    with col2:
        st.metric("Wallet Balance (USD)", f"${data['wallet_balance']['usd']:.2f}")
    
    # Active positions
    st.subheader("Active Positions")
    if data['active_orders'].empty:
        st.info("No active positions")
    else:
        st.dataframe(data['active_orders'])
    
    # Trading history tabs
    tab1, tab2 = st.tabs(["Trading History", "Discovered Tokens"])
    
    with tab1:
        if data['trading_history'].empty:
            st.info("No trading history")
        else:
            # Add filters
            col_action, col_date = st.columns(2)
            
            with col_action:
                actions = data['trading_history']['action'].unique()
                action_filter = st.multiselect(
                    "Filter by action",
                    options=actions,
                    default=actions
                )
            
            filtered_history = data['trading_history']
            if action_filter:
                filtered_history = filtered_history[filtered_history['action'].isin(action_filter)]
                
            st.dataframe(filtered_history)
    
    with tab2:
        if data['tokens'].empty:
            st.info("No tokens discovered")
        else:
            # Add search filter
            search = st.text_input("Search by ticker or contract address")
            
            filtered_tokens = data['tokens']
            if search:
                filtered_tokens = filtered_tokens[
                    filtered_tokens['ticker'].str.contains(search, case=False, na=False) |
                    filtered_tokens['contract_address'].str.contains(search, case=False, na=False)
                ]
                
            st.dataframe(filtered_tokens)
    
    # Simulation mode note
    st.info("""
    **Note**: Bot is currently running in simulation mode. Trades are recorded in the database but not executed on-chain.
    To enable real trading, edit `solana_trader.py` and set `self.simulation_mode = False`
    """)
    
    # Auto-refresh logic
    if auto_refresh:
        # Create a countdown timer
        placeholder = st.empty()
        
        for seconds_left in range(refresh_interval, 0, -1):
            placeholder.text(f"Auto-refreshing in {seconds_left} seconds...")
            time.sleep(1)
        
        placeholder.text("Refreshing...")
        st.rerun()

if __name__ == "__main__":
    main()