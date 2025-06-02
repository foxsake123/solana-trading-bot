"""
Enhanced Trading Bot Dashboard with ML Analytics and Performance Monitoring
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

# Import configuration
try:
    from config import BotConfiguration
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    st.error("⚠️ config.py not found! Using fallback configuration.")

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
    
    /* ML-specific styles */
    .ml-card { background-color: #2A1B3D; border-radius: 10px; padding: 20px; margin: 10px 0; border: 2px solid #9C27B0; }
    .ml-metric { background-color: #1A1A2E; border-radius: 10px; padding: 15px; margin: 10px 0; border-left: 4px solid #9C27B0; }
    .ml-insight { background-color: #0F3460; border-radius: 8px; padding: 12px; margin: 8px 0; }
    .accuracy-high { color: #4CAF50; font-weight: bold; }
    .accuracy-medium { color: #FF9800; font-weight: bold; }
    .accuracy-low { color: #F44336; font-weight: bold; }
    
    /* Performance indicators */
    .performance-excellent { background: linear-gradient(45deg, #4CAF50, #8BC34A); }
    .performance-good { background: linear-gradient(45deg, #2196F3, #03DAC6); }
    .performance-moderate { background: linear-gradient(45deg, #FF9800, #FFC107); }
    .performance-poor { background: linear-gradient(45deg, #F44336, #FF5722); }
    
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
    
    /* ML Specific */
    .ml-score-container { display: flex; align-items: center; justify-content: space-between; margin: 10px 0; }
    .ml-progress-bar { width: 100%; height: 20px; background-color: #333; border-radius: 10px; overflow: hidden; }
    .ml-progress-fill { height: 100%; transition: width 0.3s ease; }
</style>
""", unsafe_allow_html=True)

# Initialize session state for real-time updates
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = True
if 'refresh_interval' not in st.session_state:
    st.session_state.refresh_interval = 30

# Helper functions for basic functionality
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
                    settings['_loaded_from'] = control_file
                    settings['_loaded_at'] = datetime.now().isoformat()
                    return settings
            except Exception as e:
                logger.error(f"Error loading {control_file}: {e}")
    
    # Default settings with ML parameters (fallback)
    if CONFIG_AVAILABLE:
        config = BotConfiguration.DASHBOARD_PARAMS
        return {
            "running": False,
            "simulation_mode": True,
            "take_profit_target": config['take_profit']['default'],
            "stop_loss_percentage": config['stop_loss']['default'],
            "min_investment_per_token": config['min_investment']['default'],
            "max_investment_per_token": config['max_investment']['default'],
            "slippage_tolerance": config['slippage_tolerance']['default'],
            "use_machine_learning": False,
            "filter_fake_tokens": True,
            "ml_confidence_threshold": config['ml_confidence_threshold']['default'],
            "ml_retrain_interval_hours": config['ml_retrain_interval']['default'],
            "ml_min_training_samples": config['ml_min_samples']['default'],
            "MIN_SAFETY_SCORE": config['min_safety_score']['default'],
            "MIN_VOLUME": config['min_volume']['default'],
            "MIN_LIQUIDITY": config['min_liquidity']['default'],
            "MIN_MCAP": 50000.0,
            "MIN_HOLDERS": 30,
            "MIN_PRICE_CHANGE_1H": 5.0,
            "MIN_PRICE_CHANGE_6H": 10.0,
            "MIN_PRICE_CHANGE_24H": config['min_price_change_24h']['default'],
            "_loaded_from": "default_with_config",
            "_loaded_at": datetime.now().isoformat()
        }
    else:
        return {
            "running": False,
            "simulation_mode": True,
            "take_profit_target": 15.0,
            "stop_loss_percentage": 25.0,
            "min_investment_per_token": 0.02,
            "max_investment_per_token": 1.0,
            "slippage_tolerance": 30.0,
            "use_machine_learning": False,
            "filter_fake_tokens": True,
            "ml_confidence_threshold": 0.7,
            "ml_retrain_interval_hours": 24,
            "ml_min_training_samples": 10,
            "MIN_SAFETY_SCORE": 50.0,
            "MIN_VOLUME": 10.0,
            "MIN_LIQUIDITY": 25000.0,
            "MIN_MCAP": 50000.0,
            "MIN_HOLDERS": 30,
            "MIN_PRICE_CHANGE_1H": 5.0,
            "MIN_PRICE_CHANGE_6H": 10.0,
            "MIN_PRICE_CHANGE_24H": 20.0,
            "_loaded_from": "fallback_default",
            "_loaded_at": datetime.now().isoformat()
        }

