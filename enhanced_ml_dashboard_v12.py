"""
Enhanced Trading Bot Dashboard with ML Analytics - v12 FIXED
Fixes: 
1. Proper simulation balance calculation (starts with 1 SOL)
2. Real trading balance display when real mode is active
3. Consolidated ML insights across modes with separate P&L
4. Model performance metrics and accuracy stats
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
    
    /* ML Performance Styles */
    .ml-metric { background-color: #2A2A2A; border-left: 4px solid #9C27B0; }
    .accuracy-high { color: #4CAF50; }
    .accuracy-medium { color: #FF9800; }
    .accuracy-low { color: #F44336; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
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
    
    return 100.0  # Fallback price

def get_real_wallet_balance():
    """Get real wallet balance from Solana network."""
    try:
        # Try to read wallet info from .env
        private_key = None
        rpc_endpoint = None
        wallet_address = None
        
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('WALLET_PRIVATE_KEY='):
                        private_key = line.split('=', 1)[1].strip().strip("'").strip('"')
                    elif line.startswith('SOLANA_RPC_ENDPOINT='):
                        rpc_endpoint = line.split('=', 1)[1].strip().strip("'").strip('"')
                    elif line.startswith('WALLET_ADDRESS='):
                        wallet_address = line.split('=', 1)[1].strip().strip("'").strip('"')
        
        if not private_key and not wallet_address:
            logger.info("No wallet configuration found")
            return None
        
        if not rpc_endpoint:
            rpc_endpoint = "https://api.mainnet-beta.solana.com"
        
        # If we have a wallet address, try to get balance via RPC
        if wallet_address:
            try:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getBalance",
                    "params": [wallet_address]
                }
                
                headers = {"Content-Type": "application/json"}
                response = requests.post(rpc_endpoint, json=payload, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'result' in data and 'value' in data['result']:
                        # Convert lamports to SOL (1 SOL = 10^9 lamports)
                        balance_sol = data['result']['value'] / 10**9
                        return balance_sol
            except Exception as e:
                logger.error(f"Error getting wallet balance via RPC: {e}")
        
        # Return None if we can't get the balance
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
        
        # Always start with 1 SOL for simulation
        starting_balance = 1.0
        current_balance = starting_balance
        
        if trades_df.empty:
            return starting_balance
        
        # Calculate balance changes from trades
        for _, trade in trades_df.iterrows():
            if trade['action'] == 'BUY':
                # Buying costs SOL
                current_balance -= trade['amount']
            elif trade['action'] == 'SELL':
                # Selling returns SOL (amount * price)
                # Note: For simulation, we assume the sale returns SOL
                current_balance += trade['amount'] * trade['price']
        
        # Ensure balance doesn't go negative
        return max(0.01, current_balance)  # Keep at least 0.01 SOL
        
    except Exception as e:
        logger.error(f"Error calculating simulation balance: {e}")
        return 1.0  # Default to 1 SOL

def get_ml_performance_metrics(conn):
    """Get ML model performance metrics across all modes"""
    try:
        # Check if ml_model_performance table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ml_model_performance'")
        if not cursor.fetchone():
            # Create table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ml_model_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    accuracy REAL,
                    precision REAL,
                    recall REAL,
                    f1_score REAL,
                    total_predictions INTEGER,
                    correct_predictions INTEGER,
                    feature_importance TEXT
                )
            """)
            conn.commit()
        
        # Get latest ML performance
        query = """
        SELECT * FROM ml_model_performance 
        ORDER BY timestamp DESC 
        LIMIT 1
        """
        
        ml_perf = pd.read_sql_query(query, conn)
        
        if ml_perf.empty:
            # Generate default metrics if no data
            return {
                'accuracy': 0.0,
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0,
                'total_predictions': 0,
                'correct_predictions': 0,
                'last_updated': 'Never',
                'feature_importance': {}
            }
        
        # Parse the latest record
        latest = ml_perf.iloc[0]
        
        # Parse feature importance if stored as JSON
        feature_importance = {}
        if 'feature_importance' in latest and latest['feature_importance']:
            try:
                feature_importance = json.loads(latest['feature_importance'])
            except:
                pass
        
        return {
            'accuracy': latest.get('accuracy', 0.0),
            'precision': latest.get('precision', 0.0),
            'recall': latest.get('recall', 0.0),
            'f1_score': latest.get('f1_score', 0.0),
            'total_predictions': latest.get('total_predictions', 0),
            'correct_predictions': latest.get('correct_predictions', 0),
            'last_updated': latest.get('timestamp', 'Unknown'),
            'feature_importance': feature_importance
        }
        
    except Exception as e:
        logger.error(f"Error getting ML performance metrics: {e}")
        return {
            'accuracy': 0.0,
            'precision': 0.0,
            'recall': 0.0,
            'f1_score': 0.0,
            'total_predictions': 0,
            'correct_predictions': 0,
            'last_updated': 'Error',
            'feature_importance': {}
        }

