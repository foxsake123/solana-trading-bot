# real_trade_verifier.py - Verify real trades on the Solana blockchain

import os
import sys
import sqlite3
import pandas as pd
import requests
import json
import time
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('real_trade_verifier')

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

def get_real_trades(db_file, limit=20):
    """
    Get real trades from the database
    
    :param db_file: Path to database file
    :param limit: Maximum number of trades to return
    :return: DataFrame of real trades
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
        
        if 'is_simulation' in columns:
            # If column exists, filter by it
            query = f"SELECT * FROM trades WHERE is_simulation = 0 ORDER BY id DESC LIMIT {limit}"
            trades_df = pd.read_sql_query(query, conn)
        else:
            # If column doesn't exist, filter by contract address
            query = f"SELECT * FROM trades ORDER BY id DESC LIMIT {limit * 2}"  # Get more to filter
            all_trades = pd.read_sql_query(query, conn)
            trades_df = all_trades[~all_trades['contract_address'].apply(is_simulation_contract)]
            trades_df = trades_df.head(limit)  # Limit to requested number
        
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

def verify_real_trades():
    """Verify real trades on the Solana blockchain"""
    db_file = find_database()
    
    if not db_file:
        print("Database file not found. Please ensure the database exists.")
        return
    
    print(f"Using database: {db_file}")
    print("\nChecking real trades for blockchain verification...")
    
    # Get real trades
    real_trades = get_real_trades(db_file)
    
    if real_trades is None or real_trades.empty:
        print("No real trades found in database.")
        return
    
    # Check if we have tx_hash column
    if 'tx_hash' not in real_trades.columns:
        print("No transaction hash column found in database.")
        return
    
    # Count
    total_trades = len(real_trades)
    verified_count = 0
    unverified_count = 0
    
    print(f"Found {total_trades} real trades. Verifying transactions...")
    
    verified_trades = []
    unverified_trades = []
    
    # Verify each transaction
    for _, trade in real_trades.iterrows():
        tx_hash = trade.get('tx_hash')
        
        if not tx_hash or pd.isna(tx_hash) or not isinstance(tx_hash, str) or tx_hash.startswith('SIM_'):
            unverified_trades.append(trade)
            unverified_count += 1
            continue
        
        # Print progress
        print(f"Verifying transaction: {tx_hash}...")
        
        # Verify the transaction
        tx_details = verify_transaction(tx_hash)
        
        if tx_details:
            # Add verification details to trade
            trade_verified = trade.copy()
            trade_verified['verified'] = True
            verified_trades.append(trade_verified)
            verified_count += 1
            print(f"  ✅ Verified successfully")
        else:
            # Mark as unverified
            trade_unverified = trade.copy()
            trade_unverified['verified'] = False
            unverified_trades.append(trade_unverified)
            unverified_count += 1
            print(f"  ❌ Not verified")
    
    # Print summary
    print("\n" + "="*60)
    print(f"VERIFICATION SUMMARY: {verified_count} verified, {unverified_count} unverified")
    print("="*60)
    
    if verified_trades:
        print("\nVERIFIED TRANSACTIONS:")
        for trade in verified_trades:
            print(f"  ✅ {trade['action']} {trade['contract_address'][:8]} - {trade['amount']:.6f} SOL - {trade['tx_hash']}")
    
    if unverified_trades:
        print("\nUNVERIFIED TRANSACTIONS:")
        for trade in unverified_trades:
            print(f"  ❌ {trade['action']} {trade['contract_address'][:8]} - {trade['amount']:.6f} SOL - {trade['tx_hash']}")

if __name__ == "__main__":
    verify_real_trades()