# trade_monitor.py - Simple, reliable trade monitoring for real and simulation trades

import os
import sys
import sqlite3
import pandas as pd
import time
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('trade_monitor')

class TradeMonitor:
    """Simple, reliable trade monitor for the Solana Trading Bot"""
    
    def __init__(self, db_path=None):
        """Initialize the trade monitor"""
        self.db_path = self._find_database() if db_path is None else db_path
        
    def _find_database(self):
        """Find the SQLite database file"""
        db_files = [
            'data/sol_bot.db',
            'data/trading_bot.db',
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
    
    def get_trades(self, only_real=False, limit=100):
        """Get recent trades from the database"""
        if not self.db_path or not os.path.exists(self.db_path):
            logger.error("Database file not found")
            return pd.DataFrame()
        
        try:
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if is_simulation column exists
            cursor.execute("PRAGMA table_info(trades)")
            columns = [info[1] for info in cursor.fetchall()]
            
            if 'is_simulation' in columns and only_real:
                # Filter by is_simulation column
                query = f"SELECT * FROM trades WHERE is_simulation = 0 ORDER BY id DESC LIMIT {limit}"
                trades_df = pd.read_sql_query(query, conn)
            elif only_real:
                # Filter by contract address pattern
                query = f"SELECT * FROM trades ORDER BY id DESC"
                all_trades = pd.read_sql_query(query, conn)
                trades_df = all_trades[~all_trades['contract_address'].apply(self._is_simulation_contract)]
                trades_df = trades_df.head(limit)  # Limit to requested count
            else:
                # Return all trades
                query = f"SELECT * FROM trades ORDER BY id DESC LIMIT {limit}"
                trades_df = pd.read_sql_query(query, conn)
            
            conn.close()
            return trades_df
        
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return pd.DataFrame()
    
    def get_active_positions(self, only_real=False):
        """Get active positions (tokens where bought > sold)"""
        if not self.db_path or not os.path.exists(self.db_path):
            logger.error("Database file not found")
            return pd.DataFrame()
        
        try:
            # Connect to database
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
                    
                    # Add to active positions
                    active_positions.append({
                        'contract_address': address,
                        'ticker': ticker,
                        'name': name,
                        'amount': total_bought - total_sold,
                        'buy_price': avg_buy_price,
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
    
    def calculate_pl_metrics(self, only_real=False):
        """Calculate profit/loss metrics"""
        if not self.db_path or not os.path.exists(self.db_path):
            logger.error("Database file not found")
            return {}
        
        try:
            # Get trades
            trades_df = self.get_trades(only_real=only_real, limit=1000)
            
            if trades_df.empty:
                return {
                    "win_rate": 0.0,
                    "total_pl_sol": 0.0,
                    "total_trades": 0,
                    "best_trade_pct": 0.0,
                    "worst_trade_pct": 0.0
                }
            
            # Calculate metrics
            total_pl_sol = 0.0
            completed_trades = 0
            winning_trades = 0
            trade_percentages = []
            
            # Group by contract address
            for address, group in trades_df.groupby('contract_address'):
                buys = group[group['action'] == 'BUY']
                sells = group[group['action'] == 'SELL']
                
                if buys.empty or sells.empty:
                    continue
                
                # For each sell, find a matching buy
                for _, sell in sells.iterrows():
                    # Find buys that happened before this sell
                    prior_buys = buys
                    if 'timestamp' in buys.columns and 'timestamp' in sell:
                        prior_buys = buys[pd.to_datetime(buys['timestamp']) < pd.to_datetime(sell['timestamp'])]
                    
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
                    
                    completed_trades += 1
            
            # Calculate win rate
            win_rate = (winning_trades / completed_trades * 100) if completed_trades > 0 else 0.0
            
            # Get best and worst trades
            best_trade_pct = max(trade_percentages) if trade_percentages else 0.0
            worst_trade_pct = min(trade_percentages) if trade_percentages else 0.0
            
            return {
                "win_rate": win_rate,
                "total_pl_sol": total_pl_sol,
                "total_trades": completed_trades,
                "best_trade_pct": best_trade_pct,
                "worst_trade_pct": worst_trade_pct
            }
            
        except Exception as e:
            logger.error(f"Error calculating P&L metrics: {e}")
            return {
                "win_rate": 0.0,
                "total_pl_sol": 0.0,
                "total_trades": 0,
                "best_trade_pct": 0.0,
                "worst_trade_pct": 0.0
            }
    
    def get_bot_status(self):
        """Get the bot status from bot_control.json"""
        control_files = [
            'data/bot_control.json',
            'bot_control.json'
        ]
        
        for control_file in control_files:
            if os.path.exists(control_file):
                try:
                    import json
                    with open(control_file, 'r') as f:
                        control = json.load(f)
                    
                    return {
                        'running': control.get('running', False),
                        'simulation_mode': control.get('simulation_mode', True),
                        'take_profit_target': control.get('take_profit_target', 0.0),
                        'stop_loss_percentage': control.get('stop_loss_percentage', 0.0),
                        'max_investment_per_token': control.get('max_investment_per_token', 0.0)
                    }
                except Exception as e:
                    logger.error(f"Error loading {control_file}: {e}")
        
        return {
            'running': False,
            'simulation_mode': True,
            'take_profit_target': 0.0,
            'stop_loss_percentage': 0.0,
            'max_investment_per_token': 0.0
        }
    
    def display_summary(self):
        """Display a summary of trading activity"""
        print("\n" + "="*60)
        print("SOLANA TRADING BOT - STATUS SUMMARY")
        print("="*60)
        
        # Get bot status
        status = self.get_bot_status()
        print(f"Bot Running: {'YES' if status['running'] else 'NO'}")
        print(f"Mode: {'SIMULATION' if status['simulation_mode'] else 'REAL TRADING'}")
        print(f"Take Profit: {status['take_profit_target']*100:.1f}%")
        print(f"Stop Loss: {status['stop_loss_percentage']*100:.1f}%")
        print(f"Max Investment: {status['max_investment_per_token']:.4f} SOL")
        
        # Get current time
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Current Time: {current_time}")
        
        # Display real trading stats
        print("\n" + "-"*60)
        print("REAL TRADING STATUS")
        print("-"*60)
        
        real_metrics = self.calculate_pl_metrics(only_real=True)
        print(f"Total Trades: {real_metrics['total_trades']}")
        print(f"Win Rate: {real_metrics['win_rate']:.1f}%")
        print(f"Total P&L: {real_metrics['total_pl_sol']:.6f} SOL")
        print(f"Best Trade: {real_metrics['best_trade_pct']:.1f}%")
        print(f"Worst Trade: {real_metrics['worst_trade_pct']:.1f}%")
        
        # Get active real positions
        real_positions = self.get_active_positions(only_real=True)
        print(f"\nActive Real Positions: {len(real_positions)}")
        
        if not real_positions.empty:
            for i, pos in real_positions.iterrows():
                print(f"  {pos['ticker']} - {pos['amount']:.6f} SOL @ ${pos['buy_price']:.8f}")
        else:
            print("  No active real positions")
        
        # Display simulation stats
        print("\n" + "-"*60)
        print("SIMULATION STATUS")
        print("-"*60)
        
        sim_metrics = self.calculate_pl_metrics(only_real=False)
        print(f"Total Trades: {sim_metrics['total_trades']}")
        print(f"Win Rate: {sim_metrics['win_rate']:.1f}%")
        print(f"Total P&L: {sim_metrics['total_pl_sol']:.6f} SOL")
        print(f"Best Trade: {sim_metrics['best_trade_pct']:.1f}%")
        print(f"Worst Trade: {sim_metrics['worst_trade_pct']:.1f}%")
        
        # Get active simulation positions
        sim_positions = self.get_active_positions(only_real=False)
        sim_positions = sim_positions[sim_positions['is_simulation'] == True] if 'is_simulation' in sim_positions.columns else sim_positions
        
        print(f"\nActive Simulation Positions: {len(sim_positions)}")
        
        if not sim_positions.empty:
            # Show only the first 5 to keep output clean
            for i, pos in sim_positions.head(5).iterrows():
                print(f"  {pos['ticker']} - {pos['amount']:.6f} SOL @ ${pos['buy_price']:.8f}")
            
            if len(sim_positions) > 5:
                print(f"  ... and {len(sim_positions) - 5} more")
        else:
            print("  No active simulation positions")
        
        # Recent trades
        print("\n" + "-"*60)
        print("RECENT TRADES")
        print("-"*60)
        
        recent_trades = self.get_trades(limit=10)
        
        if not recent_trades.empty:
            for i, trade in recent_trades.iterrows():
                contract = trade['contract_address']
                ticker = contract[:8]
                
                # Format timestamp
                timestamp = trade.get('timestamp', 'Unknown')
                if 'timestamp' in trade and isinstance(trade['timestamp'], str):
                    try:
                        dt = datetime.fromisoformat(trade['timestamp'].replace('Z', '+00:00'))
                        timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                
                is_sim = self._is_simulation_contract(contract)
                
                print(f"  {'[SIM]' if is_sim else '[REAL]'} {trade['action']} {ticker} - {trade['amount']:.6f} SOL @ ${trade['price']:.8f} - {timestamp}")
        else:
            print("  No recent trades")
        
        print("="*60)

def monitor_trading(refresh_interval=30):
    """Monitor trading activity with periodic refresh"""
    monitor = TradeMonitor()
    
    try:
        while True:
            # Clear screen (works on Windows and Unix)
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # Display summary
            monitor.display_summary()
            
            # Wait before next refresh
            for i in range(refresh_interval, 0, -1):
                sys.stdout.write(f"\rRefreshing in {i} seconds... (Press Ctrl+C to quit)")
                sys.stdout.flush()
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Solana Trading Bot Monitor')
    parser.add_argument('-i', '--interval', type=int, default=30, help='Refresh interval in seconds')
    parser.add_argument('-s', '--summary', action='store_true', help='Show summary and exit')
    
    args = parser.parse_args()
    
    if args.summary:
        # Just show summary once and exit
        monitor = TradeMonitor()
        monitor.display_summary()
    else:
        # Start continuous monitoring
        monitor_trading(refresh_interval=args.interval)