import asyncio
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import time
import traceback
import json
import os
from datetime import datetime, timedelta, UTC

from config import BotConfiguration
from solana_trader import SolanaTrader
from database import Database
from token_analyzer import TokenAnalyzer
from birdeye import BirdeyeAPI
from ml_model import MLModel  # Import ML model

# Set up logging (use the existing logger from the main app)
try:
    from logging_setup import logger
except ImportError:
    import logging
    logger = logging.getLogger('trading_bot.dashboard')
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

# Cache for SOL price to avoid rate limiting
SOL_PRICE_CACHE = {
    'price': 0.0,
    'timestamp': 0,
    'ttl': 600  # Cache time in seconds (10 minutes)
}

async def get_sol_price(trader):
    """
    Get SOL price with caching to avoid rate limiting
    """
    current_time = time.time()
    
    # Check if cache is valid
    if SOL_PRICE_CACHE['price'] > 0 and current_time - SOL_PRICE_CACHE['timestamp'] < SOL_PRICE_CACHE['ttl']:
        return SOL_PRICE_CACHE['price']
    
    # Cache expired or not set, get new price
    try:
        # Try to use alternative price source first to avoid CoinGecko rate limiting
        price = await trader.get_sol_price()
        
        # Update cache
        SOL_PRICE_CACHE['price'] = price
        SOL_PRICE_CACHE['timestamp'] = current_time
        
        return price
    except Exception as e:
        logger.error(f"Error getting SOL price: {e}")
        
        # If cache exists but is expired, return the old price rather than 0
        if SOL_PRICE_CACHE['price'] > 0:
            return SOL_PRICE_CACHE['price']
        
        # Fallback price if all else fails
        return 100.0  # Default SOL price as fallback

async def calculate_simulation_stats(trades_df, sol_price_usd):
    """
    Calculate simulation statistics
    """
    stats = {
        'total_pl_sol': 0.0,
        'total_pl_usd': 0.0,
        'roi_percentage': 0.0,
        'best_trade_multiple': 0.0,
        'worst_trade_multiple': float('inf'),
        'total_trades': 0,
        'winning_trades': 0,
        'losing_trades': 0
    }
    
    if trades_df.empty:
        return stats
    
    try:
        # Filter to simulation trades
        sim_trades = trades_df[trades_df['tx_hash'].str.startswith('SIM_', na=False)].copy()
        
        if sim_trades.empty:
            return stats
        
        # Calculate total P&L
        total_buy_sol = 0.0
        total_sell_sol = 0.0
        best_multiple = 0.0
        worst_multiple = float('inf')
        winning_trades = 0
        losing_trades = 0
        
        # Group by contract address to calculate per-token P&L
        for contract in sim_trades['contract_address'].unique():
            contract_trades = sim_trades[sim_trades['contract_address'] == contract].copy()
            
            # Get buys and sells
            buys = contract_trades[contract_trades['action'] == 'BUY']
            sells = contract_trades[contract_trades['action'] == 'SELL']
            
            # Calculate buy value
            buy_amount = buys['amount'].sum()
            buy_price = buys['price'].mean() if not buys.empty else 0
            buy_value = buy_amount * buy_price
            
            # Calculate sell value
            sell_amount = sells['amount'].sum()
            sell_price = sells['price'].mean() if not sells.empty else 0
            sell_value = sell_amount * sell_price
            
            # Add to totals
            total_buy_sol += buy_amount
            total_sell_sol += sell_amount
            
            # Calculate multiple and track win/loss
            if buy_value > 0 and sell_value > 0:
                trade_multiple = sell_value / buy_value
                best_multiple = max(best_multiple, trade_multiple)
                
                if trade_multiple > 1.0:
                    winning_trades += 1
                else:
                    losing_trades += 1
                    
                # Only update worst multiple if it's a completed trade
                worst_multiple = min(worst_multiple, trade_multiple)
        
        # Calculate net P&L
        pl_sol = total_sell_sol - total_buy_sol
        pl_usd = pl_sol * sol_price_usd
        
        # Calculate ROI
        initial_investment = total_buy_sol
        roi_percentage = (pl_sol / initial_investment * 100) if initial_investment > 0 else 0.0
        
        # Handle case where no losing trades completed
        if worst_multiple == float('inf'):
            worst_multiple = 0.0
            
        # Update stats
        stats['total_pl_sol'] = pl_sol
        stats['total_pl_usd'] = pl_usd
        stats['roi_percentage'] = roi_percentage
        stats['best_trade_multiple'] = best_multiple
        stats['worst_trade_multiple'] = worst_multiple
        stats['total_trades'] = winning_trades + losing_trades
        stats['winning_trades'] = winning_trades
        stats['losing_trades'] = losing_trades
        
        return stats
    
    except Exception as e:
        logger.error(f"Error calculating simulation stats: {e}")
        return stats

