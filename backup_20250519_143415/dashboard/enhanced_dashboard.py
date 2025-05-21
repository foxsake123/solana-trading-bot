import streamlit as st
import pandas as pd
import os
import json
import time
import sqlite3
from datetime import datetime
import pytz

def get_sol_price():
    """Get the current SOL price from the database or a fallback value."""
    try:
        # Find database file
        db_file = 'data/sol_bot.db'
        if not os.path.exists(db_file):
            db_file = 'solana_trader.db'
        
        if os.path.exists(db_file):
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Try to get the latest price from the price_history table
            try:
                cursor.execute("SELECT price FROM price_history ORDER BY timestamp DESC LIMIT 1")
                result = cursor.fetchone()
                if result:
                    return result[0]
            except:
                pass
            
            # If that fails, try getting it from the last trade
            try:
                cursor.execute("SELECT price FROM trades ORDER BY timestamp DESC LIMIT 1")
                result = cursor.fetchone()
                if result:
                    return result[0]
            except:
                pass
            
            conn.close()
    except Exception:
        pass
    
    # Fallback to a reasonable SOL price if we couldn't get it from the database
    return 108.45  # Example fallback value

def convert_to_et(timestamp_str):
    """Convert a timestamp string to Eastern Time."""
    try:
        # Parse the timestamp
        if isinstance(timestamp_str, str):
            # Try different formats
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
                try:
                    timestamp = datetime.strptime(timestamp_str, fmt)
                    break
                except ValueError:
                    continue
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
    except Exception:
        # Return the original string if conversion fails
        return timestamp_str

def parse_timestamp(ts_str):
    """Parse a timestamp string to a datetime object."""
    try:
        # Try different formats
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue
        
        # If we get here, none of the formats worked
        return datetime.now()  # Fallback
    except Exception:
        return datetime.now()  # Fallback

def calculate_win_rate(trades_df):
    """Calculate the win rate from a dataframe of trades."""
    if trades_df.empty:
        return 0.0
    
    # Create pairs of trades (BUY and SELL)
    buy_trades = trades_df[trades_df['action'] == 'BUY'].copy()
    sell_trades = trades_df[trades_df['action'] == 'SELL'].copy()
    
    if sell_trades.empty:
        return 0.0
    
    # Count profitable trades
    profitable_trades = 0
    total_paired_trades = 0
    
    for _, sell in sell_trades.iterrows():
        # Find the corresponding buy
        buy = buy_trades[buy_trades['trade_id'] == sell['trade_id']].iloc[0] if not buy_trades[buy_trades['trade_id'] == sell['trade_id']].empty else None
        
        if buy is not None:
            total_paired_trades += 1
            if sell['price'] > buy['price']:
                profitable_trades += 1
    
    if total_paired_trades == 0:
        return 0.0
    
    return (profitable_trades / total_paired_trades) * 100

def calculate_profit_loss(trades_df):
    """Calculate the total profit/loss from a dataframe of trades."""
    if trades_df.empty:
        return 0.0
    
    # Create pairs of trades (BUY and SELL)
    buy_trades = trades_df[trades_df['action'] == 'BUY'].copy()
    sell_trades = trades_df[trades_df['action'] == 'SELL'].copy()
    
    if sell_trades.empty:
        return 0.0
    
    total_profit = 0.0
    
    for _, sell in sell_trades.iterrows():
        # Find the corresponding buy
        matching_buys = buy_trades[buy_trades['trade_id'] == sell['trade_id']]
        if not matching_buys.empty:
            buy = matching_buys.iloc[0]
            
            # Calculate profit for this trade pair
            buy_price = buy['price']
            sell_price = sell['price']
            amount = buy['amount']  # Assuming amount is the same for buy and sell
            
            profit = (sell_price - buy_price) * amount
            total_profit += profit
    
    return total_profit

def get_current_balance(db_file):
    """Get the current SOL balance from the database."""
    try:
        if os.path.exists(db_file):
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Try to get the balance from the balance table if it exists
            try:
                cursor.execute("SELECT balance FROM balance ORDER BY timestamp DESC LIMIT 1")
                result = cursor.fetchone()
                if result:
                    return result[0]
            except:
                pass
            
            # If balance table doesn't exist, calculate from trades
            try:
                # Get all trades
                trades_df = pd.read_sql_query("SELECT * FROM trades", conn)
                
                if not trades_df.empty:
                    # Sum up buys and sells
                    buys = trades_df[trades_df['action'] == 'BUY']['amount'].sum()
                    sells = trades_df[trades_df['action'] == 'SELL']['amount'].sum()
                    
                    # Assume initial balance of 10 SOL if not specified
                    initial_balance = 10.0
                    
                    # Current balance is initial plus sells minus buys
                    return initial_balance + sells - buys
            except:
                pass
            
            conn.close()
    except Exception:
        pass
    
    # Fallback
    return 0.0

