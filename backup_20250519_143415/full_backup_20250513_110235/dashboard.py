import asyncio
import pandas as pd
import streamlit as st
import plotly.express as px
import time
import traceback
import json  # Added missing import
from datetime import datetime, timedelta, UTC

from config import BotConfiguration
from solana_trader import SolanaTrader
from database import Database
from logging_setup import logger

async def fetch_dashboard_data():
    """
    Fetch all the data needed for the dashboard
    """
    trader = SolanaTrader()
    db = Database()
    
    try:
        # Connect to Solana
        await trader.connect()
        
        # Get wallet balance
        balance_sol, balance_usd = await trader.get_wallet_balance()
        
        # Get SOL price
        sol_price_usd = await trader.get_sol_price()
        
        # Get active positions
        positions_df = db.get_active_orders()
        
        # Get trading history
        trades_df = db.get_trading_history(limit=50)
        
        # Get discovered tokens
        tokens_df = db.get_tokens(limit=30)
        
        # Calculate bot statistics
        stats = calculate_stats(trades_df, positions_df)
        
        # Load bot control settings
        control = get_bot_control()
        
        return {
            'positions_df': positions_df,
            'trades_df': trades_df,
            'tokens_df': tokens_df,
            'wallet_balance_sol': balance_sol,
            'wallet_balance_usd': balance_usd,
            'sol_price_usd': sol_price_usd,
            'stats': stats,
            'control': control
        }
    
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}")
        logger.error(traceback.format_exc())
        return {
            'positions_df': pd.DataFrame(),
            'trades_df': pd.DataFrame(),
            'tokens_df': pd.DataFrame(),
            'wallet_balance_sol': 0.0,
            'wallet_balance_usd': 0.0,
            'sol_price_usd': 0.0,
            'stats': {
                'win_rate': 0, 
                'total_trades': 0, 
                'profit_loss': 0, 
                'avg_holding_time': 0  # Added missing key
            },
            'control': {'running': False, 'take_profit_target': 1.5, 'stop_loss_percentage': 0.25, 'max_investment_per_token': 0.1}
        }
    finally:
        # Close Solana connection
        if trader.client:
            await trader.client.close()

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
            'take_profit_target': 1.5,
            'stop_loss_percentage': 0.25,
            'max_investment_per_token': 0.1
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

def display_dashboard():
    """
    Main dashboard display function
    """
    st.set_page_config(
        page_title="Solana Trading Bot Dashboard",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Solana Trading Bot Dashboard")
    
    # Fetch data
    data = asyncio.run(fetch_dashboard_data())
    
    # Bot control section
    st.sidebar.title("Bot Controls")
    
    control = data['control']
    bot_status = "🟢 Running" if control.get('running', True) else "🔴 Stopped"
    
    if st.sidebar.button(f"{'Stop Bot' if control.get('running', True) else 'Start Bot'}"):
        control['running'] = not control.get('running', True)
        update_bot_control(control)
        st.sidebar.success(f"Bot is now {'running' if control['running'] else 'stopped'}")
        st.rerun()  # Use st.rerun() instead of st.experimental_rerun()
    
    st.sidebar.write(f"Status: {bot_status}")
    
    # Trading parameters
    st.sidebar.subheader("Trading Parameters")
    
    # Simulation Mode Toggle
    simulation_mode = st.sidebar.checkbox(
        "Simulation Mode", 
        value=control.get('simulation_mode', True),
        help="When enabled, trades are simulated without real execution. Disable for real trading."
    )
    
    if simulation_mode != control.get('simulation_mode', True):
        control['simulation_mode'] = simulation_mode
        update_bot_control(control)
        st.sidebar.success(f"Simulation mode {'enabled' if simulation_mode else 'disabled'}")
        # Display warning if disabling simulation mode
        if not simulation_mode:
            st.sidebar.warning("⚠️ CAUTION: Real trading mode activated. Bot will execute actual trades on the blockchain.")
    
    col1, col2 = st.sidebar.columns(2)
    tp_value = st.sidebar.number_input(
        "Take Profit Target (x)",
        min_value=1.1,
        max_value=5.0,
        value=float(control.get('take_profit_target', 1.5)),
        step=0.1
    )
    
    sl_value = st.sidebar.number_input(
        "Stop Loss (%)",
        min_value=5.0,
        max_value=50.0,
        value=float(control.get('stop_loss_percentage', 0.25)) * 100,
        step=5.0
    ) / 100.0
    
    max_inv = st.sidebar.number_input(
        "Max Investment per Token (SOL)",
        min_value=0.01,
        max_value=1.0,
        value=float(control.get('max_investment_per_token', 0.1)),
        step=0.01
    )
    
    if st.sidebar.button("Update Trading Parameters"):
        control['take_profit_target'] = tp_value
        control['stop_loss_percentage'] = sl_value
        control['max_investment_per_token'] = max_inv
        update_bot_control(control)
        st.sidebar.success("Trading parameters updated!")
    
    # Auto-refresh
    auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
    refresh_interval = st.sidebar.slider(
        "Refresh interval (seconds)",
        min_value=30,
        max_value=300,
        value=60
    )
    
    # Main dashboard
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
    
    # Discovered tokens
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
        
        # Display tokens
        st.dataframe(tokens_display.sort_values('last_updated', ascending=False))
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(1)  # Small delay to ensure UI is fully rendered
        
        # Create a countdown timer
        placeholder = st.empty()
        
        for seconds_left in range(refresh_interval, 0, -1):
            placeholder.text(f"Auto-refreshing in {seconds_left} seconds...")
            time.sleep(1)
        
        placeholder.text("Refreshing...")
        st.rerun()  # Use st.rerun() instead of st.experimental_rerun()

if __name__ == "__main__":
    display_dashboard()