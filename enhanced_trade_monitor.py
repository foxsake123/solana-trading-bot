# enhanced_trade_monitor.py - Enhanced trade monitoring with wallet balance and trade history

import os
import sys
import sqlite3
import pandas as pd
import time
import requests
from datetime import datetime, timedelta
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('enhanced_trade_monitor')

class EnhancedTradeMonitor:
    """Enhanced trade monitor with wallet balance and comprehensive trade history"""
    
    def __init__(self, db_path=None):
        """Initialize the enhanced trade monitor"""
        self.db_path = self._find_database() if db_path is None else db_path
        self.last_sol_price = 0.0
        self.price_cache_time = 0
        
    def _find_database(self):
        """Find the SQLite database file"""
        db_files = [
            'data/sol_bot.db',
            'data/trading_bot.db',
            'core/data/sol_bot.db',
            'sol_bot.db',
            'trading_bot.db'
        ]
        
        for db_file in db_files:
            if os.path.exists(db_file):
                logger.info(f"Found database: {db_file}")
                return db_file
        
        logger.error("No database file found")
        return None
    
    def _is_simulation_contract(self, address):
        """Check if a contract address is a simulation address"""
        if not isinstance(address, str):
            return False
        
        return (
            address.startswith('Sim') or 
            'TopGainer' in address or
            'test' in address.lower() or
            'simulation' in address.lower() or
            'demo' in address.lower()
        )
    
    def get_sol_price(self, force_refresh=False):
        """Get current SOL price with caching (5 minute cache)"""
        current_time = time.time()
        
        # Use cache if price is less than 5 minutes old and not forcing refresh
        if not force_refresh and self.last_sol_price > 0 and (current_time - self.price_cache_time) < 300:
            return self.last_sol_price
        
        try:
            # Try CoinGecko first
            response = requests.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data and 'solana' in data and 'usd' in data['solana']:
                    price = float(data['solana']['usd'])
                    self.last_sol_price = price
                    self.price_cache_time = current_time
                    return price
        except Exception as e:
            logger.warning(f"CoinGecko API error: {e}")
        
        try:
            # Try Binance as fallback
            response = requests.get(
                "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data and 'price' in data:
                    price = float(data['price'])
                    self.last_sol_price = price
                    self.price_cache_time = current_time
                    return price
        except Exception as e:
            logger.warning(f"Binance API error: {e}")
        
        # Return cached price if APIs fail
        if self.last_sol_price > 0:
            logger.warning("Using cached SOL price due to API failures")
            return self.last_sol_price
        
        # Fallback price
        logger.warning("Using fallback SOL price")
        return 100.0
    
    def get_wallet_balance(self):
        """Get wallet balance from .env file or return simulation balance"""
        try:
            # Try to get wallet balance from environment or .env file
            wallet_private_key = None
            rpc_endpoint = None
            
            # Check environment variables first
            wallet_private_key = os.getenv('WALLET_PRIVATE_KEY')
            rpc_endpoint = os.getenv('SOLANA_RPC_ENDPOINT')
            
            # If not in environment, try .env file
            if not wallet_private_key and os.path.exists('.env'):
                with open('.env', 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('WALLET_PRIVATE_KEY='):
                            wallet_private_key = line.split('=', 1)[1].strip().strip("'").strip('"')
                        elif line.startswith('SOLANA_RPC_ENDPOINT='):
                            rpc_endpoint = line.split('=', 1)[1].strip().strip("'").strip('"')
            
            # If we don't have a private key, use simulation balance
            if not wallet_private_key:
                logger.info("No wallet private key found, using simulation balance")
                return self._get_simulation_balance()
            
            # If we have a private key but can't get real balance, use simulation
            if not rpc_endpoint:
                rpc_endpoint = "https://api.mainnet-beta.solana.com"
            
            # For now, return simulation balance since we don't have wallet parsing implemented
            # In a real implementation, you would derive the public key from private key
            # and query the blockchain for the actual balance
            logger.info("Wallet configured but using simulation balance for demo")
            return self._get_simulation_balance()
            
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            return self._get_simulation_balance()
    
    def _get_simulation_balance(self):
        """Calculate simulation wallet balance based on trades"""
        if not self.db_path or not os.path.exists(self.db_path):
            return 10.0  # Default simulation balance
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get all trades to calculate spent SOL
            trades_df = pd.read_sql_query("SELECT * FROM trades", conn)
            conn.close()
            
            if trades_df.empty:
                return 10.0  # Default starting balance
            
            # Filter for simulation trades
            sim_trades = trades_df[trades_df['contract_address'].apply(self._is_simulation_contract)]
            
            if sim_trades.empty:
                return 10.0
            
            # Calculate spent SOL (buys reduce balance, sells increase balance)
            total_spent = 0.0
            for _, trade in sim_trades.iterrows():
                if trade['action'] == 'BUY':
                    total_spent += trade['amount']
                elif trade['action'] == 'SELL':
                    # Selling gives back SOL (simplified calculation)
                    total_spent -= trade['amount']
            
            # Start with 10 SOL and subtract spent amount
            balance = max(0.0, 1.0 - total_spent)
            return balance
            
        except Exception as e:
            logger.error(f"Error calculating simulation balance: {e}")
            return 10.0
    
    def get_trades(self, only_real=False, limit=100, days_back=None):
        """Get recent trades from the database with optional date filtering"""
        if not self.db_path or not os.path.exists(self.db_path):
            logger.error("Database file not found")
            return pd.DataFrame()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if is_simulation column exists
            cursor.execute("PRAGMA table_info(trades)")
            columns = [info[1] for info in cursor.fetchall()]
            
            # Build base query
            query = "SELECT * FROM trades"
            params = []
            conditions = []
            
            # Add date filtering if specified
            if days_back:
                cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
                conditions.append("timestamp >= ?")
                params.append(cutoff_date)
            
            # Add simulation filtering
            if 'is_simulation' in columns and only_real:
                conditions.append("is_simulation = 0")
            elif only_real:
                # Need to filter by contract address pattern later
                pass
            
            # Combine conditions
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY id DESC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            # Execute query
            trades_df = pd.read_sql_query(query, conn, params=params)
            
            # Additional filtering by contract address if needed
            if only_real and 'is_simulation' not in columns:
                trades_df = trades_df[~trades_df['contract_address'].apply(self._is_simulation_contract)]
                trades_df = trades_df.head(limit) if limit else trades_df
            
            conn.close()
            return trades_df
        
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return pd.DataFrame()
    
    def get_trade_summary_by_period(self, days=30):
        """Get trading summary for the specified period"""
        trades_df = self.get_trades(days_back=days)
        
        if trades_df.empty:
            return {
                'total_trades': 0,
                'buy_trades': 0,
                'sell_trades': 0,
                'total_volume_sol': 0.0,
                'unique_tokens': 0,
                'real_trades': 0,
                'sim_trades': 0
            }
        
        # Basic counts
        total_trades = len(trades_df)
        buy_trades = len(trades_df[trades_df['action'] == 'BUY'])
        sell_trades = len(trades_df[trades_df['action'] == 'SELL'])
        unique_tokens = trades_df['contract_address'].nunique()
        total_volume = trades_df['amount'].sum()
        
        # Real vs simulation counts
        real_trades = len(trades_df[~trades_df['contract_address'].apply(self._is_simulation_contract)])
        sim_trades = total_trades - real_trades
        
        return {
            'total_trades': total_trades,
            'buy_trades': buy_trades,
            'sell_trades': sell_trades,
            'total_volume_sol': total_volume,
            'unique_tokens': unique_tokens,
            'real_trades': real_trades,
            'sim_trades': sim_trades,
            'period_days': days
        }
    
    def get_daily_trading_activity(self, days=7):
        """Get daily trading activity for the past N days"""
        trades_df = self.get_trades(days_back=days)
        
        if trades_df.empty:
            return pd.DataFrame()
        
        try:
            # Convert timestamp to date
            trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
            trades_df['date'] = trades_df['timestamp'].dt.date
            
            # Group by date and calculate daily stats
            daily_stats = trades_df.groupby('date').agg({
                'id': 'count',  # Total trades
                'amount': 'sum',  # Total volume
                'contract_address': 'nunique'  # Unique tokens
            }).reset_index()
            
            daily_stats.columns = ['date', 'trades', 'volume_sol', 'unique_tokens']
            
            # Add real vs sim breakdown
            daily_real = trades_df[~trades_df['contract_address'].apply(self._is_simulation_contract)].groupby('date').size().reset_index(name='real_trades')
            daily_sim = trades_df[trades_df['contract_address'].apply(self._is_simulation_contract)].groupby('date').size().reset_index(name='sim_trades')
            
            # Merge all data
            daily_stats = daily_stats.merge(daily_real, on='date', how='left')
            daily_stats = daily_stats.merge(daily_sim, on='date', how='left')
            daily_stats = daily_stats.fillna(0)
            
            return daily_stats.sort_values('date', ascending=False)
            
        except Exception as e:
            logger.error(f"Error calculating daily activity: {e}")
            return pd.DataFrame()
    
    def get_active_positions(self, only_real=False):
        """Get active positions (tokens where bought > sold)"""
        if not self.db_path or not os.path.exists(self.db_path):
            logger.error("Database file not found")
            return pd.DataFrame()
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get trades
            trades_df = self.get_trades(only_real=only_real, limit=1000)
            
            if trades_df.empty:
                conn.close()
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
                    
                    # Get latest buy timestamp
                    latest_buy = buys['timestamp'].max() if 'timestamp' in buys.columns else None
                    
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
                    
                    # Calculate current value (would need current price in real implementation)
                    current_price = avg_buy_price  # Simplified - use buy price as current price
                    current_value = (total_bought - total_sold) * current_price
                    
                    # Add to active positions
                    active_positions.append({
                        'contract_address': address,
                        'ticker': ticker,
                        'name': name,
                        'amount': total_bought - total_sold,
                        'buy_price': avg_buy_price,
                        'current_price': current_price,
                        'current_value_sol': current_value,
                        'entry_time': latest_buy,
                        'is_simulation': self._is_simulation_contract(address)
                    })
            
            conn.close()
            
            # Convert to DataFrame
            if active_positions:
                return pd.DataFrame(active_positions)
            else:
                return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting active positions: {e}")
            return pd.DataFrame()
    
    def calculate_pl_metrics(self, only_real=False, days_back=None):
        """Calculate detailed profit/loss metrics"""
        if not self.db_path or not os.path.exists(self.db_path):
            logger.error("Database file not found")
            return {}
        
        try:
            # Get trades
            trades_df = self.get_trades(only_real=only_real, days_back=days_back, limit=1000)
            
            if trades_df.empty:
                return {
                    "win_rate": 0.0,
                    "total_pl_sol": 0.0,
                    "total_pl_usd": 0.0,
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "best_trade_pct": 0.0,
                    "worst_trade_pct": 0.0,
                    "avg_trade_pct": 0.0,
                    "total_invested_sol": 0.0,
                    "total_returned_sol": 0.0
                }
            
            # Calculate metrics
            total_pl_sol = 0.0
            completed_trades = 0
            winning_trades = 0
            losing_trades = 0
            trade_percentages = []
            total_invested = 0.0
            total_returned = 0.0
            
            # Group by contract address
            for address, group in trades_df.groupby('contract_address'):
                buys = group[group['action'] == 'BUY']
                sells = group[group['action'] == 'SELL']
                
                if buys.empty or sells.empty:
                    continue
                
                # Calculate total invested and returned for this token
                token_invested = (buys['amount'] * buys['price']).sum()
                token_returned = (sells['amount'] * sells['price']).sum()
                
                total_invested += token_invested
                total_returned += token_returned
                
                # For each sell, find a matching buy
                for _, sell in sells.iterrows():
                    # Find buys that happened before this sell
                    prior_buys = buys
                    if 'timestamp' in buys.columns and 'timestamp' in sell:
                        try:
                            prior_buys = buys[pd.to_datetime(buys['timestamp']) < pd.to_datetime(sell['timestamp'])]
                        except:
                            pass
                    
                    if prior_buys.empty:
                        continue
                    
                    # Use the earliest buy
                    buy = prior_buys.iloc[0]
                    
                    # Calculate profit
                    buy_price = buy['price']
                    sell_price = sell['price']
                    amount = min(buy['amount'], sell['amount'])
                    
                    profit = (sell_price - buy_price) * amount
                    total_pl_sol += profit
                    
                    # Calculate percentage change
                    if buy_price > 0:
                        percentage = ((sell_price / buy_price) - 1) * 100
                        trade_percentages.append(percentage)
                        
                        if percentage > 0:
                            winning_trades += 1
                        else:
                            losing_trades += 1
                    
                    completed_trades += 1
            
            # Calculate metrics
            win_rate = (winning_trades / completed_trades * 100) if completed_trades > 0 else 0.0
            best_trade_pct = max(trade_percentages) if trade_percentages else 0.0
            worst_trade_pct = min(trade_percentages) if trade_percentages else 0.0
            avg_trade_pct = sum(trade_percentages) / len(trade_percentages) if trade_percentages else 0.0
            
            # Calculate USD value
            sol_price = self.get_sol_price()
            total_pl_usd = total_pl_sol * sol_price
            
            return {
                "win_rate": win_rate,
                "total_pl_sol": total_pl_sol,
                "total_pl_usd": total_pl_usd,
                "total_trades": completed_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "best_trade_pct": best_trade_pct,
                "worst_trade_pct": worst_trade_pct,
                "avg_trade_pct": avg_trade_pct,
                "total_invested_sol": total_invested,
                "total_returned_sol": total_returned,
                "period_days": days_back
            }
            
        except Exception as e:
            logger.error(f"Error calculating P&L metrics: {e}")
            return {}
    
    def get_bot_status(self):
        """Get the bot status from bot_control.json"""
        control_files = [
            'data/bot_control.json',
            'bot_control.json',
            'core/bot_control.json'
        ]
        
        for control_file in control_files:
            if os.path.exists(control_file):
                try:
                    with open(control_file, 'r') as f:
                        control = json.load(f)
                    
                    return {
                        'running': control.get('running', False),
                        'simulation_mode': control.get('simulation_mode', True),
                        'take_profit_target': control.get('take_profit_target', 0.0),
                        'stop_loss_percentage': control.get('stop_loss_percentage', 0.0),
                        'max_investment_per_token': control.get('max_investment_per_token', 0.0),
                        'use_machine_learning': control.get('use_machine_learning', False),
                        'filter_fake_tokens': control.get('filter_fake_tokens', True),
                        'config_file': control_file
                    }
                except Exception as e:
                    logger.error(f"Error loading {control_file}: {e}")
        
        return {
            'running': False,
            'simulation_mode': True,
            'take_profit_target': 0.0,
            'stop_loss_percentage': 0.0,
            'max_investment_per_token': 0.0,
            'use_machine_learning': False,
            'filter_fake_tokens': True,
            'config_file': 'default'
        }
    
    def display_enhanced_summary(self):
        """Display an enhanced summary of trading activity"""
        print("\n" + "="*80)
        print("ENHANCED SOLANA TRADING BOT - COMPREHENSIVE STATUS")
        print("="*80)
        
        # Get current time and SOL price
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sol_price = self.get_sol_price()
        
        print(f"Report Generated: {current_time}")
        print(f"SOL Price: ${sol_price:.2f} USD")
        
        # Get bot status
        status = self.get_bot_status()
        print(f"Config Source: {status['config_file']}")
        
        # Get wallet balance
        wallet_balance = self.get_wallet_balance()
        wallet_usd = wallet_balance * sol_price
        
        print("\n" + "="*80)
        print("WALLET & BALANCE INFORMATION")
        print("="*80)
        print(f"SOL Balance: {wallet_balance:.6f} SOL")
        print(f"USD Value: ${wallet_usd:.2f}")
        print(f"Balance Type: {'Simulated' if status['simulation_mode'] else 'Real Wallet'}")
        
        # Bot configuration
        print("\n" + "="*80)
        print("BOT CONFIGURATION")
        print("="*80)
        print(f"Status: {'RUNNING' if status['running'] else 'STOPPED'}")
        print(f"Mode: {'SIMULATION' if status['simulation_mode'] else 'REAL TRADING'}")
        print(f"ML Enabled: {'YES' if status['use_machine_learning'] else 'NO'}")
        print(f"Filter Fake Tokens: {'YES' if status['filter_fake_tokens'] else 'NO'}")
        print(f"Take Profit Target: {status['take_profit_target']:.1f}x")
        print(f"Stop Loss: {status['stop_loss_percentage']*100:.1f}%")
        print(f"Max Investment: {status['max_investment_per_token']:.4f} SOL")
        
        # Get trading summary for different periods
        summary_7d = self.get_trade_summary_by_period(7)
        summary_30d = self.get_trade_summary_by_period(30)
        
        print("\n" + "="*80)
        print("TRADING ACTIVITY SUMMARY")
        print("="*80)
        print(f"{'Period':<12} {'Trades':<8} {'Buys':<6} {'Sells':<6} {'Volume':<12} {'Tokens':<8} {'Real':<6} {'Sim':<6}")
        print("-" * 80)
        print(f"{'Last 7 days':<12} {summary_7d['total_trades']:<8} {summary_7d['buy_trades']:<6} {summary_7d['sell_trades']:<6} {summary_7d['total_volume_sol']:<12.3f} {summary_7d['unique_tokens']:<8} {summary_7d['real_trades']:<6} {summary_7d['sim_trades']:<6}")
        print(f"{'Last 30 days':<12} {summary_30d['total_trades']:<8} {summary_30d['buy_trades']:<6} {summary_30d['sell_trades']:<6} {summary_30d['total_volume_sol']:<12.3f} {summary_30d['unique_tokens']:<8} {summary_30d['real_trades']:<6} {summary_30d['sim_trades']:<6}")
        
        # P&L Analysis
        print("\n" + "="*80)
        print("PROFIT & LOSS ANALYSIS")
        print("="*80)
        
        # Real trading P&L
        real_pl = self.calculate_pl_metrics(only_real=True, days_back=30)
        print("REAL TRADING (Last 30 days):")
        print(f"  Total Trades: {real_pl['total_trades']}")
        print(f"  Win Rate: {real_pl['win_rate']:.1f}% ({real_pl['winning_trades']} wins, {real_pl['losing_trades']} losses)")
        print(f"  Total P&L: {real_pl['total_pl_sol']:.6f} SOL (${real_pl['total_pl_usd']:.2f})")
        print(f"  Best Trade: {real_pl['best_trade_pct']:.1f}%")
        print(f"  Worst Trade: {real_pl['worst_trade_pct']:.1f}%")
        print(f"  Average Trade: {real_pl['avg_trade_pct']:.1f}%")
        print(f"  Total Invested: {real_pl['total_invested_sol']:.6f} SOL")
        print(f"  Total Returned: {real_pl['total_returned_sol']:.6f} SOL")
        
        # Simulation P&L
        sim_pl = self.calculate_pl_metrics(only_real=False, days_back=30)
        sim_pl_real = {k: v - real_pl.get(k, 0) for k, v in sim_pl.items() if isinstance(v, (int, float))}
        
        print("\nSIMULATION TRADING (Last 30 days):")
        print(f"  Total Trades: {sim_pl['total_trades'] - real_pl['total_trades']}")
        print(f"  Win Rate: {sim_pl_real.get('win_rate', 0):.1f}%")
        print(f"  Total P&L: {sim_pl_real.get('total_pl_sol', 0):.6f} SOL (${sim_pl_real.get('total_pl_usd', 0):.2f})")
        
        # Active positions
        print("\n" + "="*80)
        print("ACTIVE POSITIONS")
        print("="*80)
        
        # Real positions
        real_positions = self.get_active_positions(only_real=True)
        print("REAL POSITIONS:")
        if not real_positions.empty:
            print(f"{'Ticker':<10} {'Amount':<12} {'Buy Price':<12} {'Value (SOL)':<12} {'Entry Time':<20}")
            print("-" * 80)
            for _, pos in real_positions.iterrows():
                entry_time = pos['entry_time'][:19] if pos['entry_time'] else 'Unknown'
                print(f"{pos['ticker']:<10} {pos['amount']:<12.6f} ${pos['buy_price']:<11.6f} {pos['current_value_sol']:<12.6f} {entry_time:<20}")
        else:
            print("  No active real positions")
        
        # Simulation positions
        sim_positions = self.get_active_positions(only_real=False)
        sim_positions = sim_positions[sim_positions['is_simulation'] == True] if 'is_simulation' in sim_positions.columns else sim_positions
        
        print("\nSIMULATION POSITIONS:")
        if not sim_positions.empty:
            # Show first 5 simulation positions
            for _, pos in sim_positions.head(5).iterrows():
                entry_time = pos['entry_time'][:19] if pos['entry_time'] else 'Unknown'
                print(f"{pos['ticker']:<10} {pos['amount']:<12.6f} ${pos['buy_price']:<11.6f} {pos['current_value_sol']:<12.6f} {entry_time:<20}")
            
            if len(sim_positions) > 5:
                print(f"  ... and {len(sim_positions) - 5} more simulation positions")
        else:
            print("  No active simulation positions")
        
        # Daily activity
        print("\n" + "="*80)
        print("RECENT DAILY ACTIVITY")
        print("="*80)
        
        daily_activity = self.get_daily_trading_activity(7)
        if not daily_activity.empty:
            print(f"{'Date':<12} {'Trades':<8} {'Volume':<12} {'Real':<6} {'Sim':<6}")
            print("-" * 50)
            for _, day in daily_activity.iterrows():
                print(f"{day['date']:<12} {day['trades']:<8.0f} {day['volume_sol']:<12.3f} {day['real_trades']:<6.0f} {day['sim_trades']:<6.0f}")
        else:
            print("  No recent daily activity")
        
        # Recent trades
        print("\n" + "="*80)
        print("RECENT TRADES")
        print("="*80)
        
        recent_trades = self.get_trades(limit=10)
        
        if not recent_trades.empty:
            print(f"{'Type':<6} {'Action':<6} {'Token':<12} {'Amount':<12} {'Price':<12} {'Timestamp':<20}")
            print("-" * 80)
            for _, trade in recent_trades.iterrows():
                contract = trade['contract_address']
                ticker = contract[:8]
                
                # Format timestamp
                timestamp = trade.get('timestamp', 'Unknown')
                if isinstance(timestamp, str):
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                
                is_sim = self._is_simulation_contract(contract)
                trade_type = 'SIM' if is_sim else 'REAL'
                
                print(f"{trade_type:<6} {trade['action']:<6} {ticker:<12} {trade['amount']:<12.6f} ${trade['price']:<11.6f} {timestamp:<20}")
        else:
            print("  No recent trades")
        
        print("="*80)
        print(f"Report completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
    
    def display_wallet_details(self):
        """Display detailed wallet information"""
        print("\n" + "="*60)
        print("WALLET DETAILS")
        print("="*60)
        
        # Get wallet balance and SOL price
        balance = self.get_wallet_balance()
        sol_price = self.get_sol_price()
        usd_value = balance * sol_price
        
        print(f"SOL Balance: {balance:.6f} SOL")
        print(f"USD Value: ${usd_value:.2f}")
        print(f"SOL Price: ${sol_price:.2f}")
        
        # Get spent analysis
        if self.db_path and os.path.exists(self.db_path):
            try:
                conn = sqlite3.connect(self.db_path)
                trades_df = pd.read_sql_query("SELECT * FROM trades", conn)
                conn.close()
                
                if not trades_df.empty:
                    # Calculate total SOL spent on buys
                    buy_trades = trades_df[trades_df['action'] == 'BUY']
                    total_spent = buy_trades['amount'].sum()
                    
                    # Calculate total SOL received from sells
                    sell_trades = trades_df[trades_df['action'] == 'SELL']
                    total_received = sell_trades['amount'].sum()
                    
                    print(f"\nTrading Activity:")
                    print(f"Total SOL Spent: {total_spent:.6f} SOL")
                    print(f"Total SOL Received: {total_received:.6f} SOL")
                    print(f"Net Trading: {total_received - total_spent:.6f} SOL")
                    
                    # Calculate position values
                    positions = self.get_active_positions()
                    if not positions.empty:
                        total_position_value = positions['current_value_sol'].sum()
                        print(f"Current Positions Value: {total_position_value:.6f} SOL")
                        print(f"Free Balance: {balance - total_position_value:.6f} SOL")
            
            except Exception as e:
                logger.error(f"Error calculating wallet details: {e}")
        
        print("="*60)

def enhanced_monitor_trading(refresh_interval=30):
    """Enhanced monitoring with more detailed output"""
    monitor = EnhancedTradeMonitor()
    
    try:
        while True:
            # Clear screen
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # Display enhanced summary
            monitor.display_enhanced_summary()
            
            # Wait before next refresh
            for i in range(refresh_interval, 0, -1):
                sys.stdout.write(f"\rRefreshing in {i} seconds... (Press Ctrl+C to quit, 'w' for wallet details)")
                sys.stdout.flush()
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Solana Trading Bot Monitor')
    parser.add_argument('-i', '--interval', type=int, default=30, help='Refresh interval in seconds')
    parser.add_argument('-s', '--summary', action='store_true', help='Show summary and exit')
    parser.add_argument('-w', '--wallet', action='store_true', help='Show wallet details and exit')
    parser.add_argument('-p', '--positions', action='store_true', help='Show active positions and exit')
    parser.add_argument('-d', '--days', type=int, default=7, help='Number of days for analysis')
    
    args = parser.parse_args()
    
    monitor = EnhancedTradeMonitor()
    
    if args.summary:
        # Show enhanced summary and exit
        monitor.display_enhanced_summary()
    elif args.wallet:
        # Show wallet details and exit
        monitor.display_wallet_details()
    elif args.positions:
        # Show just positions
        positions = monitor.get_active_positions()
        if not positions.empty:
            print("Active Positions:")
            print(positions.to_string(index=False))
        else:
            print("No active positions found")
    else:
        # Start continuous monitoring
        enhanced_monitor_trading(refresh_interval=args.interval)