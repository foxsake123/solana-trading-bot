"""
Enhanced Trading Bot Dashboard - Unified with bot_control.json
"""
import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import time
import sqlite3
from datetime import datetime, timedelta
import requests
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
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

# Enhanced CSS
st.markdown("""
<style>
    .main { background-color: #0E1117; color: white; }
    .css-1d391kg { background-color: #1E1E1E; }
    
    /* Alert Styles */
    .alert-success { background-color: #1B4D3E; border-left: 4px solid #4CAF50; padding: 10px; margin: 10px 0; border-radius: 4px; }
    .alert-warning { background-color: #5D4037; border-left: 4px solid #FF9800; padding: 10px; margin: 10px 0; border-radius: 4px; }
    .alert-danger { background-color: #5D1A1A; border-left: 4px solid #F44336; padding: 10px; margin: 10px 0; border-radius: 4px; }
    .alert-info { background-color: #1A237E; border-left: 4px solid #2196F3; padding: 10px; margin: 10px 0; border-radius: 4px; }
    
    /* ML-specific styles */
    .ml-card { background-color: #2A1B3D; border-radius: 10px; padding: 20px; margin: 10px 0; border: 2px solid #9C27B0; }
    .ml-metric { background-color: #1A1A2E; border-radius: 10px; padding: 15px; margin: 10px 0; border-left: 4px solid #9C27B0; }
    .ml-insight { background-color: #0F3460; border-radius: 8px; padding: 12px; margin: 8px 0; }
    .accuracy-high { color: #4CAF50; font-weight: bold; }
    .accuracy-medium { color: #FF9800; font-weight: bold; }
    .accuracy-low { color: #F44336; font-weight: bold; }
    
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
    
    /* Live Data Indicators */
    .live-indicator { animation: pulse 2s infinite; }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    
    /* Tags */
    .simulation-tag { background-color: #FF9800; color: black; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
    .real-tag { background-color: #F44336; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
    .live-tag { background-color: #4CAF50; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
    .ml-tag { background-color: #9C27B0; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
    
    /* Parameter sections */
    .param-section { background-color: #1A1A1A; border-radius: 8px; padding: 15px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = True
if 'refresh_interval' not in st.session_state:
    st.session_state.refresh_interval = 30

# Parameter definitions with UI configurations
PARAMETER_CONFIG = {
    # Core Trading Parameters
    'take_profit_target': {
        'label': 'Take Profit Target (x)',
        'min_value': 1.1,
        'max_value': 50.0,
        'step': 0.5,
        'format': '%.1f',
        'help': 'Exit position when price reaches this multiple (e.g., 15.0 = 15x profit)',
        'section': 'trading'
    },
    'stop_loss_percentage': {
        'label': 'Stop Loss (%)',
        'min_value': 0.05,
        'max_value': 0.95,
        'step': 0.05,
        'format': '%.2f',
        'help': 'Exit position when loss reaches this percentage (as decimal, e.g. 0.25 = 25%)',
        'section': 'trading'
    },
    'max_investment_per_token': {
        'label': 'Max Investment per Token (SOL)',
        'min_value': 0.01,
        'max_value': 10.0,
        'step': 0.01,
        'format': '%.3f',
        'help': 'Maximum SOL amount to invest per token',
        'section': 'trading'
    },
    'min_investment_per_token': {
        'label': 'Min Investment per Token (SOL)',
        'min_value': 0.001,
        'max_value': 1.0,
        'step': 0.001,
        'format': '%.3f',
        'help': 'Minimum SOL amount to invest per token',
        'section': 'trading'
    },
    'slippage_tolerance': {
        'label': 'Slippage Tolerance',
        'min_value': 0.01,
        'max_value': 0.5,
        'step': 0.01,
        'format': '%.2f',
        'help': 'Maximum acceptable slippage (as decimal, e.g. 0.3 = 30%)',
        'section': 'trading'
    },
    
    # Token Screening Parameters
    'MIN_SAFETY_SCORE': {
        'label': 'Min Safety Score',
        'min_value': 0.0,
        'max_value': 100.0,
        'step': 5.0,
        'format': '%.1f',
        'help': 'Minimum safety score for token screening',
        'section': 'screening'
    },
    'MIN_VOLUME': {
        'label': 'Min 24h Volume (USD)',
        'min_value': 0.0,
        'max_value': 1000000.0,
        'step': 1000.0,
        'format': '%.0f',
        'help': 'Minimum 24h trading volume in USD',
        'section': 'screening'
    },
    'MIN_LIQUIDITY': {
        'label': 'Min Liquidity (USD)',
        'min_value': 0.0,
        'max_value': 1000000.0,
        'step': 1000.0,
        'format': '%.0f',
        'help': 'Minimum liquidity in USD',
        'section': 'screening'
    },
    'MIN_MCAP': {
        'label': 'Min Market Cap (USD)',
        'min_value': 0.0,
        'max_value': 10000000.0,
        'step': 10000.0,
        'format': '%.0f',
        'help': 'Minimum market capitalization in USD',
        'section': 'screening'
    },
    'MIN_HOLDERS': {
        'label': 'Min Holders',
        'min_value': 1,
        'max_value': 1000,
        'step': 1,
        'format': '%d',
        'help': 'Minimum number of token holders',
        'section': 'screening'
    },
    'MIN_PRICE_CHANGE_1H': {
        'label': 'Min 1h Price Change (%)',
        'min_value': 0.0,
        'max_value': 100.0,
        'step': 0.5,
        'format': '%.1f',
        'help': 'Minimum 1-hour price change percentage',
        'section': 'screening'
    },
    'MIN_PRICE_CHANGE_6H': {
        'label': 'Min 6h Price Change (%)',
        'min_value': 0.0,
        'max_value': 100.0,
        'step': 0.5,
        'format': '%.1f',
        'help': 'Minimum 6-hour price change percentage',
        'section': 'screening'
    },
    'MIN_PRICE_CHANGE_24H': {
        'label': 'Min 24h Price Change (%)',
        'min_value': 0.0,
        'max_value': 100.0,
        'step': 0.5,
        'format': '%.1f',
        'help': 'Minimum 24-hour price change percentage',
        'section': 'screening'
    }
}

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

def find_bot_control_file():
    """Find the bot_control.json file."""
    control_files = [
        'data/bot_control.json',
        'bot_control.json',
        'core/bot_control.json'
    ]
    
    for control_file in control_files:
        if os.path.exists(control_file):
            return control_file
    
    return None

def load_bot_settings():
    """Load bot settings from bot_control.json."""
    control_file = find_bot_control_file()
    
    if control_file:
        try:
            with open(control_file, 'r') as f:
                settings = json.load(f)
            
            # Add metadata
            settings['_loaded_from'] = control_file
            settings['_loaded_at'] = datetime.now().isoformat()
            
            # Add any missing parameters with defaults
            default_params = {
                'running': True,
                'simulation_mode': True,
                'filter_fake_tokens': True,
                'use_birdeye_api': True,
                'use_machine_learning': False,
                'take_profit_target': 15.0,
                'stop_loss_percentage': 0.25,
                'max_investment_per_token': 0.05,
                'min_investment_per_token': 0.01,
                'slippage_tolerance': 0.3,
                'MIN_SAFETY_SCORE': 15.0,
                'MIN_VOLUME': 10000,
                'MIN_LIQUIDITY': 50000.0,
                'MIN_MCAP': 100000.0,
                'MIN_HOLDERS': 10,
                'MIN_PRICE_CHANGE_1H': 2.0,
                'MIN_PRICE_CHANGE_6H': 3.0,
                'MIN_PRICE_CHANGE_24H': 5.0
            }
            
            # Add missing parameters
            for key, default_value in default_params.items():
                if key not in settings:
                    settings[key] = default_value
            
            return settings
            
        except Exception as e:
            logger.error(f"Error loading {control_file}: {e}")
    
    # Return defaults if file not found
    st.warning("⚠️ bot_control.json not found! Using default settings.")
    return {
        'running': True,
        'simulation_mode': True,
        'filter_fake_tokens': True,
        'use_birdeye_api': True,
        'use_machine_learning': False,
        'take_profit_target': 15.0,
        'stop_loss_percentage': 0.25,
        'max_investment_per_token': 0.05,
        'min_investment_per_token': 0.01,
        'slippage_tolerance': 0.3,
        'MIN_SAFETY_SCORE': 15.0,
        'MIN_VOLUME': 10000,
        'MIN_LIQUIDITY': 50000.0,
        'MIN_MCAP': 100000.0,
        'MIN_HOLDERS': 10,
        'MIN_PRICE_CHANGE_1H': 2.0,
        'MIN_PRICE_CHANGE_6H': 3.0,
        'MIN_PRICE_CHANGE_24H': 5.0,
        '_loaded_from': 'default',
        '_loaded_at': datetime.now().isoformat()
    }

def save_bot_settings(updated_settings):
    """Save updated settings back to bot_control.json."""
    control_file = find_bot_control_file()
    
    if not control_file:
        # Create in data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        control_file = 'data/bot_control.json'
    
    try:
        # Load current settings
        current_settings = {}
        if os.path.exists(control_file):
            with open(control_file, 'r') as f:
                current_settings = json.load(f)
        
        # Update with new settings
        current_settings.update(updated_settings)
        
        # Remove metadata before saving
        settings_to_save = {k: v for k, v in current_settings.items() 
                           if not k.startswith('_')}
        
        # Save to file
        with open(control_file, 'w') as f:
            json.dump(settings_to_save, f, indent=4)
        
        logger.info(f"Settings saved to {control_file}")
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

def format_parameter_value(value, param_key):
    """Format parameter value for display."""
    config = PARAMETER_CONFIG.get(param_key, {})
    format_str = config.get('format', '%.2f')
    
    if '%d' in format_str:
        return int(value)
    return value

def get_parameter_display_value(value, param_key):
    """Get display value for parameter (convert decimals to percentages where appropriate)."""
    if param_key in ['stop_loss_percentage', 'slippage_tolerance']:
        return value * 100  # Convert 0.25 to 25 for display
    return value

def get_parameter_storage_value(display_value, param_key):
    """Convert display value back to storage value."""
    if param_key in ['stop_loss_percentage', 'slippage_tolerance']:
        return display_value / 100  # Convert 25 back to 0.25 for storage
    return display_value

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
            st.rerun()
    
    # Load data
    bot_settings = load_bot_settings()
    sol_price = get_live_sol_price()
    db_file = find_database()
    
    # Status bar
    status_col1, status_col2, status_col3, status_col4, status_col5 = st.columns(5)
    
    with status_col1:
        bot_status = "🟢 RUNNING" if bot_settings.get('running', False) else "🔴 STOPPED"
        st.markdown(f"**Bot:** {bot_status}")
    
    with status_col2:
        mode_status = "🧪 SIM" if bot_settings.get('simulation_mode', True) else "💰 REAL"
        st.markdown(f"**Mode:** {mode_status}")
    
    with status_col3:
        ml_status = "🤖 ON" if bot_settings.get('use_machine_learning', False) else "🤖 OFF"
        ml_color = "status-online" if bot_settings.get('use_machine_learning', False) else "status-offline"
        st.markdown(f"**ML:** <span class='{ml_color}'>{ml_status}</span>", unsafe_allow_html=True)
    
    with status_col4:
        st.markdown(f"**SOL:** ${sol_price:.2f}")
    
    with status_col5:
        last_update = st.session_state.last_update.strftime("%H:%M:%S")
        st.markdown(f"**Updated:** <span class='live-tag'>{last_update}</span>", unsafe_allow_html=True)
    
    # Main tabs
    tabs = st.tabs([
        "⚙️ Trading Parameters", 
        "📊 Live Monitor", 
        "💰 Balance & Positions", 
        "🤖 AI/ML Analytics", 
        "📈 Traditional Analytics", 
        "🔧 System"
    ])
    
    # Tab 1: Trading Parameters
    with tabs[0]:
        st.subheader("⚙️ Trading Parameters")
        
        # Show config file status
        config_file = bot_settings.get('_loaded_from', 'unknown')
        if config_file != 'default':
            st.markdown(f"""
            <div class='alert-success'>
                <strong>✅ Configuration Loaded</strong><br>
                Using settings from: <code>{config_file}</code>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class='alert-warning'>
                <strong>⚠️ Using Default Configuration</strong><br>
                bot_control.json not found. Changes will create a new file.
            </div>
            """, unsafe_allow_html=True)
        
        # Safety warning for real trading
        if not bot_settings.get('simulation_mode', True):
            st.markdown("""
            <div class='alert-danger'>
                <strong>🔥 REAL TRADING MODE ACTIVE</strong><br>
                Changes to parameters will affect real money trades. Be extremely careful!
            </div>
            """, unsafe_allow_html=True)
        
        # Core Controls
        st.markdown("#### Core Controls")
        
        core_col1, core_col2 = st.columns(2)
        
        with core_col1:
            bot_running = st.checkbox(
                "🤖 Bot Running",
                value=bot_settings.get('running', False),
                help="Start or stop the trading bot"
            )
            
            simulation_mode = st.checkbox(
                "🧪 Simulation Mode",
                value=bot_settings.get('simulation_mode', True),
                help="Toggle between simulation and real trading mode"
            )
        
        with core_col2:
            filter_fake = st.checkbox(
                "🛡️ Filter Fake Tokens",
                value=bot_settings.get('filter_fake_tokens', True),
                help="Enable filtering of likely scam tokens"
            )
            
            use_birdeye = st.checkbox(
                "👁️ Use Birdeye API",
                value=bot_settings.get('use_birdeye_api', True),
                help="Use Birdeye API for additional token data"
            )
        
        # ML Controls
        st.markdown("#### 🤖 Machine Learning")
        
        ml_enabled = st.checkbox(
            "Enable Machine Learning",
            value=bot_settings.get('use_machine_learning', False),
            help="Enable AI-powered trading decisions"
        )
        
        # Trading Parameters Section
        st.markdown("#### 💰 Trading Parameters")
        
        trading_params = {}
        
        # Group parameters by section
        trading_section_params = {k: v for k, v in PARAMETER_CONFIG.items() if v['section'] == 'trading'}
        
        param_cols = st.columns(3)
        
        for i, (param_key, param_config) in enumerate(trading_section_params.items()):
            with param_cols[i % 3]:
                current_value = bot_settings.get(param_key, 0)
                display_value = get_parameter_display_value(current_value, param_key)
                
                # Special handling for percentage parameters
                if param_key in ['stop_loss_percentage', 'slippage_tolerance']:
                    new_value = st.number_input(
                        param_config['label'] + " (%)",
                        min_value=param_config['min_value'] * 100,
                        max_value=param_config['max_value'] * 100,
                        value=float(display_value),
                        step=param_config['step'] * 100,
                        help=param_config['help'] + " (displayed as percentage)",
                        key=f"param_{param_key}"
                    )
                    trading_params[param_key] = get_parameter_storage_value(new_value, param_key)
                else:
                    new_value = st.number_input(
                        param_config['label'],
                        min_value=param_config['min_value'],
                        max_value=param_config['max_value'],
                        value=float(current_value),
                        step=param_config['step'],
                        help=param_config['help'],
                        key=f"param_{param_key}"
                    )
                    trading_params[param_key] = new_value
        
        # Token Screening Parameters Section
        st.markdown("#### 🔍 Token Screening Parameters")
        
        screening_params = {}
        
        # Group screening parameters
        screening_section_params = {k: v for k, v in PARAMETER_CONFIG.items() if v['section'] == 'screening'}
        
        # Create columns for screening parameters
        screening_cols = st.columns(3)
        
        for i, (param_key, param_config) in enumerate(screening_section_params.items()):
            with screening_cols[i % 3]:
                current_value = bot_settings.get(param_key, 0)
                
                if param_key == 'MIN_HOLDERS':
                    # Integer parameter
                    new_value = st.number_input(
                        param_config['label'],
                        min_value=int(param_config['min_value']),
                        max_value=int(param_config['max_value']),
                        value=int(current_value),
                        step=int(param_config['step']),
                        help=param_config['help'],
                        key=f"param_{param_key}"
                    )
                else:
                    # Float parameter
                    new_value = st.number_input(
                        param_config['label'],
                        min_value=param_config['min_value'],
                        max_value=param_config['max_value'],
                        value=float(current_value),
                        step=param_config['step'],
                        help=param_config['help'],
                        key=f"param_{param_key}"
                    )
                
                screening_params[param_key] = new_value
        
        # Save Button
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            if st.button("💾 Save All Parameters", type="primary", use_container_width=True):
                # Collect all parameters
                all_params = {
                    'running': bot_running,
                    'simulation_mode': simulation_mode,
                    'filter_fake_tokens': filter_fake,
                    'use_birdeye_api': use_birdeye,
                    'use_machine_learning': ml_enabled,
                    **trading_params,
                    **screening_params
                }
                
                # Save settings
                if save_bot_settings(all_params):
                    st.success("✅ All parameters saved successfully!")
                    st.info("🔄 The trading bot will use these settings on next restart.")
                    
                    # Refresh after short delay
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to save parameters. Check file permissions.")
        
        # Show current configuration summary
        st.markdown("#### 📋 Current Configuration Summary")
        
        summary_col1, summary_col2 = st.columns(2)
        
        with summary_col1:
            st.markdown("**Trading Settings:**")
            st.code(f"""
Take Profit: {bot_settings.get('take_profit_target', 0):.1f}x
Stop Loss: {bot_settings.get('stop_loss_percentage', 0)*100:.1f}%
Max Investment: {bot_settings.get('max_investment_per_token', 0):.3f} SOL
Min Investment: {bot_settings.get('min_investment_per_token', 0):.3f} SOL
Slippage: {bot_settings.get('slippage_tolerance', 0)*100:.1f}%
            """)
        
        with summary_col2:
            st.markdown("**Screening Filters:**")
            st.code(f"""
Min Safety Score: {bot_settings.get('MIN_SAFETY_SCORE', 0):.1f}
Min Volume: ${bot_settings.get('MIN_VOLUME', 0):,.0f}
Min Liquidity: ${bot_settings.get('MIN_LIQUIDITY', 0):,.0f}
Min Market Cap: ${bot_settings.get('MIN_MCAP', 0):,.0f}
Min Holders: {bot_settings.get('MIN_HOLDERS', 0)}
            """)
    
    # Tab 2: Live Monitor
    with tabs[1]:
        st.subheader("📊 Live Trading Monitor")
        
        # Key metrics
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            st.metric("SOL Price", f"${sol_price:.2f}")
        
        with metric_col2:
            st.metric("Bot Status", "Running" if bot_settings.get('running') else "Stopped")
        
        with metric_col3:
            st.metric("Mode", "Simulation" if bot_settings.get('simulation_mode') else "Real")
        
        with metric_col4:
            st.metric("ML Status", "Enabled" if bot_settings.get('use_machine_learning') else "Disabled")
        
        if db_file:
            st.info(f"📊 Database found: {db_file}")
            # Add database monitoring here
        else:
            st.info("📊 Connect database for full monitoring features.")
    
    # Tab 3: Balance & Positions
    with tabs[2]:
        st.subheader("💰 Balance & Positions")
        st.info("💰 Connect wallet for balance tracking.")
    
    # Tab 4: AI/ML Analytics
    with tabs[3]:
        st.subheader("🤖 AI/ML Analytics")
        
        if bot_settings.get('use_machine_learning'):
            st.info("🤖 ML is enabled. Analytics will appear when model starts training.")
        else:
            st.warning("🤖 Machine Learning is disabled. Enable in Trading Parameters to see analytics.")
    
    # Tab 5: Traditional Analytics
    with tabs[4]:
        st.subheader("📈 Traditional Analytics")
        st.info("📈 Connect database for trading analytics.")
    
    # Tab 6: System Information
    with tabs[5]:
        st.subheader("🔧 System Information")
        
        sys_col1, sys_col2 = st.columns(2)
        
        with sys_col1:
            st.markdown("#### Configuration")
            config_file = bot_settings.get('_loaded_from', 'unknown')
            if config_file != 'default':
                st.success(f"✅ Config file: {config_file}")
            else:
                st.warning("⚠️ Using default configuration")
            
            st.info(f"📊 Parameters loaded: {len([k for k in bot_settings.keys() if not k.startswith('_')])}")
        
        with sys_col2:
            st.markdown("#### Database")
            if db_file:
                st.success(f"✅ Database: {db_file}")
                
                # Show database stats
                try:
                    conn = sqlite3.connect(db_file)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    st.info(f"📋 Tables: {len(tables)}")
                    conn.close()
                except Exception as e:
                    st.error(f"Database error: {e}")
            else:
                st.warning("⚠️ No database found")
        
        # Show raw configuration
        if st.checkbox("Show Raw Configuration"):
            st.json({k: v for k, v in bot_settings.items() if not k.startswith('_')})

if __name__ == "__main__":
    main()