async def fetch_dashboard_data():
    """
    Fetch all the data needed for the dashboard
    """
    # Create the database first
    db = Database()
    
    # Then initialize the trader with the database
    trader = SolanaTrader(db=db)
    
    # Initialize other components that need the database
    birdeye = BirdeyeAPI()
    
    try:
        # Connect to Solana
        await trader.connect()
        
        # Get SOL price (cached)
        sol_price_usd = await get_sol_price(trader)
        
        # Get wallet balance using the cached SOL price
        if trader.simulation_mode:
            # In simulation mode, return a simulated balance of 5 SOL
            balance_sol = 5.0
            balance_usd = balance_sol * sol_price_usd
        else:
            # Only make RPC call for balance in real trading mode
            balance_response = await trader.client.get_balance(trader.keypair.pubkey())
            balance_lamports = balance_response.value
            balance_sol = balance_lamports / 1_000_000_000
            balance_usd = balance_sol * sol_price_usd
        
        # Get active positions
        positions_df = db.get_active_orders()
        
        # Get trading history
        trades_df = db.get_trading_history(limit=50)
        
        # Get discovered tokens
        tokens_df = db.get_tokens(limit=30)
        
        # Get trending tokens from Birdeye/DexScreener
        trending_tokens = await birdeye.get_trending_tokens(limit=10)
        
        # Calculate bot statistics
        stats = calculate_stats(trades_df, positions_df)
        
        # Calculate simulation statistics
        simulation_stats = await calculate_simulation_stats(trades_df, sol_price_usd)
        
        # Load bot control settings
        control = get_bot_control()
        
        # Load ML model stats if enabled
        ml_stats = {}
        ml_predictions = []
        if control.get('use_machine_learning', False):
            try:
                # Import only when needed to avoid circular imports
                from token_scanner import TokenScanner
                scanner = TokenScanner()
                ml_stats = scanner.get_ml_stats()
                ml_predictions = scanner.get_ml_predictions()
            except Exception as e:
                logger.error(f"Error getting ML stats: {e}")
                # Use MLModel directly as fallback
                try:
                    ml_model = MLModel()
                    ml_stats = ml_model.get_performance_stats()
                except:
                    pass
        
        return {
            'positions_df': positions_df,
            'trades_df': trades_df,
            'tokens_df': tokens_df,
            'trending_tokens': trending_tokens,
            'wallet_balance_sol': balance_sol,
            'wallet_balance_usd': balance_usd,
            'sol_price_usd': sol_price_usd,
            'stats': stats,
            'simulation_stats': simulation_stats,
            'control': control,
            'ml_stats': ml_stats,
            'ml_predictions': ml_predictions
        }
    
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}")
        logger.error(traceback.format_exc())
        return {
            'positions_df': pd.DataFrame(),
            'trades_df': pd.DataFrame(),
            'tokens_df': pd.DataFrame(),
            'trending_tokens': [],
            'wallet_balance_sol': 0.0,
            'wallet_balance_usd': 0.0,
            'sol_price_usd': 0.0,
            'stats': {
                'win_rate': 0, 
                'total_trades': 0, 
                'profit_loss': 0, 
                'avg_holding_time': 0
            },
            'simulation_stats': {
                'total_pl_sol': 0.0,
                'total_pl_usd': 0.0,
                'roi_percentage': 0.0,
                'best_trade_multiple': 0.0,
                'worst_trade_multiple': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0
            },
            'control': {'running': False, 'take_profit_target': 15.0, 'stop_loss_percentage': 0.25, 'max_investment_per_token': 1.0},
            'ml_stats': {},
            'ml_predictions': []
        }
    finally:
        # Close Solana connection
        try:
            # Just call the close method directly instead of accessing client
            await trader.close()
        except Exception as e:
            logger.error(f"Error closing Solana connection: {e}")
            # Continue with cleanup even if there's an error

