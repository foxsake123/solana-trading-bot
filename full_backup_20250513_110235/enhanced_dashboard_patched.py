import asyncio
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import time
import traceback
import json
import os
from datetime import datetime, timedelta, timezone
import pytz  # Add pytz for timezone handling
from timestamp_fix import safe_parse_timestamp


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

# Define Eastern Time zone
ET = pytz.timezone('US/Eastern')


# Safe timestamp parsing function
def safe_parse_timestamp(timestamp_str):
    """Parse timestamp safely handling multiple formats"""
    import logging
    from datetime import datetime, timezone
    import pytz
    
    logger = logging.getLogger('trading_bot')
    ET = pytz.timezone('US/Eastern')
    
    try:
        if timestamp_str is None:
            return None
        
        # Handle ET format separately
        if isinstance(timestamp_str, str) and ' ET' in timestamp_str:
            # Already in ET format, keep it as is
            return timestamp_str
            
        # Handle various timestamp formats
        if isinstance(timestamp_str, str) and 'Z' in timestamp_str:
            # ISO format with Z
            try:
                dt = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            except ValueError:
                try:
                    dt = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%SZ')
                except ValueError:
                    # Last resort - try to replace Z
                    try:
                        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    except:
                        return timestamp_str  # Keep original if parsing fails
            
            # Convert to ET format
            et_dt = dt.astimezone(ET)
            return et_dt.strftime('%Y-%m-%d %I:%M:%S %p ET')
            
        elif isinstance(timestamp_str, str) and ('+' in timestamp_str or '-' in timestamp_str and 'T' in timestamp_str):
            # ISO format with timezone offset
            try:
                dt = datetime.fromisoformat(timestamp_str)
                et_dt = dt.astimezone(ET)
                return et_dt.strftime('%Y-%m-%d %I:%M:%S %p ET')
            except:
                return timestamp_str  # Keep original if parsing fails
        else:
            # No timezone information, try multiple formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %I:%M:%S %p',
                '%Y-%m-%dT%H:%M:%S',
                '%m/%d/%Y %H:%M:%S',
                '%m/%d/%Y %I:%M:%S %p'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(timestamp_str, fmt)
                    dt = dt.replace(tzinfo=timezone.utc)
                    et_dt = dt.astimezone(ET)
                    return et_dt.strftime('%Y-%m-%d %I:%M:%S %p ET')
                except ValueError:
                    continue
            
            # If all formats fail, return original
            return timestamp_str
    except Exception as e:
        logger.error(f"Error converting timestamp {timestamp_str} to ET: {e}")
        return timestamp_str  # Return original if any error occurs
def get_sol_price(trader):
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
        return 145.0  # Default SOL price as fallback

