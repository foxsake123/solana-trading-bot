"""
Simple Dashboard for Solana Trading Bot - Core Functionality Only
"""
import streamlit as st
import pandas as pd
import os
import json
import sqlite3
from datetime import datetime
import plotly.graph_objects as go
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('simple_dashboard')

# Set page title and icon
st.set_page_config(
    page_title="Solana Trading Bot Dashboard",
    page_icon="💸",
    layout="wide",
)

# Simple dark theme CSS (minimal styling)
st.markdown("""
<style>
    .metric-card {
        background-color: #252525;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .main-metric {
        font-size: 24px;
        font-weight: bold;
    }
    .sub-metric {
        font-size: 16px;
        color: #BDBDBD;
    }
    .simulation-tag {
        background-color: #FF9800;
        color: black;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
    }
    .real-tag {
        background-color: #F44336;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
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
        "min_investment_per_token": 0.02,
        "max_investment_per_token": 0.1,
        "use_machine_learning": False,
        "MIN_SAFETY_SCORE": 15.0,
        "MIN_VOLUME": 10.0,
        "MIN_LIQUIDITY": 5000.0,
        "MIN_MCAP": 10000.0,
        "MIN_HOLDERS": 10,
        "MIN_PRICE_CHANGE_1H": 1.0,
        "MIN_PRICE_CHANGE_6H": 2.0,
        "MIN_PRICE_CHANGE_24H": 5.0
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

def get_trades_by_type(conn, is_simulation=True):
    """
    Get trades filtered by simulation/real status
    
    :param conn: Database connection
    :param is_simulation: Whether to get simulation trades (True) or real trades (False)
    :return: DataFrame of trades
    """
    try:
        # First determine if the 'is_simulation' column exists
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(trades)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'is_simulation' in columns:
            # If the column exists, filter by it
            query = f"SELECT * FROM trades WHERE is_simulation = {1 if is_simulation else 0} ORDER BY id DESC"
            trades_df = pd.read_sql_query(query, conn)
        else:
            # If the column doesn't exist, use contract address pattern
            query = "SELECT * FROM trades ORDER BY id DESC"
            all_trades = pd.read_sql_query(query, conn)
            
            # Define a function to check if a contract is a simulation contract
            def is_sim_contract(address):
                if not isinstance(address, str):
                    return False
                
                return (
                    address.startswith('Sim') or 
                    'TopGainer' in address or
                    'test' in address.lower() or
                    'simulation' in address.lower()
                )
            
            # Filter trades based on contract address
            if is_simulation:
                trades_df = all_trades[all_trades['contract_address'].apply(is_sim_contract)]
            else:
                trades_df = all_trades[~all_trades['contract_address'].apply(is_sim_contract)]
        
        return trades_df
    
    except Exception as e:
        logger.error(f"Error getting trades by type: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error

def get_active_positions(conn, is_simulation=True):
    """
    Get active positions filtered by simulation/real status
    
    :param conn: Database connection
    :param is_simulation: Whether to get simulation positions (True) or real positions (False)
    :return: DataFrame of active positions
    """
    try:
        # Get all trades
        trades_df = get_trades_by_type(conn, is_simulation)
        
        if trades_df.empty:
            return pd.DataFrame()
        
        # Calculate active positions
        active_positions = []
        
        for address, group in trades_df.groupby('contract_address'):
            buys = group[group['action'] == 'BUY']
            sells = group[group['action'] == 'SELL']
            
            # Calculate total bought and sold
            total_bought = buys['amount'].sum()
            total_sold = sells['amount'].sum() if not sells.empty else 0
            
            # If we have more bought than sold, this is an active position
            if total_bought > total_sold:
                # Calculate average buy price
                weighted_prices = (buys['amount'] * buys['price']).sum()
                avg_buy_price = weighted_prices / total_bought if total_bought > 0 else 0
                
                # Get the token name and ticker
                cursor = conn.cursor()
                ticker = address[:8]  # Default to first 8 chars
                name = f"Unknown {ticker}"
                
                try:
                    cursor.execute("SELECT ticker, name FROM tokens WHERE contract_address = ?", (address,))
                    token_info = cursor.fetchone()
                    if token_info:
                        ticker = token_info[0] or ticker
                        name = token_info[1] or name
                except:
                    pass
                
                # Add to active positions
                active_positions.append({
                    'contract_address': address,
                    'ticker': ticker,
                    'name': name,
                    'amount': total_bought - total_sold,
                    'avg_buy_price': avg_buy_price
                })
        
        # Convert to DataFrame
        if active_positions:
            return pd.DataFrame(active_positions)
        else:
            return pd.DataFrame()
    
    except Exception as e:
        logger.error(f"Error getting active positions: {e}")
        return pd.DataFrame()

def create_simple_pl_chart(trades_df, chart_title="Profit/Loss Over Time", line_color="cyan"):
    """Create a simplified P&L chart for the dashboard."""
    if trades_df.empty:
        # Return an empty figure
        fig = go.Figure()
        fig.update_layout(
            title=chart_title,
            xaxis_title="Date",
            yaxis_title="P&L (SOL)",
            height=400,
            template="plotly_dark"
        )
        return fig
        
    try:
        # Convert timestamp to datetime
        trades_df = trades_df.copy()
        if 'timestamp' in trades_df.columns:
            trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
        
        # Group by date and calculate daily P&L
        buys = trades_df[trades_df['action'] == 'BUY'].copy()
        sells = trades_df[trades_df['action'] == 'SELL'].copy()
        
        # Simple cumulative P&L calculation
        total_bought = buys['amount'].sum() if not buys.empty else 0
        total_sold = sells['amount'].sum() if not sells.empty else 0
        
        # Use naive P&L calculation for simplicity
        total_buy_value = (buys['amount'] * buys['price']).sum() if not buys.empty else 0
        total_sell_value = (sells['amount'] * sells['price']).sum() if not sells.empty else 0
        
        pl = total_sell_value - total_buy_value
        
        # Create a simple figure showing P&L
        fig = go.Figure()
        
        # Add a bar for P&L
        fig.add_trace(go.Bar(
            x=["Total P&L"],
            y=[pl],
            marker_color='green' if pl >= 0 else 'red',
            name="P&L (SOL)"
        ))
        
        # Update layout
        fig.update_layout(
            title=chart_title,
            yaxis_title="P&L (SOL)",
            height=400,
            template="plotly_dark"
        )
        
        return fig
    
    except Exception as e:
        logger.error(f"Error creating P&L chart: {e}")
        # Return an empty figure
        fig = go.Figure()
        fig.update_layout(
            title=chart_title,
            height=400,
            template="plotly_dark"
        )
        return fig

def main():
    """Main dashboard function - simplified for reliability"""
    st.title("💸 Solana Trading Bot - Simple Dashboard")
    
    # Load settings and find database
    bot_settings = load_bot_settings()
    db_file = find_database()
    
    # Create tabs for dashboard sections
    tabs = st.tabs(["Overview", "Trading Data", "Settings"])
    
    # Overview Tab
    with tabs[0]:
        st.subheader("Bot Status")
        
        # Create columns for status metrics
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Bot Status", 
                "Running ✅" if bot_settings.get('running', False) else "Stopped ⛔"
            )
        
        with col2:
            st.metric(
                "Mode", 
                "Simulation 🧪" if bot_settings.get('simulation_mode', True) else "Real Trading 💰"
            )
        
        # Load data from database
        trades_real = pd.DataFrame()
        trades_sim = pd.DataFrame()
        positions_real = pd.DataFrame()
        positions_sim = pd.DataFrame()
        
        if db_file and os.path.exists(db_file):
            try:
                # Connect to database
                conn = sqlite3.connect(db_file)
                
                # Get trades
                trades_real = get_trades_by_type(conn, is_simulation=False)
                trades_sim = get_trades_by_type(conn, is_simulation=True)
                
                # Get active positions
                positions_real = get_active_positions(conn, is_simulation=False)
                positions_sim = get_active_positions(conn, is_simulation=True)
                
                conn.close()
            except Exception as e:
                st.error(f"Error loading data from database: {e}")
        else:
            st.warning(f"Database file not found. Looked for: {db_file}")
        
        # Show simple stats
        st.subheader("Trading Stats")
        
        # Create columns for real and sim stats
        real_col, sim_col = st.columns(2)
        
        with real_col:
            st.markdown("#### Real Trading")
            
            # Count trades
            real_buys = len(trades_real[trades_real['action'] == 'BUY']) if not trades_real.empty else 0
            real_sells = len(trades_real[trades_real['action'] == 'SELL']) if not trades_real.empty else 0
            real_positions = len(positions_real) if not positions_real.empty else 0
            
            st.markdown(f"- Total Buys: {real_buys}")
            st.markdown(f"- Total Sells: {real_sells}")
            st.markdown(f"- Active Positions: {real_positions}")
            
            # Simple P&L chart
            pl_chart_real = create_simple_pl_chart(trades_real, chart_title="Real Trading P&L", line_color="lime")
            st.plotly_chart(pl_chart_real, use_container_width=True)
        
        with sim_col:
            st.markdown("#### Simulation")
            
            # Count trades
            sim_buys = len(trades_sim[trades_sim['action'] == 'BUY']) if not trades_sim.empty else 0
            sim_sells = len(trades_sim[trades_sim['action'] == 'SELL']) if not trades_sim.empty else 0
            sim_positions = len(positions_sim) if not positions_sim.empty else 0
            
            st.markdown(f"- Total Buys: {sim_buys}")
            st.markdown(f"- Total Sells: {sim_sells}")
            st.markdown(f"- Active Positions: {sim_positions}")
            
            # Simple P&L chart
            pl_chart_sim = create_simple_pl_chart(trades_sim, chart_title="Simulation P&L", line_color="cyan")
            st.plotly_chart(pl_chart_sim, use_container_width=True)
    
    # Trading Data Tab
    with tabs[1]:
        st.subheader("Trading Data")
        
        # Create subtabs for real and simulation data
        data_tabs = st.tabs(["Real Trading", "Simulation"])
        
        with data_tabs[0]:
            st.markdown("### Real Trading Data")
            
            # Show active positions
            st.subheader("Active Real Positions")
            
            if not positions_real.empty:
                st.dataframe(positions_real[['ticker', 'amount', 'avg_buy_price']], use_container_width=True)
            else:
                st.info("No active real positions")
            
            # Show recent trades
            st.subheader("Recent Real Trades")
            
            if not trades_real.empty:
                # Display recent trades, limited to 20 rows
                st.dataframe(trades_real.head(20), use_container_width=True)
            else:
                st.info("No real trades recorded")
        
        with data_tabs[1]:
            st.markdown("### Simulation Data")
            
            # Show active positions
            st.subheader("Active Simulation Positions")
            
            if not positions_sim.empty:
                st.dataframe(positions_sim[['ticker', 'amount', 'avg_buy_price']], use_container_width=True)
            else:
                st.info("No active simulation positions")
            
            # Show recent trades
            st.subheader("Recent Simulation Trades")
            
            if not trades_sim.empty:
                # Display recent trades, limited to 20 rows
                st.dataframe(trades_sim.head(20), use_container_width=True)
            else:
                st.info("No simulation trades recorded")
    
    # Settings Tab
    with tabs[2]:
        st.subheader("Bot Settings")
        
        # Core settings
        st.markdown("### Core Settings")
        
        # Bot running toggle
        bot_running = st.checkbox(
            "Bot Running",
            value=bot_settings.get('running', False),
            help="Start or stop the trading bot"
        )
        
        # Simulation mode toggle
        simulation_mode = st.checkbox(
            "Simulation Mode",
            value=bot_settings.get('simulation_mode', True),
            help="Toggle between simulation and real trading mode"
        )
        
        # Save settings button
        if st.button("Save Core Settings"):
            # Update settings
            bot_settings['running'] = bot_running
            bot_settings['simulation_mode'] = simulation_mode
            
            # Save settings
            if save_bot_settings(bot_settings):
                st.success("Settings saved successfully!")
            else:
                st.error("Failed to save settings")
        
        # Trading parameters
        st.markdown("### Trading Parameters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Convert take_profit from decimal to percentage if needed
            take_profit_value = bot_settings.get('take_profit_target', 50.0)
            if take_profit_value < 1.0:  # If it's stored as decimal (0.15 instead of 15.0)
                take_profit_value = take_profit_value * 100
                
            take_profit = st.number_input(
                "Take Profit (%)",
                min_value=1.0,
                max_value=1000.0,
                value=float(take_profit_value),
                step=5.0
            )
            
            # Convert stop_loss from decimal to percentage if needed
            stop_loss_value = bot_settings.get('stop_loss_percentage', 25.0)
            if stop_loss_value < 1.0:  # If it's stored as decimal (0.25 instead of 25.0)
                stop_loss_value = stop_loss_value * 100
                
            stop_loss = st.number_input(
                "Stop Loss (%)",
                min_value=1.0,
                max_value=100.0,
                value=float(stop_loss_value),
                step=1.0
            )
        
        with col2:
            min_investment = st.number_input(
                "Min Investment (SOL)",
                min_value=0.001,
                max_value=1.0,
                value=float(bot_settings.get('min_investment_per_token', 0.02)),
                step=0.001
            )
            
            max_investment = st.number_input(
                "Max Investment (SOL)",
                min_value=0.01,
                max_value=10.0,
                value=float(bot_settings.get('max_investment_per_token', 0.1)),
                step=0.01
            )
        
        # Save trading parameters button
        if st.button("Save Trading Parameters"):
            # Update settings
            bot_settings['take_profit_target'] = take_profit / 100  # Convert back to decimal
            bot_settings['stop_loss_percentage'] = stop_loss / 100  # Convert back to decimal
            bot_settings['min_investment_per_token'] = min_investment
            bot_settings['max_investment_per_token'] = max_investment
            
            # Save settings
            if save_bot_settings(bot_settings):
                st.success("Trading parameters saved successfully!")
            else:
                st.error("Failed to save trading parameters")
    
    # Add refresh button at the bottom
    if st.button("Refresh Dashboard"):
        st.experimental_rerun()
    
    # Add timestamp for last update
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
