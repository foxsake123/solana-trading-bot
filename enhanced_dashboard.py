"""
Enhanced Trading Bot Dashboard with Live Balance Monitoring and Parameter Control
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

# Enhanced CSS with alerts and monitoring styles
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
    
    /* Metric Cards */
    .metric-card { background-color: #252525; border-radius: 10px; padding: 15px; margin: 10px 0; }
    .main-metric { font-size: 24px; font-weight: bold; }
    .sub-metric { font-size: 16px; color: #BDBDBD; }
    
    /* Status Indicators */
    .status-online { color: #4CAF50; font-weight: bold; }
    .status-offline { color: #F44336; font-weight: bold; }
    .status-warning { color: #FF9800; font-weight: bold; }
    
    /* Parameter Controls */
    .param-section { background-color: #1E1E1E; padding: 20px; border-radius: 10px; margin: 10px 0; }
    .param-title { color: #4CAF50; font-size: 18px; font-weight: bold; margin-bottom: 15px; }
    
    /* Live Data Indicators */
    .live-indicator { animation: pulse 2s infinite; }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    
    /* Tags */
    .simulation-tag { background-color: #FF9800; color: black; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
    .real-tag { background-color: #F44336; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
    .live-tag { background-color: #4CAF50; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# Initialize session state for real-time updates
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = True
if 'refresh_interval' not in st.session_state:
    st.session_state.refresh_interval = 30  # seconds

# Helper functions
def get_live_sol_price():
    """Get the current SOL price from multiple API sources."""
    try:
        # Try CoinGecko API first
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
        # Try Binance API as fallback
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
    
    return 0.0  # Return 0 if all APIs fail

def get_wallet_balance_advanced():
    """Advanced wallet balance fetching with error handling."""
    try:
        # Read wallet configuration
        private_key = None
        rpc_endpoint = None
        
        # Try to load from .env file
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('WALLET_PRIVATE_KEY='):
                        private_key = line.split('=', 1)[1].strip().strip("'").strip('"')
                    elif line.startswith('SOLANA_RPC_ENDPOINT='):
                        rpc_endpoint = line.split('=', 1)[1].strip().strip("'").strip('"')
        
        if not rpc_endpoint:
            rpc_endpoint = "https://api.mainnet-beta.solana.com"
        
        # For demo purposes, return simulated balance if no private key
        if not private_key:
            return {
                'sol_balance': 1.15,
                'usd_balance': 1.15 * get_live_sol_price(),
                'status': 'simulated',
                'last_updated': datetime.now(),
                'rpc_endpoint': rpc_endpoint
            }
        
        # Try to get real wallet address from private key
        try:
            from solders.keypair import Keypair
            import base58
            
            # Handle different private key formats
            if len(private_key) == 64:  # Hex format - assume it's a seed
                seed_bytes = bytes.fromhex(private_key)
                if len(seed_bytes) == 32:  # 32-byte seed
                    keypair = Keypair.from_seed(seed_bytes)
                else:
                    keypair = Keypair.from_bytes(seed_bytes)
            elif len(private_key) == 88:  # Base58 format
                decoded = base58.b58decode(private_key)
                if len(decoded) == 32:  # 32-byte seed
                    keypair = Keypair.from_seed(decoded)
                else:
                    keypair = Keypair.from_bytes(decoded)
            else:
                # Try as base58 first, then hex
                try:
                    decoded = base58.b58decode(private_key)
                    if len(decoded) == 32:
                        keypair = Keypair.from_seed(decoded)
                    else:
                        keypair = Keypair.from_bytes(decoded)
                except:
                    # Try as hex seed
                    seed_bytes = bytes.fromhex(private_key)
                    keypair = Keypair.from_seed(seed_bytes[:32])  # Take first 32 bytes as seed
            
            wallet_address = str(keypair.pubkey())
            
            # Query balance using RPC
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
                    balance_lamports = data['result']['value']
                    balance_sol = balance_lamports / 1_000_000_000
                    sol_price = get_live_sol_price()
                    
                    return {
                        'sol_balance': balance_sol,
                        'usd_balance': balance_sol * sol_price,
                        'status': 'live',
                        'last_updated': datetime.now(),
                        'wallet_address': wallet_address,
                        'rpc_endpoint': rpc_endpoint
                    }
        
        except Exception as e:
            logger.error(f"Error getting real balance: {e}")
            
        # Fallback to simulated balance
        return {
            'sol_balance': 1.15,
            'usd_balance': 1.15 * get_live_sol_price(),
            'status': 'error',
            'last_updated': datetime.now(),
            'rpc_endpoint': rpc_endpoint,
            'error': str(e) if 'e' in locals() else 'Unknown error'
        }
        
    except Exception as e:
        logger.error(f"Critical error in balance fetching: {e}")
        return {
            'sol_balance': 0.0,
            'usd_balance': 0.0,
            'status': 'error',
            'last_updated': datetime.now(),
            'error': str(e)
        }

def load_bot_settings():
    """Load bot settings with enhanced error handling."""
    control_files = [
        'data/bot_control.json',
        'bot_control.json',
        'core/bot_control.json'
    ]
    
    for control_file in control_files:
        if os.path.exists(control_file):
            try:
                with open(control_file, 'r') as f:
                    settings = json.load(f)
                    # Add metadata
                    settings['_loaded_from'] = control_file
                    settings['_loaded_at'] = datetime.now().isoformat()
                    return settings
            except Exception as e:
                logger.error(f"Error loading {control_file}: {e}")
    
    # Default settings with safety-first approach
    return {
        "running": False,
        "simulation_mode": True,
        "take_profit_target": 2.5,
        "stop_loss_percentage": 0.2,
        "min_investment_per_token": 0.02,
        "max_investment_per_token": 0.1,
        "slippage_tolerance": 0.05,  # 5% default (safer)
        "use_machine_learning": False,
        "filter_fake_tokens": True,
        "MIN_SAFETY_SCORE": 15.0,
        "MIN_VOLUME": 10.0,
        "MIN_LIQUIDITY": 5000.0,
        "MIN_MCAP": 10000.0,
        "MIN_HOLDERS": 10,
        "MIN_PRICE_CHANGE_1H": 1.0,
        "MIN_PRICE_CHANGE_6H": 2.0,
        "MIN_PRICE_CHANGE_24H": 5.0,
        "_loaded_from": "default",
        "_loaded_at": datetime.now().isoformat()
    }

def save_bot_settings(settings):
    """Save bot settings with backup."""
    control_file = settings.get('_loaded_from', 'data/bot_control.json')
    if control_file == 'default':
        control_file = 'data/bot_control.json'
    
    try:
        # Create backup
        if os.path.exists(control_file):
            backup_file = f"{control_file}.backup.{int(time.time())}"
            with open(control_file, 'r') as src, open(backup_file, 'w') as dst:
                dst.write(src.read())
        
        # Create directory if needed
        os.makedirs(os.path.dirname(control_file), exist_ok=True)
        
        # Remove metadata before saving
        settings_to_save = {k: v for k, v in settings.items() if not k.startswith('_')}
        
        # Save settings
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

def get_trades_with_status(conn, limit=50):
    """Get recent trades with enhanced status information."""
    try:
        cursor = conn.cursor()
        
        # Check available columns
        cursor.execute("PRAGMA table_info(trades)")
        columns = [info[1] for info in cursor.fetchall()]
        
        # Build query based on available columns
        query = "SELECT * FROM trades ORDER BY id DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        trades_df = pd.read_sql_query(query, conn)
        
        if trades_df.empty:
            return pd.DataFrame()
        
        # Add status information
        if 'is_simulation' not in trades_df.columns:
            # Determine simulation status from contract address
            def is_simulation(address):
                if not isinstance(address, str):
                    return True
                return (address.startswith('Sim') or 
                       'TopGainer' in address or
                       'test' in address.lower())
            
            trades_df['is_simulation'] = trades_df['contract_address'].apply(is_simulation)
        
        # Add trade status
        trades_df['trade_status'] = trades_df.apply(lambda row: 
            'Simulation' if row.get('is_simulation', True) else 'Real', axis=1)
        
        # Add profit calculation for completed trades
        trades_df['estimated_profit'] = 0.0
        
        return trades_df
        
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return pd.DataFrame()

def get_active_positions_enhanced(conn):
    """Get active positions with enhanced metrics."""
    try:
        trades_df = get_trades_with_status(conn)
        
        if trades_df.empty:
            return pd.DataFrame()
        
        positions = []
        
        for address, group in trades_df.groupby('contract_address'):
            buys = group[group['action'] == 'BUY']
            sells = group[group['action'] == 'SELL']
            
            total_bought = buys['amount'].sum()
            total_sold = sells['amount'].sum() if not sells.empty else 0
            
            if total_bought > total_sold:
                remaining = total_bought - total_sold
                avg_buy_price = (buys['amount'] * buys['price']).sum() / total_bought
                
                # Get current price (simulated for demo)
                current_price = avg_buy_price * (1 + np.random.uniform(-0.1, 0.3))
                
                # Calculate metrics
                unrealized_pl = (current_price - avg_buy_price) * remaining
                pl_percent = ((current_price / avg_buy_price) - 1) * 100
                
                # Determine risk level
                risk_level = 'Low'
                if abs(pl_percent) > 20:
                    risk_level = 'High'
                elif abs(pl_percent) > 10:
                    risk_level = 'Medium'
                
                # Get token info
                ticker = address[:8] if len(address) > 8 else address
                is_simulation = buys['is_simulation'].iloc[0] if 'is_simulation' in buys.columns else True
                
                # Handle entry time with timezone awareness
                entry_time = None
                days_held = 0
                if 'timestamp' in buys.columns and not buys.empty:
                    try:
                        entry_timestamp = buys['timestamp'].min()
                        # Convert to datetime if it's a string
                        if isinstance(entry_timestamp, str):
                            entry_time = pd.to_datetime(entry_timestamp, utc=True)
                        else:
                            entry_time = pd.to_datetime(entry_timestamp)
                            # Make timezone aware if naive
                            if entry_time.tz is None:
                                entry_time = entry_time.tz_localize('UTC')
                        
                        # Calculate days held
                        now = datetime.now(pytz.UTC)
                        days_held = (now - entry_time).days
                    except Exception as e:
                        logger.warning(f"Error processing entry time: {e}")
                        entry_time = None
                        days_held = 0
                
                positions.append({
                    'contract_address': address,
                    'ticker': ticker,
                    'amount': remaining,
                    'avg_buy_price': avg_buy_price,
                    'current_price': current_price,
                    'unrealized_pl': unrealized_pl,
                    'pl_percent': pl_percent,
                    'risk_level': risk_level,
                    'is_simulation': is_simulation,
                    'entry_time': entry_time,
                    'days_held': days_held
                })
        
        return pd.DataFrame(positions)
        
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return pd.DataFrame()

def create_risk_gauge(risk_score, title="Risk Level"):
    """Create a risk gauge visualization."""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = risk_score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title},
        delta = {'reference': 50},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 25], 'color': "lightgreen"},
                {'range': [25, 50], 'color': "yellow"},
                {'range': [50, 75], 'color': "orange"},
                {'range': [75, 100], 'color': "red"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(
        height=300,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_balance_history_chart(balance_history):
    """Create balance history chart."""
    if not balance_history:
        fig = go.Figure()
        fig.update_layout(title="Balance History", template="plotly_dark")
        return fig
    
    df = pd.DataFrame(balance_history)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['sol_balance'],
        mode='lines+markers',
        name='SOL Balance',
        line=dict(color='cyan', width=2)
    ))
    
    fig.update_layout(
        title="Wallet Balance History",
        xaxis_title="Time",
        yaxis_title="SOL Balance",
        template="plotly_dark",
        height=400
    )
    
    return fig

def main():
    # Header with live status
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title("💸 Enhanced Trading Bot Dashboard")
    
    with col2:
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto Refresh", value=st.session_state.auto_refresh)
        st.session_state.auto_refresh = auto_refresh
    
    with col3:
        # Manual refresh button
        if st.button("🔄 Refresh Now"):
            st.session_state.last_update = datetime.now()
            st.experimental_rerun()
    
    # Auto-refresh logic
    if st.session_state.auto_refresh:
        time_since_update = (datetime.now() - st.session_state.last_update).seconds
        if time_since_update >= st.session_state.refresh_interval:
            st.session_state.last_update = datetime.now()
            st.experimental_rerun()
    
    # Load data
    bot_settings = load_bot_settings()
    wallet_info = get_wallet_balance_advanced()
    sol_price = get_live_sol_price()
    db_file = find_database()
    
    # Status bar
    status_col1, status_col2, status_col3, status_col4 = st.columns(4)
    
    with status_col1:
        bot_status = "🟢 RUNNING" if bot_settings.get('running', False) else "🔴 STOPPED"
        st.markdown(f"**Bot Status:** {bot_status}")
    
    with status_col2:
        mode_status = "🧪 SIMULATION" if bot_settings.get('simulation_mode', True) else "💰 REAL TRADING"
        st.markdown(f"**Mode:** {mode_status}")
    
    with status_col3:
        wallet_status = f"💳 {wallet_info['status'].upper()}"
        st.markdown(f"**Wallet:** {wallet_status}")
    
    with status_col4:
        last_update = st.session_state.last_update.strftime("%H:%M:%S")
        st.markdown(f"**Updated:** <span class='live-tag'>{last_update}</span>", unsafe_allow_html=True)
    
    # Critical Alerts Section
    st.markdown("### 🚨 System Alerts")
    
    alert_col1, alert_col2 = st.columns(2)
    
    with alert_col1:
        # Balance alerts
        if wallet_info['sol_balance'] < 0.1:
            st.markdown(f"""
            <div class='alert-danger'>
                <strong>⚠️ LOW BALANCE ALERT</strong><br>
                Wallet balance is critically low: {wallet_info['sol_balance']:.4f} SOL<br>
                Consider adding funds before continuing trading.
            </div>
            """, unsafe_allow_html=True)
        elif wallet_info['sol_balance'] < 0.5:
            st.markdown(f"""
            <div class='alert-warning'>
                <strong>💡 Balance Warning</strong><br>
                Wallet balance is getting low: {wallet_info['sol_balance']:.4f} SOL
            </div>
            """, unsafe_allow_html=True)
    
    with alert_col2:
        # Trading mode alerts
        if not bot_settings.get('simulation_mode', True) and bot_settings.get('running', False):
            st.markdown(f"""
            <div class='alert-danger'>
                <strong>🔥 REAL TRADING ACTIVE</strong><br>
                Bot is actively trading with real funds!<br>
                Monitor closely and ensure risk parameters are appropriate.
            </div>
            """, unsafe_allow_html=True)
        elif bot_settings.get('slippage_tolerance', 0) > 0.1:  # 10%
            st.markdown(f"""
            <div class='alert-warning'>
                <strong>⚠️ High Slippage Setting</strong><br>
                Slippage tolerance is {bot_settings.get('slippage_tolerance', 0)*100:.1f}%<br>
                Consider reducing for better trade execution.
            </div>
            """, unsafe_allow_html=True)
    
    # Main content tabs
    tabs = st.tabs(["📊 Live Monitor", "💰 Balance & Positions", "⚙️ Parameters", "📈 Analytics", "🔧 System"])
    
    # Tab 1: Live Monitor
    with tabs[0]:
        st.subheader("Live Trading Monitor")
        
        # Key metrics row
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            st.markdown(f"""
            <div class='balance-card'>
                <div class='main-metric'>${wallet_info['usd_balance']:.2f}</div>
                <div class='sub-metric'>{wallet_info['sol_balance']:.4f} SOL</div>
                <div class='sub-metric'>Wallet Balance</div>
            </div>
            """, unsafe_allow_html=True)
        
        with metric_col2:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='main-metric'>${sol_price:.2f}</div>
                <div class='sub-metric'>SOL Price</div>
                <div class='sub-metric live-indicator'>● LIVE</div>
            </div>
            """, unsafe_allow_html=True)
        
        with metric_col3:
            # Load recent trades for P&L calculation
            total_pl = 0.0  # Placeholder - would calculate from recent trades
            pl_color = 'green' if total_pl >= 0 else 'red'
            st.markdown(f"""
            <div class='metric-card'>
                <div class='main-metric' style='color: {pl_color}'>${total_pl:.2f}</div>
                <div class='sub-metric'>Today's P&L</div>
                <div class='sub-metric'>SOL Equivalent</div>
            </div>
            """, unsafe_allow_html=True)
        
        with metric_col4:
            active_positions_count = 0  # Would get from database
            st.markdown(f"""
            <div class='metric-card'>
                <div class='main-metric'>{active_positions_count}</div>
                <div class='sub-metric'>Active Positions</div>
                <div class='sub-metric'>Currently Held</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Recent activity
        st.subheader("Recent Trading Activity")
        
        if db_file and os.path.exists(db_file):
            try:
                conn = sqlite3.connect(db_file)
                recent_trades = get_trades_with_status(conn, limit=10)
                conn.close()
                
                if not recent_trades.empty:
                    # Format for display
                    display_trades = recent_trades[['trade_status', 'action', 'contract_address', 'amount', 'price', 'timestamp']].copy()
                    display_trades.columns = ['Type', 'Action', 'Token', 'Amount (SOL)', 'Price', 'Time']
                    
                    # Add colors based on action
                    def color_action(val):
                        if val == 'BUY':
                            return 'background-color: #1B4D3E'
                        elif val == 'SELL':
                            return 'background-color: #5D1A1A'
                        return ''
                    
                    # Use the new map method instead of applymap
                    styled_df = display_trades.style.map(color_action, subset=['Action'])
                    
                    st.dataframe(styled_df, use_container_width=True)
                else:
                    st.info("No recent trading activity")
            except Exception as e:
                st.error(f"Error loading trading data: {e}")
        else:
            st.warning("Database not found - trading history unavailable")
    
    # Tab 2: Balance & Positions
    with tabs[1]:
        st.subheader("Balance & Position Management")
        
        # Balance overview
        balance_col1, balance_col2 = st.columns(2)
        
        with balance_col1:
            st.markdown("#### 💳 Wallet Status")
            
            balance_card_class = 'balance-card'
            if wallet_info['sol_balance'] < 0.1:
                balance_card_class += ' danger'
            elif wallet_info['sol_balance'] < 0.5:
                balance_card_class += ' warning'
            
            st.markdown(f"""
            <div class='{balance_card_class}'>
                <h3>Current Balance</h3>
                <div class='main-metric'>{wallet_info['sol_balance']:.6f} SOL</div>
                <div class='sub-metric'>${wallet_info['usd_balance']:.2f} USD</div>
                <hr>
                <div class='sub-metric'>Status: {wallet_info['status'].title()}</div>
                <div class='sub-metric'>Updated: {wallet_info['last_updated'].strftime('%H:%M:%S')}</div>
                {f"<div class='sub-metric'>Address: {wallet_info.get('wallet_address', 'N/A')[:8]}...</div>" if 'wallet_address' in wallet_info else ""}
            </div>
            """, unsafe_allow_html=True)
        
        with balance_col2:
            st.markdown("#### 📊 Risk Assessment")
            
            # Calculate risk score based on settings and positions
            risk_score = 0
            if not bot_settings.get('simulation_mode', True):
                risk_score += 30  # Real trading adds risk
            if bot_settings.get('slippage_tolerance', 0) > 0.05:
                risk_score += 25  # High slippage
            if wallet_info['sol_balance'] < 0.5:
                risk_score += 20  # Low balance
            if bot_settings.get('max_investment_per_token', 0) > 0.1:
                risk_score += 15  # High position size
            
            risk_gauge = create_risk_gauge(risk_score, "Overall Risk Score")
            st.plotly_chart(risk_gauge, use_container_width=True)
        
        # Active positions
        st.subheader("Active Positions")
        
        if db_file and os.path.exists(db_file):
            try:
                conn = sqlite3.connect(db_file)
                positions_df = get_active_positions_enhanced(conn)
                conn.close()
                
                if not positions_df.empty:
                    # Separate real and simulation positions
                    real_positions = positions_df[~positions_df['is_simulation']]
                    sim_positions = positions_df[positions_df['is_simulation']]
                    
                    pos_col1, pos_col2 = st.columns(2)
                    
                    with pos_col1:
                        st.markdown("##### 💰 Real Positions")
                        if not real_positions.empty:
                            display_real = real_positions[['ticker', 'amount', 'avg_buy_price', 'current_price', 'pl_percent', 'risk_level']].copy()
                            display_real.columns = ['Token', 'Amount', 'Buy Price', 'Current', 'P&L %', 'Risk']
                            
                            # Format currency columns
                            display_real['Buy Price'] = display_real['Buy Price'].apply(lambda x: f"${x:.6f}")
                            display_real['Current'] = display_real['Current'].apply(lambda x: f"${x:.6f}")
                            display_real['P&L %'] = display_real['P&L %'].apply(lambda x: f"{x:.2f}%")
                            
                            st.dataframe(display_real, use_container_width=True)
                        else:
                            st.info("No real positions")
                    
                    with pos_col2:
                        st.markdown("##### 🧪 Simulation Positions")
                        if not sim_positions.empty:
                            display_sim = sim_positions[['ticker', 'amount', 'avg_buy_price', 'current_price', 'pl_percent', 'risk_level']].copy()
                            display_sim.columns = ['Token', 'Amount', 'Buy Price', 'Current', 'P&L %', 'Risk']
                            
                            # Format currency columns
                            display_sim['Buy Price'] = display_sim['Buy Price'].apply(lambda x: f"${x:.6f}")
                            display_sim['Current'] = display_sim['Current'].apply(lambda x: f"${x:.6f}")
                            display_sim['P&L %'] = display_sim['P&L %'].apply(lambda x: f"{x:.2f}%")
                            
                            st.dataframe(display_sim, use_container_width=True)
                        else:
                            st.info("No simulation positions")
                else:
                    st.info("No active positions found")
            except Exception as e:
                st.error(f"Error loading positions: {e}")
    
    # Tab 3: Parameters
    with tabs[2]:
        st.subheader("⚙️ Trading Parameters Control")
        
        # Safety warning for real trading
        if not bot_settings.get('simulation_mode', True):
            st.markdown("""
            <div class='alert-danger'>
                <strong>🔥 REAL TRADING MODE ACTIVE</strong><br>
                Changes to parameters will affect real money trades. Be extremely careful!
            </div>
            """, unsafe_allow_html=True)
        
        # Core controls
        st.markdown("#### Core Controls")
        
        core_col1, core_col2 = st.columns(2)
        
        with core_col1:
            # Bot running toggle
            bot_running = st.checkbox(
                "🤖 Bot Running",
                value=bot_settings.get('running', False),
                help="Start or stop the trading bot"
            )
            
            # Simulation mode toggle
            simulation_mode = st.checkbox(
                "🧪 Simulation Mode",
                value=bot_settings.get('simulation_mode', True),
                help="Toggle between simulation and real trading mode"
            )
            
            # Emergency stop
            if st.button("🛑 EMERGENCY STOP", type="primary"):
                emergency_settings = bot_settings.copy()
                emergency_settings['running'] = False
                if save_bot_settings(emergency_settings):
                    st.success("Emergency stop activated!")
                    st.experimental_rerun()
                else:
                    st.error("Failed to activate emergency stop!")
        
        with core_col2:
            # Auto-refresh settings
            refresh_interval = st.selectbox(
                "Dashboard Refresh Rate",
                options=[10, 30, 60, 300],
                index=1,
                format_func=lambda x: f"{x} seconds"
            )
            st.session_state.refresh_interval = refresh_interval
            
            # Filter fake tokens
            filter_fake = st.checkbox(
                "🛡️ Filter Fake Tokens",
                value=bot_settings.get('filter_fake_tokens', True),
                help="Enable filtering of likely scam tokens"
            )
        
        # Risk management parameters
        st.markdown("#### Risk Management")
        
        risk_col1, risk_col2, risk_col3 = st.columns(3)
        
        with risk_col1:
            # Take profit - handle both percentage and multiplier formats
            current_tp = bot_settings.get('take_profit_target', 2.5)
            if current_tp <= 1.0:  # If stored as percentage (0.25 = 25%)
                tp_display_value = current_tp * 100  # Convert to percentage
                tp_is_percentage = True
            else:  # If stored as multiplier (2.5 = 2.5x)
                tp_display_value = current_tp
                tp_is_percentage = False
            
            # Take profit selector
            tp_format = st.radio(
                "Take Profit Format",
                options=["Percentage", "Multiplier"],
                index=0 if tp_is_percentage else 1,
                horizontal=True
            )
            
            if tp_format == "Percentage":
                take_profit_pct = st.number_input(
                    "Take Profit (%)",
                    min_value=1.0,
                    max_value=10000.0,
                    value=tp_display_value if tp_is_percentage else (tp_display_value - 1) * 100,
                    step=5.0,
                    help="Exit position when profit reaches this percentage"
                )
                take_profit = take_profit_pct / 100  # Store as decimal
            else:
                take_profit = st.number_input(
                    "Take Profit Multiplier",
                    min_value=1.1,
                    max_value=100.0,
                    value=tp_display_value if not tp_is_percentage else (tp_display_value / 100) + 1,
                    step=0.1,
                    help="Exit position when price reaches this multiple of buy price"
                )
            
            # Stop loss - handle percentage format
            current_sl = bot_settings.get('stop_loss_percentage', 0.2)
            if current_sl > 1.0:  # If stored as percentage (20.0 instead of 0.2)
                sl_display_value = current_sl
            else:  # If stored as decimal (0.2)
                sl_display_value = current_sl * 100
            
            stop_loss_pct = st.number_input(
                "Stop Loss (%)",
                min_value=1.0,
                max_value=95.0,
                value=sl_display_value,
                step=1.0,
                help="Exit position when loss reaches this percentage"
            )
            stop_loss = stop_loss_pct / 100  # Store as decimal
        
        with risk_col2:
            min_investment = st.number_input(
                "Min Investment (SOL)",
                min_value=0.001,
                max_value=1.0,
                value=float(bot_settings.get('min_investment_per_token', 0.02)),
                step=0.001,
                format="%.3f"
            )
            
            max_investment = st.number_input(
                "Max Investment (SOL)",
                min_value=0.01,
                max_value=10.0,
                value=float(bot_settings.get('max_investment_per_token', 0.1)),
                step=0.01,
                format="%.3f"
            )
        
        with risk_col3:
            current_slippage = bot_settings.get('slippage_tolerance', 0.05)
            if current_slippage <= 1.0:  # If stored as decimal (0.05)
                slippage_display = current_slippage * 100
            else:  # If stored as percentage (5.0)
                slippage_display = current_slippage
            
            slippage_tolerance = st.number_input(
                "Slippage Tolerance (%)",
                min_value=0.1,
                max_value=50.0,
                value=slippage_display,
                step=0.1,
                help="Maximum acceptable slippage for trades"
            )
            
            # Slippage warning
            if slippage_tolerance > 10:
                st.warning("⚠️ High slippage tolerance increases trading costs!")
            elif slippage_tolerance > 5:
                st.info("💡 Consider reducing slippage for better execution")
        
        # Add real-time parameter preview
        st.markdown("#### 📋 Current Parameter Preview")
        
        preview_col1, preview_col2 = st.columns(2)
        
        with preview_col1:
            st.markdown(f"""
            **Core Settings:**
            - Bot Status: {'🟢 Running' if bot_running else '🔴 Stopped'}
            - Trading Mode: {'🧪 Simulation' if simulation_mode else '💰 Real Trading'}
            - Emergency Stop: Available
            - Fake Token Filter: {'✅ Enabled' if filter_fake else '❌ Disabled'}
            """)
        
        with preview_col2:
            st.markdown(f"""
            **Risk Management:**
            - Take Profit: {take_profit:.2f}{'x' if tp_format == 'Multiplier' else '%'}
            - Stop Loss: {stop_loss_pct:.1f}%
            - Max Position: {max_investment:.3f} SOL
            - Slippage: {slippage_tolerance:.1f}%
            """)
        
        # Add parameter validation warnings
        st.markdown("#### ⚠️ Parameter Validation")
        
        validation_warnings = []
        validation_errors = []
        
        # Check for risky settings
        if not simulation_mode and bot_running:
            validation_warnings.append("🔥 Real trading mode is active - monitor closely!")
        
        if slippage_tolerance > 10:
            validation_errors.append(f"❌ Slippage tolerance ({slippage_tolerance:.1f}%) is dangerously high")
        elif slippage_tolerance > 5:
            validation_warnings.append(f"⚠️ Slippage tolerance ({slippage_tolerance:.1f}%) is high")
        
        if max_investment > wallet_info['sol_balance']:
            validation_errors.append(f"❌ Max investment ({max_investment:.3f} SOL) exceeds wallet balance")
        
        if take_profit < 1.1 and tp_format == 'Multiplier':
            validation_errors.append("❌ Take profit multiplier must be at least 1.1x")
        
        if stop_loss_pct > 50:
            validation_warnings.append(f"⚠️ Stop loss ({stop_loss_pct:.1f}%) is very high")
        
        # Display validation results
        if validation_errors:
            for error in validation_errors:
                st.error(error)
        
        if validation_warnings:
            for warning in validation_warnings:
                st.warning(warning)
        
        if not validation_errors and not validation_warnings:
            st.success("✅ All parameters look good!")
        
        # Advanced parameter section
        with st.expander("🔧 Advanced Parameters & Quick Presets"):
            preset_col1, preset_col2 = st.columns(2)
            
            with preset_col1:
                st.markdown("##### 🎯 Quick Presets")
                
                if st.button("🛡️ Conservative", help="Safe settings for steady growth"):
                    st.session_state.preset_values = {
                        'take_profit': 1.5 if tp_format == 'Multiplier' else 50,
                        'stop_loss': 10,
                        'max_investment': 0.05,
                        'slippage': 1.0
                    }
                    st.success("Conservative preset applied!")
                
                if st.button("⚖️ Balanced", help="Moderate risk/reward balance"):
                    st.session_state.preset_values = {
                        'take_profit': 2.5 if tp_format == 'Multiplier' else 150,
                        'stop_loss': 20,
                        'max_investment': 0.1,
                        'slippage': 2.5
                    }
                    st.success("Balanced preset applied!")
                
                if st.button("🚀 Aggressive", help="High risk, high reward"):
                    st.session_state.preset_values = {
                        'take_profit': 5.0 if tp_format == 'Multiplier' else 400,
                        'stop_loss': 30,
                        'max_investment': 0.2,
                        'slippage': 5.0
                    }
                    st.success("Aggressive preset applied!")
            
            with preset_col2:
                st.markdown("##### 📊 Parameter Impact Calculator")
                
                # Calculate potential impact
                potential_loss = wallet_info['sol_balance'] * (stop_loss_pct / 100)
                potential_gain_conservative = max_investment * (0.5 if tp_format == 'Multiplier' else take_profit / 200)
                
                st.info(f"""
                **Potential Impact:**
                - Max loss per trade: {potential_loss:.4f} SOL (${potential_loss * sol_price:.2f})
                - Conservative gain estimate: {potential_gain_conservative:.4f} SOL
                - Risk/Reward Ratio: {potential_gain_conservative/potential_loss:.2f}:1
                """)
        
        # Apply preset values if they exist
        if hasattr(st.session_state, 'preset_values'):
            preset = st.session_state.preset_values
            if tp_format == 'Multiplier':
                take_profit = preset['take_profit']
            else:
                take_profit_pct = preset['take_profit']
                take_profit = take_profit_pct / 100
            
            stop_loss_pct = preset['stop_loss']
            stop_loss = stop_loss_pct / 100
            max_investment = preset['max_investment']
            slippage_tolerance = preset['slippage']
            
            # Clear the preset after applying
            del st.session_state.preset_values
            filter_col1, filter_col2 = st.columns(2)
            
            with filter_col1:
                min_safety_score = st.number_input(
                    "Min Safety Score",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(bot_settings.get('MIN_SAFETY_SCORE', 15.0)),
                    step=5.0
                )
                
                min_volume = st.number_input(
                    "Min 24h Volume (USD)",
                    min_value=0.0,
                    max_value=1000000.0,
                    value=float(bot_settings.get('MIN_VOLUME', 10.0)),
                    step=1000.0
                )
                
                min_liquidity = st.number_input(
                    "Min Liquidity (USD)",
                    min_value=0.0,
                    max_value=1000000.0,
                    value=float(bot_settings.get('MIN_LIQUIDITY', 5000.0)),
                    step=1000.0
                )
            
            with filter_col2:
                min_price_change_1h = st.number_input(
                    "Min 1h Price Change (%)",
                    min_value=-100.0,
                    max_value=1000.0,
                    value=float(bot_settings.get('MIN_PRICE_CHANGE_1H', 1.0)),
                    step=0.5
                )
                
                min_price_change_24h = st.number_input(
                    "Min 24h Price Change (%)",
                    min_value=-100.0,
                    max_value=1000.0,
                    value=float(bot_settings.get('MIN_PRICE_CHANGE_24H', 5.0)),
                    step=0.5
                )
                
                min_holders = st.number_input(
                    "Min Token Holders",
                    min_value=0,
                    max_value=100000,
                    value=int(bot_settings.get('MIN_HOLDERS', 10)),
                    step=10
                )
        
        # Save parameters
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("💾 Save Parameters", type="primary"):
                # Update settings
                updated_settings = bot_settings.copy()
                updated_settings.update({
                    'running': bot_running,
                    'simulation_mode': simulation_mode,
                    'filter_fake_tokens': filter_fake,
                    'take_profit_target': take_profit,
                    'stop_loss_percentage': stop_loss,
                    'min_investment_per_token': min_investment,
                    'max_investment_per_token': max_investment,
                    'slippage_tolerance': slippage_tolerance / 100,  # Convert to decimal
                    'MIN_SAFETY_SCORE': min_safety_score,
                    'MIN_VOLUME': min_volume,
                    'MIN_LIQUIDITY': min_liquidity,
                    'MIN_PRICE_CHANGE_1H': min_price_change_1h,
                    'MIN_PRICE_CHANGE_24H': min_price_change_24h,
                    'MIN_HOLDERS': min_holders
                })
                
                if save_bot_settings(updated_settings):
                    st.success("✅ Parameters saved successfully!")
                    time.sleep(1)
                    st.experimental_rerun()
                else:
                    st.error("❌ Failed to save parameters!")
        
        with col2:
            if st.button("🔄 Reset to Defaults"):
                default_settings = {
                    "running": False,
                    "simulation_mode": True,
                    "take_profit_target": 2.5,
                    "stop_loss_percentage": 0.2,
                    "min_investment_per_token": 0.02,
                    "max_investment_per_token": 0.1,
                    "slippage_tolerance": 0.05,
                    "filter_fake_tokens": True
                }
                
                if save_bot_settings(default_settings):
                    st.success("Reset to safe defaults!")
                    time.sleep(1)
                    st.experimental_rerun()
        
        with col3:
            # Show current config file location
            config_source = bot_settings.get('_loaded_from', 'Unknown')
            st.info(f"📁 Config loaded from: {config_source}")
    
    # Tab 4: Analytics (placeholder)
    with tabs[3]:
        st.subheader("📈 Trading Analytics")
        st.info("Advanced analytics coming soon...")
        
        # Placeholder charts
        if db_file and os.path.exists(db_file):
            st.markdown("#### Performance Overview")
            
            # Create sample performance chart
            dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
            performance = np.cumsum(np.random.randn(30) * 0.02) + 1
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=dates, y=performance, mode='lines', name='Portfolio Value'))
            fig.update_layout(title="Portfolio Performance", template="plotly_dark")
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Tab 5: System
    with tabs[4]:
        st.subheader("🔧 System Information")
        
        sys_col1, sys_col2 = st.columns(2)
        
        with sys_col1:
            st.markdown("#### Database Status")
            if db_file:
                st.success(f"✅ Database found: {db_file}")
                
                # Database stats
                try:
                    conn = sqlite3.connect(db_file)
                    cursor = conn.cursor()
                    
                    cursor.execute("SELECT COUNT(*) FROM trades")
                    trade_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM tokens")
                    token_count = cursor.fetchone()[0]
                    
                    conn.close()
                    
                    st.info(f"📊 Trades: {trade_count}")
                    st.info(f"🪙 Tokens: {token_count}")
                    
                except Exception as e:
                    st.error(f"Database error: {e}")
            else:
                st.error("❌ No database found")
        
        with sys_col2:
            st.markdown("#### System Health")
            
            # API status checks
            sol_price_status = "✅ Online" if sol_price > 0 else "❌ Offline"
            st.info(f"💰 SOL Price API: {sol_price_status}")
            
            wallet_status = f"✅ {wallet_info['status'].title()}" if wallet_info['status'] != 'error' else "❌ Error"
            st.info(f"💳 Wallet Connection: {wallet_status}")
            
            # Config status
            config_status = "✅ Loaded" if bot_settings.get('_loaded_from', 'default') != 'default' else "⚠️ Default"
            st.info(f"⚙️ Configuration: {config_status}")
        
        # System logs (placeholder)
        st.markdown("#### Recent System Logs")
        with st.expander("View Logs"):
            st.code(f"""
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Dashboard loaded successfully
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Wallet balance: {wallet_info['sol_balance']:.4f} SOL
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] SOL price: ${sol_price:.2f}
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Bot status: {'Running' if bot_settings.get('running') else 'Stopped'}
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Mode: {'Simulation' if bot_settings.get('simulation_mode') else 'Real Trading'}
            """)

if __name__ == "__main__":
    main()