async def update_token_prices(positions_df, db, trader):
    """
    Update token prices in the positions dataframe with improved USD calculations
    
    :param positions_df: DataFrame of positions
    :param db: Database instance
    :param trader: SolanaTrader instance
    :return: Updated DataFrame
    """
    # Import logger at function level to avoid unbound variable error
    from logging import getLogger
    logger = getLogger('trading_bot.dashboard')
    
    if positions_df.empty:
        return positions_df
        
    # Get current SOL price
    sol_price_usd = await trader.get_sol_price()
    logger.info(f"Current SOL price for calculations: ${sol_price_usd}")
    
    # Make a copy to avoid modifying the original
    updated_df = positions_df.copy()
    
    # Add current price column if it doesn't exist
    if 'current_price_usd' not in updated_df.columns:
        updated_df['current_price_usd'] = 0.0
    
    # Process each token to get current price
    for idx, row in updated_df.iterrows():
        contract_address = row['contract_address']
        
        # Get token info from database or API
        token_info = db.get_token(contract_address)
        if token_info:
            # Use price from database if available and recent (last 24 hours)
            from datetime import datetime, timedelta, timezone
            last_updated = None
            if 'last_updated' in token_info:
                try:
                    last_updated = datetime.fromisoformat(token_info['last_updated'].replace('Z', '+00:00'))
                except:
                    pass
            
            now = datetime.now(timezone.utc)
            if last_updated and (now - last_updated) < timedelta(hours=24):
                updated_df.at[idx, 'current_price_usd'] = float(token_info.get('price_usd', 0.0))
            else:
                # Price data too old, need to fetch fresh data
                try:
                    # Try to get fresh data from token_analyzer
                    from token_analyzer import TokenAnalyzer
                    analyzer = TokenAnalyzer(db)
                    token_data = await analyzer.fetch_token_data(contract_address)
                    if token_data and 'price_usd' in token_data:
                        updated_df.at[idx, 'current_price_usd'] = float(token_data['price_usd'])
                    else:
                        # Simulate a current price based on buy price
                        buy_price_sol_per_token = float(row['buy_price'])
                        # For simulation, use a random value between 0.5x-3x the buy price
                        import random
                        current_price_sol_per_token = buy_price_sol_per_token * random.uniform(0.5, 3.0)
                        updated_df.at[idx, 'current_price_usd'] = current_price_sol_per_token
                except Exception as e:
                    # Get a local logger instance to avoid unbound variable error
                    import logging
                    local_logger = logging.getLogger('trading_bot.dashboard')
                    local_logger.error(f"Error fetching current price for {contract_address}: {e}")
                    # Fallback to simulation
                    buy_price_sol_per_token = float(row['buy_price'])
                    import random
                    current_price_sol_per_token = buy_price_sol_per_token * random.uniform(0.5, 3.0)
                    updated_df.at[idx, 'current_price_usd'] = current_price_sol_per_token
        else:
            # No token info in database, simulate a price
            buy_price_sol_per_token = float(row['buy_price'])
            import random
            current_price_sol_per_token = buy_price_sol_per_token * random.uniform(0.5, 3.0)
            updated_df.at[idx, 'current_price_usd'] = current_price_sol_per_token
    
    # IMPORTANT FIX: Calculate investment metrics with proper SOL price conversion
    # The critical fix here is understanding what the buy_price actually represents:
    # buy_price is the tokens per SOL (e.g., 0.0000001 means 10000000 tokens per 1 SOL)
    
    # Calculate token quantities for each position (this is number of tokens)
    updated_df['token_quantity'] = updated_df['amount'] / updated_df['buy_price']
    
    # Calculate invested value in USD (amount in SOL * SOL price in USD)
    updated_df['invested_usd'] = updated_df['amount'] * sol_price_usd
    
    # Calculate current value in USD (token quantity * current token price * SOL price)
    updated_df['current_value_usd'] = updated_df['token_quantity'] * updated_df['current_price_usd'] * sol_price_usd
    
    # Calculate PnL metrics
    updated_df['pnl_usd'] = updated_df['current_value_usd'] - updated_df['invested_usd']
    updated_df['pnl_percent'] = (updated_df['pnl_usd'] / updated_df['invested_usd']) * 100
    updated_df['multiple'] = updated_df['current_price_usd'] / updated_df['buy_price']
    
    # Format numeric columns for display
    updated_df['invested_usd'] = updated_df['invested_usd'].round(2)
    updated_df['current_value_usd'] = updated_df['current_value_usd'].round(2)
    updated_df['pnl_usd'] = updated_df['pnl_usd'].round(2)
    updated_df['pnl_percent'] = updated_df['pnl_percent'].round(2)
    updated_df['multiple'] = updated_df['multiple'].round(3)
    
    # Log some debug info to help identify issues
    logger.info(f"Updated {len(updated_df)} positions with proper USD values")
    for idx, row in updated_df.iterrows():
        logger.debug(f"Position {row.get('ticker')}: Invested=${row.get('invested_usd')}, Current=${row.get('current_value_usd')}, PnL=${row.get('pnl_usd')}")
    
    return updated_df

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
    
    # Load bot control settings to check simulation mode
    control = get_bot_control()
    simulation_mode = control.get('simulation_mode', True)
    
    # Then initialize the trader with the database and simulation mode
    trader = SolanaTrader(db=db, simulation_mode=simulation_mode)
    
    # Initialize other components that need the database
    birdeye = BirdeyeAPI()
    
    try:
        # Connect to Solana
        await trader.connect()
        
        # Get SOL price (cached)
        sol_price_usd = await trader.get_sol_price()
        
        # Get active positions
        positions_df = db.get_active_orders()
        
        # Get wallet balance - this now works for both simulation and real mode
        balance_sol, balance_usd = await trader.get_wallet_balance()
        
        # Calculate adjusted wallet balance that accounts for active positions
        # In simulation mode, subtract active positions from 1.0 SOL starting balance
        if simulation_mode and not positions_df.empty:
            # Sum the amount of SOL invested in active positions
            invested_sol = positions_df['amount'].sum() if 'amount' in positions_df.columns else 0
            
            # Get logging
            from logging import getLogger
            logger = getLogger('trading_bot.dashboard')
            logger.info(f"Adjusting wallet balance: Starting with {balance_sol} SOL, {invested_sol} SOL in active positions")
            
            # In simulation mode, the starting balance is typically 1.0 SOL
            # Adjust the displayed balance to show remaining funds
            adjusted_balance_sol = max(0, balance_sol - invested_sol)
            adjusted_balance_usd = adjusted_balance_sol * sol_price_usd
            
            logger.info(f"Adjusted wallet balance: {adjusted_balance_sol} SOL (${adjusted_balance_usd:.2f})")
        else:
            # In real trading mode, use the actual wallet balance from trader
            adjusted_balance_sol = balance_sol
            adjusted_balance_usd = balance_usd
        
        # Enhance positions with token price data if we have positions
        if not positions_df.empty:
            positions_df = await update_token_prices(positions_df, db, trader)
        
        # Get trading history
        trades_df = db.get_trading_history(limit=50)
        
        # Convert timestamps to Eastern Time
        if not trades_df.empty and 'timestamp' in trades_df.columns:
            trades_df['timestamp_et'] = trades_df['timestamp'].apply(safe_parse_timestamp)
            # Keep original timestamp column for calculations
            trades_df['original_timestamp'] = trades_df['timestamp']
            trades_df['timestamp'] = trades_df['timestamp_et']
        
        # Get discovered tokens
        tokens_df = db.get_tokens(limit=30)
        
        # Convert timestamps to Eastern Time for tokens
        if not tokens_df.empty and 'last_updated' in tokens_df.columns:
            tokens_df['last_updated_et'] = tokens_df['last_updated'].apply(safe_parse_timestamp)
            tokens_df['last_updated'] = tokens_df['last_updated_et']
        
        # Get trending tokens from Birdeye/DexScreener
        trending_tokens = await birdeye.get_trending_tokens(limit=10)
        
        # Calculate bot statistics
        stats = calculate_stats(trades_df, positions_df)
        
        # Calculate simulation statistics - only if in simulation mode
        simulation_stats = await calculate_simulation_stats(trades_df, sol_price_usd) if simulation_mode else {
            'total_pl_sol': 0.0,
            'total_pl_usd': 0.0,
            'roi_percentage': 0.0,
            'best_trade_multiple': 0.0,
            'worst_trade_multiple': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }
        
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
            'wallet_balance_sol': adjusted_balance_sol,
            'wallet_balance_usd': adjusted_balance_usd,
            'sol_price_usd': sol_price_usd,
            'stats': stats,
            'simulation_stats': simulation_stats,
            'control': control,
            'ml_stats': ml_stats,
            'ml_predictions': ml_predictions,
            'simulation_mode': simulation_mode  # Add simulation mode flag to context
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
            'ml_predictions': [],
            'simulation_mode': True  # Default to simulation mode on error
        }
    finally:
        # Close Solana connection
        try:
            await trader.close()
        except Exception as e:
            logger.error(f"Error closing Solana connection: {e}")

