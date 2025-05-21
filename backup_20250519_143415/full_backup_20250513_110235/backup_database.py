import os
import sqlite3
import pandas as pd
import logging
from datetime import datetime, UTC
from typing import Optional, Dict

from config import BotConfiguration

logger = logging.getLogger('trading_bot.database')

class Database:
    """
    Database management for the trading bot
    """
    def __init__(self):
        """
        Initialize database connection
        """
        self.db_path = BotConfiguration.DB_PATH
        if not self.db_path:
            raise ValueError("Database path is empty. Please set BotConfiguration.DB_PATH.")
        
        # Create directory if it has a path component
        db_dir = os.path.dirname(self.db_path)
        if db_dir:  # Only create directory if there's a path component
            os.makedirs(db_dir, exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._initialize_tables()
    
    def _initialize_tables(self):
        """
        Initialize database tables
        """
        # Tokens table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                contract_address TEXT PRIMARY KEY,
                ticker TEXT,
                name TEXT,
                launch_date TEXT,
                volume_24h REAL,
                safety_score REAL,
                liquidity_locked BOOLEAN
            )
        ''')

        # Trades table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_address TEXT,
                action TEXT,
                amount REAL,
                price REAL,
                timestamp TEXT,
                txid TEXT,
                FOREIGN KEY (contract_address) REFERENCES tokens (contract_address)
            )
        ''')

        # Active orders table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_orders (
                contract_address TEXT PRIMARY KEY,
                amount REAL,
                buy_price REAL,
                timestamp TEXT,
                FOREIGN KEY (contract_address) REFERENCES tokens (contract_address)
            )
        ''')

        self.conn.commit()
        logger.info("Database tables initialized")

    def store_token(self, contract_address: str, ticker: str, name: str, launch_date: str, volume_24h: float, safety_score: float, liquidity_locked: bool = False):
        """
        Store token data in the database
        """
        self.cursor.execute('''
            INSERT OR REPLACE INTO tokens (contract_address, ticker, name, launch_date, volume_24h, safety_score, liquidity_locked)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (contract_address, ticker, name, launch_date, volume_24h, safety_score, liquidity_locked))
        self.conn.commit()

    def get_token(self, contract_address: str) -> Optional[dict]:
        """
        Get token data by contract address
        """
        self.cursor.execute('SELECT * FROM tokens WHERE contract_address = ?', (contract_address,))
        result = self.cursor.fetchone()
        if result:
            return {
                'contract_address': result[0],
                'ticker': result[1],
                'name': result[2],
                'launch_date': result[3],
                'volume_24h': result[4],
                'safety_score': result[5],
                'liquidity_locked': bool(result[6])
            }
        return None

    def get_tokens(self, limit: int = 100, min_safety_score: float = 0.0) -> pd.DataFrame:
        """
        Get all tokens with optional filters
        """
        query = 'SELECT * FROM tokens WHERE safety_score >= ? ORDER BY safety_score DESC LIMIT ?'
        df = pd.read_sql_query(query, self.conn, params=(min_safety_score, limit))
        return df

    def record_trade(self, contract_address: str, action: str, amount: float, price: float, txid: str = None):
        """
        Record a trade in the database
        """
        timestamp = datetime.now(UTC).isoformat()
        self.cursor.execute('''
            INSERT INTO trades (contract_address, action, amount, price, timestamp, txid)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (contract_address, action, amount, price, timestamp, txid))
        
        if action.upper() == 'BUY':
            self.cursor.execute('''
                INSERT OR REPLACE INTO active_orders (contract_address, amount, buy_price, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (contract_address, amount, price, timestamp))
        elif action.upper() == 'SELL':
            self.cursor.execute('DELETE FROM active_orders WHERE contract_address = ?', (contract_address,))
        
        self.conn.commit()

    def get_active_orders(self) -> pd.DataFrame:
        """
        Get all active orders
        """
        return pd.read_sql_query('SELECT * FROM active_orders', self.conn)

    def get_trades(self, contract_address: str = None) -> pd.DataFrame:
        """
        Get trade history
        """
        if contract_address:
            query = 'SELECT * FROM trades WHERE contract_address = ? ORDER BY timestamp DESC'
            return pd.read_sql_query(query, self.conn, params=(contract_address,))
        return pd.read_sql_query('SELECT * FROM trades ORDER BY timestamp DESC', self.conn)

    def close(self):
        """
        Close database connection
        """
        self.conn.close()
        logger.info("Database connection closed")