def calculate_stats(trades_df, positions_df):
    """
    Calculate trading statistics
    """
    if trades_df.empty:
        return {
            'win_rate': 0,
            'total_trades': 0,
            'profit_loss': 0,
            'avg_holding_time': 0
        }
    
    try:
        # Filter completed trades
        sell_trades = trades_df[trades_df['action'] == 'SELL'].copy()
        total_completed = len(sell_trades)
        
        if total_completed > 0:
            # Calculate profit/loss
            total_profit_loss = 0
            winning_trades = 0
            holding_times = []
            
            for contract in sell_trades['contract_address'].unique():
                contract_trades = trades_df[trades_df['contract_address'] == contract].copy()
                contract_trades = contract_trades.sort_values('timestamp')
                
                buys = contract_trades[contract_trades['action'] == 'BUY']
                sells = contract_trades[contract_trades['action'] == 'SELL']
                
                if not buys.empty and not sells.empty:
                    # Get first buy and last sell
                    first_buy = buys.iloc[0]
                    last_sell = sells.iloc[-1]
                    
                    # Calculate profit/loss
                    buy_value = first_buy['amount'] * first_buy['price']
                    sell_value = last_sell['amount'] * last_sell['price']
                    trade_pl = sell_value - buy_value
                    
                    # Track winning trades
                    if trade_pl > 0:
                        winning_trades += 1
                    
                    # Add to total P&L
                    total_profit_loss += trade_pl
                    
                    # Calculate holding time
                    buy_time = datetime.fromisoformat(first_buy['timestamp'].replace('Z', '+00:00') if 'Z' in first_buy['timestamp'] else first_buy['timestamp'])
                    sell_time = datetime.fromisoformat(last_sell['timestamp'].replace('Z', '+00:00') if 'Z' in last_sell['timestamp'] else last_sell['timestamp'])
                    holding_time = (sell_time - buy_time).total_seconds() / 3600  # hours
                    holding_times.append(holding_time)
            
            # Calculate statistics
            win_rate = (winning_trades / total_completed) * 100 if total_completed > 0 else 0
            avg_holding_time = sum(holding_times) / len(holding_times) if holding_times else 0
            
            return {
                'win_rate': win_rate,
                'total_trades': total_completed,
                'profit_loss': total_profit_loss,
                'avg_holding_time': avg_holding_time
            }
        else:
            return {
                'win_rate': 0,
                'total_trades': 0,
                'profit_loss': 0,
                'avg_holding_time': 0
            }
    
    except Exception as e:
        logger.error(f"Error calculating stats: {e}")
        return {
            'win_rate': 0,
            'total_trades': 0,
            'profit_loss': 0,
            'avg_holding_time': 0
        }

