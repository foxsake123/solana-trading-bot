"""
Enhanced Trading Bot Dashboard with ML Analytics - FIXED VERSION
Fixes: 
1. No hardcoded 1.15 SOL fallback - shows real balance or N/A
2. Added P&L calculations for individual trades
3. Proper real vs simulation balance handling
"""
import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import time
import sqlite3
from datetime import datetime, timedelta
import pytz
import requests
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
import base64
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('enhanced_dashboard')

# Set page title and icon
st.set_page_config(
    page_title="Enhanced Solana Trading Bot Dashboard",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS with ML-specific styles
st.markdown("""
<style>
    .main { background-color: #0E1117; color: white; }
    .css-1d391kg { background-color: #1E1E1E; }
    
    /* Alert Styles */
    .alert-success { background-color: #1B4D3E; border-left: 4px solid #4CAF50; padding: 10px; margin: 10px 0; border-radius: 4px; }
    .alert-warning { background-color: #5D4037; border-left: 4px solid #FF9800; padding: 10px; margin: 10px 0; border-radius: 4px; }
    .alert-danger { background-color: #5D1A1A; border-left: 4px solid #F44336; padding: 10px; margin: 10px 0; border-radius: 4px; }
    .alert-info { background-color: #1A237E; border-left: 4px solid #2196F3; padding: 10px; margin: 10px 0; border-radius: 4px; }
    
    /* Balance Cards */
    .balance-card { background-color: #252525; border-radius: 10px; padding: 20px; margin: 10px 0; border: 2px solid #4CAF50; }
    .balance-card.warning { border-color: #FF9800; }
    .balance-card.danger { border-color: #F44336; }
    .balance-card.na { border-color: #666; background-color: #1a1a1a; }
    
    /* Metric Cards */
    .metric-card { background-color: #252525; border-radius: 10px; padding: 15px; margin: 10px 0; }
    .main-metric { font-size: 24px; font-weight: bold; }
    .sub-metric { font-size: 16px; color: #BDBDBD; }
    
    /* P&L specific styles */
    .profit { color: #4CAF50; font-weight: bold; }
    .loss { color: #F44336; font-weight: bold; }
    .neutral { color: #2196F3; font-weight: bold; }
    
    /* Tags */
    .simulation-tag { background-color: #FF9800; color: black; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
    .real-tag { background-color: #F44336; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
    .live-tag { background-color: #4CAF50; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
    
    /* Status Indicators */
    .status-online { color: #4CAF50; font-weight: bold; }
    .status-offline { color: #F44336; font-weight: bold; }
    .status-na { color: #666; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Initialize session state for real-time updates
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = True

# Helper functions
def get_live_sol_price():
    """Get the current SOL price from multiple API sources."""
    try:
        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data and 'solana' in data and 'usd' in data['solana']:
                return float(data['solana']['usd'])
    except Exception as e:
        logger.warning(f"CoinGecko API error: {e}")
    
    try:
        response = requests.get(
            "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data and 'price' in data:
                return float(data['price'])
    except Exception as e:
        logger.warning(f"Binance API error: {e}")
    
    return 0.0

def get_real_wallet_balance():
    """Get real wallet balance from Solana network - NO FALLBACK to 1.15"""
    try:
        # Try to read wallet info from .env
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
        
        if not private_key:
            logger.info("No wallet private key found - cannot get real balance")
            return None
        
        if not rpc_endpoint:
            rpc_endpoint = "https://api.mainnet-beta.solana.com"
        
        # For now, return None since we don't want to expose private key handling in the dashboard
        # In a real implementation, this would use the wallet adapter to get balance
        logger.info("Real wallet balance query not implemented in dashboard")
        return None
        
    except Exception as e:
        logger.error(f"Error getting real wallet balance: {e}")
        return None

def get_simulation_wallet_balance(conn):
    """Calculate simulation wallet balance from trades"""
    try:
        # Get all simulation trades
        query = """
        SELECT * FROM trades 
        WHERE (is_simulation = 1) OR 
              (is_simulation IS NULL AND contract_address LIKE 'Sim%')
        ORDER BY timestamp ASC
        """
        
        trades_df = pd.read_sql_query(query, conn)
        
        if trades_df.empty:
            return 1.0  # Default simulation starting balance
        
        # Calculate balance from trades
        starting_balance = 1.0  # Starting simulation balance
        current_balance = starting_balance
        
        for _, trade in trades_df.iterrows():
            if trade['action'] == 'BUY':
                # Subtract SOL spent on buying
                current_balance -= trade['amount']
            elif trade['action'] == 'SELL':
                # Add SOL received from selling
                current_balance += (trade['amount'] * trade['price'])
        
        return max(0, current_balance)  # Don't allow negative balance
        
    except Exception as e:
        logger.error(f"Error calculating simulation balance: {e}")
        return 1.0

def load_bot_settings():
    """Load bot settings with enhanced error handling - SINGLE SOURCE OF TRUTH."""
    control_files = [
        'bot_control.json',  # Primary location
        'data/bot_control.json',
        'core/bot_control.json'
    ]
    
    for control_file in control_files:
        if os.path.exists(control_file):
            try:
                with open(control_file, 'r') as f:
                    settings = json.load(f)
                    settings['_loaded_from'] = control_file
                    settings['_loaded_at'] = datetime.now().isoformat()
                    
                    # NORMALIZE PERCENTAGE VALUES - Convert decimals to percentages for display
                    # stop_loss_percentage: 0.25 -> 25.0 for display
                    if 'stop_loss_percentage' in settings and settings['stop_loss_percentage'] < 1.0:
                        settings['stop_loss_percentage_display'] = settings['stop_loss_percentage'] * 100
                    else:
                        settings['stop_loss_percentage_display'] = settings.get('stop_loss_percentage', 25.0)
                    
                    # slippage_tolerance: 0.3 -> 30.0 for display  
                    if 'slippage_tolerance' in settings and settings['slippage_tolerance'] < 1.0:
                        settings['slippage_tolerance_display'] = settings['slippage_tolerance'] * 100
                    else:
                        settings['slippage_tolerance_display'] = settings.get('slippage_tolerance', 30.0)
                    
                    logger.info(f"Loaded settings from {control_file}")
                    logger.info(f"Stop loss: {settings.get('stop_loss_percentage')} -> {settings['stop_loss_percentage_display']}% for display")
                    logger.info(f"Slippage: {settings.get('slippage_tolerance')} -> {settings['slippage_tolerance_display']}% for display")
                    
                    return settings
            except Exception as e:
                logger.error(f"Error loading {control_file}: {e}")
    
    # Default settings - should rarely be used
    logger.warning("No bot_control.json found, using defaults")
    return {
        "running": False,
        "simulation_mode": True,
        "take_profit_target": 2.5,
        "stop_loss_percentage": 0.25,  # Store as decimal
        "stop_loss_percentage_display": 25.0,  # Display as percentage
        "min_investment_per_token": 0.02,
        "max_investment_per_token": 0.1,
        "slippage_tolerance": 0.3,  # Store as decimal
        "slippage_tolerance_display": 30.0,  # Display as percentage
        "use_machine_learning": False,
        "_loaded_from": "default",
        "_loaded_at": datetime.now().isoformat()
    }

def find_database():
    """Find database with priority order."""
    db_files = [
        'data/sol_bot.db',
        'data/trading_bot.db',
        'core/data/sol_bot.db',
        'sol_bot.db',
        'trading_bot.db'
    ]
    
    for db_file in db_files:
        if os.path.exists(db_file):
            return db_file
    
    return None

def calculate_trade_pl(trades_df):
    """Calculate P&L for individual trades and overall performance"""
    if trades_df.empty:
        return trades_df, {}
    
    trades_with_pl = trades_df.copy()
    trades_with_pl['pl_sol'] = 0.0
    trades_with_pl['pl_usd'] = 0.0
    trades_with_pl['pl_percentage'] = 0.0
    trades_with_pl['trade_pair_id'] = None
    
    completed_trades = []
    overall_pl_sol = 0.0
    winning_trades = 0
    total_completed_trades = 0
    
    # Group by contract address to match buys with sells
    for contract_address, group in trades_df.groupby('contract_address'):
        buys = group[group['action'] == 'BUY'].copy()
        sells = group[group['action'] == 'SELL'].copy()
        
        # Match sells with buys (FIFO - First In, First Out)
        for sell_idx, sell_trade in sells.iterrows():
            # Find earliest buy that hasn't been fully matched
            remaining_sell_amount = sell_trade['amount']
            sell_price = sell_trade['price']
            
            for buy_idx, buy_trade in buys.iterrows():
                if remaining_sell_amount <= 0:
                    break
                
                buy_price = buy_trade['price']
                buy_amount = buy_trade['amount']
                
                # Calculate how much of this buy order to match
                matched_amount = min(remaining_sell_amount, buy_amount)
                
                # Calculate P&L for this matched portion
                pl_per_token = sell_price - buy_price
                pl_sol = pl_per_token * matched_amount
                pl_percentage = ((sell_price / buy_price) - 1) * 100 if buy_price > 0 else 0
                
                # Update the sell trade with P&L info
                trades_with_pl.loc[sell_idx, 'pl_sol'] = pl_sol
                trades_with_pl.loc[sell_idx, 'pl_percentage'] = pl_percentage
                trades_with_pl.loc[sell_idx, 'trade_pair_id'] = f"{contract_address}_{buy_idx}_{sell_idx}"
                
                # Track overall statistics
                overall_pl_sol += pl_sol
                total_completed_trades += 1
                if pl_sol > 0:
                    winning_trades += 1
                
                # Store completed trade info
                completed_trades.append({
                    'contract_address': contract_address,
                    'buy_time': buy_trade['timestamp'],
                    'sell_time': sell_trade['timestamp'],
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'amount': matched_amount,
                    'pl_sol': pl_sol,
                    'pl_percentage': pl_percentage,
                    'holding_time_hours': 0  # Calculate if needed
                })
                
                # Reduce remaining amounts
                remaining_sell_amount -= matched_amount
                buys.loc[buy_idx, 'amount'] -= matched_amount
                
                # Remove fully matched buy orders
                if buys.loc[buy_idx, 'amount'] <= 0:
                    buys = buys.drop(buy_idx)
    
    # Calculate USD P&L if SOL price is available
    sol_price = get_live_sol_price()
    if sol_price > 0:
        trades_with_pl['pl_usd'] = trades_with_pl['pl_sol'] * sol_price
    
    # Calculate overall metrics
    win_rate = (winning_trades / total_completed_trades * 100) if total_completed_trades > 0 else 0
    
    metrics = {
        'total_pl_sol': overall_pl_sol,
        'total_pl_usd': overall_pl_sol * sol_price if sol_price > 0 else 0,
        'win_rate': win_rate,
        'total_trades': total_completed_trades,
        'winning_trades': winning_trades,
        'losing_trades': total_completed_trades - winning_trades,
        'completed_trades': completed_trades
    }
    
    return trades_with_pl, metrics

def get_active_positions(conn, is_simulation=None):
    """Get active positions with current P&L"""
    try:
        # Build query based on simulation filter
        if is_simulation is True:
            query = """
            SELECT * FROM trades 
            WHERE (is_simulation = 1) OR 
                  (is_simulation IS NULL AND contract_address LIKE 'Sim%')
            """
        elif is_simulation is False:
            query = """
            SELECT * FROM trades 
            WHERE (is_simulation = 0) OR 
                  (is_simulation IS NULL AND contract_address NOT LIKE 'Sim%')
            """
        else:
            query = "SELECT * FROM trades"
        
        trades_df = pd.read_sql_query(query, conn)
        
        if trades_df.empty:
            return pd.DataFrame()
        
        active_positions = []
        
        for contract_address, group in trades_df.groupby('contract_address'):
            buys = group[group['action'] == 'BUY']
            sells = group[group['action'] == 'SELL']
            
            total_bought = buys['amount'].sum()
            total_sold = sells['amount'].sum() if not sells.empty else 0
            
            if total_bought > total_sold:
                # Calculate average buy price
                avg_buy_price = (buys['amount'] * buys['price']).sum() / total_bought
                
                # Get token info
                cursor = conn.cursor()
                cursor.execute("SELECT ticker, name FROM tokens WHERE contract_address = ?", (contract_address,))
                token_info = cursor.fetchone()
                
                ticker = token_info[0] if token_info and token_info[0] else contract_address[:8]
                name = token_info[1] if token_info and token_info[1] else f"Token {ticker}"
                
                # Calculate current position value (using buy price as current price for now)
                # In a real implementation, you'd fetch current market price
                current_price = avg_buy_price  # Placeholder
                position_amount = total_bought - total_sold
                
                # Calculate unrealized P&L
                unrealized_pl_sol = (current_price - avg_buy_price) * position_amount
                unrealized_pl_percentage = ((current_price / avg_buy_price) - 1) * 100 if avg_buy_price > 0 else 0
                
                # Determine if simulation
                is_sim = contract_address.startswith('Sim') or 'simulation' in contract_address.lower()
                
                active_positions.append({
                    'contract_address': contract_address,
                    'ticker': ticker,
                    'name': name,
                    'amount': position_amount,
                    'avg_buy_price': avg_buy_price,
                    'current_price': current_price,
                    'unrealized_pl_sol': unrealized_pl_sol,
                    'unrealized_pl_percentage': unrealized_pl_percentage,
                    'entry_time': buys['timestamp'].min(),
                    'is_simulation': is_sim
                })
        
        return pd.DataFrame(active_positions) if active_positions else pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Error getting active positions: {e}")
        return pd.DataFrame()

def main():
    # Header with live status
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title("🤖 Enhanced AI Trading Bot Dashboard")
    
    with col2:
        auto_refresh = st.checkbox("Auto Refresh", value=st.session_state.auto_refresh)
        st.session_state.auto_refresh = auto_refresh
    
    with col3:
        if st.button("🔄 Refresh Now"):
            st.session_state.last_update = datetime.now()
            st.experimental_rerun()
    
    # Load data
    bot_settings = load_bot_settings()
    sol_price = get_live_sol_price()
    db_file = find_database()
    
    # Get wallet balances (FIXED - no hardcoded fallback)
    simulation_mode = bot_settings.get('simulation_mode', True)
    
    real_wallet_balance = None
    sim_wallet_balance = None
    
    if db_file and os.path.exists(db_file):
        conn = sqlite3.connect(db_file)
        
        # Always calculate simulation balance from trades
        sim_wallet_balance = get_simulation_wallet_balance(conn)
        
        # Only try to get real balance if not in simulation mode
        if not simulation_mode:
            real_wallet_balance = get_real_wallet_balance()
        
        conn.close()
    
    # Status bar
    status_col1, status_col2, status_col3, status_col4, status_col5 = st.columns(5)
    
    with status_col1:
        bot_status = "🟢 RUNNING" if bot_settings.get('running', False) else "🔴 STOPPED"
        st.markdown(f"**Bot:** {bot_status}")
    
    with status_col2:
        mode_status = "🧪 SIM" if simulation_mode else "💰 REAL"
        st.markdown(f"**Mode:** {mode_status}")
    
    with status_col3:
        ml_status = "🤖 ON" if bot_settings.get('use_machine_learning', False) else "🤖 OFF"
        ml_color = "status-online" if bot_settings.get('use_machine_learning', False) else "status-offline"
        st.markdown(f"**ML:** <span class='{ml_color}'>{ml_status}</span>", unsafe_allow_html=True)
    
    with status_col4:
        sol_status = f"${sol_price:.2f}" if sol_price > 0 else "N/A"
        st.markdown(f"**SOL:** {sol_status}")
    
    with status_col5:
        last_update = st.session_state.last_update.strftime("%H:%M:%S")
        st.markdown(f"**Updated:** <span class='live-tag'>{last_update}</span>", unsafe_allow_html=True)
    
    # Main content tabs
    tabs = st.tabs([
        "📊 Live Monitor", 
        "💰 Balance & Positions", 
        "📈 Trading Analysis",
        "⚙️ Parameters"
    ])
    
    # Tab 1: Live Monitor
    with tabs[0]:
        st.subheader("📊 Live Trading Monitor")
        
        # Key metrics row with FIXED balance display
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            # FIXED: Show appropriate balance based on mode, with NO fallback
            if simulation_mode:
                if sim_wallet_balance is not None:
                    balance_sol = sim_wallet_balance
                    balance_usd = balance_sol * sol_price if sol_price > 0 else 0
                    st.markdown(f"""
                    <div class='balance-card'>
                        <div class='main-metric'>{balance_sol:.6f} SOL</div>
                        <div class='sub-metric'>${balance_usd:.2f} USD</div>
                        <div class='sub-metric'>Simulation Balance</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class='balance-card na'>
                        <div class='main-metric'>N/A</div>
                        <div class='sub-metric'>Simulation Balance</div>
                        <div class='sub-metric'>No trade data</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # Real trading mode
                if real_wallet_balance is not None:
                    balance_usd = real_wallet_balance * sol_price if sol_price > 0 else 0
                    st.markdown(f"""
                    <div class='balance-card'>
                        <div class='main-metric'>{real_wallet_balance:.6f} SOL</div>
                        <div class='sub-metric'>${balance_usd:.2f} USD</div>
                        <div class='sub-metric'>Real Balance</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class='balance-card na'>
                        <div class='main-metric status-na'>N/A</div>
                        <div class='sub-metric'>Real Balance</div>
                        <div class='sub-metric'>Cannot connect to wallet</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        with metric_col2:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='main-metric'>${sol_price:.2f}</div>
                <div class='sub-metric'>SOL Price</div>
                <div class='sub-metric live-tag'>● LIVE</div>
            </div>
            """, unsafe_allow_html=True)
        
        with metric_col3:
            # Calculate P&L from database
            total_pl_sol = 0.0
            total_pl_usd = 0.0
            
            if db_file and os.path.exists(db_file):
                try:
                    conn = sqlite3.connect(db_file)
                    
                    # Get trades for current mode
                    if simulation_mode:
                        query = """
                        SELECT * FROM trades 
                        WHERE (is_simulation = 1) OR 
                              (is_simulation IS NULL AND contract_address LIKE 'Sim%')
                        """
                    else:
                        query = """
                        SELECT * FROM trades 
                        WHERE (is_simulation = 0) OR 
                              (is_simulation IS NULL AND contract_address NOT LIKE 'Sim%')
                        """
                    
                    trades_df = pd.read_sql_query(query, conn)
                    
                    if not trades_df.empty:
                        _, metrics = calculate_trade_pl(trades_df)
                        total_pl_sol = metrics.get('total_pl_sol', 0.0)
                        total_pl_usd = metrics.get('total_pl_usd', 0.0)
                    
                    conn.close()
                except Exception as e:
                    logger.error(f"Error calculating P&L: {e}")
            
            pl_color = 'profit' if total_pl_sol >= 0 else 'loss'
            st.markdown(f"""
            <div class='metric-card'>
                <div class='main-metric {pl_color}'>${total_pl_usd:.2f}</div>
                <div class='sub-metric {pl_color}'>{total_pl_sol:.6f} SOL</div>
                <div class='sub-metric'>Total P&L</div>
            </div>
            """, unsafe_allow_html=True)
        
        with metric_col4:
            # Get active positions count
            active_positions_count = 0
            if db_file and os.path.exists(db_file):
                try:
                    conn = sqlite3.connect(db_file)
                    active_positions = get_active_positions(conn, is_simulation=simulation_mode)
                    active_positions_count = len(active_positions)
                    conn.close()
                except Exception as e:
                    logger.error(f"Error getting positions count: {e}")
            
            st.markdown(f"""
            <div class='metric-card'>
                <div class='main-metric'>{active_positions_count}</div>
                <div class='sub-metric'>Active Positions</div>
                <div class='sub-metric'>Currently Held</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Recent trading activity with P&L
        st.subheader("Recent Trading Activity")
        
        if db_file and os.path.exists(db_file):
            try:
                conn = sqlite3.connect(db_file)
                
                # Get recent trades for current mode
                if simulation_mode:
                    query = """
                    SELECT * FROM trades 
                    WHERE (is_simulation = 1) OR 
                          (is_simulation IS NULL AND contract_address LIKE 'Sim%')
                    ORDER BY id DESC 
                    LIMIT 20
                    """
                else:
                    query = """
                    SELECT * FROM trades 
                    WHERE (is_simulation = 0) OR 
                          (is_simulation IS NULL AND contract_address NOT LIKE 'Sim%')
                    ORDER BY id DESC 
                    LIMIT 20
                    """
                
                recent_trades = pd.read_sql_query(query, conn)
                
                if not recent_trades.empty:
                    # Calculate P&L for recent trades
                    trades_with_pl, _ = calculate_trade_pl(recent_trades)
                    
                    # Format for display
                    display_trades = trades_with_pl[['timestamp', 'action', 'contract_address', 'amount', 'price', 'pl_sol', 'pl_percentage']].copy()
                    display_trades.columns = ['Time', 'Action', 'Token', 'Amount (SOL)', 'Price', 'P&L (SOL)', 'P&L (%)']
                    
                    # Format columns
                    display_trades['Time'] = pd.to_datetime(display_trades['Time']).dt.strftime('%H:%M:%S')
                    display_trades['Token'] = display_trades['Token'].apply(lambda x: x[:8] + "..." if len(str(x)) > 8 else str(x))
                    display_trades['Price'] = display_trades['Price'].apply(lambda x: f"${x:.8f}" if pd.notna(x) else "N/A")
                    display_trades['Amount (SOL)'] = display_trades['Amount (SOL)'].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "N/A")
                    
                    # Format P&L columns with colors
                    def format_pl_sol(val):
                        if pd.isna(val) or val == 0:
                            return "N/A"
                        color = "🟢" if val > 0 else "🔴" if val < 0 else "⚪"
                        return f"{color} {val:.6f}"
                    
                    def format_pl_pct(val):
                        if pd.isna(val) or val == 0:
                            return "N/A"
                        color = "🟢" if val > 0 else "🔴" if val < 0 else "⚪"
                        return f"{color} {val:.2f}%"
                    
                    display_trades['P&L (SOL)'] = display_trades['P&L (SOL)'].apply(format_pl_sol)
                    display_trades['P&L (%)'] = display_trades['P&L (%)'].apply(format_pl_pct)
                    
                    st.dataframe(display_trades, use_container_width=True)
                else:
                    mode_text = "simulation" if simulation_mode else "real"
                    st.info(f"No recent {mode_text} trading activity")
                
                conn.close()
                
            except Exception as e:
                st.error(f"Error loading trading data: {e}")
        else:
            st.warning("Database not found - trading history unavailable")
    
    # Tab 2: Balance & Positions (FIXED)
    with tabs[1]:
        st.subheader("💰 Balance & Position Management")
        
        # Balance overview with FIXED display
        balance_col1, balance_col2 = st.columns(2)
        
        with balance_col1:
            st.markdown("#### 💳 Wallet Status")
            
            if simulation_mode:
                # Simulation mode
                if sim_wallet_balance is not None:
                    balance_usd = sim_wallet_balance * sol_price if sol_price > 0 else 0
                    st.markdown(f"""
                    <div class='balance-card'>
                        <h3>Simulation Balance</h3>
                        <div class='main-metric'>{sim_wallet_balance:.6f} SOL</div>
                        <div class='sub-metric'>${balance_usd:.2f} USD</div>
                        <hr>
                        <div class='sub-metric'>Calculated from trades</div>
                        <div class='sub-metric'>Updated: {datetime.now().strftime('%H:%M:%S')}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class='balance-card na'>
                        <h3>Simulation Balance</h3>
                        <div class='main-metric status-na'>N/A</div>
                        <div class='sub-metric'>No trade data available</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # Real trading mode
                if real_wallet_balance is not None:
                    balance_usd = real_wallet_balance * sol_price if sol_price > 0 else 0
                    st.markdown(f"""
                    <div class='balance-card'>
                        <h3>Real Wallet Balance</h3>
                        <div class='main-metric'>{real_wallet_balance:.6f} SOL</div>
                        <div class='sub-metric'>${balance_usd:.2f} USD</div>
                        <hr>
                        <div class='sub-metric'>Live from blockchain</div>
                        <div class='sub-metric'>Updated: {datetime.now().strftime('%H:%M:%S')}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class='balance-card danger'>
                        <h3>Real Wallet Balance</h3>
                        <div class='main-metric status-na'>N/A</div>
                        <div class='sub-metric'>Cannot connect to wallet</div>
                        <div class='sub-metric'>Check wallet configuration</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        with balance_col2:
            st.markdown("#### 📊 Risk Assessment")
            
            # Calculate risk score
            risk_score = 0
            if not simulation_mode:
                risk_score += 30
            if bot_settings.get('slippage_tolerance', 5.0) > 10:
                risk_score += 25
            
            # Add balance-based risk
            current_balance = sim_wallet_balance if simulation_mode else real_wallet_balance
            if current_balance is not None and current_balance < 0.1:
                risk_score += 30
            elif current_balance is not None and current_balance < 0.5:
                risk_score += 15
            
            risk_level = "Low" if risk_score < 25 else "Medium" if risk_score < 50 else "High"
            risk_color = "#4CAF50" if risk_score < 25 else "#FF9800" if risk_score < 50 else "#F44336"
            
            st.markdown(f"""
            <div class='metric-card'>
                <div class='main-metric' style='color: {risk_color}'>Risk Level: {risk_level}</div>
                <div class='sub-metric'>Score: {risk_score}/100</div>
                <div class='sub-metric'>Mode: {'Simulation' if simulation_mode else 'Real Trading'}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Active positions with P&L
        st.subheader("Active Positions with P&L")
        
        if db_file and os.path.exists(db_file):
            try:
                conn = sqlite3.connect(db_file)
                active_positions = get_active_positions(conn, is_simulation=simulation_mode)
                
                if not active_positions.empty:
                    # Format for display
                    display_positions = active_positions[['ticker', 'name', 'amount', 'avg_buy_price', 'current_price', 'unrealized_pl_sol', 'unrealized_pl_percentage']].copy()
                    display_positions.columns = ['Ticker', 'Name', 'Amount', 'Buy Price', 'Current Price', 'Unrealized P&L (SOL)', 'Unrealized P&L (%)']
                    
                    # Format columns
                    display_positions['Buy Price'] = display_positions['Buy Price'].apply(lambda x: f"${x:.6f}")
                    display_positions['Current Price'] = display_positions['Current Price'].apply(lambda x: f"${x:.6f}")
                    
                    def format_pl_sol_detailed(val):
                        if pd.isna(val):
                            return "N/A"
                        color = "🟢" if val > 0 else "🔴" if val < 0 else "⚪"
                        return f"{color} {val:.6f}"
                    
                    def format_pl_pct_detailed(val):
                        if pd.isna(val):
                            return "N/A"
                        color = "🟢" if val > 0 else "🔴" if val < 0 else "⚪"
                        return f"{color} {val:.2f}%"
                    
                    display_positions['Unrealized P&L (SOL)'] = display_positions['Unrealized P&L (SOL)'].apply(format_pl_sol_detailed)
                    display_positions['Unrealized P&L (%)'] = display_positions['Unrealized P&L (%)'].apply(format_pl_pct_detailed)
                    
                    st.dataframe(display_positions, use_container_width=True)
                    
                    # Summary metrics
                    total_unrealized_pl = active_positions['unrealized_pl_sol'].sum()
                    avg_pl_percentage = active_positions['unrealized_pl_percentage'].mean()
                    
                    summary_col1, summary_col2, summary_col3 = st.columns(3)
                    
                    with summary_col1:
                        pl_color = 'profit' if total_unrealized_pl >= 0 else 'loss'
                        st.markdown(f"""
                        <div class='metric-card'>
                            <div class='main-metric {pl_color}'>Total Unrealized P&L</div>
                            <div class='sub-metric {pl_color}'>{total_unrealized_pl:.6f} SOL</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with summary_col2:
                        avg_color = 'profit' if avg_pl_percentage >= 0 else 'loss'
                        st.markdown(f"""
                        <div class='metric-card'>
                            <div class='main-metric {avg_color}'>Average P&L</div>
                            <div class='sub-metric {avg_color}'>{avg_pl_percentage:.2f}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with summary_col3:
                        st.markdown(f"""
                        <div class='metric-card'>
                            <div class='main-metric'>Total Positions</div>
                            <div class='sub-metric'>{len(active_positions)}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                else:
                    mode_text = "simulation" if simulation_mode else "real"
                    st.info(f"No active {mode_text} positions")
                
                conn.close()
                
            except Exception as e:
                st.error(f"Error loading positions: {e}")
        else:
            st.info("No database found")
    
    # Tab 3: Trading Analysis with enhanced P&L tracking
    with tabs[2]:
        st.subheader("📈 Trading Performance Analysis")
        
        if db_file and os.path.exists(db_file):
            try:
                conn = sqlite3.connect(db_file)
                
                # Get trades for current mode
                if simulation_mode:
                    query = """
                    SELECT * FROM trades 
                    WHERE (is_simulation = 1) OR 
                          (is_simulation IS NULL AND contract_address LIKE 'Sim%')
                    """
                else:
                    query = """
                    SELECT * FROM trades 
                    WHERE (is_simulation = 0) OR 
                          (is_simulation IS NULL AND contract_address NOT LIKE 'Sim%')
                    """
                
                trades_df = pd.read_sql_query(query, conn)
                
                if not trades_df.empty:
                    # Calculate comprehensive P&L
                    trades_with_pl, metrics = calculate_trade_pl(trades_df)
                    
                    # Performance metrics
                    st.markdown("#### 📊 Performance Summary")
                    
                    perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)
                    
                    with perf_col1:
                        total_pl_sol = metrics['total_pl_sol']
                        pl_color = 'profit' if total_pl_sol >= 0 else 'loss'
                        st.markdown(f"""
                        <div class='metric-card'>
                            <div class='main-metric {pl_color}'>Total P&L</div>
                            <div class='sub-metric {pl_color}'>{total_pl_sol:.6f} SOL</div>
                            <div class='sub-metric {pl_color}'>${metrics["total_pl_usd"]:.2f} USD</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with perf_col2:
                        win_rate = metrics['win_rate']
                        wr_color = 'profit' if win_rate >= 60 else 'neutral' if win_rate >= 40 else 'loss'
                        st.markdown(f"""
                        <div class='metric-card'>
                            <div class='main-metric {wr_color}'>Win Rate</div>
                            <div class='sub-metric {wr_color}'>{win_rate:.1f}%</div>
                            <div class='sub-metric'>{metrics["winning_trades"]}/{metrics["total_trades"]} trades</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with perf_col3:
                        st.markdown(f"""
                        <div class='metric-card'>
                            <div class='main-metric'>Total Trades</div>
                            <div class='sub-metric'>{metrics["total_trades"]}</div>
                            <div class='sub-metric'>Completed pairs</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with perf_col4:
                        # Calculate best trade
                        if metrics['completed_trades']:
                            best_trade = max(metrics['completed_trades'], key=lambda x: x['pl_percentage'])
                            st.markdown(f"""
                            <div class='metric-card'>
                                <div class='main-metric profit'>Best Trade</div>
                                <div class='sub-metric profit'>{best_trade['pl_percentage']:.2f}%</div>
                                <div class='sub-metric'>{best_trade['pl_sol']:.6f} SOL</div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class='metric-card'>
                                <div class='main-metric'>Best Trade</div>
                                <div class='sub-metric'>N/A</div>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Completed trades table
                    st.markdown("#### 📋 Completed Trades with P&L")
                    
                    if metrics['completed_trades']:
                        completed_df = pd.DataFrame(metrics['completed_trades'])
                        
                        # Format for display
                        display_completed = completed_df[['buy_time', 'sell_time', 'contract_address', 'amount', 'buy_price', 'sell_price', 'pl_sol', 'pl_percentage']].copy()
                        display_completed.columns = ['Buy Time', 'Sell Time', 'Token', 'Amount', 'Buy Price', 'Sell Price', 'P&L (SOL)', 'P&L (%)']
                        
                        # Format columns
                        display_completed['Buy Time'] = pd.to_datetime(display_completed['Buy Time']).dt.strftime('%Y-%m-%d %H:%M')
                        display_completed['Sell Time'] = pd.to_datetime(display_completed['Sell Time']).dt.strftime('%Y-%m-%d %H:%M')
                        display_completed['Token'] = display_completed['Token'].apply(lambda x: x[:12] + "..." if len(str(x)) > 12 else str(x))
                        display_completed['Buy Price'] = display_completed['Buy Price'].apply(lambda x: f"${x:.6f}")
                        display_completed['Sell Price'] = display_completed['Sell Price'].apply(lambda x: f"${x:.6f}")
                        
                        def format_completed_pl_sol(val):
                            color = "🟢" if val > 0 else "🔴" if val < 0 else "⚪"
                            return f"{color} {val:.6f}"
                        
                        def format_completed_pl_pct(val):
                            color = "🟢" if val > 0 else "🔴" if val < 0 else "⚪"
                            return f"{color} {val:.2f}%"
                        
                        display_completed['P&L (SOL)'] = display_completed['P&L (SOL)'].apply(format_completed_pl_sol)
                        display_completed['P&L (%)'] = display_completed['P&L (%)'].apply(format_completed_pl_pct)
                        
                        st.dataframe(display_completed, use_container_width=True)
                        
                        # Download button
                        csv = completed_df.to_csv(index=False)
                        b64 = base64.b64encode(csv.encode()).decode()
                        href = f'<a href="data:file/csv;base64,{b64}" download="trading_analysis.csv">Download Analysis CSV</a>'
                        st.markdown(href, unsafe_allow_html=True)
                    else:
                        st.info("No completed trades yet")
                
                else:
                    mode_text = "simulation" if simulation_mode else "real"
                    st.info(f"No {mode_text} trading data available for analysis")
                
                conn.close()
                
            except Exception as e:
                st.error(f"Error loading analysis data: {e}")
        else:
            st.warning("No database found - analysis unavailable")
    
    # Tab 4: Parameters (unchanged)
    with tabs[3]:
        st.subheader("⚙️ Trading Parameters")
        
        param_col1, param_col2 = st.columns(2)
        
        with param_col1:
            bot_running = st.checkbox(
                "🤖 Bot Running",
                value=bot_settings.get('running', False)
            )
            
            simulation_mode_setting = st.checkbox(
                "🧪 Simulation Mode",
                value=bot_settings.get('simulation_mode', True)
            )
        
        with param_col2:
            ml_enabled = st.checkbox(
                "🧠 Machine Learning",
                value=bot_settings.get('use_machine_learning', False)
            )
        
        # Trading parameters
        st.markdown("#### Trading Parameters")
        
        tp_col1, tp_col2, tp_col3 = st.columns(3)
        
        with tp_col1:
            take_profit = st.number_input(
                "Take Profit Target",
                min_value=1.1,
                max_value=10.0,
                value=float(bot_settings.get('take_profit_target', 2.5)),
                step=0.1
            )
        
        with tp_col2:
            # FIXED: Use the display version and handle conversion properly
            stop_loss_display = bot_settings.get('stop_loss_percentage_display', 25.0)
            stop_loss = st.number_input(
                "Stop Loss (%)",
                min_value=1.0,  # Changed min_value to 1.0
                max_value=50.0,
                value=float(stop_loss_display),
                step=1.0,
                help="Stop loss percentage (stored as decimal in config)"
            )
        
        with tp_col3:
            max_investment = st.number_input(
                "Max Investment (SOL)",
                min_value=0.01,
                max_value=10.0,
                value=float(bot_settings.get('max_investment_per_token', 0.1)),
                step=0.01
            )
        
def save_bot_settings(settings, control_file='bot_control.json'):
    """Save bot settings to control file - SINGLE SOURCE OF TRUTH."""
    try:
        # Convert display percentages back to decimals for storage
        settings_to_save = settings.copy()
        
        # Convert percentage displays back to decimals for storage
        if 'stop_loss_percentage_display' in settings_to_save:
            settings_to_save['stop_loss_percentage'] = settings_to_save['stop_loss_percentage_display'] / 100
            del settings_to_save['stop_loss_percentage_display']
        
        if 'slippage_tolerance_display' in settings_to_save:
            settings_to_save['slippage_tolerance'] = settings_to_save['slippage_tolerance_display'] / 100
            del settings_to_save['slippage_tolerance_display']
        
        # Remove metadata
        settings_to_save.pop('_loaded_from', None)
        settings_to_save.pop('_loaded_at', None)
        
        with open(control_file, 'w') as f:
            json.dump(settings_to_save, f, indent=4)
        
        logger.info(f"Settings saved to {control_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving settings to {control_file}: {e}")
        return False

def save_bot_settings(settings, control_file='bot_control.json'):
    """Save bot settings to control file - SINGLE SOURCE OF TRUTH."""
    try:
        # Convert display percentages back to decimals for storage
        settings_to_save = settings.copy()
        
        # Convert percentage displays back to decimals for storage
        if 'stop_loss_percentage_display' in settings_to_save:
            settings_to_save['stop_loss_percentage'] = settings_to_save['stop_loss_percentage_display'] / 100
            del settings_to_save['stop_loss_percentage_display']
        
        if 'slippage_tolerance_display' in settings_to_save:
            settings_to_save['slippage_tolerance'] = settings_to_save['slippage_tolerance_display'] / 100
            del settings_to_save['slippage_tolerance_display']
        
        # Remove metadata
        settings_to_save.pop('_loaded_from', None)
        settings_to_save.pop('_loaded_at', None)
        
        with open(control_file, 'w') as f:
            json.dump(settings_to_save, f, indent=4)
        
        logger.info(f"Settings saved to {control_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving settings to {control_file}: {e}")
        return False

if __name__ == "__main__":
    main()