def calculate_stats(trades_df, positions_df):
    """
    Calculate trading statistics from completed trades
    """
    # Add debug logging
    from logging import getLogger
    logger = getLogger('trading_bot.dashboard')
    logger.info(f"Calculating stats from {len(trades_df)} trades")
    
    if trades_df.empty:
        logger.info("No trades found for stats calculation")
        return {
            'win_rate': 0,
            'total_trades': 0,
            'profit_loss': 0,
            'avg_holding_time': 0
        }
    
    try:
        # Filter completed trades (SELL trades)
        sell_trades = trades_df[trades_df['action'] == 'SELL'].copy()
        total_completed = len(sell_trades)
        
        logger.info(f"Found {total_completed} completed (SELL) trades")
        
        if total_completed > 0:
            # Calculate profit/loss
            total_profit_loss = 0
            winning_trades = 0
            holding_times = []
            
            # For debugging
            for idx, row in sell_trades.iterrows():
                if 'gain_loss_sol' in row:
                    logger.info(f"SELL trade {row.get('id', 'unknown')}: P&L = {row['gain_loss_sol']}")
                else:
                    logger.info(f"SELL trade {row.get('id', 'unknown')}: No P&L data")
            
            # Check if gain_loss_sol exists in the dataframe
            if 'gain_loss_sol' in sell_trades.columns:
                # Calculate total P&L directly from sell trades
                total_profit_loss = sell_trades['gain_loss_sol'].sum()
                winning_trades = len(sell_trades[sell_trades['gain_loss_sol'] > 0])
                logger.info(f"Calculated P&L directly from gain_loss_sol: {total_profit_loss}")
            else:
                # Need to calculate P&L manually from buy and sell pairs
                logger.info("No gain_loss_sol column found, calculating P&L manually from buy/sell pairs")
                
                for contract in sell_trades['contract_address'].unique():
                    contract_trades = trades_df[trades_df['contract_address'] == contract].copy()
                    contract_trades = contract_trades.sort_values('original_timestamp' if 'original_timestamp' in contract_trades.columns else 'timestamp')
                    
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
                        
                        logger.info(f"Contract {contract}: Buy={buy_value}, Sell={sell_value}, P&L={trade_pl}")
                        
                        # Track winning trades
                        if trade_pl > 0:
                            winning_trades += 1
                        
                        # Add to total P&L
                        total_profit_loss += trade_pl
            
            # Calculate holding times
            for contract in sell_trades['contract_address'].unique():
                contract_trades = trades_df[trades_df['contract_address'] == contract].copy()
                
                # Use original timestamps for sorting if available
                timestamp_field = 'original_timestamp' if 'original_timestamp' in contract_trades.columns else 'timestamp'
                contract_trades = contract_trades.sort_values(timestamp_field)
                
                buys = contract_trades[contract_trades['action'] == 'BUY']
                sells = contract_trades[contract_trades['action'] == 'SELL']
                
                if not buys.empty and not sells.empty:
                    # Get first buy and last sell timestamps
                    buy_time_str = buys.iloc[0][timestamp_field]
                    sell_time_str = sells.iloc[-1][timestamp_field]
                    
                    # Parse timestamps consistently
                    try:
                        if 'Z' in buy_time_str:
                            buy_time = datetime.fromisoformat(buy_time_str.replace('Z', '+00:00'))
                        else:
                            buy_time = datetime.fromisoformat(buy_time_str)
                            if buy_time.tzinfo is None:
                                buy_time = buy_time.replace(tzinfo=timezone.utc)
                                
                        if 'Z' in sell_time_str:
                            sell_time = datetime.fromisoformat(sell_time_str.replace('Z', '+00:00'))
                        else:
                            sell_time = datetime.fromisoformat(sell_time_str)
                            if sell_time.tzinfo is None:
                                sell_time = sell_time.replace(tzinfo=timezone.utc)
                                
                        holding_time = (sell_time - buy_time).total_seconds() / 3600  # hours
                        holding_times.append(holding_time)
                        logger.info(f"Contract {contract}: Holding time = {holding_time} hours")
                    except Exception as e:
                        logger.error(f"Error calculating holding time: {e}")
                        # Skip this holding time calculation
                        pass
            
            # Calculate statistics
            win_rate = (winning_trades / total_completed) * 100 if total_completed > 0 else 0
            avg_holding_time = sum(holding_times) / len(holding_times) if holding_times else 0
            
            logger.info(f"Final stats: Win rate={win_rate}%, Total trades={total_completed}, P&L={total_profit_loss}, Avg hold time={avg_holding_time}h")
            
            return {
                'win_rate': win_rate,
                'total_trades': total_completed,
                'profit_loss': total_profit_loss,
                'avg_holding_time': avg_holding_time
            }
        else:
            logger.info("No completed trades found for statistics")
            return {
                'win_rate': 0,
                'total_trades': 0,
                'profit_loss': 0,
                'avg_holding_time': 0
            }
    
    except Exception as e:
        logger.error(f"Error calculating stats: {e}")
        logger.error(traceback.format_exc())
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
        
        # Simulation Mode Toggle with Warning
        simulation_mode = st.checkbox(
            "Simulation Mode", 
            value=control.get('simulation_mode', True),
            help="When enabled, trades are simulated without real execution. Disable for real trading."
        )
        
        # Add a warning/info box about trading mode
        if simulation_mode:
            st.info("🛠️ Bot is running in SIMULATION mode. No real trades will be executed.")
        else:
            st.warning("💰 REAL TRADING mode is active! Bot will execute actual trades on Solana blockchain.")
            
            # Add additional warning and confirmation when switching to real trading
            if simulation_mode != control.get('simulation_mode', True) and not simulation_mode:
                confirm_real = st.checkbox("I confirm that I want to enable REAL TRADING with my wallet")
                if not confirm_real:
                    st.error("You must confirm that you want to enable real trading to proceed.")
                    simulation_mode = True  # Reset to simulation mode if not confirmed
                else:
                    # Check wallet configuration
                    private_key = BotConfiguration.API_KEYS.get('WALLET_PRIVATE_KEY')
                    rpc_endpoint = BotConfiguration.API_KEYS.get('SOLANA_RPC_ENDPOINT')
                    
                    if not private_key or not rpc_endpoint:
                        st.error("Missing wallet configuration. Please set WALLET_PRIVATE_KEY and SOLANA_RPC_ENDPOINT in your .env file.")
                        simulation_mode = True  # Reset to simulation mode if config is missing
        
        # Add Machine Learning Toggle
        ml_mode = st.checkbox(
            "Machine Learning", 
            value=control.get('use_machine_learning', False),
            help="When enabled, the bot will use machine learning to predict token performance."
        )
        
        # Update simulation mode in control settings if changed
        if simulation_mode != control.get('simulation_mode', True):
            control['simulation_mode'] = simulation_mode
            update_bot_control(control)
            
            if simulation_mode:
                st.success("Simulation mode enabled. Bot will not execute real trades.")
            else:
                st.success("Real trading mode enabled.")
                st.warning("⚠️ CAUTION: Bot will execute actual trades on the blockchain using your wallet.")
            
            # Restart necessary for simulation mode changes to take effect
            st.warning("Please restart the bot for this change to take effect.")
        
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
        # Show trading mode indicator at the top
        mode_col1, mode_col2 = st.columns(2)
        with mode_col1:
            if data.get('simulation_mode', True):
                st.info("🛠️ **SIMULATION MODE**: All trades are simulated. No real trades are executed.")
            else:
                st.warning("💰 **REAL TRADING MODE**: Bot is executing real trades on the Solana blockchain.")
        
        with mode_col2:
            # Display wallet information
            if not data.get('simulation_mode', True):
                # Try to show wallet address in real mode
                try:
                    from solders.pubkey import Pubkey
                    from solders.keypair import Keypair
                    
                    private_key_str = BotConfiguration.API_KEYS.get('WALLET_PRIVATE_KEY', '')
                    if private_key_str:
                        if len(private_key_str) == 64:  # Hex string
                            private_key_bytes = bytes.fromhex(private_key_str)
                        elif len(private_key_str) == 88:  # Base58 encoded
                            import base58
                            private_key_bytes = base58.b58decode(private_key_str)
                        else:
                            private_key_bytes = None
                            
                        if private_key_bytes:
                            keypair = Keypair.from_seed(private_key_bytes)
                            wallet_address = str(keypair.pubkey())
                            st.info(f"🔑 Active Wallet: {wallet_address[:6]}...{wallet_address[-6:]}")
                except:
                    st.info("🔑 Active Wallet: Connected")
        
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
        
        # Add Simulation P&L metrics - only show in simulation mode
        if data.get('simulation_mode', True):
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
            
            # Fix any remaining NaN values
            display_df = display_df.fillna(0)
            
            # Force numeric columns to be numeric
            numeric_cols = ['invested_usd', 'current_value_usd', 'pnl_usd', 'pnl_percent', 'multiple']
            for col in numeric_cols:
                if col in display_df.columns:
                    display_df[col] = pd.to_numeric(display_df[col], errors='coerce').fillna(0)
            
            # Apply conditional formatting for PnL columns
            def color_pnl(val):
                if isinstance(val, (int, float)) and val > 0:
                    return 'color: green'
                elif isinstance(val, (int, float)) and val < 0:
                    return 'color: red'
                else:
                    return ''
                
            # Apply styles
            styled_df = display_df.style.applymap(color_pnl, subset=['pnl_usd', 'pnl_percent'])
            
            # Display the dataframe
            st.dataframe(styled_df)
            
            # Add position distribution chart if we have positions
            if not display_df.empty and 'amount' in display_df.columns:
                st.subheader("Position Distribution")
                
                try:
                    # Create a simple pie chart of positions by amount
                    fig = px.pie(
                        display_df,
                        values='amount',
                        names='ticker',
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
                # Convert timezone for date picker
                current_et = datetime.now(ET).date()
                seven_days_ago_et = (datetime.now(ET) - timedelta(days=7)).date()
                
                date_range = st.date_input(
                    "Date range (ET)",
                    value=(seven_days_ago_et, current_et)
                )
            
            # Apply filters
            if action_filter:
                trades_display = trades_display[trades_display['action'].isin(action_filter)]
            
            if len(date_range) == 2:
                start_date, end_date = date_range
                
                # Convert to Eastern Time for comparison
                try:
                    # Create datetime objects in ET timezone
                    start_et = datetime.combine(start_date, datetime.min.time(), tzinfo=ET)
                    end_et = datetime.combine(end_date, datetime.max.time(), tzinfo=ET)
                    
                    # Convert to ISO format for string comparison
                    start_iso = start_et.isoformat()
                    end_iso = end_et.isoformat()
                    
                    # Use original timestamps for filtering if available
                    if 'original_timestamp' in trades_display.columns:
                        # Filter by converting each original timestamp to ET for comparison
                        def is_in_date_range(timestamp_str):
                            try:
                                if timestamp_str is None:
                                    return False
                                    
                                # Parse the timestamp to datetime
                                if 'Z' in timestamp_str:
                                    dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                elif '+' in timestamp_str or '-' in timestamp_str:
                                    dt = datetime.fromisoformat(timestamp_str)
                                else:
                                    dt = datetime.fromisoformat(timestamp_str)
                                    dt = dt.replace(tzinfo=timezone.utc)
                                
                                # Convert to ET
                                dt_et = dt.astimezone(ET)
                                
                                # Check if it's in range (compare just the dates, not times)
                                return start_date <= dt_et.date() <= end_date
                            except:
                                return False
                        
                        # Apply the filter
                        trades_display = trades_display[trades_display['original_timestamp'].apply(is_in_date_range)]
                    else:
                        # Fall back to timestamp field (which might be already in ET format as a string)
                        # This is less accurate but works as a fallback
                        trades_display = trades_display[
                            (trades_display['timestamp'] >= start_et.strftime('%Y-%m-%d')) & 
                            (trades_display['timestamp'] <= end_et.strftime('%Y-%m-%d'))
                        ]
                except Exception as e:
                    st.error(f"Error filtering by date: {e}")
            
            # Enhance the display with calculated metrics
            if 'price' in trades_display.columns and 'amount' in trades_display.columns:
                # Get SOL price
                sol_price_usd = data['sol_price_usd']
                
                # Calculate USD values
                trades_display['amount_usd'] = trades_display['amount'] * sol_price_usd
                
                # Calculate token quantity
                trades_display['token_quantity'] = trades_display['amount'] / trades_display['price']
                
                # For SELL trades, add additional metrics
                if 'gain_loss_sol' in trades_display.columns:
                    # Calculate P&L in USD
                    trades_display['pnl_usd'] = trades_display['gain_loss_sol'] * sol_price_usd
                    
                    # Format for display
                    trades_display['pnl_usd'] = trades_display['pnl_usd'].round(2)
                    trades_display['gain_loss_sol'] = trades_display['gain_loss_sol'].round(4)
                    trades_display['percentage_change'] = trades_display['percentage_change'].round(2)
                    
                    # Create a formatted display field for P&L
                    def format_pnl(row):
                        if row['action'] == 'SELL':
                            pnl_sol = row['gain_loss_sol']
                            pnl_usd = row['pnl_usd']
                            pnl_pct = row['percentage_change']
                            return f"{pnl_sol:.4f} SOL (${pnl_usd:.2f}, {pnl_pct:.1f}%)"
                        else:
                            return ""
                    
                    trades_display['pnl_formatted'] = trades_display.apply(format_pnl, axis=1)
            
            # Apply conditional formatting for P&L columns
            try:
                def color_pnl(val):
                    if isinstance(val, (int, float)) and val > 0:
                        return 'color: green; font-weight: bold'
                    elif isinstance(val, (int, float)) and val < 0:
                        return 'color: red; font-weight: bold'
                    else:
                        return ''
                
                # Add style if we have the columns
                if 'gain_loss_sol' in trades_display.columns:
                    styled_df = trades_display.style.applymap(color_pnl, subset=['gain_loss_sol', 'percentage_change', 'pnl_usd'])
                    
                    # Create better column headers for display
                    column_map = {
                        'gain_loss_sol': 'P&L (SOL)',
                        'pnl_usd': 'P&L (USD)',
                        'percentage_change': 'P&L (%)',
                        'price_multiple': 'Multiple (x)'
                    }
                    
                    # Rename columns for display
                    trades_display = trades_display.rename(columns=column_map)
                else:
                    styled_df = trades_display
            except Exception as e:
                st.error(f"Error formatting trade display: {e}")
                styled_df = trades_display
                
            # Column ordering and selection for better display
            try:
                # Define preferred column order
                preferred_columns = [
                    'id', 'timestamp', 'action', 'contract_address', 'ticker', 'amount', 
                    'amount_usd', 'price', 'P&L (SOL)', 'P&L (USD)', 'P&L (%)', 'Multiple (x)', 'tx_hash'
                ]
                
                # Filter to only include columns that actually exist in the dataframe
                display_columns = [col for col in preferred_columns if col in trades_display.columns]
                
                # Add any remaining columns not explicitly ordered
                for col in trades_display.columns:
                    if col not in display_columns and not col.startswith('original_'):
                        display_columns.append(col)
                        
                # Reorder columns for display
                trades_display = trades_display[display_columns]
            except Exception as e:
                st.warning(f"Warning during column reordering: {e}")
            
            # Display the enhanced dataframe
            st.dataframe(styled_df)
            
            # Add trade history chart
            if not trades_display.empty and 'timestamp' in trades_display.columns:
                st.subheader("Trade History Visualization")
                
                try:
                    # Convert timestamp to datetime for charting
                    timestamp_field = 'original_timestamp' if 'original_timestamp' in trades_display.columns else 'timestamp'
                    
                    # Create a copy for charting 
                    chart_df = trades_display.copy()
                    
                    # Parse timestamps and convert to datetime objects
                    def safe_parse_timestamp(ts_str):
                        """
                        Safely parse timestamp string to datetime object
                        """
                        from logging import getLogger
                        logger = getLogger('trading_bot.dashboard')
                        
                        try:
                            # If already a datetime object, return it
                            if isinstance(ts_str, datetime):
                                return ts_str
                                
                            # Handle already formatted ET timestamps
                            if isinstance(ts_str, str) and ' ET' in ts_str:
                                # Remove " ET" suffix
                                clean_ts = ts_str.replace(' ET', '')
                                try:
                                    # Try with AM/PM format
                                    dt = datetime.strptime(clean_ts, "%Y-%m-%d %I:%M:%S %p")
                                    return ET.localize(dt)
                                except ValueError:
                                    try:
                                        # Try without AM/PM
                                        dt = datetime.strptime(clean_ts, "%Y-%m-%d %H:%M:%S")
                                        return ET.localize(dt)
                                    except ValueError:
                                        # If both fail, fallback to a default
                                        logger.warning(f"Could not parse timestamp: {ts_str}, using fallback")
                                        return datetime.now(ET)
                            
                            # Otherwise try to parse as a normal datetime string
                            if 'Z' in ts_str:
                                dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                                return dt.astimezone(ET)
                            
                            if '+' in ts_str or '-' in ts_str and 'T' in ts_str:
                                dt = datetime.fromisoformat(ts_str)
                                return dt.astimezone(ET)
                            
                            # Try common formats
                            formats = [
                                '%Y-%m-%d %H:%M:%S',
                                '%Y-%m-%d %I:%M:%S %p',
                                '%Y-%m-%dT%H:%M:%S',
                                '%m/%d/%Y %H:%M:%S',
                                '%m/%d/%Y %I:%M:%S %p'
                            ]
                            
                            for fmt in formats:
                                try:
                                    dt = datetime.strptime(ts_str, fmt)
                                    dt = dt.replace(tzinfo=timezone.utc)
                                    return dt.astimezone(ET)
                                except ValueError:
                                    continue
                            
                            # Last resort - use current date
                            logger.warning(f"Failed to parse timestamp: {ts_str}")
                            return datetime.now(ET)
                        except Exception as e:
                            logger.error(f"Error in safe_parse_timestamp for {ts_str}: {e}")
                            return datetime.now(ET)
                    
                    # Apply the safe parsing function
                    chart_df['dt'] = chart_df[timestamp_field].apply(safe_parse_timestamp)
                    chart_df = chart_df.sort_values('dt')
                    
                    # Count trades by day
                    trades_by_day = chart_df.groupby([pd.Grouper(key='dt', freq='D'), 'action']).size().unstack(fill_value=0)
                    
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
                        title='Trades by Day (Eastern Time)',
                        xaxis_title='Date',
                        yaxis_title='Number of Trades',
                        barmode='group'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"Error creating trade history chart: {e}")
                    st.error(traceback.format_exc())
                    
            # Add P&L over time chart
            if not trades_display.empty and 'timestamp' in trades_display.columns:
                st.subheader("P&L Over Time")
                
                try:
                    # Use both simulation and real trades
                    all_trades = trades_display.copy()
                    
                    if not all_trades.empty:
                        # Get the timestamp field to use for date calculations
                        timestamp_field = 'original_timestamp' if 'original_timestamp' in all_trades.columns else 'timestamp'
                        
                        # Parse timestamps and convert to datetime objects
                        def parse_timestamp(ts_str):
    """
    Parse timestamp string to datetime object - safely
    """
    from datetime import datetime, timezone
    import pytz
    from logging import getLogger
    logger = getLogger('trading_bot')
    ET = pytz.timezone('US/Eastern')
    
    try:
        # If already a datetime, return it
        if isinstance(ts_str, datetime):
            return ts_str.astimezone(ET) if ts_str.tzinfo else ET.localize(ts_str)
            
        # Handle None
        if ts_str is None:
            return datetime.now(ET)
        
        # Handle ET format strings specifically
        if isinstance(ts_str, str) and ' ET' in ts_str:
            # Extract the date part
            date_str = ts_str.replace(' ET', '')
            try:
                if 'AM' in date_str or 'PM' in date_str:
                    # 12-hour format
                    dt = datetime.strptime(date_str, '%Y-%m-%d %I:%M:%S %p')
                else:
                    # 24-hour format
                    dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                return ET.localize(dt)
            except ValueError:
                # Log but don't crash
                logger.warning(f"Could not parse ET timestamp: {ts_str}")
                return datetime.now(ET)
        
        # Try multiple formats
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %I:%M:%S %p',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d',
            '%m/%d/%Y %H:%M:%S',
            '%m/%d/%Y'
        ]
        
        # Try each format
        for fmt in formats:
            try:
                dt = datetime.strptime(ts_str, fmt)
                if fmt.endswith('Z'):
                    # Handle UTC timezone
                    dt = dt.replace(tzinfo=timezone.utc)
                elif dt.tzinfo is None:
                    # Assume UTC for naive datetime
                    dt = dt.replace(tzinfo=timezone.utc)
                # Convert to ET
                return dt.astimezone(ET)
            except ValueError:
                continue
        
        # If all formats fail, try a last-resort approach
        try:
            # Clean string and try split approach
            clean_str = ts_str.replace('Z', '').replace('T', ' ')
            parts = clean_str.split(' ')[0].split('-')
            if len(parts) >= 3:
                # At least have a date portion
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                dt = datetime(year, month, day, tzinfo=timezone.utc)
                return dt.astimezone(ET)
        except:
            pass
            
        # Complete fallback
        logger.warning(f"Failed to parse timestamp with all methods: {ts_str}")
        return datetime.now(ET)
    except Exception as e:
        logger.error(f"Error in parse_timestamp: {str(e)}")
        return datetime.now(ET)