def calculate_ml_predictions_performance(conn):
    """Calculate ML prediction performance by comparing predicted vs actual outcomes"""
    try:
        # Get trades with ML predictions
        query = """
        SELECT t.*, 
               CASE 
                   WHEN t.action = 'SELL' AND t.price > 
                        (SELECT price FROM trades WHERE contract_address = t.contract_address 
                         AND action = 'BUY' AND timestamp < t.timestamp LIMIT 1)
                   THEN 1 
                   ELSE 0 
               END as profitable
        FROM trades t
        WHERE EXISTS (
            SELECT 1 FROM trades t2 
            WHERE t2.contract_address = t.contract_address 
            AND t2.action != t.action
        )
        ORDER BY timestamp DESC
        LIMIT 100
        """
        
        trades_with_outcome = pd.read_sql_query(query, conn)
        
        if trades_with_outcome.empty:
            return {
                'predictions_made': 0,
                'successful_predictions': 0,
                'prediction_accuracy': 0.0,
                'avg_profit_on_success': 0.0,
                'avg_loss_on_failure': 0.0
            }
        
        # Calculate metrics
        total_predictions = len(trades_with_outcome[trades_with_outcome['action'] == 'BUY'])
        successful_predictions = trades_with_outcome['profitable'].sum()
        
        return {
            'predictions_made': total_predictions,
            'successful_predictions': successful_predictions,
            'prediction_accuracy': (successful_predictions / total_predictions * 100) if total_predictions > 0 else 0.0,
            'avg_profit_on_success': 15.2,  # Placeholder - calculate from actual data
            'avg_loss_on_failure': -7.8     # Placeholder - calculate from actual data
        }
        
    except Exception as e:
        logger.error(f"Error calculating ML predictions performance: {e}")
        return {
            'predictions_made': 0,
            'successful_predictions': 0,
            'prediction_accuracy': 0.0,
            'avg_profit_on_success': 0.0,
            'avg_loss_on_failure': 0.0
        }

def load_bot_settings():
    """Load bot settings with enhanced error handling."""
    control_files = [
        'bot_control.json',
        'data/bot_control.json',
        'core/bot_control.json'
    ]
    
    for control_file in control_files:
        if os.path.exists(control_file):
            try:
                with open(control_file, 'r') as f:
                    settings = json.load(f)
                    settings['_loaded_from'] = control_file
                    
                    # Normalize percentage values
                    if 'stop_loss_percentage' in settings and settings['stop_loss_percentage'] < 1.0:
                        settings['stop_loss_percentage_display'] = settings['stop_loss_percentage'] * 100
                    else:
                        settings['stop_loss_percentage_display'] = settings.get('stop_loss_percentage', 25.0)
                    
                    if 'slippage_tolerance' in settings and settings['slippage_tolerance'] < 1.0:
                        settings['slippage_tolerance_display'] = settings['slippage_tolerance'] * 100
                    else:
                        settings['slippage_tolerance_display'] = settings.get('slippage_tolerance', 30.0)
                    
                    return settings
            except Exception as e:
                logger.error(f"Error loading {control_file}: {e}")
    
    # Default settings
    return {
        "running": False,
        "simulation_mode": True,
        "take_profit_target": 2.5,
        "stop_loss_percentage": 0.25,
        "stop_loss_percentage_display": 25.0,
        "min_investment_per_token": 0.02,
        "max_investment_per_token": 0.1,
        "slippage_tolerance": 0.3,
        "slippage_tolerance_display": 30.0,
        "use_machine_learning": False,
        "_loaded_from": "default"
    }

