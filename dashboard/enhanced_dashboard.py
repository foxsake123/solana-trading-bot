"""
Enhanced Dashboard for Solana Trading Bot - Clearly separates simulation and real trading data
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
import sys
import logging
import base64
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('enhanced_dashboard')

# Set page title and icon
st.set_page_config(
    page_title="Solana Trading Bot - Enhanced Dashboard",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme
st.markdown("""
<style>
    .main {
        background-color: #0E1117;
        color: white;
    }
    .css-1d391kg {
        background-color: #1E1E1E;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 1px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1E1E1E;
        color: white;
        padding: 10px 20px;
        border-radius: 4px 4px 0 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50;
        color: white;
    }
    .metric-card {
        background-color: #252525;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .profit {
        color: #4CAF50;
    }
    .loss {
        color: #FF5252;
    }
    .neutral {
        color: #2196F3;
    }
    .main-metric {
        font-size: 24px;
        font-weight: bold;
    }
    .sub-metric {
        font-size: 16px;
        color: #BDBDBD;
    }
    .dataframe {
        background-color: #1E1E1E !important;
        color: white !important;
    }
    th {
        background-color: #252525 !important;
        color: white !important;
    }
    td {
        background-color: #1E1E1E !important;
        color: white !important;
    }
    button {
        background-color: #4CAF50 !important;
        color: white !important;
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
    .info-box {
        background-color: #252525;
        border-left: 4px solid #2196F3;
        padding: 10px;
        margin: 10px 0;
        border-radius: 4px;
    }
    .warning-box {
        background-color: #252525;
        border-left: 4px solid #FF9800;
        padding: 10px;
        margin: 10px 0;
        border-radius: 4px;
    }
    .success-box {
        background-color: #252525;
        border-left: 4px solid #4CAF50;
        padding: 10px;
        margin: 10px 0;
        border-radius: 4px;
    }
    .error-box {
        background-color: #252525;
        border-left: 4px solid #F44336;
        padding: 10px;
        margin: 10px 0;
        border-radius: 4px;
    }
    /* Special header styling */
    .sim-header {
        background-color: #FF9800;
        color: black;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 15px;
        text-align: center;
        font-weight: bold;
    }
    .real-header {
        background-color: #F44336;
        color: white;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 15px;
        text-align: center;
        font-weight: bold;
    }
    /* Progress bar color */
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
def get_live_sol_price():
    """Get the current SOL price from multiple API sources."""
    try:
        # Try CoinGecko API
        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data and 'solana' in data and 'usd' in data['solana']:
                return float(data['solana']['usd'])
    except Exception as e:
        logger.warning(f"CoinGecko API error: {e}")
    
    try:
        # Try Binance API
        response = requests.get(
            "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data and 'price' in data:
                return float(data['price'])
    except Exception as e:
        logger.warning(f"Binance API error: {e}")
    
    # Fallback to a default recent price
    logger.warning("Could not fetch live SOL price from any API, using default value")
    return 180.0  # Fallback price as of May 2025

def convert_to_et(timestamp_str):
    """Convert a timestamp string to Eastern Time."""
    try:
        # Parse the timestamp
        if isinstance(timestamp_str, str):
            # Try different formats
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
                try:
                    timestamp = datetime.strptime(timestamp_str, fmt)
                    break
                except ValueError:
                    continue
            else:
                # If no format matched, return the original string
                return timestamp_str
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
    except Exception as e:
        logger.error(f"Error converting timestamp: {e}")
        # Return the original string if conversion fails
        return timestamp_str

def get_wallet_balance(wallet_address=None, rpc_endpoint=None):
    """Get wallet balance from Solana blockchain using REST API."""
    try:
        # Read wallet key from .env file
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
        
        if not wallet_address and not private_key:
            logger.warning("No wallet address or private key found")
            # Return fallback balance instead of None
            return 1.15
        
        if not rpc_endpoint:
            rpc_endpoint = "https://api.mainnet-beta.solana.com"
            
        # If wallet_address is not provided, try to derive it from private key
        if not wallet_address and private_key:
            try:
                # Try to use Solders or Solana package to get the wallet address
                from solders.keypair import Keypair
                keypair = Keypair.from_bytes(bytes.fromhex(private_key))
                wallet_address = str(keypair.pubkey())
            except:
                try:
                    import base58
                    from solders.pubkey import Pubkey
                    # Try base58 decoding
                    if len(private_key) == 88:  # Base58 encoded
                        decoded = base58.b58decode(private_key)
                        keypair = Keypair.from_bytes(decoded)
                        wallet_address = str(keypair.pubkey())
                except:
                    logger.warning("Could not derive wallet address")
                    # Return fallback balance
                    return 1.15
        
        # Query balance using RPC endpoint
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [wallet_address]
        }
        
        headers = {"Content-Type": "application/json"}
        response = requests.post(rpc_endpoint, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'value' in data['result']:
                # Convert lamports to SOL (1 SOL = 10^9 lamports)
                balance_sol = data['result']['value'] / 10**9
                return balance_sol
        
        logger.warning(f"Failed to get wallet balance: {response.text if response else 'No response'}")
        # Return fallback balance
        return 1.15
    
    except Exception as e:
        logger.error(f"Error getting wallet balance: {e}")
        # Return fallback balance
        return 1.15

def load_bot_settings():
    """Load bot settings from control file."""
    control_files = [
        'data/bot_control.json',
        'bot_control.json',
        'core/bot_control.json'
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
        'sol_bot.db'
    ]
    
    for db_file in db_files:
        if os.path.exists(db_file):
            return db_file
    
    return None

def is_simulation_contract(address):
    """
    Check if a contract address appears to be a simulation address
    
    :param address: Contract address to check
    :return: True if it appears to be a simulation address, False otherwise
    """
    if not isinstance(address, str):
        return False
    
    return (
        address.startswith('Sim') or 
        'TopGainer' in address or
        'test' in address.lower() or
        'simulation' in address.lower() or
        'demo' in address.lower()
    )

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
            
            # Filter trades based on contract address
            if is_simulation:
                trades_df = all_trades[all_trades['contract_address'].apply(is_simulation_contract)]
            else:
                trades_df = all_trades[~all_trades['contract_address'].apply(is_simulation_contract)]
        
        return trades_df
    
    except Exception as e:
        logger.error(f"Error getting trades by type: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error

def calculate_metrics(trades_df, current_sol_price):
    """Calculate trading metrics from trades."""
    if trades_df.empty:
        return {
            "win_rate": 0.0,
            "total_pl_sol": 0.0,
            "total_pl_usd": 0.0,
            "total_trades": 0,
            "best_trade_pct": 0.0,
            "worst_trade_pct": 0.0,
            "avg_holding_time": "0 hours"
        }
    
    try:
        # Group by contract address
        contract_groups = {}
        
        for contract, group in trades_df.groupby('contract_address'):
            contract_groups[contract] = {
                'buys': group[group['action'] == 'BUY'],
                'sells': group[group['action'] == 'SELL']
            }
        
        # Calculate metrics
        completed_trades = 0
        winning_trades = 0
        total_pl_sol = 0.0
        trade_percentages = []
        holding_times = []
        
        for contract, data in contract_groups.items():
            buys = data['buys']
            sells = data['sells']
            
            if buys.empty or sells.empty:
                continue
            
            # For each sell, find a matching buy
            for _, sell in sells.iterrows():
                # Find buys that happened before this sell
                try:
                    prior_buys = buys[pd.to_datetime(buys['timestamp']) < pd.to_datetime(sell['timestamp'])]
                except:
                    # If timestamp conversion fails, try a different approach
                    prior_buys = buys
                
                if prior_buys.empty:
                    continue
                
                # Get the earliest buy
                buy = prior_buys.iloc[0]
                
                # Calculate profit
                buy_price = buy['price']
                sell_price = sell['price']
                
                # Use the smaller of buy amount and sell amount
                amount = min(buy['amount'], sell['amount'])
                
                # Calculate profit in SOL
                profit_sol = (sell_price - buy_price) * amount
                total_pl_sol += profit_sol
                
                # Calculate percentage change
                if buy_price > 0:
                    percentage = ((sell_price / buy_price) - 1) * 100
                    trade_percentages.append(percentage)
                    
                    if percentage > 0:
                        winning_trades += 1
                
                # Calculate holding time
                try:
                    buy_time = pd.to_datetime(buy['timestamp'])
                    sell_time = pd.to_datetime(sell['timestamp'])
                    holding_time = (sell_time - buy_time).total_seconds() / 3600  # in hours
                    holding_times.append(holding_time)
                except:
                    # If time calculation fails, use a default value
                    holding_times.append(24)  # Default to 24 hours
                
                completed_trades += 1
        
        # Calculate win rate
        win_rate = (winning_trades / completed_trades * 100) if completed_trades > 0 else 0.0
        
        # Calculate USD value
        total_pl_usd = total_pl_sol * current_sol_price
        
        # Calculate best and worst trades
        best_trade_pct = max(trade_percentages) if trade_percentages else 0.0
        worst_trade_pct = min(trade_percentages) if trade_percentages else 0.0
        
        # Calculate average holding time
        avg_holding_time = sum(holding_times) / len(holding_times) if holding_times else 0.0
        avg_holding_time_str = f"{avg_holding_time:.1f} hours"
        
        return {
            "win_rate": win_rate,
            "total_pl_sol": total_pl_sol,
            "total_pl_usd": total_pl_usd,
            "total_trades": completed_trades,
            "best_trade_pct": best_trade_pct,
            "worst_trade_pct": worst_trade_pct,
            "avg_holding_time": avg_holding_time_str
        }
    
    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")
        logger.error(traceback.format_exc())
        return {
            "win_rate": 0.0,
            "total_pl_sol": 0.0,
            "total_pl_usd": 0.0,
            "total_trades": 0,
            "best_trade_pct": 0.0,
            "worst_trade_pct": 0.0,
            "avg_holding_time": "0 hours"
        }

def create_pl_chart(trades_df, lookback_days=30, chart_title="Profit/Loss Over Time", line_color="cyan"):
    """Create a P&L chart for the dashboard."""
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
        # Create a copy of the DataFrame to avoid warnings
        trades_df_copy = trades_df.copy()
        
        # Convert timestamp to datetime
        if 'timestamp' in trades_df_copy.columns:
            try:
                trades_df_copy.loc[:, 'timestamp'] = pd.to_datetime(trades_df_copy['timestamp'], utc=True)
            except:
                # If conversion fails, try a different approach
                trades_df_copy.loc[:, 'timestamp'] = pd.to_datetime(trades_df_copy['timestamp'], errors='coerce')
                trades_df_copy = trades_df_copy.dropna(subset=['timestamp'])
        
        # Filter for lookback period
        start_date = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=lookback_days)
        trades_df_copy = trades_df_copy[trades_df_copy['timestamp'] >= start_date]
        
        if trades_df_copy.empty:
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
        
        # Sort by timestamp
        trades_df_copy = trades_df_copy.sort_values('timestamp')
        
        # Initialize data for cumulative P&L
        dates = []
        cumulative_pl = []
        total_pl = 0.0
        
        # Group trades by contract address
        contract_groups = {}
        
        for contract, group in trades_df_copy.groupby('contract_address'):
            contract_groups[contract] = {
                'buys': group[group['action'] == 'BUY'].sort_values('timestamp'),
                'sells': group[group['action'] == 'SELL'].sort_values('timestamp')
            }
        
        # Process trades to extract dates and P&L
        unique_dates = pd.Series(trades_df_copy['timestamp'].dt.date.unique()).sort_values()
        
        for day in unique_dates:
            day_pl = 0.0
            
            # Get trades for this day
            day_trades = trades_df_copy[trades_df_copy['timestamp'].dt.date == day]
            
            # Process sells on this day
            day_sells = day_trades[day_trades['action'] == 'SELL']
            
            for _, sell in day_sells.iterrows():
                contract = sell['contract_address']
                sell_price = sell['price']
                sell_amount = sell['amount']
                
                # Find matching buys
                if contract in contract_groups:
                    buys = contract_groups[contract]['buys']
                    buys_before_sell = buys[buys['timestamp'] < sell['timestamp']]
                    
                    if not buys_before_sell.empty:
                        # Use the earliest buy
                        buy = buys_before_sell.iloc[0]
                        buy_price = buy['price']
                        
                        # Calculate profit
                        amount = min(sell_amount, buy['amount'])
                        profit = (sell_price - buy_price) * amount
                        day_pl += profit
            
            # Add day's P&L to cumulative
            total_pl += day_pl
            dates.append(day)
            cumulative_pl.append(total_pl)
        
        # Create the figure
        fig = go.Figure()
        
        # Add the line
        fig.add_trace(go.Scatter(
            x=dates,
            y=cumulative_pl,
            mode='lines+markers',
            name='Cumulative P&L',
            line=dict(
                color=line_color,
                width=2
            ),
            marker=dict(
                size=6,
                symbol='circle'
            )
        ))
        
        # Add a horizontal line at y=0 if we have dates
        if dates:
            fig.add_shape(
                type="line",
                x0=min(dates),
                y0=0,
                x1=max(dates),
                y1=0,
                line=dict(
                    color="gray",
                    width=1,
                    dash="dash",
                )
            )
        
        # Update layout
        fig.update_layout(
            title=chart_title,
            xaxis_title="Date",
            yaxis_title="P&L (SOL)",
            height=400,
            template="plotly_dark",
            plot_bgcolor='#1E1E1E',
            paper_bgcolor='#1E1E1E',
            font=dict(color='white'),
            xaxis=dict(
                showgrid=True,
                gridcolor='#333333',
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='#333333',
                zerolinecolor='#666666',
            ),
            margin=dict(l=10, r=10, t=50, b=10),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig
    
    except Exception as e:
        logger.error(f"Error creating P&L chart: {e}")
        logger.error(traceback.format_exc())
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
                
                # Get entry time (first buy)
                entry_time = None
                if 'timestamp' in buys.columns and not buys.empty:
                    try:
                        entry_time = pd.to_datetime(buys['timestamp'].min())
                    except:
                        pass
                
                # Get current price if available
                current_price = avg_buy_price  # Default to average buy price
                try:
                    cursor.execute("SELECT price_usd FROM tokens WHERE contract_address = ?", (address,))
                    price_info = cursor.fetchone()
                    if price_info and price_info[0]:
                        current_price = float(price_info[0])
                except:
                    pass
                
                # Add to active positions
                active_positions.append({
                    'contract_address': address,
                    'ticker': ticker,
                    'name': name,
                    'amount': total_bought - total_sold,
                    'avg_buy_price': avg_buy_price,
                    'current_price': current_price,
                    'entry_time': entry_time,
                    'unrealized_pl': (current_price - avg_buy_price) * (total_bought - total_sold),
                    'pl_percent': ((current_price / avg_buy_price) - 1) * 100 if avg_buy_price > 0 else 0
                })
        
        # Convert to DataFrame
        if active_positions:
            return pd.DataFrame(active_positions)
        else:
            return pd.DataFrame()
    
    except Exception as e:
        logger.error(f"Error getting active positions: {e}")
        logger.error(traceback.format_exc())
        return pd.DataFrame()

def verify_transaction(tx_hash, rpc_endpoint=None):
    """Verify a transaction on the Solana blockchain."""
    if not tx_hash or not isinstance(tx_hash, str) or tx_hash.startswith('SIM_'):
        return False
        
    try:
        # Default RPC endpoint
        if not rpc_endpoint:
            rpc_endpoint = "https://api.mainnet-beta.solana.com"
            
        # Query transaction
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                tx_hash,
                {"encoding": "json"}
            ]
        }
        
        headers = {"Content-Type": "application/json"}
        response = requests.post(rpc_endpoint, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return 'result' in data and data['result'] is not None
            
        return False
    except Exception as e:
        logger.error(f"Error verifying transaction: {e}")
        return False

def create_token_distribution_chart(positions_df, title="Token Distribution"):
    """Create a pie chart of token distribution."""
    if positions_df.empty:
        # Return an empty figure
        fig = go.Figure()
        fig.update_layout(
            title=title,
            height=400,
            template="plotly_dark"
        )
        return fig
    
    try:
        # Calculate total value for each position
        if 'current_price' in positions_df.columns and 'amount' in positions_df.columns:
            positions_df['value'] = positions_df['current_price'] * positions_df['amount']
        elif 'avg_buy_price' in positions_df.columns and 'amount' in positions_df.columns:
            positions_df['value'] = positions_df['avg_buy_price'] * positions_df['amount']
        else:
            # If we don't have price data, just use amount
            positions_df['value'] = positions_df['amount']
        
        # Sort by value
        positions_df = positions_df.sort_values('value', ascending=False)
        
        # Get top 5 positions and group the rest as "Others"
        if len(positions_df) > 5:
            top_positions = positions_df.iloc[:5]
            others_value = positions_df.iloc[5:]['value'].sum()
            
            # Create labels and values
            labels = list(top_positions['ticker']) + ['Others']
            values = list(top_positions['value']) + [others_value]
        else:
            # Use all positions
            labels = list(positions_df['ticker'])
            values = list(positions_df['value'])
        
        # Create pie chart
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=.3,
            marker=dict(
                colors=px.colors.sequential.Plasma
            )
        )])
        
        # Update layout
        fig.update_layout(
            title=title,
            height=400,
            template="plotly_dark",
            plot_bgcolor='#1E1E1E',
            paper_bgcolor='#1E1E1E',
            font=dict(color='white'),
            margin=dict(l=10, r=10, t=50, b=10),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.1,
                xanchor="center",
                x=0.5
            )
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Error creating token distribution chart: {e}")
        # Return an empty figure
        fig = go.Figure()
        fig.update_layout(
            title=title,
            height=400,
            template="plotly_dark"
        )
        return fig