def display_enhanced_dashboard():
    """Display an enhanced dashboard with profit/loss, trade history, and more metrics."""
    st.set_page_config(
        page_title="Solana Trading Bot",
        page_icon="💸",
        layout="wide"
    )
    
    st.title("Solana Trading Bot - Enhanced Dashboard")
    
    # Load bot control settings
    control_file = 'data/bot_control.json'
    if not os.path.exists(control_file):
        control_file = 'bot_control.json'
        
    bot_settings = {}
    if os.path.exists(control_file):
        try:
            with open(control_file, 'r') as f:
                bot_settings = json.load(f)
        except:
            st.error(f"Could not load {control_file}")
    
    # Find database file
    db_file = 'data/sol_bot.db'
    if not os.path.exists(db_file):
        db_file = 'solana_trader.db'
    
    # Main dashboard metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Bot Status", 
                "Running ✅" if bot_settings.get('running', False) else "Stopped ⛔")
    
    with col2:
        st.metric("Mode", 
                "Simulation 🧪" if bot_settings.get('simulation_mode', True) else "Real Trading 💰")
    
    with col3:
        current_price = get_sol_price()
        st.metric("SOL Price", f"${current_price:.2f}")
    
    with col4:
        st.metric("Last Updated", time.strftime("%H:%M:%S ET"))
    
    # Try to load trades for metrics
    try:
        if os.path.exists(db_file):
            conn = sqlite3.connect(db_file)
            
            # Get all trades for calculations
            all_trades = pd.read_sql_query("SELECT * FROM trades", conn)
            
            # Create metrics columns
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # Calculate total profit/loss
                total_pl = calculate_profit_loss(all_trades)
                # Format color based on profit/loss
                color = "green" if total_pl > 0 else "red" if total_pl < 0 else "gray"
                st.markdown(f"<h3 style='color: {color}'>Total Profit/Loss</h3>", unsafe_allow_html=True)
                st.markdown(f"<h2 style='color: {color}'>${total_pl:.2f}</h2>", unsafe_allow_html=True)
            
            with col2:
                # Current SOL balance
                current_balance = get_current_balance(db_file)
                st.markdown("<h3>SOL Balance</h3>", unsafe_allow_html=True)
                st.markdown(f"<h2>{current_balance:.4f} SOL</h2>", unsafe_allow_html=True)
            
            with col3:
                # Number of trades
                num_trades = len(all_trades[all_trades['action'] == 'SELL'])
                st.markdown("<h3>Total Trades</h3>", unsafe_allow_html=True)
                st.markdown(f"<h2>{num_trades}</h2>", unsafe_allow_html=True)
            
            with col4:
                # Win rate
                win_rate = calculate_win_rate(all_trades)
                st.markdown("<h3>Win Rate</h3>", unsafe_allow_html=True)
                st.markdown(f"<h2>{win_rate:.1f}%</h2>", unsafe_allow_html=True)
            
            # Get active positions
            active_orders = pd.read_sql_query(
                "SELECT * FROM trades WHERE action='BUY' AND trade_id NOT IN (SELECT trade_id FROM trades WHERE action='SELL') ORDER BY timestamp DESC", 
                conn
            )
            
            # Create two columns for the next section
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Active Positions")
                if not active_orders.empty:
                    # Calculate current P/L for each position
                    active_orders['current_price'] = current_price
                    active_orders['unrealized_pl'] = (active_orders['current_price'] - active_orders['price']) * active_orders['amount']
                    active_orders['pl_percent'] = ((active_orders['current_price'] / active_orders['price']) - 1) * 100
                    
                    # Format the timestamp column
                    active_orders['formatted_time'] = active_orders['timestamp'].apply(convert_to_et)
                    
                    # Select and rename columns for display
                    display_columns = active_orders[['trade_id', 'formatted_time', 'price', 'amount', 'unrealized_pl', 'pl_percent']]
                    display_columns.columns = ['ID', 'Time (ET)', 'Buy Price', 'Amount', 'Unrealized P/L', 'P/L %']
                    
                    # Format the P/L columns
                    display_columns['Unrealized P/L'] = display_columns['Unrealized P/L'].map('${:.2f}'.format)
                    display_columns['P/L %'] = display_columns['P/L %'].map('{:.2f}%'.format)
                    
                    # Apply styling to the P/L columns
                    def color_pl(val):
                        try:
                            # For P/L % column
                            if '%' in val:
                                num = float(val.replace('%', ''))
                                if num > 0:
                                    return 'color: green'
                                elif num < 0:
                                    return 'color: red'
                            # For Unrealized P/L column
                            elif '$' in val:
                                num = float(val.replace('$', ''))
                                if num > 0:
                                    return 'color: green'
                                elif num < 0:
                                    return 'color: red'
                        except:
                            pass
                        return ''
                    
                    st.dataframe(display_columns.style.applymap(color_pl, subset=['Unrealized P/L', 'P/L %']), 
                               use_container_width=True)
                else:
                    st.info("No active positions")
            
            with col2:
                st.subheader("Trading Performance")
                
                # Get completed trades (buy-sell pairs)
                completed_trades = []
                
                buy_trades = all_trades[all_trades['action'] == 'BUY'].copy()
                sell_trades = all_trades[all_trades['action'] == 'SELL'].copy()
                
                for _, sell in sell_trades.iterrows():
                    matching_buys = buy_trades[buy_trades['trade_id'] == sell['trade_id']]
                    if not matching_buys.empty:
                        buy = matching_buys.iloc[0]
                        
                        # Calculate profit for this trade pair
                        buy_price = buy['price']
                        sell_price = sell['price']
                        amount = buy['amount']
                        profit = (sell_price - buy_price) * amount
                        profit_percent = ((sell_price / buy_price) - 1) * 100
                        
                        # Duration of the trade
                        buy_time = parse_timestamp(buy['timestamp'])
                        sell_time = parse_timestamp(sell['timestamp'])
                        duration = (sell_time - buy_time).total_seconds() / 60  # in minutes
                        
                        completed_trades.append({
                            'ID': buy['trade_id'],
                            'Buy Time': convert_to_et(buy['timestamp']),
                            'Sell Time': convert_to_et(sell['timestamp']),
                            'Buy Price': buy_price,
                            'Sell Price': sell_price,
                            'Amount': amount,
                            'Profit/Loss': profit,
                            'P/L %': profit_percent,
                            'Duration (min)': duration
                        })
                
                if completed_trades:
                    # Create a dataframe of completed trades
                    completed_df = pd.DataFrame(completed_trades)
                    
                    # Format the P/L columns
                    completed_df['Profit/Loss'] = completed_df['Profit/Loss'].map('${:.2f}'.format)
                    completed_df['P/L %'] = completed_df['P/L %'].map('{:.2f}%'.format)
                    
                    # Apply styling to the P/L columns
                    def color_pl(val):
                        try:
                            # For P/L % column
                            if '%' in val:
                                num = float(val.replace('%', ''))
                                if num > 0:
                                    return 'color: green'
                                elif num < 0:
                                    return 'color: red'
                            # For Profit/Loss column
                            elif '$' in val:
                                num = float(val.replace('$', ''))
                                if num > 0:
                                    return 'color: green'
                                elif num < 0:
                                    return 'color: red'
                        except:
                            pass
                        return ''
                    
                    st.dataframe(completed_df.style.applymap(color_pl, subset=['Profit/Loss', 'P/L %']), 
                               use_container_width=True)
                else:
                    st.info("No completed trades yet")
            
            # Recent trades
            st.subheader("Recent Trades")
            recent_trades = pd.read_sql_query("SELECT * FROM trades ORDER BY timestamp DESC LIMIT 20", conn)
            
            if not recent_trades.empty:
                # Format the timestamp column
                recent_trades['formatted_time'] = recent_trades['timestamp'].apply(convert_to_et)
                
                # Select and rename columns for display
                display_columns = recent_trades[['trade_id', 'action', 'formatted_time', 'price', 'amount']]
                display_columns.columns = ['ID', 'Action', 'Time (ET)', 'Price', 'Amount']
                
                # Define a styling function for the Action column
                def style_action(df):
                    styles = []
                    for val in df['Action']:
                        if val == 'BUY':
                            styles.append('background-color: green; color: white;')
                        elif val == 'SELL':
                            styles.append('background-color: red; color: white;')
                        else:
                            styles.append('')
                    return styles
                
                # Apply the styling to just the Action column
                styled_df = display_columns.copy()
                st.dataframe(styled_df, column_config={
                    "Action": st.column_config.Column(
                        "Action",
                        help="Buy or Sell transaction",
                        width="small",
                    )
                }, use_container_width=True)
                
                # Add CSV download button
                csv = display_columns.to_csv(index=False)
                st.download_button(
                    label="Download Recent Trades CSV",
                    data=csv,
                    file_name='recent_trades.csv',
                    mime='text/csv',
                )
            else:
                st.info("No trades found")
            
            conn.close()
        else:
            st.warning(f"Database file not found: {db_file}")
            
    except Exception as e:
        st.error(f"Error accessing database: {e}")
    
    # Display bot settings in an expandable section
    with st.expander("Bot Settings"):
        st.json(bot_settings)
    
    # Add refresh button with custom styling
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
    display_enhanced_dashboard()