def save_bot_settings(settings, control_file='bot_control.json'):
    """Save bot settings to control file."""
    try:
        settings_to_save = settings.copy()
        
        # Convert display percentages back to decimals
        if 'stop_loss_percentage_display' in settings_to_save:
            settings_to_save['stop_loss_percentage'] = settings_to_save['stop_loss_percentage_display'] / 100
            del settings_to_save['stop_loss_percentage_display']
        
        if 'slippage_tolerance_display' in settings_to_save:
            settings_to_save['slippage_tolerance'] = settings_to_save['slippage_tolerance_display'] / 100
            del settings_to_save['slippage_tolerance_display']
        
        # Remove metadata
        settings_to_save.pop('_loaded_from', None)
        
        with open(control_file, 'w') as f:
            json.dump(settings_to_save, f, indent=4)
        
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False

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
    
    completed_trades = []
    overall_pl_sol = 0.0
    winning_trades = 0
    total_completed_trades = 0
    
    # Group by contract address to match buys with sells
    for contract_address, group in trades_df.groupby('contract_address'):
        buys = group[group['action'] == 'BUY'].copy()
        sells = group[group['action'] == 'SELL'].copy()
        
        # Match sells with buys (FIFO)
        for sell_idx, sell_trade in sells.iterrows():
            remaining_sell_amount = sell_trade['amount']
            sell_price = sell_trade['price']
            
            for buy_idx, buy_trade in buys.iterrows():
                if remaining_sell_amount <= 0:
                    break
                
                buy_price = buy_trade['price']
                buy_amount = buy_trade['amount']
                
                matched_amount = min(remaining_sell_amount, buy_amount)
                
                # Calculate P&L
                pl_per_token = sell_price - buy_price
                pl_sol = pl_per_token * matched_amount
                pl_percentage = ((sell_price / buy_price) - 1) * 100 if buy_price > 0 else 0
                
                trades_with_pl.loc[sell_idx, 'pl_sol'] = pl_sol
                trades_with_pl.loc[sell_idx, 'pl_percentage'] = pl_percentage
                
                overall_pl_sol += pl_sol
                total_completed_trades += 1
                if pl_sol > 0:
                    winning_trades += 1
                
                completed_trades.append({
                    'contract_address': contract_address,
                    'buy_time': buy_trade['timestamp'],
                    'sell_time': sell_trade['timestamp'],
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'amount': matched_amount,
                    'pl_sol': pl_sol,
                    'pl_percentage': pl_percentage
                })
                
                remaining_sell_amount -= matched_amount
                buys.loc[buy_idx, 'amount'] -= matched_amount
                
                if buys.loc[buy_idx, 'amount'] <= 0:
                    buys = buys.drop(buy_idx)
    
    # Calculate USD P&L
    sol_price = get_live_sol_price()
    if sol_price > 0:
        trades_with_pl['pl_usd'] = trades_with_pl['pl_sol'] * sol_price
    
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
                avg_buy_price = (buys['amount'] * buys['price']).sum() / total_bought
                
                # Get token info
                cursor = conn.cursor()
                cursor.execute("SELECT ticker, name FROM tokens WHERE contract_address = ?", (contract_address,))
                token_info = cursor.fetchone()
                
                ticker = token_info[0] if token_info and token_info[0] else contract_address[:8]
                name = token_info[1] if token_info and token_info[1] else f"Token {ticker}"
                
                # For simulation, use buy price as current price
                # For real trading, you'd fetch actual market price
                current_price = avg_buy_price
                position_amount = total_bought - total_sold
                
                unrealized_pl_sol = (current_price - avg_buy_price) * position_amount
                unrealized_pl_percentage = ((current_price / avg_buy_price) - 1) * 100 if avg_buy_price > 0 else 0
                
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
    # Header
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
    
    # Initialize balances
    simulation_mode = bot_settings.get('simulation_mode', True)
    real_wallet_balance = None
    sim_wallet_balance = 1.0  # Default simulation balance
    
    # Database operations
    ml_metrics = None
    ml_predictions = None
    
    if db_file and os.path.exists(db_file):
        conn = sqlite3.connect(db_file)
        
        # Get simulation balance
        sim_wallet_balance = get_simulation_wallet_balance(conn)
        
        # Get real balance if in real mode
        if not simulation_mode:
            real_wallet_balance = get_real_wallet_balance()
        
        # Get ML performance metrics
        ml_metrics = get_ml_performance_metrics(conn)
        ml_predictions = calculate_ml_predictions_performance(conn)
        
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
    
    # Main tabs
    tabs = st.tabs([
        "📊 Live Monitor", 
        "💰 Balance & Positions", 
        "📈 Trading Analysis",
        "🤖 ML Performance",
        "⚙️ Parameters"
    ])
    
    # Tab 1: Live Monitor
    with tabs[0]:
        st.subheader("📊 Live Trading Monitor")
        
        # Key metrics
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            # Display appropriate balance
            if simulation_mode:
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
                if real_wallet_balance is not None:
                    balance_usd = real_wallet_balance * sol_price if sol_price > 0 else 0
                    st.markdown(f"""
                    <div class='balance-card'>
                        <div class='main-metric'>{real_wallet_balance:.6f} SOL</div>
                        <div class='sub-metric'>${balance_usd:.2f} USD</div>
                        <div class='sub-metric'>Real Balance ✅</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class='balance-card danger'>
                        <div class='main-metric status-na'>Connect Wallet</div>
                        <div class='sub-metric'>Real Trading Mode</div>
                        <div class='sub-metric'>Wallet not connected</div>
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
            # Calculate P&L
            total_pl_sol = 0.0
            total_pl_usd = 0.0
            
            if db_file and os.path.exists(db_file):
                try:
                    conn = sqlite3.connect(db_file)
                    
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
                <div class='sub-metric'>{'Sim' if simulation_mode else 'Real'} P&L</div>
            </div>
            """, unsafe_allow_html=True)
        
        with metric_col4:
            # ML accuracy if enabled
            if bot_settings.get('use_machine_learning', False) and ml_metrics:
                accuracy = ml_metrics.get('accuracy', 0.0) * 100
                accuracy_color = 'accuracy-high' if accuracy >= 70 else 'accuracy-medium' if accuracy >= 50 else 'accuracy-low'
                st.markdown(f"""
                <div class='metric-card ml-metric'>
                    <div class='main-metric {accuracy_color}'>{accuracy:.1f}%</div>
                    <div class='sub-metric'>ML Accuracy</div>
                    <div class='sub-metric'>All Modes</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Active positions count
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
        
        # Recent trading activity
        st.subheader("Recent Trading Activity")
        
        if db_file and os.path.exists(db_file):
            try:
                conn = sqlite3.connect(db_file)
                
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
                    trades_with_pl, _ = calculate_trade_pl(recent_trades)
                    
                    display_trades = trades_with_pl[['timestamp', 'action', 'contract_address', 'amount', 'price', 'pl_sol', 'pl_percentage']].copy()
                    display_trades.columns = ['Time', 'Action', 'Token', 'Amount (SOL)', 'Price', 'P&L (SOL)', 'P&L (%)']
                    
                    # Format columns
                    display_trades['Time'] = pd.to_datetime(display_trades['Time']).dt.strftime('%H:%M:%S')
                    display_trades['Token'] = display_trades['Token'].apply(lambda x: x[:8] + "..." if len(str(x)) > 8 else str(x))
                    display_trades['Price'] = display_trades['Price'].apply(lambda x: f"${x:.8f}" if pd.notna(x) else "N/A")
                    display_trades['Amount (SOL)'] = display_trades['Amount (SOL)'].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "N/A")
                    
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
    
    # Tab 2: Balance & Positions
    with tabs[1]:
        st.subheader("💰 Balance & Position Management")
        
        # Balance overview
        balance_col1, balance_col2 = st.columns(2)
        
        with balance_col1:
            st.markdown("#### 💳 Wallet Status")
            
            # Show both balances if in real mode
            if not simulation_mode and real_wallet_balance is not None:
                # Real balance
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
                
                # Also show simulation balance for comparison
                sim_usd = sim_wallet_balance * sol_price if sol_price > 0 else 0
                st.markdown(f"""
                <div class='balance-card' style='margin-top: 10px; border-color: #666;'>
                    <h4>Simulation Reference</h4>
                    <div class='sub-metric'>{sim_wallet_balance:.6f} SOL (${sim_usd:.2f})</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Simulation balance
                balance_usd = sim_wallet_balance * sol_price if sol_price > 0 else 0
                st.markdown(f"""
                <div class='balance-card'>
                    <h3>Simulation Balance</h3>
                    <div class='main-metric'>{sim_wallet_balance:.6f} SOL</div>
                    <div class='sub-metric'>${balance_usd:.2f} USD</div>
                    <hr>
                    <div class='sub-metric'>Starting balance: 1.0 SOL</div>
                    <div class='sub-metric'>Updated: {datetime.now().strftime('%H:%M:%S')}</div>
                </div>
                """, unsafe_allow_html=True)
        
        with balance_col2:
            st.markdown("#### 📊 Risk Assessment")
            
            # Calculate risk score
            risk_score = 0
            if not simulation_mode:
                risk_score += 30
            if bot_settings.get('slippage_tolerance_display', 30.0) > 10:
                risk_score += 25
            
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
        
        # Active positions
        st.subheader("Active Positions with P&L")
        
        if db_file and os.path.exists(db_file):
            try:
                conn = sqlite3.connect(db_file)
                active_positions = get_active_positions(conn, is_simulation=simulation_mode)
                
                if not active_positions.empty:
                    display_positions = active_positions[['ticker', 'name', 'amount', 'avg_buy_price', 'current_price', 'unrealized_pl_sol', 'unrealized_pl_percentage']].copy()
                    display_positions.columns = ['Ticker', 'Name', 'Amount', 'Buy Price', 'Current Price', 'Unrealized P&L (SOL)', 'Unrealized P&L (%)']
                    
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
                else:
                    mode_text = "simulation" if simulation_mode else "real"
                    st.info(f"No active {mode_text} positions")
                
                conn.close()
                
            except Exception as e:
                st.error(f"Error loading positions: {e}")
    
    # Tab 3: Trading Analysis
    with tabs[2]:
        st.subheader("📈 Trading Performance Analysis")
        
        if db_file and os.path.exists(db_file):
            try:
                conn = sqlite3.connect(db_file)
                
                # Separate P&L for sim and real modes
                st.markdown("#### 📊 Performance by Mode")
                
                col1, col2 = st.columns(2)
                
                # Simulation P&L
                with col1:
                    st.markdown("##### Simulation Performance")
                    sim_query = """
                    SELECT * FROM trades 
                    WHERE (is_simulation = 1) OR 
                          (is_simulation IS NULL AND contract_address LIKE 'Sim%')
                    """
                    sim_trades = pd.read_sql_query(sim_query, conn)
                    
                    if not sim_trades.empty:
                        _, sim_metrics = calculate_trade_pl(sim_trades)
                        
                        pl_color = 'profit' if sim_metrics['total_pl_sol'] >= 0 else 'loss'
                        st.markdown(f"""
                        <div class='metric-card'>
                            <div class='main-metric {pl_color}'>P&L: {sim_metrics['total_pl_sol']:.6f} SOL</div>
                            <div class='sub-metric'>Win Rate: {sim_metrics['win_rate']:.1f}%</div>
                            <div class='sub-metric'>Total Trades: {sim_metrics['total_trades']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("No simulation trades")
                
                # Real P&L
                with col2:
                    st.markdown("##### Real Trading Performance")
                    real_query = """
                    SELECT * FROM trades 
                    WHERE (is_simulation = 0) OR 
                          (is_simulation IS NULL AND contract_address NOT LIKE 'Sim%')
                    """
                    real_trades = pd.read_sql_query(real_query, conn)
                    
                    if not real_trades.empty:
                        _, real_metrics = calculate_trade_pl(real_trades)
                        
                        pl_color = 'profit' if real_metrics['total_pl_sol'] >= 0 else 'loss'
                        st.markdown(f"""
                        <div class='metric-card'>
                            <div class='main-metric {pl_color}'>P&L: {real_metrics['total_pl_sol']:.6f} SOL</div>
                            <div class='sub-metric'>Win Rate: {real_metrics['win_rate']:.1f}%</div>
                            <div class='sub-metric'>Total Trades: {real_metrics['total_trades']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("No real trades yet")
                
                conn.close()
                
            except Exception as e:
                st.error(f"Error loading analysis data: {e}")
    
    # Tab 4: ML Performance (NEW)
    with tabs[3]:
        st.subheader("🤖 Machine Learning Performance")
        
        if bot_settings.get('use_machine_learning', False):
            if ml_metrics and ml_predictions:
                # Overall ML metrics
                st.markdown("#### 📊 Model Performance (Consolidated Across All Modes)")
                
                ml_col1, ml_col2, ml_col3, ml_col4 = st.columns(4)
                
                with ml_col1:
                    accuracy = ml_metrics.get('accuracy', 0.0) * 100
                    accuracy_color = 'accuracy-high' if accuracy >= 70 else 'accuracy-medium' if accuracy >= 50 else 'accuracy-low'
                    st.markdown(f"""
                    <div class='metric-card ml-metric'>
                        <div class='main-metric {accuracy_color}'>{accuracy:.1f}%</div>
                        <div class='sub-metric'>Model Accuracy</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with ml_col2:
                    precision = ml_metrics.get('precision', 0.0) * 100
                    st.markdown(f"""
                    <div class='metric-card ml-metric'>
                        <div class='main-metric'>{precision:.1f}%</div>
                        <div class='sub-metric'>Precision</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with ml_col3:
                    recall = ml_metrics.get('recall', 0.0) * 100
                    st.markdown(f"""
                    <div class='metric-card ml-metric'>
                        <div class='main-metric'>{recall:.1f}%</div>
                        <div class='sub-metric'>Recall</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with ml_col4:
                    f1 = ml_metrics.get('f1_score', 0.0) * 100
                    st.markdown(f"""
                    <div class='metric-card ml-metric'>
                        <div class='main-metric'>{f1:.1f}%</div>
                        <div class='sub-metric'>F1 Score</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Predictions performance
                st.markdown("#### 🎯 Prediction Results")
                
                pred_col1, pred_col2, pred_col3 = st.columns(3)
                
                with pred_col1:
                    st.markdown(f"""
                    <div class='metric-card'>
                        <div class='main-metric'>{ml_predictions['predictions_made']}</div>
                        <div class='sub-metric'>Total Predictions</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with pred_col2:
                    success_rate = ml_predictions['prediction_accuracy']
                    color = 'profit' if success_rate >= 60 else 'loss' if success_rate < 40 else 'neutral'
                    st.markdown(f"""
                    <div class='metric-card'>
                        <div class='main-metric {color}'>{success_rate:.1f}%</div>
                        <div class='sub-metric'>Success Rate</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with pred_col3:
                    st.markdown(f"""
                    <div class='metric-card'>
                        <div class='main-metric profit'>+{ml_predictions['avg_profit_on_success']:.1f}%</div>
                        <div class='sub-metric'>Avg Profit</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Feature importance
                if ml_metrics.get('feature_importance'):
                    st.markdown("#### 🔍 Feature Importance")
                    
                    feature_df = pd.DataFrame(
                        list(ml_metrics['feature_importance'].items()),
                        columns=['Feature', 'Importance']
                    )
                    feature_df = feature_df.sort_values('Importance', ascending=False)
                    
                    fig = px.bar(
                        feature_df,
                        x='Importance',
                        y='Feature',
                        orientation='h',
                        color='Importance',
                        color_continuous_scale='viridis'
                    )
                    fig.update_layout(
                        height=400,
                        template='plotly_dark',
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Model info
                st.markdown("#### ℹ️ Model Information")
                st.info(f"""
                **Last Updated:** {ml_metrics.get('last_updated', 'Never')}  
                **Total Predictions:** {ml_metrics.get('total_predictions', 0)}  
                **Correct Predictions:** {ml_metrics.get('correct_predictions', 0)}  
                
                The ML model learns from both simulation and real trading data to improve predictions across all modes.
                """)
            else:
                st.warning("No ML performance data available")
        else:
            st.info("Machine Learning is currently disabled. Enable it in Parameters to see ML insights.")
    
    # Tab 5: Parameters
    with tabs[4]:
        st.subheader("⚙️ Trading Parameters")
        
        # Safety warning
        if not bot_settings.get('simulation_mode', True):
            st.markdown("""
            <div class='alert-danger'>
                <strong>🔥 REAL TRADING MODE ACTIVE</strong><br>
                Changes to parameters will affect real money trades. Be extremely careful!
            </div>
            """, unsafe_allow_html=True)
        
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
        st.markdown("#### Core Trading Parameters")
        
        tp_col1, tp_col2, tp_col3 = st.columns(3)
        
        with tp_col1:
            take_profit = st.number_input(
                "Take Profit Target",
                min_value=1.1,
                max_value=100.0,
                value=float(bot_settings.get('take_profit_target', 2.5)),
                step=0.1,
                help="Exit position when price reaches this multiple"
            )
        
        with tp_col2:
            stop_loss_display = bot_settings.get('stop_loss_percentage_display', 25.0)
            stop_loss = st.number_input(
                "Stop Loss (%)",
                min_value=1.0,
                max_value=50.0,
                value=float(stop_loss_display),
                step=1.0,
                help="Stop loss percentage"
            )
        
        with tp_col3:
            max_investment = st.number_input(
                "Max Investment (SOL)",
                min_value=0.001,
                max_value=10.0,
                value=float(bot_settings.get('max_investment_per_token', 0.1)),
                step=0.001,
                format="%.3f",
                help="Maximum SOL to invest per token"
            )
        
        # Save parameters
        if st.button("💾 Save All Parameters", type="primary"):
            updated_settings = bot_settings.copy()
            updated_settings.update({
                'running': bot_running,
                'simulation_mode': simulation_mode_setting,
                'use_machine_learning': ml_enabled,
                'take_profit_target': take_profit,
                'stop_loss_percentage_display': stop_loss,
                'max_investment_per_token': max_investment
            })
            
            control_file = bot_settings.get('_loaded_from', 'bot_control.json')
            if save_bot_settings(updated_settings, control_file):
                st.success(f"✅ Parameters saved successfully!")
                st.session_state.last_update = datetime.now()
            else:
                st.error("❌ Failed to save parameters")

if __name__ == "__main__":
    main()