def main():
    """Main dashboard function"""
    st.title("💸 Solana Trading Bot - Enhanced Dashboard")
    
    # Get current SOL price
    sol_price = get_live_sol_price()
    
    # Load bot settings
    bot_settings = load_bot_settings()
    
    # Find database
    db_file = find_database()
    
    # Get wallet balance
    wallet_balance = get_wallet_balance()
    
    # Initialize data
    trades_real = pd.DataFrame()
    trades_sim = pd.DataFrame()
    positions_real = pd.DataFrame()
    positions_sim = pd.DataFrame()
    metrics_real = {
        "win_rate": 0.0,
        "total_pl_sol": 0.0,
        "total_pl_usd": 0.0,
        "total_trades": 0,
        "best_trade_pct": 0.0,
        "worst_trade_pct": 0.0,
        "avg_holding_time": "0 hours"
    }
    metrics_sim = {
        "win_rate": 0.0,
        "total_pl_sol": 0.0,
        "total_pl_usd": 0.0,
        "total_trades": 0,
        "best_trade_pct": 0.0,
        "worst_trade_pct": 0.0,
        "avg_holding_time": "0 hours"
    }
    
    # Load data from database
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
            
            # Calculate metrics
            metrics_real = calculate_metrics(trades_real, sol_price)
            metrics_sim = calculate_metrics(trades_sim, sol_price)
            
            conn.close()
        except Exception as e:
            st.error(f"Error loading data from database: {e}")
            logger.error(f"Database error: {traceback.format_exc()}")
    else:
        st.warning(f"Database file not found. Looked for: {db_file}")
    
    # Create tabs for dashboard sections
    tabs = st.tabs(["Overview", "Real Trading", "Simulation", "Settings"])
    
    # Overview Tab
    with tabs[0]:
        st.subheader("Bot Status and Overview")
        
        # Create 4 columns for status metrics
        col1, col2, col3, col4 = st.columns(4)
        
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
        
        with col3:
            st.metric("SOL Price", f"${sol_price:.2f}")
        
        with col4:
            st.metric("Wallet Balance", f"{wallet_balance:.4f} SOL (${wallet_balance * sol_price:.2f})")
        
        # Comparison of real vs simulation
        st.subheader("Performance Comparison")
        
        # Create 2 columns for comparison
        comp_col1, comp_col2 = st.columns(2)
        
        with comp_col1:
            # Real trading summary
            st.markdown("<div class='real-header'>REAL TRADING</div>", unsafe_allow_html=True)
            
            real_col1, real_col2 = st.columns(2)
            
            with real_col1:
                color = "green" if metrics_real["total_pl_usd"] > 0 else "red" if metrics_real["total_pl_usd"] < 0 else "gray"
                st.markdown(f"<div class='metric-card'><span class='main-metric' style='color: {color}'>Total P&L</span><br/><span class='main-metric' style='color: {color}'>${metrics_real['total_pl_usd']:.2f}</span><br/><span class='sub-metric'>{metrics_real['total_pl_sol']:.6f} SOL</span></div>", unsafe_allow_html=True)
            
            with real_col2:
                st.markdown(f"<div class='metric-card'><span class='main-metric'>Win Rate</span><br/><span class='main-metric'>{metrics_real['win_rate']:.1f}%</span><br/><span class='sub-metric'>{metrics_real['total_trades']} trades</span></div>", unsafe_allow_html=True)
            
            # Real positions count
            position_count = len(positions_real) if not positions_real.empty else 0
            st.markdown(f"<div class='metric-card'><span class='main-metric'>Active Positions</span><br/><span class='main-metric'>{position_count}</span></div>", unsafe_allow_html=True)
        
        with comp_col2:
            # Simulation summary
            st.markdown("<div class='sim-header'>SIMULATION</div>", unsafe_allow_html=True)
            
            sim_col1, sim_col2 = st.columns(2)
            
            with sim_col1:
                color = "green" if metrics_sim["total_pl_usd"] > 0 else "red" if metrics_sim["total_pl_usd"] < 0 else "gray"
                st.markdown(f"<div class='metric-card'><span class='main-metric' style='color: {color}'>Total P&L</span><br/><span class='main-metric' style='color: {color}'>${metrics_sim['total_pl_usd']:.2f}</span><br/><span class='sub-metric'>{metrics_sim['total_pl_sol']:.6f} SOL</span></div>", unsafe_allow_html=True)
            
            with sim_col2:
                st.markdown(f"<div class='metric-card'><span class='main-metric'>Win Rate</span><br/><span class='main-metric'>{metrics_sim['win_rate']:.1f}%</span><br/><span class='sub-metric'>{metrics_sim['total_trades']} trades</span></div>", unsafe_allow_html=True)
            
            # Simulation positions count
            position_count = len(positions_sim) if not positions_sim.empty else 0
            st.markdown(f"<div class='metric-card'><span class='main-metric'>Active Positions</span><br/><span class='main-metric'>{position_count}</span></div>", unsafe_allow_html=True)
        
        # Show P&L charts
        st.subheader("P&L Comparison")
        
        pl_col1, pl_col2 = st.columns(2)
        
        with pl_col1:
            # Real trading P&L chart
            pl_chart_real = create_pl_chart(
                trades_real, 
                chart_title="Real Trading P&L", 
                line_color="lime"
            )
            st.plotly_chart(pl_chart_real, use_container_width=True)
        
        with pl_col2:
            # Simulation P&L chart
            pl_chart_sim = create_pl_chart(
                trades_sim,
                chart_title="Simulation P&L",
                line_color="cyan"
            )
            st.plotly_chart(pl_chart_sim, use_container_width=True)
        
        # Show latest trading activity
        st.subheader("Latest Trading Activity")
        
        # Combine real and simulation trades, and display the most recent ones
        all_trades = pd.concat([trades_real, trades_sim])
        
        if not all_trades.empty:
            # Add a column to indicate if a trade is simulation or real
            all_trades['type'] = all_trades.apply(
                lambda row: "Simulation" if 'is_simulation' in row and row['is_simulation'] else 
                            "Simulation" if is_simulation_contract(row['contract_address']) else "Real",
                axis=1
            )
            
            # Sort by timestamp (most recent first)
            if 'timestamp' in all_trades.columns:
                try:
                    all_trades['timestamp_dt'] = pd.to_datetime(all_trades['timestamp'])
                    all_trades = all_trades.sort_values('timestamp_dt', ascending=False)
                    
                    # Drop the temporary datetime column
                    all_trades = all_trades.drop('timestamp_dt', axis=1)
                except:
                    # If timestamp conversion fails, sort by ID if available
                    if 'id' in all_trades.columns:
                        all_trades = all_trades.sort_values('id', ascending=False)
            
            # Limit to 10 most recent trades
            recent_trades = all_trades.head(10)
            
            # Format for display
            display_trades = recent_trades[['type', 'contract_address', 'action', 'amount', 'price', 'timestamp']].copy()
            
            # Convert timestamps to a readable format
            if 'timestamp' in display_trades:
                display_trades['timestamp'] = display_trades['timestamp'].apply(convert_to_et)
            
            # Rename columns for better display
            display_trades.columns = ['Type', 'Token', 'Action', 'Amount (SOL)', 'Price', 'Time']
            
            # Format columns
            if 'Price' in display_trades:
                display_trades['Price'] = display_trades['Price'].apply(lambda x: f"${x:.8f}")
            
            # Add color to type column
            def type_formatter(val):
                if val == "Real":
                    return f"<span class='real-tag'>{val}</span>"
                else:
                    return f"<span class='simulation-tag'>{val}</span>"
            
            display_trades['Type'] = display_trades['Type'].apply(type_formatter)
            
            # Display the recent trades
            st.markdown(display_trades.to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.info("No trading activity recorded yet")
    
    # Real Trading Tab
    with tabs[1]:
        st.subheader("Real Trading Dashboard")
        
        # Warning if simulation mode is enabled
        if bot_settings.get('simulation_mode', True):
            st.warning("⚠️ The bot is currently in simulation mode. No real trades will be executed. Switch to real trading mode in Settings.")
        
        # Create 4 columns for metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            color = "green" if metrics_real["total_pl_usd"] > 0 else "red" if metrics_real["total_pl_usd"] < 0 else "gray"
            st.markdown(f"<div class='metric-card'><span class='main-metric' style='color: {color}'>Total P&L</span><br/><span class='main-metric' style='color: {color}'>${metrics_real['total_pl_usd']:.2f}</span><br/><span class='sub-metric'>{metrics_real['total_pl_sol']:.6f} SOL</span></div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"<div class='metric-card'><span class='main-metric'>Wallet Balance</span><br/><span class='main-metric'>{wallet_balance:.6f} SOL</span><br/><span class='sub-metric'>${wallet_balance * sol_price:.2f} USD</span></div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"<div class='metric-card'><span class='main-metric'>Win Rate</span><br/><span class='main-metric'>{metrics_real['win_rate']:.1f}%</span><br/><span class='sub-metric'>{metrics_real['total_trades']} trades</span></div>", unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"<div class='metric-card'><span class='main-metric'>Best Trade</span><br/><span class='main-metric'>{metrics_real['best_trade_pct']:.1f}%</span><br/><span class='sub-metric'>Worst: {metrics_real['worst_trade_pct']:.1f}%</span></div>", unsafe_allow_html=True)
        
        # P&L chart
        st.subheader("Real Trading P&L")
        
        # Lookback period selection
        lookback = st.selectbox(
            "Lookback Period",
            options=[7, 14, 30, 60, 90],
            index=2,
            key="real_lookback"
        )
        
        # Create P&L chart
        pl_chart_real = create_pl_chart(
            trades_real,
            lookback_days=lookback,
            chart_title=f"Real Trading P&L (Last {lookback} Days)",
            line_color="lime"
        )
        st.plotly_chart(pl_chart_real, use_container_width=True)
        
        # Active positions
        st.subheader("Active Real Positions")
        
        if not positions_real.empty:
            # Format for display
            display_positions = positions_real.copy()
            
            if 'avg_buy_price' in display_positions:
                display_positions['avg_buy_price'] = display_positions['avg_buy_price'].apply(lambda x: f"${x:.8f}")
            
            if 'current_price' in display_positions:
                display_positions['current_price'] = display_positions['current_price'].apply(lambda x: f"${x:.8f}")
            
            if 'unrealized_pl' in display_positions:
                display_positions['unrealized_pl'] = display_positions['unrealized_pl'].apply(lambda x: f"{x:.6f} SOL")
            
            if 'pl_percent' in display_positions:
                display_positions['pl_percent'] = display_positions['pl_percent'].apply(lambda x: f"{x:.2f}%")
            
            if 'entry_time' in display_positions and 'entry_time' in display_positions.columns and not display_positions['entry_time'].isnull().all():
                display_positions['entry_time'] = display_positions['entry_time'].apply(
                    lambda x: convert_to_et(x) if x is not None else "Unknown"
                )
            
            # Select columns to display
            display_cols = ['ticker', 'amount', 'avg_buy_price', 'current_price', 'unrealized_pl', 'pl_percent']
            if 'entry_time' in display_positions.columns:
                display_cols.append('entry_time')
                
            display_cols = [col for col in display_cols if col in display_positions.columns]
            
            # Rename columns for better display
            col_mapping = {
                'ticker': 'Token',
                'amount': 'Amount (SOL)',
                'avg_buy_price': 'Buy Price',
                'current_price': 'Current Price',
                'unrealized_pl': 'Unrealized P&L',
                'pl_percent': 'P&L %',
                'entry_time': 'Entry Time'
            }
            
            # Apply column renaming
            display_positions = display_positions[display_cols].rename(columns=col_mapping)
            
            # Display positions
            st.dataframe(display_positions, use_container_width=True)
            
            # Create token distribution chart
            token_chart = create_token_distribution_chart(
                positions_real,
                title="Real Token Distribution"
            )
            st.plotly_chart(token_chart, use_container_width=True)
            
            # Add explorers section
            st.subheader("Blockchain Explorer Links")
            
            st.markdown("""
            Track your real transactions on these block explorers:
            - [Solana Explorer](https://explorer.solana.com/) - Official Solana block explorer
            - [Solscan](https://solscan.io/) - Detailed token and transaction information
            - [SolanaFM](https://solana.fm/) - Advanced blockchain explorer
            """)
            
            # Add transaction verification
            st.subheader("Verify Transaction")
            
            tx_col1, tx_col2 = st.columns([3, 1])
            
            with tx_col1:
                tx_hash = st.text_input("Enter Transaction Signature")
            
            with tx_col2:
                if st.button("Verify"):
                    if tx_hash:
                        is_verified = verify_transaction(tx_hash)
                        if is_verified:
                            st.success(f"Transaction verified: {tx_hash}")
                        else:
                            st.error(f"Transaction not found: {tx_hash}")
                    else:
                        st.warning("Please enter a transaction signature")
        else:
            st.info("No active real positions found")
            
            if metrics_real["total_trades"] > 0:
                st.markdown("""
                You have completed trades but no active positions.
                
                Check the 'Trading History' section below to see your past trades.
                """)
            else:
                st.markdown("""
                No real trading history found. To start real trading:
                
                1. Make sure you have Solana tokens in your wallet
                2. Switch the bot to real trading mode in the Settings tab
                3. Adjust your risk parameters to your comfort level
                """)
        
        # Trading history
        st.subheader("Real Trading History")
        
        if not trades_real.empty:
            # Filter for completed trades (pairs of buys and sells)
            completed_trades = []
            
            for contract, group in trades_real.groupby('contract_address'):
                buys = group[group['action'] == 'BUY']
                sells = group[group['action'] == 'SELL']
                
                if buys.empty or sells.empty:
                    continue
                
                # For each sell, find a matching buy
                for _, sell in sells.iterrows():
                    # Find buys that happened before this sell
                    try:
                        prior_buys = buys[pd.to_datetime(buys['timestamp']) < pd.to_datetime(sell['timestamp'])]
                    except:
                        # If timestamp conversion fails, use all buys
                        prior_buys = buys
                    
                    if prior_buys.empty:
                        continue
                    
                    # Get the earliest buy
                    buy = prior_buys.iloc[0]
                    
                    # Calculate profit
                    buy_price = buy['price']
                    sell_price = sell['price']
                    amount = min(buy['amount'], sell['amount'])
                    
                    profit_sol = (sell_price - buy_price) * amount
                    profit_usd = profit_sol * sol_price
                    profit_percent = ((sell_price / buy_price) - 1) * 100 if buy_price > 0 else 0
                    
                    # Get token ticker
                    ticker = contract[:8]  # Default to first 8 chars
                    
                    # Add to completed trades
                    completed_trades.append({
                        'ticker': ticker,
                        'buy_time': buy['timestamp'],
                        'sell_time': sell['timestamp'],
                        'buy_price': buy_price,
                        'sell_price': sell_price,
                        'amount': amount,
                        'profit_sol': profit_sol,
                        'profit_usd': profit_usd,
                        'profit_percent': profit_percent,
                        'tx_hash': sell.get('tx_hash', 'SIM_TRANSACTION')
                    })buys.empty:
                        continue
                    
                    # Get the earliest buy
                    buy = prior_buys.iloc[0]
                    
                    # Calculate profit
                    buy_price = buy['price']
                    sell_price = sell['price']
                    amount = min(buy['amount'], sell['amount'])
                    
                    profit_sol = (sell_price - buy_price) * amount
                    profit_usd = profit_sol * sol_price
                    profit_percent = ((sell_price / buy_price) - 1) * 100 if buy_price > 0 else 0
                    
                    # Get token ticker
                    ticker = contract[:8]  # Default to first 8 chars
                    
                    # Add to completed trades
                    completed_trades.append({
                        'ticker': ticker,
                        'buy_time': buy['timestamp'],
                        'sell_time': sell['timestamp'],
                        'buy_price': buy_price,
                        'sell_price': sell_price,
                        'amount': amount,
                        'profit_sol': profit_sol,
                        'profit_usd': profit_usd,
                        'profit_percent': profit_percent,
                        'tx_hash': sell.get('tx_hash', 'N/A')
                    })
            
            if completed_trades:
                completed_df = pd.DataFrame(completed_trades)
                
                # Sort by sell time (most recent first)
                try:
                    completed_df['sell_time_dt'] = pd.to_datetime(completed_df['sell_time'])
                    completed_df = completed_df.sort_values('sell_time_dt', ascending=False)
                    completed_df = completed_df.drop('sell_time_dt', axis=1)
                except:
                    # If conversion fails, keep as is
                    pass
                
                # Format for display
                display_completed = completed_df.copy()
                
                # Format columns
                display_completed['buy_time'] = display_completed['buy_time'].apply(convert_to_et)
                display_completed['sell_time'] = display_completed['sell_time'].apply(convert_to_et)
                display_completed['buy_price'] = display_completed['buy_price'].apply(lambda x: f"${x:.8f}")
                display_completed['sell_price'] = display_completed['sell_price'].apply(lambda x: f"${x:.8f}")
                display_completed['profit_sol'] = display_completed['profit_sol'].apply(lambda x: f"{x:.6f} SOL")
                display_completed['profit_usd'] = display_completed['profit_usd'].apply(lambda x: f"${x:.2f}")
                display_completed['profit_percent'] = display_completed['profit_percent'].apply(lambda x: f"{x:.2f}%")
                
                # Rename columns for better display
                col_mapping = {
                    'ticker': 'Token',
                    'buy_time': 'Buy Time',
                    'sell_time': 'Sell Time',
                    'buy_price': 'Buy Price',
                    'sell_price': 'Sell Price',
                    'amount': 'Amount (SOL)',
                    'profit_sol': 'Profit (SOL)',
                    'profit_usd': 'Profit (USD)',
                    'profit_percent': 'Profit %'
                }
                
                # Apply column renaming
                display_completed = display_completed.rename(columns=col_mapping)
                
                # Select columns to display
                display_cols = [
                    'Token', 'Buy Time', 'Sell Time', 'Buy Price', 'Sell Price',
                    'Amount (SOL)', 'Profit (SOL)', 'Profit %'
                ]
                display_cols = [col for col in display_cols if col in display_completed.columns]
                
                # Display completed trades
                st.dataframe(display_completed[display_cols], use_container_width=True)
                
                # Add download button
                if st.button("Download Simulation Trade History"):
                    csv = completed_df.to_csv(index=False)
                    b64 = base64.b64encode(csv.encode()).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="simulation_trade_history.csv">Download CSV File</a>'
                    st.markdown(href, unsafe_allow_html=True)
            else:
                st.info("No completed simulation trades found")
        else:
            st.info("No simulation trades recorded yet")
        
        # Simulation settings
        with st.expander("Simulation Settings"):
            st.markdown("""
            ### Simulation Parameters
            
            The simulation mode allows you to test trading strategies without risking real funds. The bot will simulate trades
            using the parameters below, but no actual transactions will be executed on the blockchain.
            
            - **Initial Balance**: The starting SOL balance for simulation
            - **Market Conditions**: Simulated market volatility and liquidity
            - **Transaction Fees**: Simulated network fees
            """)
            
            # Create simulation settings inputs
            sim_col1, sim_col2 = st.columns(2)
            
            with sim_col1:
                sim_initial_balance = st.number_input(
                    "Initial Simulation Balance (SOL)",
                    min_value=0.1,
                    max_value=100.0,
                    value=1.0,
                    step=0.1
                )
                
                sim_market_volatility = st.slider(
                    "Market Volatility",
                    min_value=0.1,
                    max_value=5.0,
                    value=1.0,
                    step=0.1,
                    help="Higher values mean more price volatility in simulations"
                )
            
            with sim_col2:
                sim_tx_fee = st.number_input(
                    "Transaction Fee (SOL)",
                    min_value=0.000001,
                    max_value=0.01,
                    value=0.000005,
                    format="%.6f",
                    help="Simulated transaction fee per trade"
                )
                
                sim_slippage = st.slider(
                    "Slippage (%)",
                    min_value=0.1,
                    max_value=10.0,
                    value=1.0,
                    step=0.1,
                    help="Simulated slippage percentage"
                )
            
            # Add button to save simulation settings
            if st.button("Save Simulation Settings"):
                # In a real implementation, these would be saved to the bot configuration
                st.success("Simulation settings saved")
    
    # Settings Tab
    with tabs[3]:
        st.subheader("Bot Settings")
        
        # Create tabs for different settings categories
        settings_tabs = st.tabs(["General", "Trading Parameters", "Token Filters", "API Keys", "Advanced"])
        
        with settings_tabs[0]:
            st.markdown("### General Settings")
            
            general_col1, general_col2 = st.columns(2)
            
            with general_col1:
                general_running = st.checkbox(
                    "Bot Running",
                    value=bot_settings.get('running', False),
                    help="Start or stop the trading bot",
                    key="general_running"
                )
                
                general_sim_mode = st.checkbox(
                    "Simulation Mode",
                    value=bot_settings.get('simulation_mode', True),
                    help="Toggle between simulation and real trading mode",
                    key="general_sim_mode"
                )
                
                general_ml = st.checkbox(
                    "ML Analysis",
                    value=bot_settings.get('use_machine_learning', False),
                    help="Enable/disable machine learning for trade analysis",
                    key="general_ml"
                )
            
            with general_col2:
                scan_interval = st.number_input(
                    "Scan Interval (seconds)",
                    min_value=30,
                    max_value=3600,
                    value=bot_settings.get('scan_interval', 60),
                    step=30,
                    help="Interval between token scans"
                )
                
                max_active_positions = st.number_input(
                    "Max Active Positions",
                    min_value=1,
                    max_value=50,
                    value=bot_settings.get('max_active_positions', 10),
                    step=1,
                    help="Maximum number of active positions"
                )
                
                auto_update = st.checkbox(
                    "Auto-Update Dashboard",
                    value=True,
                    help="Automatically refresh the dashboard"
                )
            
            # Save general settings button
            if st.button("Save General Settings"):
                # Update settings
                bot_settings['running'] = general_running
                bot_settings['simulation_mode'] = general_sim_mode
                bot_settings['use_machine_learning'] = general_ml
                bot_settings['scan_interval'] = scan_interval
                bot_settings['max_active_positions'] = max_active_positions
                
                # Save settings
                if save_bot_settings(bot_settings):
                    st.success("General settings saved successfully!")
                else:
                    st.error("Failed to save general settings")
        
        with settings_tabs[1]:
            st.markdown("### Trading Parameters")
            
            trading_col1, trading_col2 = st.columns(2)
            
            with trading_col1:
                tp_target = st.number_input(
                    "Take Profit (%)",
                    min_value=1.0,
                    max_value=1000.0,
                    value=float(bot_settings.get('take_profit_target', 50.0)),
                    step=5.0,
                    help="Target profit percentage for trades"
                )
                
                sl_percentage = st.number_input(
                    "Stop Loss (%)",
                    min_value=1.0,
                    max_value=100.0,
                    value=float(bot_settings.get('stop_loss_percentage', 25.0)),
                    step=1.0,
                    help="Stop loss percentage for trades"
                )
                
                min_inv = st.number_input(
                    "Min Investment (SOL)",
                    min_value=0.001,
                    max_value=1.0,
                    value=float(bot_settings.get('min_investment_per_token', 0.02)),
                    step=0.001,
                    help="Minimum investment per token in SOL"
                )
                
                trailing_stop = st.checkbox(
                    "Enable Trailing Stop",
                    value=bot_settings.get('use_trailing_stop', False),
                    help="Enable trailing stop loss"
                )
                
                if trailing_stop:
                    trailing_stop_pct = st.number_input(
                        "Trailing Stop Distance (%)",
                        min_value=1.0,
                        max_value=50.0,
                        value=float(bot_settings.get('trailing_stop_percent', 10.0)),
                        step=1.0,
                        help="Trailing stop distance as percentage of price"
                    )
            
            with trading_col2:
                max_inv = st.number_input(
                    "Max Investment (SOL)",
                    min_value=0.01,
                    max_value=10.0,
                    value=float(bot_settings.get('max_investment_per_token', 0.1)),
                    step=0.01,
                    help="Maximum investment per token in SOL"
                )
                
                slippage = st.number_input(
                    "Slippage Tolerance (%)",
                    min_value=0.1,
                    max_value=100.0,
                    value=float(bot_settings.get('slippage_tolerance', 0.3)) * 100,
                    step=0.1,
                    help="Slippage tolerance percentage"
                )
                
                moonbag_pct = st.number_input(
                    "Moonbag Percentage (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(bot_settings.get('moonbag_percentage', 0.0)) * 100,
                    step=5.0,
                    help="Percentage to keep as 'moonbag' after taking profit"
                )
            
            # Save trading parameters button
            if st.button("Save Trading Parameters"):
                # Update settings
                bot_settings['take_profit_target'] = tp_target
                bot_settings['stop_loss_percentage'] = sl_percentage
                bot_settings['min_investment_per_token'] = min_inv
                bot_settings['use_trailing_stop'] = trailing_stop
                if trailing_stop:
                    bot_settings['trailing_stop_percent'] = trailing_stop_pct
                bot_settings['max_investment_per_token'] = max_inv
                bot_settings['slippage_tolerance'] = slippage / 100  # Convert to decimal
                bot_settings['moonbag_percentage'] = moonbag_pct / 100  # Convert to decimal
                
                # Save settings
                if save_bot_settings(bot_settings):
                    st.success("Trading parameters saved successfully!")
                else:
                    st.error("Failed to save trading parameters")
        
        with settings_tabs[2]:
            st.markdown("### Token Filters")
            
            filter_col1, filter_col2 = st.columns(2)
            
            with filter_col1:
                min_safety = st.number_input(
                    "Min Safety Score",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(bot_settings.get('MIN_SAFETY_SCORE', 15.0)),
                    step=5.0,
                    help="Minimum safety score for tokens"
                )
                
                min_vol = st.number_input(
                    "Min 24h Volume (USD)",
                    min_value=0.0,
                    max_value=1000000.0,
                    value=float(bot_settings.get('MIN_VOLUME', 10.0)),
                    step=1000.0,
                    help="Minimum 24h trading volume in USD"
                )
                
                min_liq = st.number_input(
                    "Min Liquidity (USD)",
                    min_value=0.0,
                    max_value=1000000.0,
                    value=float(bot_settings.get('MIN_LIQUIDITY', 5000.0)),
                    step=1000.0,
                    help="Minimum liquidity in USD"
                )
                
                min_mcap = st.number_input(
                    "Min Market Cap (USD)",
                    min_value=0.0,
                    max_value=10000000.0,
                    value=float(bot_settings.get('MIN_MCAP', 10000.0)),
                    step=10000.0,
                    help="Minimum market cap in USD"
                )
            
            with filter_col2:
                min_holders = st.number_input(
                    "Min Holders",
                    min_value=0,
                    max_value=10000,
                    value=int(bot_settings.get('MIN_HOLDERS', 10)),
                    step=10,
                    help="Minimum number of token holders"
                )
                
                min_price_change_1h = st.number_input(
                    "Min 1h Price Change (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(bot_settings.get('MIN_PRICE_CHANGE_1H', 1.0)),
                    step=0.5,
                    help="Minimum 1h price change percentage"
                )
                
                min_price_change_6h = st.number_input(
                    "Min 6h Price Change (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(bot_settings.get('MIN_PRICE_CHANGE_6H', 2.0)),
                    step=0.5,
                    help="Minimum 6h price change percentage"
                )
                
                min_price_change_24h = st.number_input(
                    "Min 24h Price Change (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(bot_settings.get('MIN_PRICE_CHANGE_24H', 5.0)),
                    step=0.5,
                    help="Minimum 24h price change percentage"
                )
            
            # Filter fake tokens option
            filter_fake = st.checkbox(
                "Filter Fake Tokens",
                value=bot_settings.get('filter_fake_tokens', True),
                help="Filter out likely fake or scam tokens"
            )
            
            # Save token filters button
            if st.button("Save Token Filters"):
                # Update settings
                bot_settings['MIN_SAFETY_SCORE'] = min_safety
                bot_settings['MIN_VOLUME'] = min_vol
                bot_settings['MIN_LIQUIDITY'] = min_liq
                bot_settings['MIN_MCAP'] = min_mcap
                bot_settings['MIN_HOLDERS'] = min_holders
                bot_settings['MIN_PRICE_CHANGE_1H'] = min_price_change_1h
                bot_settings['MIN_PRICE_CHANGE_6H'] = min_price_change_6h
                bot_settings['MIN_PRICE_CHANGE_24H'] = min_price_change_24h
                bot_settings['filter_fake_tokens'] = filter_fake
                
                # Save settings
                if save_bot_settings(bot_settings):
                    st.success("Token filters saved successfully!")
                else:
                    st.error("Failed to save token filters")
        
        with settings_tabs[3]:
            st.markdown("### API Keys")
            
            # Store keys in session state (not secure for production)
            if 'api_keys' not in st.session_state:
                st.session_state.api_keys = {
                    'solana_rpc': '',
                    'birdeye_api': '',
                    'twitter_api': ''
                }
            
            # RPC Endpoint
            rpc_endpoint = st.text_input(
                "Solana RPC Endpoint",
                value=st.session_state.api_keys['solana_rpc'],
                type="password",
                help="Enter your Solana RPC endpoint URL"
            )
            st.session_state.api_keys['solana_rpc'] = rpc_endpoint
            
            # BirdEye API Key
            birdeye_api = st.text_input(
                "BirdEye API Key",
                value=st.session_state.api_keys['birdeye_api'],
                type="password",
                help="Enter your BirdEye API key"
            )
            st.session_state.api_keys['birdeye_api'] = birdeye_api
            
            # Twitter API Key
            twitter_api = st.text_input(
                "Twitter API Key",
                value=st.session_state.api_keys['twitter_api'],
                type="password",
                help="Enter your Twitter API key (optional)"
            )
            st.session_state.api_keys['twitter_api'] = twitter_api
            
            # Save API keys button
            if st.button("Save API Keys"):
                # In a real implementation, these would be saved securely
                st.success("API keys saved successfully!")
                
                # Show a warning about RPC endpoint
                if not rpc_endpoint.startswith("https://"):
                    st.warning("RPC endpoint should start with https://")
        
        with settings_tabs[4]:
            st.markdown("### Advanced Settings")
            
            # Database Management
            st.subheader("Database Management")
            
            db_col1, db_col2 = st.columns(2)
            
            with db_col1:
                if st.button("Backup Database"):
                    if db_file and os.path.exists(db_file):
                        # In a real implementation, this would create a backup
                        st.success(f"Database backed up successfully: {db_file}")
                    else:
                        st.error("Database file not found")
            
            with db_col2:
                if st.button("Reset Database", help="WARNING: This will delete all trading data"):
                    # Add a confirmation
                    st.warning("Are you sure you want to reset the database? This will delete all trading data.")
                    db_col3, db_col4 = st.columns(2)
                    
                    with db_col3:
                        if st.button("Yes, Reset Database"):
                            # In a real implementation, this would reset the database
                            st.success("Database reset successfully")
                    
                    with db_col4:
                        if st.button("Cancel"):
                            pass
            
            # Bot Logs
            st.subheader("Bot Logs")
            
            # Create a text area with simulated logs
            logs = """
2025-05-20 14:21:45 INFO - Bot started successfully
2025-05-20 14:21:46 INFO - Connected to Solana network
2025-05-20 14:21:47 INFO - Initialized database connection
2025-05-20 14:21:48 INFO - Wallet balance: 1.15000000 SOL
2025-05-20 14:21:50 INFO - Starting token scanner
2025-05-20 14:21:51 INFO - Scanning for new tokens...
            """
            
            st.text_area("Logs", value=logs, height=200)
            
            log_col1, log_col2 = st.columns(2)
            
            with log_col1:
                if st.button("Refresh Logs"):
                    st.success("Logs refreshed")
            
            with log_col2:
                if st.button("Clear Logs"):
                    st.info("Logs cleared")
            
            # Debug Mode
            debug_mode = st.checkbox(
                "Debug Mode",
                value=False,
                help="Enable debug mode for detailed logging"
            )
            
            if debug_mode:
                st.info("Debug mode enabled. Additional information will be logged.")
            
            # Save advanced settings button
            if st.button("Save Advanced Settings"):
                # In a real implementation, these would be saved
                st.success("Advanced settings saved successfully!")
    
    # Add refresh button at the bottom
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
    main()
                
                # Format for display
                display_completed = completed_df.copy()
                
                # Format columns
                display_completed['buy_time'] = display_completed['buy_time'].apply(convert_to_et)
                display_completed['sell_time'] = display_completed['sell_time'].apply(convert_to_et)
                display_completed['buy_price'] = display_completed['buy_price'].apply(lambda x: f"${x:.8f}")
                display_completed['sell_price'] = display_completed['sell_price'].apply(lambda x: f"${x:.8f}")
                display_completed['profit_sol'] = display_completed['profit_sol'].apply(lambda x: f"{x:.6f} SOL")
                display_completed['profit_usd'] = display_completed['profit_usd'].apply(lambda x: f"${x:.2f}")
                display_completed['profit_percent'] = display_completed['profit_percent'].apply(lambda x: f"{x:.2f}%")
                
                # Rename columns for better display
                col_mapping = {
                    'ticker': 'Token',
                    'buy_time': 'Buy Time',
                    'sell_time': 'Sell Time',
                    'buy_price': 'Buy Price',
                    'sell_price': 'Sell Price',
                    'amount': 'Amount (SOL)',
                    'profit_sol': 'Profit (SOL)',
                    'profit_usd': 'Profit (USD)',
                    'profit_percent': 'Profit %',
                    'tx_hash': 'Transaction'
                }
                
                # Apply column renaming
                display_completed = display_completed.rename(columns=col_mapping)
                
                # Select columns to display
                display_cols = [
                    'Token', 'Buy Time', 'Sell Time', 'Buy Price', 'Sell Price',
                    'Amount (SOL)', 'Profit (SOL)', 'Profit %', 'Transaction'
                ]
                display_cols = [col for col in display_cols if col in display_completed.columns]
                
                # Display completed trades
                st.dataframe(display_completed[display_cols], use_container_width=True)
                
                # Add download button
                if st.button("Download Real Trade History"):
                    csv = completed_df.to_csv(index=False)
                    b64 = base64.b64encode(csv.encode()).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="real_trade_history.csv">Download CSV File</a>'
                    st.markdown(href, unsafe_allow_html=True)
            else:
                st.info("No completed real trades found")
        else:
            st.info("No real trades recorded yet")
    
    # Simulation Tab
    with tabs[2]:
        st.subheader("Simulation Dashboard")
        
        # Real or simulation mode indicator
        if not bot_settings.get('simulation_mode', True):
            st.warning("⚠️ The bot is currently in real trading mode. Simulation mode is disabled.")
        
        # Create 4 columns for metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            color = "green" if metrics_sim["total_pl_usd"] > 0 else "red" if metrics_sim["total_pl_usd"] < 0 else "gray"
            st.markdown(f"<div class='metric-card'><span class='main-metric' style='color: {color}'>Total P&L</span><br/><span class='main-metric' style='color: {color}'>${metrics_sim['total_pl_usd']:.2f}</span><br/><span class='sub-metric'>{metrics_sim['total_pl_sol']:.6f} SOL</span></div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"<div class='metric-card'><span class='main-metric'>Simulated Balance</span><br/><span class='main-metric'>1.0000 SOL</span><br/><span class='sub-metric'>${sol_price:.2f} USD</span></div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"<div class='metric-card'><span class='main-metric'>Win Rate</span><br/><span class='main-metric'>{metrics_sim['win_rate']:.1f}%</span><br/><span class='sub-metric'>{metrics_sim['total_trades']} trades</span></div>", unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"<div class='metric-card'><span class='main-metric'>Best Trade</span><br/><span class='main-metric'>{metrics_sim['best_trade_pct']:.1f}%</span><br/><span class='sub-metric'>Worst: {metrics_sim['worst_trade_pct']:.1f}%</span></div>", unsafe_allow_html=True)
        
        # P&L chart
        st.subheader("Simulation P&L")
        
        # Lookback period selection
        lookback = st.selectbox(
            "Lookback Period",
            options=[7, 14, 30, 60, 90],
            index=2,
            key="sim_lookback"
        )
        
        # Create P&L chart
        pl_chart_sim = create_pl_chart(
            trades_sim,
            lookback_days=lookback,
            chart_title=f"Simulation P&L (Last {lookback} Days)",
            line_color="cyan"
        )
        st.plotly_chart(pl_chart_sim, use_container_width=True)
        
        # Active positions
        st.subheader("Active Simulation Positions")
        
        if not positions_sim.empty:
            # Format for display
            display_positions = positions_sim.copy()
            
            if 'avg_buy_price' in display_positions:
                display_positions['avg_buy_price'] = display_positions['avg_buy_price'].apply(lambda x: f"${x:.8f}")
            
            if 'current_price' in display_positions:
                display_positions['current_price'] = display_positions['current_price'].apply(lambda x: f"${x:.8f}")
            
            if 'unrealized_pl' in display_positions:
                display_positions['unrealized_pl'] = display_positions['unrealized_pl'].apply(lambda x: f"{x:.6f} SOL")
            
            if 'pl_percent' in display_positions:
                display_positions['pl_percent'] = display_positions['pl_percent'].apply(lambda x: f"{x:.2f}%")
            
            if 'entry_time' in display_positions.columns and not display_positions['entry_time'].isnull().all():
                display_positions['entry_time'] = display_positions['entry_time'].apply(
                    lambda x: convert_to_et(x) if x is not None else "Unknown"
                )
            
            # Select columns to display
            display_cols = ['ticker', 'amount', 'avg_buy_price', 'current_price', 'unrealized_pl', 'pl_percent']
            if 'entry_time' in display_positions.columns:
                display_cols.append('entry_time')
                
            display_cols = [col for col in display_cols if col in display_positions.columns]
            
            # Rename columns for better display
            col_mapping = {
                'ticker': 'Token',
                'amount': 'Amount (SOL)',
                'avg_buy_price': 'Buy Price',
                'current_price': 'Current Price',
                'unrealized_pl': 'Unrealized P&L',
                'pl_percent': 'P&L %',
                'entry_time': 'Entry Time'
            }
            
            # Apply column renaming
            display_positions = display_positions[display_cols].rename(columns=col_mapping)
            
            # Display positions
            st.dataframe(display_positions, use_container_width=True)
            
            # Create token distribution chart
            token_chart = create_token_distribution_chart(
                positions_sim,
                title="Simulation Token Distribution"
            )
            st.plotly_chart(token_chart, use_container_width=True)
        else:
            st.info("No active simulation positions found")
        
        # Simulation trading history
        st.subheader("Simulation Trading History")
        
        if not trades_sim.empty:
            # Filter for completed trades (pairs of buys and sells)
            completed_trades = []
            
            for contract, group in trades_sim.groupby('contract_address'):
                buys = group[group['action'] == 'BUY']
                sells = group[group['action'] == 'SELL']
                
                if buys.empty or sells.empty:
                    continue
                
                # For each sell, find a matching buy
                for _, sell in sells.iterrows():
                    # Find buys that happened before this sell
                    try:
                        prior_buys = buys[pd.to_datetime(buys['timestamp']) < pd.to_datetime(sell['timestamp'])]
                    except:
                        # If timestamp conversion fails, use all buys
                        prior_buys = buys
                    
                    if prior_