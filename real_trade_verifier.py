"""
Script to check and verify real trading transactions in the Solana Trading Bot database
"""
import os
import sys
import sqlite3
import pandas as pd
import time
import requests
import logging
from datetime import datetime, timezone
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('real_trade_checker')

def find_database():
    """Find the SQLite database file."""
    db_files = [
        'data/sol_bot.db',
        'data/trading_bot.db',
        'sol_bot.db',
        'trading_bot.db'
    ]
    
    for db_file in db_files:
        if os.path.exists(db_file):
            return db_file
    
    return None

def is_simulation_contract(address):
    """Check if a contract address appears to be a simulation address."""
    if not isinstance(address, str):
        return False
    
    return (
        address.startswith('Sim') or 
        'TopGainer' in address or
        'test' in address.lower() or
        'simulation' in address.lower() or
        'demo' in address.lower()
    )

def get_recent_trades(db_file, limit=20, only_real=True):
    """
    Get recent trades from the database
    
    :param db_file: Path to database file
    :param limit: Maximum number of trades to return
    :param only_real: Whether to return only real trades
    :return: DataFrame of trades
    """
    if not db_file or not os.path.exists(db_file):
        logger.error("Database file not found")
        return None
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Check if the 'is_simulation' column exists
        cursor.execute("PRAGMA table_info(trades)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'is_simulation' in columns and only_real:
            # If column exists, filter by it
            query = f"SELECT * FROM trades WHERE is_simulation = 0 ORDER BY id DESC LIMIT {limit}"
            trades_df = pd.read_sql_query(query, conn)
        elif only_real:
            # If column doesn't exist but we want real trades, filter by contract address
            query = f"SELECT * FROM trades ORDER BY id DESC LIMIT {limit * 2}"  # Get more to filter
            all_trades = pd.read_sql_query(query, conn)
            trades_df = all_trades[~all_trades['contract_address'].apply(is_simulation_contract)]
            trades_df = trades_df.head(limit)  # Limit to requested number
        else:
            # If we want all trades
            query = f"SELECT * FROM trades ORDER BY id DESC LIMIT {limit}"
            trades_df = pd.read_sql_query(query, conn)
        
        conn.close()
        return trades_df
    
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return None

def verify_transaction(tx_hash, rpc_endpoint=None):
    """
    Verify a transaction on the Solana blockchain
    
    :param tx_hash: Transaction hash/signature
    :param rpc_endpoint: RPC endpoint URL
    :return: Transaction details if valid, None otherwise
    """
    if not tx_hash or not isinstance(tx_hash, str) or tx_hash.startswith('SIM_'):
        return None
    
    # If it's a simulation transaction, return None
    if 'SIM' in tx_hash or 'simulation' in tx_hash.lower():
        return None
    
    try:
        # Get RPC endpoint
        if not rpc_endpoint:
            # Try to load from .env file
            if os.path.exists('.env'):
                with open('.env', 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('SOLANA_RPC_ENDPOINT='):
                            rpc_endpoint = line.split('=', 1)[1].strip().strip("'").strip('"')
            
            # If still not found, use default
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
        response = requests.post(rpc_endpoint, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and data['result'] is not None:
                return data['result']
            
        return None
    
    except Exception as e:
        logger.error(f"Error verifying transaction: {e}")
        return None

def get_verified_trades(db_file, limit=10):
    """
    Get and verify recent real trades
    
    :param db_file: Path to database file
    :param limit: Maximum number of trades to check
    :return: Tuple of (verified_trades, unverified_trades)
    """
    # Get recent real trades
    real_trades = get_recent_trades(db_file, limit, only_real=True)
    
    if real_trades is None or real_trades.empty:
        logger.warning("No real trades found")
        return [], []
    
    verified_trades = []
    unverified_trades = []
    
    for _, trade in real_trades.iterrows():
        tx_hash = trade.get('tx_hash')
        
        if not tx_hash or pd.isna(tx_hash) or not isinstance(tx_hash, str) or tx_hash.startswith('SIM_'):
            unverified_trades.append(trade)
            continue
        
        # Verify the transaction
        tx_details = verify_transaction(tx_hash)
        
        if tx_details:
            # Add verification details to trade
            trade_verified = trade.copy()
            trade_verified['verified'] = True
            trade_verified['tx_details'] = tx_details
            verified_trades.append(trade_verified)
        else:
            # Mark as unverified
            trade_unverified = trade.copy()
            trade_unverified['verified'] = False
            unverified_trades.append(trade_unverified)
    
    return verified_trades, unverified_trades

def print_trade_summary(trade, show_tx_details=False):
    """Print a summary of a trade."""
    if not isinstance(trade, dict) and not isinstance(trade, pd.Series):
        logger.error(f"Invalid trade format: {type(trade)}")
        return
    
    # Format timestamp
    timestamp = trade.get('timestamp', 'Unknown')
    try:
        if isinstance(timestamp, str):
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        pass
    
    # Print trade details
    print(f"\nTrade: {trade.get('contract_address', 'Unknown')}")
    print(f"  Action: {trade.get('action', 'Unknown')}")
    print(f"  Amount: {trade.get('amount', 0):.6f} SOL")
    print(f"  Price: ${trade.get('price', 0):.8f}")
    print(f"  Time: {timestamp}")
    print(f"  Transaction: {trade.get('tx_hash', 'None')}")
    
    # Print verification status
    if 'verified' in trade:
        print(f"  Verified: {'Yes ✅' if trade['verified'] else 'No ❌'}")
    
    # Print transaction details if requested
    if show_tx_details and 'tx_details' in trade and trade['tx_details']:
        print("\n  Transaction Details:")
        
        # Format the transaction details
        tx = trade['tx_details']
        
        # Basic transaction info
        if 'slot' in tx:
            print(f"    Slot: {tx['slot']}")
        
        if 'blockTime' in tx:
            block_time = datetime.fromtimestamp(tx['blockTime']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"    Block Time: {block_time}")
        
        # Transaction status
        if 'meta' in tx and 'err' in tx['meta']:
            if tx['meta']['err']:
                print(f"    Status: Failed ❌")
                print(f"    Error: {tx['meta']['err']}")
            else:
                print(f"    Status: Success ✅")
        
        # Transaction fee
        if 'meta' in tx and 'fee' in tx['meta']:
            fee_sol = tx['meta']['fee'] / 1_000_000_000  # Convert lamports to SOL
            print(f"    Fee: {fee_sol:.9f} SOL")
        
        # Post balances (if available)
        if 'meta' in tx and 'postBalances' in tx['meta'] and 'postTokenBalances' in tx['meta']:
            print(f"    Post-Transaction Token Balances: {len(tx['meta']['postTokenBalances'])}")

def main():
    # Find the database
    db_file = find_database()
    
    if not db_file:
        print("Database file not found. Please ensure the database exists.")
        return
    
    print(f"Using database: {db_file}")
    print("\nChecking recent real trades...")
    
    # Get and verify recent real trades
    verified_trades, unverified_trades = get_verified_trades(db_file, limit=10)
    
    # Print summary
    print(f"\nFound {len(verified_trades)} verified and {len(unverified_trades)} unverified real trades.")
    
    # Print verified trades
    if verified_trades:
        print("\n=== VERIFIED TRADES ===")
        for trade in verified_trades:
            print_trade_summary(trade)
            
        # Ask if user wants to see transaction details
        if len(verified_trades) > 0:
            show_details = input("\nShow transaction details for verified trades? (y/n): ")
            if show_details.lower() == 'y':
                print("\n=== TRANSACTION DETAILS ===")
                for trade in verified_trades:
                    print_trade_summary(trade, show_tx_details=True)
    
    # Print unverified trades
    if unverified_trades:
        print("\n=== UNVERIFIED TRADES ===")
        for trade in unverified_trades:
            print_trade_summary(trade)

if __name__ == "__main__":
    main()
