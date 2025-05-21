"""
Quick utility to check active positions and recent trades in the database
"""
import os
import sys
import pandas as pd
import sqlite3
import time
from datetime import datetime

def check_database():
    """Check the database for active positions and recent trades"""
    # Find the database file
    db_files = [
        'data/sol_bot.db',
        'data/trading_bot.db',
        'sol_bot.db',
        'trading_bot.db',
    ]
    
    db_file = None
    for file in db_files:
        if os.path.exists(file):
            db_file = file
            break
    
    if not db_file:
        print("Database file not found!")
        return
    
    print(f"Using database: {db_file}")
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Connect to the database
    conn = sqlite3.connect(db_file)
    
    try:
        # Check if trades table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
        has_trades = cursor.fetchone() is not None
        
        if has_trades:
            # Get recent trades
            print("\n=== Recent Trades ===")
            trades_df = pd.read_sql("SELECT * FROM trades ORDER BY id DESC LIMIT 20", conn)
            
            if not trades_df.empty:
                # Calculate some additional information
                trades_with_info = []
                for _, trade in trades_df.iterrows():
                    trade_info = dict(trade)
                    
                    # Get token ticker if available
                    contract_address = trade['contract_address']
                    ticker = contract_address[:8]  # Default to first 8 chars
                    
                    try:
                        cursor.execute("SELECT ticker FROM tokens WHERE contract_address = ?", (contract_address,))
                        result = cursor.fetchone()
                        if result and result[0]:
                            ticker = result[0]
                    except:
                        pass
                    
                    trade_info['ticker'] = ticker
                    trades_with_info.append(trade_info)
                
                # Create a new DataFrame with the additional info
                enhanced_df = pd.DataFrame(trades_with_info)
                
                # Select only the most relevant columns for display
                display_cols = ['id', 'ticker', 'action', 'amount', 'price', 'tx_hash', 'timestamp']
                display_cols = [col for col in display_cols if col in enhanced_df.columns]
                
                # Display trades
                print(enhanced_df[display_cols])
                
                # Get trade counts
                buy_count = len(enhanced_df[enhanced_df['action'] == 'BUY'])
                sell_count = len(enhanced_df[enhanced_df['action'] == 'SELL'])
                print(f"\nTotal trades: {len(enhanced_df)} ({buy_count} buys, {sell_count} sells)")
            else:
                print("No trades found in the database.")
        else:
            print("No trades table found in the database.")
        
        # Calculate active positions
        print("\n=== Active Positions ===")
        print("Calculating positions from trade history...")
        
        if has_trades:
            # Get all trades
            all_trades_df = pd.read_sql("SELECT * FROM trades", conn)
            
            if not all_trades_df.empty:
                # Group by contract address
                active_positions = []
                
                for address, group in all_trades_df.groupby('contract_address'):
                    buys = group[group['action'] == 'BUY']
                    sells = group[group['action'] == 'SELL']
                    
                    # Calculate total bought and sold
                    total_bought = buys['amount'].sum()
                    total_sold = sells['amount'].sum() if not sells.empty else 0
                    
                    # If we have more bought than sold, this is an active position
                    if total_bought > total_sold:
                        # Get the ticker if possible
                        ticker = address[:8]  # Default to first 8 chars of address
                        
                        try:
                            cursor.execute("SELECT ticker FROM tokens WHERE contract_address = ?", (address,))
                            token_info = cursor.fetchone()
                            if token_info and token_info[0]:
                                ticker = token_info[0]
                        except:
                            pass
                        
                        # Calculate average buy price
                        avg_buy_price = (buys['amount'] * buys['price']).sum() / total_bought if total_bought > 0 else 0
                        
                        # Get the entry time (first buy)
                        entry_time = None
                        if 'timestamp' in buys.columns and not buys.empty:
                            try:
                                entry_time = buys['timestamp'].min()
                            except:
                                pass
                        
                        active_positions.append({
                            'contract_address': address,
                            'ticker': ticker,
                            'amount': total_bought - total_sold,
                            'avg_buy_price': avg_buy_price,
                            'value_sol': (total_bought - total_sold) * avg_buy_price,
                            'entry_time': entry_time or 'Unknown'
                        })
                
                if active_positions:
                    positions_df = pd.DataFrame(active_positions)
                    
                    # Format the value column for better display
                    if 'value_sol' in positions_df.columns:
                        positions_df['value_sol'] = positions_df['value_sol'].apply(lambda x: f"{x:.6f} SOL")
                    
                    if 'avg_buy_price' in positions_df.columns:
                        positions_df['avg_buy_price'] = positions_df['avg_buy_price'].apply(lambda x: f"{x:.8f}")
                    
                    # Sort by entry time if available
                    if 'entry_time' in positions_df.columns:
                        try:
                            positions_df = positions_df.sort_values('entry_time', ascending=False)
                        except:
                            pass
                    
                    print(positions_df)
                    print(f"\nTotal active positions: {len(positions_df)}")
                    
                    # Calculate total investment
                    total_amount = sum(position['amount'] for position in active_positions)
                    print(f"Total investment: {total_amount:.6f} SOL")
                else:
                    print("No active positions found.")
            else:
                print("No trades found to calculate positions.")
        
        # Check tokens table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tokens'")
        has_tokens = cursor.fetchone() is not None
        
        if has_tokens:
            # Count tokens
            cursor.execute("SELECT COUNT(*) FROM tokens")
            token_count = cursor.fetchone()[0]
            print(f"\n=== Token Stats ===")
            print(f"Total tokens in database: {token_count}")
            
            # Show some recent tokens
            if token_count > 0:
                print("\nMost recent tokens:")
                try:
                    recent_tokens = pd.read_sql(
                        "SELECT contract_address, ticker, name, price_usd, volume_24h, liquidity_usd FROM tokens ORDER BY last_updated DESC LIMIT 5", 
                        conn
                    )
                    print(recent_tokens)
                except Exception as e:
                    print(f"Error getting recent tokens: {e}")
    
    except Exception as e:
        print(f"Error checking database: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    check_database()