def get_bot_control():
    """
    Get bot control settings
    """
    try:
        import json
        with open(BotConfiguration.BOT_CONTROL_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading bot control: {e}")
        return {
            'running': False,
            'simulation_mode': True,  # Default to simulation mode
            'use_machine_learning': False,  # Default to ML disabled
            'take_profit_target': 15.0,
            'stop_loss_percentage': 0.25,
            'max_investment_per_token': 1.0,
            'slippage_tolerance': 0.30,
            'MIN_SAFETY_SCORE': 15.0,
            'MIN_VOLUME': 10.0,
            'MIN_LIQUIDITY': 5000.0,
            'MIN_MCAP': 10000.0,
            'MIN_HOLDERS': 10,
            'MIN_PRICE_CHANGE_1H': 1.0,
            'MIN_PRICE_CHANGE_6H': 2.0,
            'MIN_PRICE_CHANGE_24H': 5.0
        }

def update_bot_control(control):
    """
    Update bot control settings
    """
    try:
        import json
        with open(BotConfiguration.BOT_CONTROL_FILE, 'w') as f:
            json.dump(control, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error updating bot control: {e}")
        return False

def reset_database():
    """
    Reset the database
    """
    try:
        db = Database()
        return db.reset_database()
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        return False

def display_dashboard():
    """
    Main dashboard display function
    """
    st.set_page_config(
        page_title="Solana Memecoin Trading Bot Dashboard",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Solana Memecoin Trading Bot Dashboard")
    
    # Fetch data
    data = asyncio.run(fetch_dashboard_data())
    
    # Bot control section
    with st.sidebar:
        st.title("Bot Controls")
        
        control = data['control']
        bot_status = "🟢 Running" if control.get('running', True) else "🔴 Stopped"
        
        if st.button(f"{'Stop Bot' if control.get('running', True) else 'Start Bot'}"):
            control['running'] = not control.get('running', True)
            update_bot_control(control)
            st.success(f"Bot is now {'running' if control['running'] else 'stopped'}")
            st.rerun()
        
        st.write(f"Status: {bot_status}")
        
        # Simulation Mode Toggle
        simulation_mode = st.checkbox(
            "Simulation Mode", 
            value=control.get('simulation_mode', True),
            help="When enabled, trades are simulated without real execution. Disable for real trading."
        )
        
        # Add Machine Learning Toggle
        ml_mode = st.checkbox(
            "Machine Learning", 
            value=control.get('use_machine_learning', False),
            help="When enabled, the bot will use machine learning to predict token performance."
        )
        
        if simulation_mode != control.get('simulation_mode', True):
            control['simulation_mode'] = simulation_mode
            update_bot_control(control)
            st.success(f"Simulation mode {'enabled' if simulation_mode else 'disabled'}")
            # Display warning if disabling simulation mode
            if not simulation_mode:
                st.warning("⚠️ CAUTION: Real trading mode activated. Bot will execute actual trades on the blockchain.")
        
        if ml_mode != control.get('use_machine_learning', False):
            control['use_machine_learning'] = ml_mode
            update_bot_control(control)
            st.success(f"Machine Learning {'enabled' if ml_mode else 'disabled'}")
            
        st.subheader("Trading Parameters")
        
        # Trading parameters in tabs for better organization
        tabs = st.tabs(["Core", "Screening", "Price Change"])
        
        with tabs[0]:  # Core parameters
            tp_value = st.number_input(
                "Take Profit Target (x)",
                min_value=1.1,
                max_value=20.0,
                value=float(control.get('take_profit_target', 15.0)),
                step=0.5,
                help="Multiplier for take profit (e.g. 15.0 = 1500% profit)"
            )
            
            sl_value = st.number_input(
                "Stop Loss (%)",
                min_value=5.0,
                max_value=50.0,
                value=float(control.get('stop_loss_percentage', 0.25)) * 100,
                step=5.0,
                help="Percentage for stop loss trigger"
            ) / 100.0
            
            max_inv = st.number_input(
                "Max Investment per Token (SOL)",
                min_value=0.01,
                max_value=5.0,
                value=float(control.get('max_investment_per_token', 1.0)),
                step=0.1,
                help="Maximum SOL to invest in a single token"
            )
            
            slippage = st.number_input(
                "Slippage Tolerance (%)",
                min_value=1.0,
                max_value=50.0,
                value=float(control.get('slippage_tolerance', 0.30)) * 100,
                step=1.0,
                help="Allowable slippage percentage for trades"
            ) / 100.0
        
        with tabs[1]:  # Screening parameters
            min_safety = st.number_input(
                "Min Safety Score",
                min_value=0.0,
                max_value=100.0,
                value=float(control.get('MIN_SAFETY_SCORE', 15.0)),
                step=5.0,
                help="Minimum safety score (0-100) for trading"
            )
            
            min_volume = st.number_input(
                "Min 24h Volume ($)",
                min_value=0.0,
                max_value=100000.0,
                value=float(control.get('MIN_VOLUME', 10.0)),
                step=10.0,
                help="Minimum 24-hour trading volume in USD"
            )
            
            min_liquidity = st.number_input(
                "Min Liquidity ($)",
                min_value=0.0,
                max_value=100000.0,
                value=float(control.get('MIN_LIQUIDITY', 5000.0)),
                step=1000.0,
                help="Minimum liquidity in USD"
            )
            
            min_mcap = st.number_input(
                "Min Market Cap ($)",
                min_value=0.0,
                max_value=500000.0,
                value=float(control.get('MIN_MCAP', 10000.0)),
                step=5000.0,
                help="Minimum market capitalization in USD"
            )
            
            min_holders = st.number_input(
                "Min Holders",
                min_value=0,
                max_value=1000,
                value=int(control.get('MIN_HOLDERS', 10)),
                step=10,
                help="Minimum number of token holders"
            )
        
        with tabs[2]:  # Price change parameters
            min_change_1h = st.number_input(
                "Min 1h Price Change (%)",
                min_value=0.0,
                max_value=50.0,
                value=float(control.get('MIN_PRICE_CHANGE_1H', 1.0)),
                step=0.5,
                help="Minimum price change over 1 hour"
            )
            
            min_change_6h = st.number_input(
                "Min 6h Price Change (%)",
                min_value=0.0,
                max_value=50.0,
                value=float(control.get('MIN_PRICE_CHANGE_6H', 2.0)),
                step=0.5,
                help="Minimum price change over 6 hours"
            )
            
            min_change_24h = st.number_input(
                "Min 24h Price Change (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(control.get('MIN_PRICE_CHANGE_24H', 5.0)),
                step=1.0,
                help="Minimum price change over 24 hours"
            )
        
        if st.button("Update Trading Parameters", type="primary"):
            # Update control with new values
            control['take_profit_target'] = tp_value
            control['stop_loss_percentage'] = sl_value
            control['max_investment_per_token'] = max_inv
            control['slippage_tolerance'] = slippage
            control['MIN_SAFETY_SCORE'] = min_safety
            control['MIN_VOLUME'] = min_volume
            control['MIN_LIQUIDITY'] = min_liquidity
            control['MIN_MCAP'] = min_mcap
            control['MIN_HOLDERS'] = min_holders
            control['MIN_PRICE_CHANGE_1H'] = min_change_1h
            control['MIN_PRICE_CHANGE_6H'] = min_change_6h
            control['MIN_PRICE_CHANGE_24H'] = min_change_24h
            
            # Save to control file
            update_bot_control(control)
            st.success("Trading parameters updated!")
        
        # Advanced section (collapsible)
        with st.expander("Advanced Controls"):
            if st.button("Reset Database", type="secondary"):
                if reset_database():
                    st.success("Database reset successfully!")
                else:
                    st.error("Failed to reset database.")
            
            st.caption("Warning: Resetting the database will delete all token and trade data.")
        
        # Auto-refresh
        auto_refresh = st.checkbox("Auto-refresh", value=True)
        refresh_interval = st.slider(
            "Refresh interval (seconds)",
            min_value=10,
            max_value=300,
            value=30
        )
    
    # Main dashboard - use tabs for better organization
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Tokens", "Trading", "ML Stats"])
    
    # Tab 1: Overview
    with tab1:
        # Key metrics
        st.subheader("Bot Status and Balance")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Wallet Balance (SOL)",
                f"{data['wallet_balance_sol']:.4f}"
            )
        
        with col2:
            st.metric(
                "Wallet Balance (USD)",
                f"${data['wallet_balance_usd']:.2f}"
            )
        
        with col3:
            st.metric(
                "SOL Price",
                f"${data['sol_price_usd']:.2f}"
            )
        
        # Add Simulation P&L metrics
        st.subheader("Simulation Performance")
        
        sim_col1, sim_col2, sim_col3, sim_col4 = st.columns(4)
        
        with sim_col1:
            st.metric(
                "Simulated Total P&L (SOL)",
                f"{data['simulation_stats']['total_pl_sol']:.4f}",
                delta=f"{data['simulation_stats']['total_pl_sol']:.4f}",
                delta_color="normal"
            )
        
        with sim_col2:
            st.metric(
                "Simulated Total P&L (USD)",
                f"${data['simulation_stats']['total_pl_usd']:.2f}",
                delta=f"${data['simulation_stats']['total_pl_usd']:.2f}",
                delta_color="normal"
            )
        
        with sim_col3:
            st.metric(
                "Simulated ROI (%)",
                f"{data['simulation_stats']['roi_percentage']:.2f}%",
                delta=f"{data['simulation_stats']['roi_percentage']:.2f}%",
                delta_color="normal"
            )
        
        with sim_col4:
            st.metric(
                "Best Trade Multiple",
                f"{data['simulation_stats']['best_trade_multiple']:.2f}x"
            )
        
        # Stats section
        st.subheader("Trading Performance")
        
        stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
        
        with stats_col1:
            st.metric("Total Completed Trades", data['stats']['total_trades'])
        
        with stats_col2:
            st.metric("Win Rate", f"{data['stats']['win_rate']:.1f}%")
        
        with stats_col3:
            st.metric(
                "Total Profit/Loss (SOL)",
                f"{data['stats']['profit_loss']:.4f}",
                delta=f"{data['stats']['profit_loss']:.4f}",
                delta_color="normal"
            )
        
        with stats_col4:
            avg_hours = data['stats']['avg_holding_time']
            if avg_hours >= 24:
                holding_time = f"{avg_hours/24:.1f} days"
            else:
                holding_time = f"{avg_hours:.1f} hours"
            st.metric("Avg Holding Time", holding_time)
        
        # Active positions table
        st.subheader("Active Positions")
        
        if data['positions_df'].empty:
            st.info("No active positions")
        else:
            # Format the dataframe
            display_df = data['positions_df'].copy()
            
            if 'buy_price' in display_df.columns and 'amount' in display_df.columns:
                # Calculate current value if we have prices
                if 'current_price_usd' not in display_df.columns:
                    display_df['current_price_usd'] = 0.0
                
                # Calculate profit/loss
                display_df['invested_usd'] = display_df['amount'] * display_df['buy_price'] * data['sol_price_usd']
                display_df['current_value_usd'] = display_df['amount'] * display_df['current_price_usd']
                display_df['pnl_usd'] = display_df['current_value_usd'] - display_df['invested_usd']
                display_df['pnl_percent'] = (display_df['pnl_usd'] / display_df['invested_usd']) * 100
                display_df['multiple'] = display_df['current_price_usd'] / (display_df['buy_price'] * data['sol_price_usd'])
            
            # Display the dataframe
            st.dataframe(display_df)
        
        # Add position distribution chart if we have positions
        if not data['positions_df'].empty and 'amount' in data['positions_df'].columns:
            st.subheader("Position Distribution")
            
            try:
                # Create a simple pie chart of positions by amount
                fig = px.pie(
                    data['positions_df'],
                    values='amount',
                    names='contract_address',
                    title="Position Distribution by Amount (SOL)"
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating position chart: {e}")
    
    # Tab 2: Tokens
    with tab2:
        # Discovered tokens section
        st.subheader("Discovered Tokens")
        
        if data['tokens_df'].empty:
            st.info("No tokens discovered yet")
        else:
            # Add search filter
            token_filter = st.text_input("Filter by ticker or contract address")
            
            # Apply filter
            tokens_display = data['tokens_df'].copy()
            
            if token_filter:
                # Check if columns exist
                if 'ticker' in tokens_display.columns and 'contract_address' in tokens_display.columns:
                    tokens_display = tokens_display[
                        tokens_display['ticker'].str.contains(token_filter, case=False, na=False) |
                        tokens_display['contract_address'].str.contains(token_filter, case=False, na=False)
                    ]
            
            # Sort options
            sort_options = {
                'Last Updated': 'last_updated',
                'Safety Score': 'safety_score',
                'Volume': 'volume_24h',
                'Liquidity': 'liquidity_usd'
            }
            
            sort_by = st.selectbox("Sort by", list(sort_options.keys()))
            sort_column = sort_options[sort_by]
            
            # Display tokens with sorting
            if sort_column in tokens_display.columns:
                tokens_display = tokens_display.sort_values(sort_column, ascending=False)
            
            st.dataframe(tokens_display)
        
        # Trending tokens from DexScreener
        st.subheader("Trending Tokens (DexScreener)")
        
        if not data['trending_tokens']:
            st.info("No trending tokens available")
        else:
            # Convert to DataFrame for display
            trending_df = pd.DataFrame(data['trending_tokens'])
            st.dataframe(trending_df)
            
            # Create a bar chart of top tokens by volume
            try:
                fig = px.bar(
                    trending_df.sort_values('volume_24h', ascending=False).head(10),
                    x='ticker',
                    y='volume_24h',
                    title="Top Trending Tokens by 24h Volume",
                    labels={'volume_24h': 'Volume (USD)', 'ticker': 'Token'}
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating trending tokens chart: {e}")
    
    # Tab 3: Trading
    with tab3:
        # Trade history
        st.subheader("Recent Trades")
        
        if data['trades_df'].empty:
            st.info("No trade history yet")
        else:
            # Format the dataframe
            trades_display = data['trades_df'].copy()
            
            # Add filters
            col_act, col_date = st.columns(2)
            
            with col_act:
                action_filter = st.multiselect(
                    "Filter by action",
                    options=['BUY', 'SELL'],
                    default=['BUY', 'SELL']
                )
            
            with col_date:
                date_range = st.date_input(
                    "Date range",
                    value=(
                        (datetime.now(UTC) - timedelta(days=7)).date(),
                        datetime.now(UTC).date()
                    )
                )
            
            # Apply filters
            if action_filter:
                trades_display = trades_display[trades_display['action'].isin(action_filter)]
            
            if len(date_range) == 2:
                start_date, end_date = date_range
                start = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC).isoformat()
                end = datetime.combine(end_date, datetime.max.time(), tzinfo=UTC).isoformat()
                
                trades_display = trades_display[
                    (trades_display['timestamp'] >= start) & 
                    (trades_display['timestamp'] <= end)
                ]
            
            # Display the dataframe
            st.dataframe(trades_display)
            
            # Add trade history chart
            if not trades_display.empty and 'timestamp' in trades_display.columns:
                st.subheader("Trade History Visualization")
                
                try:
                    # Convert timestamp to datetime
                    trades_display['dt'] = pd.to_datetime(trades_display['timestamp'])
                    trades_display = trades_display.sort_values('dt')
                    
                    # Count trades by day
                    trades_by_day = trades_display.groupby([pd.Grouper(key='dt', freq='D'), 'action']).size().unstack(fill_value=0)
                    
                    # Create figure
                    fig = go.Figure()
                    
                    if 'BUY' in trades_by_day.columns:
                        fig.add_trace(go.Bar(
                            x=trades_by_day.index,
                            y=trades_by_day['BUY'],
                            name='BUY',
                            marker_color='green'
                        ))
                    
                    if 'SELL' in trades_by_day.columns:
                        fig.add_trace(go.Bar(
                            x=trades_by_day.index,
                            y=trades_by_day['SELL'],
                            name='SELL',
                            marker_color='red'
                        ))
                    
                    fig.update_layout(
                        title='Trades by Day',
                        xaxis_title='Date',
                        yaxis_title='Number of Trades',
                        barmode='group'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"Error creating trade history chart: {e}")
                    
            # Add P&L over time chart
            if not trades_display.empty and 'timestamp' in trades_display.columns:
                st.subheader("Simulated P&L Over Time")
                
                try:
                    # Filter simulation trades only
                    sim_trades = trades_display[trades_display['tx_hash'].str.startswith('SIM_', na=False)].copy()
                    
                    if not sim_trades.empty:
                        # Convert timestamp to datetime
                        sim_trades['dt'] = pd.to_datetime(sim_trades['timestamp'])
                        sim_trades = sim_trades.sort_values('dt')
                        
                        # Calculate cumulative buys and sells
                        buys = sim_trades[sim_trades['action'] == 'BUY'].copy()
                        sells = sim_trades[sim_trades['action'] == 'SELL'].copy()
                        
                        buys['cumulative_sol'] = -buys['amount'].cumsum()
                        sells['cumulative_sol'] = sells['amount'].cumsum()
                        
                        # Combine and calculate net P&L
                        combined = pd.concat([buys[['dt', 'cumulative_sol']], sells[['dt', 'cumulative_sol']]])
                        combined = combined.sort_values('dt')
                        combined['net_pl'] = combined['cumulative_sol'].cumsum()
                        
                        # Create figure
                        fig = px.line(
                            combined, 
                            x='dt', 
                            y='net_pl',
                            title='Simulated P&L Over Time (SOL)',
                            labels={'dt': 'Date', 'net_pl': 'Cumulative P&L (SOL)'}
                        )
                        
                        # Add zero line
                        fig.add_hline(y=0, line_dash="dash", line_color="gray")
                        
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No simulation trades available for P&L chart")
                        
                except Exception as e:
                    st.error(f"Error creating P&L chart: {e}")
                    st.error(traceback.format_exc())
                
    # Tab 4: Machine Learning Stats
    with tab4:
        st.subheader("Machine Learning Model Performance")
        
        # ML Status
        ml_status = "Enabled" if control.get('use_machine_learning', False) else "Disabled"
        st.info(f"Machine Learning Status: {ml_status}")
        
        # ML Model Stats
        if 'ml_stats' in data and data['ml_stats']:
            stats = data['ml_stats']
            
            # Display metrics
            ml_col1, ml_col2, ml_col3, ml_col4 = st.columns(4)
            
            with ml_col1:
                st.metric("Model Accuracy", f"{stats.get('accuracy', 0.0) * 100:.2f}%")
            
            with ml_col2:
                st.metric("Model Precision", f"{stats.get('precision', 0.0) * 100:.2f}%")
            
            with ml_col3:
                st.metric("Model Recall", f"{stats.get('recall', 0.0) * 100:.2f}%")
            
            with ml_col4:
                st.metric("Model F1 Score", f"{stats.get('f1', 0.0) * 100:.2f}%")
            
            # Training info
            st.subheader("Training Information")
            
            train_col1, train_col2 = st.columns(2)
            
            with train_col1:
                last_training = stats.get('last_training', 'Never')
                if last_training != 'Never' and last_training is not None:
                    try:
                        training_date = datetime.fromisoformat(last_training.replace('Z', '+00:00'))
                        last_training = training_date.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        pass
                st.info(f"Last Model Training: {last_training}")
            
            with train_col2:
                st.info(f"Training Samples: {stats.get('training_samples', 0)}")
            
            # Feature importance
            if 'feature_importance' in stats and stats['feature_importance']:
                st.subheader("Feature Importance")
                
                # Convert to DataFrame for chart
                importance_df = pd.DataFrame({
                    'Feature': list(stats['feature_importance'].keys()),
                    'Importance': list(stats['feature_importance'].values())
                })
                
                # Sort by importance
                importance_df = importance_df.sort_values('Importance', ascending=False)
                
                # Plot
                fig = px.bar(
                    importance_df,
                    x='Feature',
                    y='Importance',
                    title="Feature Importance in ML Model",
                    labels={'Feature': 'Feature', 'Importance': 'Importance Score'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # ML Predictions
            if 'ml_predictions' in data and data['ml_predictions']:
                st.subheader("Recent ML Predictions")
                
                # Convert to DataFrame
                predictions_df = pd.DataFrame(data['ml_predictions'])
                
                # Display
                st.dataframe(predictions_df)
                
                # Plot predictions distribution
                fig = px.histogram(
                    predictions_df,
                    x='prediction',
                    nbins=20,
                    title="Distribution of ML Predictions",
                    labels={'prediction': 'Prediction Score (higher = more likely to profit)'}
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No machine learning data available. Enable ML mode and allow the bot to collect more data.")
            
            if st.button("Train Model", type="primary"):
                st.info("Training ML model... This may take a moment.")
                try:
                    from ml_model import MLModel
                    ml_model = MLModel()
                    db = Database()
                    success = ml_model.train(db)
                    
                    if success:
                        st.success("Model trained successfully! Refresh to see stats.")
                    else:
                        st.error("Model training failed. Not enough data yet.")
                except Exception as e:
                    st.error(f"Error training model: {e}")
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(1)  # Small delay to ensure UI is fully rendered
        
        # Create a countdown timer
        placeholder = st.empty()
        
        for seconds_left in range(refresh_interval, 0, -1):
            placeholder.text(f"Auto-refreshing in {seconds_left} seconds...")
            time.sleep(1)
        
        placeholder.text("Refreshing...")
        st.rerun()

if __name__ == "__main__":
    display_dashboard()