def save_bot_settings(updated_settings):
    """Save updated bot settings to control file."""
    if not CONFIG_AVAILABLE:
        st.warning("⚠️ Configuration system not available - changes will not persist!")
        return False
    
    try:
        # Map dashboard parameter names to control file names
        param_mapping = {
            'take_profit_target': 'take_profit_target',
            'stop_loss_percentage': 'stop_loss_percentage', 
            'min_investment_per_token': 'min_investment_per_token',
            'max_investment_per_token': 'max_investment_per_token',
            'slippage_tolerance': 'slippage_tolerance',
            'ml_confidence_threshold': 'ml_confidence_threshold',
            'ml_retrain_interval_hours': 'ml_retrain_interval_hours',
            'ml_min_training_samples': 'ml_min_training_samples',
            'MIN_SAFETY_SCORE': 'MIN_SAFETY_SCORE',
            'MIN_VOLUME': 'MIN_VOLUME',
            'MIN_LIQUIDITY': 'MIN_LIQUIDITY',
            'MIN_PRICE_CHANGE_24H': 'MIN_PRICE_CHANGE_24H'
        }
        
        # Create mapped settings for saving
        save_settings = {}
        for dashboard_key, control_key in param_mapping.items():
            if dashboard_key in updated_settings:
                save_settings[control_key] = updated_settings[dashboard_key]
        
        # Use BotConfiguration to save
        success = BotConfiguration.save_trading_parameters(save_settings)
        return success
        
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

# [Previous ML helper functions would go here - they remain the same]
# ... (keeping the rest of the helper functions as they were)

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
    
    # Auto-refresh logic
    if st.session_state.auto_refresh:
        time_since_update = (datetime.now() - st.session_state.last_update).seconds
        if time_since_update >= st.session_state.refresh_interval:
            st.session_state.last_update = datetime.now()
            st.experimental_rerun()
    
    # Load data
    bot_settings = load_bot_settings()
    sol_price = get_live_sol_price()
    db_file = find_database()
    
    # Status bar with ML status
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
    
    # Main content tabs
    tabs = st.tabs([
        "🤖 AI/ML Analytics", 
        "📊 Live Monitor", 
        "💰 Balance & Positions", 
        "⚙️ Parameters", 
        "📈 Traditional Analytics", 
        "🔧 System"
    ])
    
    # Tab 4: Parameters - Updated section
    with tabs[3]:
        st.subheader("⚙️ Trading Parameters Control")
        
        # Safety warning for real trading
        if not bot_settings.get('simulation_mode', True):
            st.markdown("""
            <div class='alert-danger'>
                <strong>🔥 REAL TRADING MODE ACTIVE</strong><br>
                Changes to parameters will affect real money trades. Be extremely careful!
            </div>
            """, unsafe_allow_html=True)
        
        # Configuration status
        if CONFIG_AVAILABLE:
            st.markdown("""
            <div class='alert-success'>
                <strong>✅ Configuration System Active</strong><br>
                Parameters will be saved to your bot_control.json file and loaded by the trading bot.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class='alert-warning'>
                <strong>⚠️ Configuration System Unavailable</strong><br>
                config.py not found. Parameter changes will not persist across sessions.
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
        
        with core_col2:
            # Filter fake tokens
            filter_fake = st.checkbox(
                "🛡️ Filter Fake Tokens",
                value=bot_settings.get('filter_fake_tokens', True),
                help="Enable filtering of likely scam tokens"
            )
            
            # Emergency stop
            if st.button("🛑 EMERGENCY STOP", type="primary"):
                st.success("Emergency stop would be activated!")
        
        # Trading Parameters - Using configuration
        st.markdown("#### Trading Parameters")
        
        param_col1, param_col2, param_col3 = st.columns(3)
        
        with param_col1:
            # Get config for take profit
            if CONFIG_AVAILABLE:
                tp_config = BotConfiguration.get_dashboard_param_config('take_profit')
            else:
                tp_config = {'default': 15.0, 'min_value': 1.1, 'max_value': 50.0, 'step': 0.5, 'help': 'Exit when price reaches this multiple'}
            
            take_profit = st.number_input(
                "Take Profit Target",
                min_value=tp_config['min_value'],
                max_value=tp_config['max_value'],
                value=float(bot_settings.get('take_profit_target', tp_config['default'])),
                step=tp_config['step'],
                help=tp_config['help']
            )
            
            # Get config for stop loss
            if CONFIG_AVAILABLE:
                sl_config = BotConfiguration.get_dashboard_param_config('stop_loss')
            else:
                sl_config = {'default': 25.0, 'min_value': 5.0, 'max_value': 50.0, 'step': 1.0, 'help': 'Exit when loss reaches this percentage'}
            
            stop_loss = st.number_input(
                "Stop Loss (%)",
                min_value=sl_config['min_value'],
                max_value=sl_config['max_value'],
                value=float(bot_settings.get('stop_loss_percentage', sl_config['default'])),
                step=sl_config['step'],
                help=sl_config['help']
            )
        
        with param_col2:
            # Get config for min investment
            if CONFIG_AVAILABLE:
                min_inv_config = BotConfiguration.get_dashboard_param_config('min_investment')
            else:
                min_inv_config = {'default': 0.02, 'min_value': 0.001, 'max_value': 1.0, 'step': 0.001, 'help': 'Minimum SOL per token'}
            
            min_investment = st.number_input(
                "Min Investment (SOL)",
                min_value=min_inv_config['min_value'],
                max_value=min_inv_config['max_value'],
                value=float(bot_settings.get('min_investment_per_token', min_inv_config['default'])),
                step=min_inv_config['step'],
                format="%.3f",
                help=min_inv_config['help']
            )
            
            # Get config for max investment
            if CONFIG_AVAILABLE:
                max_inv_config = BotConfiguration.get_dashboard_param_config('max_investment')
            else:
                max_inv_config = {'default': 1.0, 'min_value': 0.01, 'max_value': 10.0, 'step': 0.1, 'help': 'Maximum SOL per token'}
            
            max_investment = st.number_input(
                "Max Investment (SOL)",
                min_value=max_inv_config['min_value'],
                max_value=max_inv_config['max_value'],
                value=float(bot_settings.get('max_investment_per_token', max_inv_config['default'])),
                step=max_inv_config['step'],
                format="%.3f",
                help=max_inv_config['help']
            )
        
        with param_col3:
            # Get config for slippage
            if CONFIG_AVAILABLE:
                slip_config = BotConfiguration.get_dashboard_param_config('slippage_tolerance')
            else:
                slip_config = {'default': 30.0, 'min_value': 0.1, 'max_value': 50.0, 'step': 0.5, 'help': 'Maximum acceptable slippage (%)'}
            
            slippage_tolerance = st.number_input(
                "Slippage Tolerance (%)",
                min_value=slip_config['min_value'],
                max_value=slip_config['max_value'],
                value=float(bot_settings.get('slippage_tolerance', slip_config['default'])),
                step=slip_config['step'],
                help=slip_config['help']
            )
            
            if slippage_tolerance > 10:
                st.warning("⚠️ High slippage tolerance increases trading costs!")
        
        # ML Settings
        st.markdown("#### 🤖 Machine Learning Settings")
        
        ml_col1, ml_col2 = st.columns(2)
        
        with ml_col1:
            ml_enabled = st.checkbox(
                "Enable Machine Learning",
                value=bot_settings.get('use_machine_learning', False),
                help="Enable AI-powered trading decisions"
            )
            
            # Get config for ML confidence
            if CONFIG_AVAILABLE:
                conf_config = BotConfiguration.get_dashboard_param_config('ml_confidence_threshold')
            else:
                conf_config = {'default': 0.7, 'min_value': 0.5, 'max_value': 0.95, 'step': 0.05, 'help': 'Minimum ML confidence'}
            
            confidence_threshold = st.slider(
                "ML Confidence Threshold",
                min_value=conf_config['min_value'],
                max_value=conf_config['max_value'],
                value=float(bot_settings.get('ml_confidence_threshold', conf_config['default'])),
                step=conf_config['step'],
                disabled=not ml_enabled,
                help=conf_config['help']
            )
        
        with ml_col2:
            # Get config for retrain interval
            if CONFIG_AVAILABLE:
                retrain_config = BotConfiguration.get_dashboard_param_config('ml_retrain_interval')
                retrain_options = retrain_config.get('options', [6, 12, 24, 48, 72])
            else:
                retrain_options = [6, 12, 24, 48, 72]
                
            current_interval = int(bot_settings.get('ml_retrain_interval_hours', 24))
            if current_interval not in retrain_options:
                retrain_options.append(current_interval)
                retrain_options.sort()
            
            retrain_interval = st.selectbox(
                "Retrain Interval",
                options=retrain_options,
                index=retrain_options.index(current_interval),
                format_func=lambda x: f"{x} hours",
                disabled=not ml_enabled
            )
            
            # Get config for min samples
            if CONFIG_AVAILABLE:
                samples_config = BotConfiguration.get_dashboard_param_config('ml_min_samples')
            else:
                samples_config = {'default': 10, 'min_value': 5, 'max_value': 100, 'step': 5, 'help': 'Minimum training samples'}
            
            min_samples = st.number_input(
                "Min Training Samples",
                min_value=samples_config['min_value'],
                max_value=samples_config['max_value'],
                value=int(bot_settings.get('ml_min_training_samples', samples_config['default'])),
                step=samples_config['step'],
                disabled=not ml_enabled,
                help=samples_config['help']
            )
        
        # Token Filters
        st.markdown("#### Token Screening Filters")
        
        filter_col1, filter_col2 = st.columns(2)
        
        with filter_col1:
            # Get config for safety score
            if CONFIG_AVAILABLE:
                safety_config = BotConfiguration.get_dashboard_param_config('min_safety_score')
            else:
                safety_config = {'default': 50.0, 'min_value': 0.0, 'max_value': 100.0, 'step': 5.0, 'help': 'Minimum safety score'}
            
            min_safety_score = st.number_input(
                "Min Safety Score",
                min_value=safety_config['min_value'],
                max_value=safety_config['max_value'],
                value=float(bot_settings.get('MIN_SAFETY_SCORE', safety_config['default'])),
                step=safety_config['step'],
                help=safety_config['help']
            )
            
            # Get config for volume
            if CONFIG_AVAILABLE:
                vol_config = BotConfiguration.get_dashboard_param_config('min_volume')
            else:
                vol_config = {'default': 10.0, 'min_value': 0.0, 'max_value': 1000000.0, 'step': 10.0, 'help': 'Minimum 24h volume (USD)'}
            
            min_volume = st.number_input(
                "Min 24h Volume (USD)",
                min_value=vol_config['min_value'],
                max_value=vol_config['max_value'],
                value=float(bot_settings.get('MIN_VOLUME', vol_config['default'])),
                step=vol_config['step'],
                help=vol_config['help']
            )
        
        with filter_col2:
            # Get config for liquidity
            if CONFIG_AVAILABLE:
                liq_config = BotConfiguration.get_dashboard_param_config('min_liquidity')
            else:
                liq_config = {'default': 25000.0, 'min_value': 0.0, 'max_value': 1000000.0, 'step': 1000.0, 'help': 'Minimum liquidity (USD)'}
            
            min_liquidity = st.number_input(
                "Min Liquidity (USD)",
                min_value=liq_config['min_value'],
                max_value=liq_config['max_value'],
                value=float(bot_settings.get('MIN_LIQUIDITY', liq_config['default'])),
                step=liq_config['step'],
                help=liq_config['help']
            )
            
            # Get config for price change
            if CONFIG_AVAILABLE:
                price_config = BotConfiguration.get_dashboard_param_config('min_price_change_24h')
            else:
                price_config = {'default': 20.0, 'min_value': 0.0, 'max_value': 100.0, 'step': 1.0, 'help': 'Minimum 24h price change (%)'}
            
            min_price_change = st.number_input(
                "Min 24h Price Change (%)",
                min_value=price_config['min_value'],
                max_value=price_config['max_value'],
                value=float(bot_settings.get('MIN_PRICE_CHANGE_24H', price_config['default'])),
                step=price_config['step'],
                help=price_config['help']
            )
        
        # Save button
        if st.button("💾 Save All Parameters", type="primary"):
            if CONFIG_AVAILABLE:
                # Collect all updated parameters
                updated_params = {
                    'running': bot_running,
                    'simulation_mode': simulation_mode,
                    'filter_fake_tokens': filter_fake,
                    'use_machine_learning': ml_enabled,
                    'take_profit_target': take_profit,
                    'stop_loss_percentage': stop_loss,
                    'min_investment_per_token': min_investment,
                    'max_investment_per_token': max_investment,
                    'slippage_tolerance': slippage_tolerance,
                    'ml_confidence_threshold': confidence_threshold,
                    'ml_retrain_interval_hours': retrain_interval,
                    'ml_min_training_samples': min_samples,
                    'MIN_SAFETY_SCORE': min_safety_score,
                    'MIN_VOLUME': min_volume,
                    'MIN_LIQUIDITY': min_liquidity,
                    'MIN_PRICE_CHANGE_24H': min_price_change
                }
                
                # Attempt to save
                if save_bot_settings(updated_params):
                    st.success("✅ Parameters saved successfully to bot_control.json!")
                    st.info("🔄 The trading bot will use these settings on next restart.")
                    
                    # Update session state
                    time.sleep(1)
                    st.experimental_rerun()
                else:
                    st.error("❌ Failed to save parameters. Check logs for details.")
            else:
                st.warning("⚠️ Configuration system not available - changes will not persist!")
    
    # [Other tabs remain the same...]

if __name__ == "__main__":
    main()