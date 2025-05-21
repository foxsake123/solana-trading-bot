import asyncio
import os
import sys
import json
import time
import random
import base64
import re
import logging
import logging.handlers
import traceback
import pandas as pd
import tweepy
import aiohttp
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Tuple, Any, Set, Union
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
import sqlite3

# Load environment variables from .env file
load_dotenv()

#################################
# CONFIGURATION AND DATABASE
#################################

class BotConfiguration:
    """
    Centralized configuration class for Solana Trading Bot
    """
    
    # File paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    DB_PATH = os.path.join(DATA_DIR, 'trading_bot.db')
    BOT_CONTROL_FILE = os.path.join(DATA_DIR, 'bot_control.json')
    
    # API endpoints and keys
    API_KEYS = {
        'TWITTER_BEARER_TOKEN': os.getenv('TWITTER_BEARER_TOKEN'),
        'SOLANA_RPC_ENDPOINT': os.getenv('SOLANA_RPC_ENDPOINT', 'https://mainnet.helius-rpc.com/?api-key=3c05add4-9974-4e11-a003-ef52c488edee'),
        'WALLET_PRIVATE_KEY': os.getenv('WALLET_PRIVATE_KEY'),
        'DEXSCREENER_BASE_URL': os.getenv('DEXSCREENER_BASE_URL', 'https://api.dexscreener.com'),
        'JUPITER_QUOTE_API': os.getenv('JUPITER_QUOTE_API', 'https://quote-api.jup.ag/v6/quote'),
        'JUPITER_SWAP_API': os.getenv('JUPITER_SWAP_API', 'https://quote-api.jup.ag/v6/swap'),
        'BIRDEYE_API_KEY': os.getenv('BIRDEYE_API_KEY', '')
    }
    
    # Trading parameters with defaults
    TRADING_PARAMETERS = {
        # Core trading parameters
        'MAX_BUY_RETRIES': int(os.getenv('MAX_BUY_RETRIES', 3)),
        'MAX_SELL_RETRIES': int(os.getenv('MAX_SELL_RETRIES', 3)),
        'SLIPPAGE_TOLERANCE': float(os.getenv('SLIPPAGE_TOLERANCE', 0.15)),  # 15%
        'TAKE_PROFIT_TARGET': float(os.getenv('TAKE_PROFIT_TARGET', 1.5)),   # 50% profit
        'STOP_LOSS_PERCENTAGE': float(os.getenv('STOP_LOSS_PERCENTAGE', 0.25)),  # 25% loss
        'MOONBAG_PERCENTAGE': float(os.getenv('MOONBAG_PERCENTAGE', 0.15)),  # 15% of position kept as moonbag
        'MAX_INVESTMENT_PER_TOKEN': float(os.getenv('MAX_INVESTMENT_PER_TOKEN', 0.1)),  # 0.1 SOL
        
        # Token screening parameters
        'MIN_SAFETY_SCORE': float(os.getenv('MIN_SAFETY_SCORE', 50.0)),
        'MIN_VOLUME': float(os.getenv('MIN_VOLUME', 10000)),          # $10K min volume
        'MIN_LIQUIDITY': float(os.getenv('MIN_LIQUIDITY', 50000)),   # $50K min liquidity
        'MIN_MCAP': float(os.getenv('MIN_MCAP', 100000)),             # $100K min market cap
        'MIN_HOLDERS': int(os.getenv('MIN_HOLDERS', 50)),            # 50 min holders
        
        # Top gainer thresholds
        'MIN_PRICE_CHANGE_1H': float(os.getenv('MIN_PRICE_CHANGE_1H', 5.0)),   # 5% min 1h gain
        'MIN_PRICE_CHANGE_6H': float(os.getenv('MIN_PRICE_CHANGE_6H', 10.0)),  # 10% min 6h gain
        'MIN_PRICE_CHANGE_24H': float(os.getenv('MIN_PRICE_CHANGE_24H', 20.0)), # 20% min 24h gain
        
        # Other settings
        'SCAN_INTERVAL': int(os.getenv('SCAN_INTERVAL', 300)),  # 5 minutes
        'TWITTER_RATE_LIMIT_BUFFER': int(os.getenv('TWITTER_RATE_LIMIT_BUFFER', 5)),
        'USE_BIRDEYE_API': os.getenv('USE_BIRDEYE_API', 'true').lower() == 'true'  # Default to using Birdeye API if key is provided
    }
    
    @classmethod
    def setup_bot_controls(cls):
        """
        Set up the bot control file if it doesn't exist
        """
        # Create data directory if it doesn't exist
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        
        if not os.path.exists(cls.BOT_CONTROL_FILE):
            control_data = {
                'running': True,
                'simulation_mode': True,
                'filter_fake_tokens': True,
                'use_birdeye_api': cls.TRADING_PARAMETERS['USE_BIRDEYE_API'],
                'max_investment_per_token': cls.TRADING_PARAMETERS['MAX_INVESTMENT_PER_TOKEN'],
                'take_profit_target': cls.TRADING_PARAMETERS['TAKE_PROFIT_TARGET'],
                'stop_loss_percentage': cls.TRADING_PARAMETERS['STOP_LOSS_PERCENTAGE'],
                'MIN_SAFETY_SCORE': cls.TRADING_PARAMETERS['MIN_SAFETY_SCORE'],
                'MIN_VOLUME': cls.TRADING_PARAMETERS['MIN_VOLUME'],
                'MIN_LIQUIDITY': cls.TRADING_PARAMETERS['MIN_LIQUIDITY'],
                'MIN_MCAP': cls.TRADING_PARAMETERS['MIN_MCAP'],
                'MIN_HOLDERS': cls.TRADING_PARAMETERS['MIN_HOLDERS'],
                'MIN_PRICE_CHANGE_1H': cls.TRADING_PARAMETERS['MIN_PRICE_CHANGE_1H'],
                'MIN_PRICE_CHANGE_6H': cls.TRADING_PARAMETERS['MIN_PRICE_CHANGE_6H'],
                'MIN_PRICE_CHANGE_24H': cls.TRADING_PARAMETERS['MIN_PRICE_CHANGE_24H']
            }
            
            with open(cls.BOT_CONTROL_FILE, 'w') as f:
                json.dump(control_data, f, indent=4)
            
        return True
    
    @classmethod
    def load_trading_parameters(cls):
        """
        Load trading parameters from control file
        """
        try:
            # Create the control file if it doesn't exist
            cls.setup_bot_controls()
            
            with open(cls.BOT_CONTROL_FILE, 'r') as f:
                control = json.load(f)
                
            # Update core trading parameters
            cls.TRADING_PARAMETERS['MAX_INVESTMENT_PER_TOKEN'] = control.get(
                'max_investment_per_token', 
                cls.TRADING_PARAMETERS['MAX_INVESTMENT_PER_TOKEN']
            )
            
            cls.TRADING_PARAMETERS['TAKE_PROFIT_TARGET'] = control.get(
                'take_profit_target', 
                cls.TRADING_PARAMETERS['TAKE_PROFIT_TARGET']
            )
            
            cls.TRADING_PARAMETERS['STOP_LOSS_PERCENTAGE'] = control.get(
                'stop_loss_percentage', 
                cls.TRADING_PARAMETERS['STOP_LOSS_PERCENTAGE']
            )
            
            # Update API usage settings
            cls.TRADING_PARAMETERS['USE_BIRDEYE_API'] = control.get(
                'use_birdeye_api',
                cls.TRADING_PARAMETERS['USE_BIRDEYE_API']
            )
            
            # Update screening parameters
            cls.TRADING_PARAMETERS['MIN_SAFETY_SCORE'] = control.get(
                'MIN_SAFETY_SCORE',
                cls.TRADING_PARAMETERS['MIN_SAFETY_SCORE']
            )
            
            cls.TRADING_PARAMETERS['MIN_VOLUME'] = control.get(
                'MIN_VOLUME',
                cls.TRADING_PARAMETERS['MIN_VOLUME']
            )
            
            cls.TRADING_PARAMETERS['MIN_LIQUIDITY'] = control.get(
                'MIN_LIQUIDITY',
                cls.TRADING_PARAMETERS['MIN_LIQUIDITY']
            )
            
            cls.TRADING_PARAMETERS['MIN_MCAP'] = control.get(
                'MIN_MCAP',
                cls.TRADING_PARAMETERS['MIN_MCAP']
            )
            
            cls.TRADING_PARAMETERS['MIN_HOLDERS'] = control.get(
                'MIN_HOLDERS',
                cls.TRADING_PARAMETERS['MIN_HOLDERS']
            )
            
            # Update top gainer thresholds
            cls.TRADING_PARAMETERS['MIN_PRICE_CHANGE_1H'] = control.get(
                'MIN_PRICE_CHANGE_1H',
                cls.TRADING_PARAMETERS['MIN_PRICE_CHANGE_1H']
            )
            
            cls.TRADING_PARAMETERS['MIN_PRICE_CHANGE_6H'] = control.get(
                'MIN_PRICE_CHANGE_6H',
                cls.TRADING_PARAMETERS['MIN_PRICE_CHANGE_6H']
            )
            
            cls.TRADING_PARAMETERS['MIN_PRICE_CHANGE_24H'] = control.get(
                'MIN_PRICE_CHANGE_24H',
                cls.TRADING_PARAMETERS['MIN_PRICE_CHANGE_24H']
            )
            
            # Return bot running status
            return control.get('running', True)
            
        except Exception as e:
            logging.error(f"Failed to load trading parameters: {e}")
            return True  # Default to running

class Database:
    """
    SQLite database for storing discovered tokens and trades
    """
    
    def __init__(self):
        """
        Initialize database connection
        """
        self.db_path = BotConfiguration.DB_PATH
        self._initialize_db()
    
    def _initialize_db(self):
        """
        Initialize database tables if they don't exist
        """
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tokens table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tokens (
                    contract_address TEXT PRIMARY KEY,
                    ticker TEXT,
                    name TEXT,
                    launch_date TEXT,
                    safety_score REAL DEFAULT 0.0,
                    volume_24h REAL DEFAULT 0.0,
                    liquidity_locked BOOLEAN DEFAULT FALSE,
                    last_updated TEXT
                )
            ''')
            
            # Create trades table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_address TEXT,
                    action TEXT,
                    amount REAL,
                    price REAL,
                    timestamp TEXT,
                    tx_signature TEXT
                )
            ''')
            
            # Index for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_contract ON trades (contract_address)')
            
            conn.commit()
            conn.close()
            
            logging.info("Database tables initialized")
        
        except Exception as e:
            logging.error(f"Database initialization error: {e}")
            raise
    
    def store_token(self, contract_address: str, ticker: str, name: str, 
                   launch_date: str, safety_score: float = 0.0, 
                   volume_24h: float = 0.0, liquidity_locked: bool = False):
        """
        Store token information in database
        
        :param contract_address: Token contract address
        :param ticker: Token ticker symbol
        :param name: Token name
        :param launch_date: Token launch date
        :param safety_score: Token safety score
        :param volume_24h: 24-hour trading volume
        :param liquidity_locked: Whether liquidity is locked
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if token already exists
            cursor.execute(
                'SELECT contract_address FROM tokens WHERE contract_address = ?', 
                (contract_address,)
            )
            token = cursor.fetchone()
            
            timestamp = datetime.now(UTC).isoformat()
            
            if token:
                # Update existing token
                cursor.execute('''
                    UPDATE tokens SET 
                        ticker = ?,
                        name = ?,
                        safety_score = ?,
                        volume_24h = ?,
                        liquidity_locked = ?,
                        last_updated = ?
                    WHERE contract_address = ?
                ''', (
                    ticker, name, safety_score, volume_24h,
                    liquidity_locked, timestamp, contract_address
                ))
            else:
                # Insert new token
                cursor.execute('''
                    INSERT INTO tokens (
                        contract_address, ticker, name, launch_date,
                        safety_score, volume_24h, liquidity_locked, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    contract_address, ticker, name, launch_date,
                    safety_score, volume_24h, liquidity_locked, timestamp
                ))
            
            conn.commit()
            conn.close()
        
        except Exception as e:
            logging.error(f"Failed to store token {contract_address}: {e}")
    
    def record_trade(self, contract_address: str, action: str, amount: float, 
                    price: float, tx_signature: str = None):
        """
        Record a trade in database
        
        :param contract_address: Token contract address
        :param action: Trade action (BUY/SELL)
        :param amount: Trade amount in SOL
        :param price: Trade price in SOL
        :param tx_signature: Transaction signature
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert trade record
            cursor.execute('''
                INSERT INTO trades (
                    contract_address, action, amount, price, timestamp, tx_signature
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                contract_address, action, amount, price, 
                datetime.now(UTC).isoformat(), tx_signature
            ))
            
            conn.commit()
            conn.close()
        
        except Exception as e:
            logging.error(f"Failed to record trade for {contract_address}: {e}")
    
    def get_active_orders(self):
        """
        Get active orders (tokens that have been bought but not fully sold)
        
        :return: DataFrame with active orders
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Identify active positions
            query = '''
                SELECT 
                    t1.contract_address,
                    (SELECT ticker FROM tokens WHERE contract_address = t1.contract_address) as ticker,
                    t1.price as buy_price,
                    t1.amount as amount,
                    t1.timestamp
                FROM trades t1
                JOIN (
                    SELECT 
                        contract_address,
                        SUM(CASE WHEN action = 'BUY' THEN amount ELSE -amount END) as net_amount
                    FROM trades
                    GROUP BY contract_address
                    HAVING net_amount > 0
                ) t2 ON t1.contract_address = t2.contract_address
                WHERE t1.action = 'BUY'
                ORDER BY t1.timestamp DESC
            '''
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Deduplicate to keep only the latest buy for each token
            if not df.empty:
                df = df.drop_duplicates(subset=['contract_address'], keep='first')
            
            return df
        
        except Exception as e:
            logging.error(f"Failed to get active orders: {e}")
            return pd.DataFrame()
    
    def get_trading_history(self, limit: int = 100):
        """
        Get trading history
        
        :param limit: Maximum number of trades to return
        :return: DataFrame with trading history
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = f'''
                SELECT
                    id,
                    contract_address,
                    (SELECT ticker FROM tokens WHERE contract_address = trades.contract_address) as ticker,
                    action,
                    amount,
                    price,
                    timestamp,
                    tx_signature
                FROM trades
                ORDER BY timestamp DESC
                LIMIT {limit}
            '''
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            return df
        
        except Exception as e:
            logging.error(f"Failed to get trading history: {e}")
            return pd.DataFrame()
    
    def get_tokens(self, limit: int = 100, min_safety_score: float = 0.0):
        """
        Get discovered tokens
        
        :param limit: Maximum number of tokens to return
        :param min_safety_score: Minimum safety score
        :return: DataFrame with tokens
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = f'''
                SELECT *
                FROM tokens
                WHERE safety_score >= {min_safety_score}
                ORDER BY last_updated DESC
                LIMIT {limit}
            '''
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            return df
        
        except Exception as e:
            logging.error(f"Failed to get tokens: {e}")
            return pd.DataFrame()

#################################
# UTILITY FUNCTIONS
#################################

# Rate limiting tracking for different API endpoints
RATE_LIMIT_STATE = {
    'dexscreener': {
        'consecutive_limits': 0,
        'backoff_until': 0,
        'last_request_time': 0,
        'request_count': 0,
        'window_start': time.time(),
        'max_requests_per_minute': 30
    }
}

def is_valid_solana_address(address: str) -> bool:
    """
    Check if a string is a valid Solana address
    
    :param address: String to check
    :return: True if valid Solana address, False otherwise
    """
    if not isinstance(address, str) or len(address) < 32 or len(address) > 44:
        return False
    
    try:
        Pubkey.from_string(address)
        return True
    except Exception:
        return False

async def fetch_with_retries(url: str, method: str = 'GET', 
                           headers: Optional[Dict] = None,
                           params: Optional[Dict] = None, 
                           json_data: Optional[Dict] = None,
                           max_retries: int = 5,
                           base_delay: int = 2) -> Optional[Dict]:
    """
    Fetch data from API with improved retry and rate limiting mechanism
    
    :param url: URL to fetch
    :param method: HTTP method
    :param headers: HTTP headers
    :param params: Query parameters
    :param json_data: JSON data for POST requests
    :param max_retries: Maximum retry attempts
    :param base_delay: Base delay between retries
    :return: API response as dictionary or None
    """
    # First check for problematic tokens in URL
    suspicious_terms = ['pump', 'moon', 'scam', 'fake', 'elon', 'musk', 'inu', 'shib', 'doge']
    for term in suspicious_terms:
        if term in url.lower():
            logging.warning(f"Skipping URL with suspicious term '{term}': {url}")
            return None
    
    # Set default headers
    if headers is None:
        headers = {'accept': 'application/json'}
    
    # Fix for DexScreener API - if using the invalid endpoint, switch to a valid one
    # This is a key fix based on the error logs
    if url.endswith('/pairs/solana') and 'dexscreener.com' in url:
        # Use tokens endpoint instead which works
        url = url.replace('/pairs/solana', '/tokens/solana')
        logging.info(f"Fixed DexScreener API URL to: {url}")
    
    # Fix for Jupiter API - ensure amount is a string
    if 'jup.ag' in url and params and 'amount' in params and not isinstance(params['amount'], str):
        params['amount'] = str(params['amount'])
    
    # Determine which API is being used
    api_type = None
    if 'dexscreener.com' in url:
        api_type = 'dexscreener'
    
    # Check if we're in a backoff period for this API
    current_time = time.time()
    if api_type and current_time < RATE_LIMIT_STATE[api_type]['backoff_until']:
        # Still in backoff period, wait longer
        wait_remaining = int(RATE_LIMIT_STATE[api_type]['backoff_until'] - current_time)
        logging.warning(f"Still in rate limit backoff period for {api_type}. Waiting {wait_remaining} seconds.")
        await asyncio.sleep(wait_remaining)
    
    # Track requests per minute for rate limiting
    if api_type:
        # Reset window if it's been more than a minute
        if current_time - RATE_LIMIT_STATE[api_type]['window_start'] > 60:
            RATE_LIMIT_STATE[api_type]['window_start'] = current_time
            RATE_LIMIT_STATE[api_type]['request_count'] = 0
        
        # Increment request count
        RATE_LIMIT_STATE[api_type]['request_count'] += 1
        RATE_LIMIT_STATE[api_type]['last_request_time'] = current_time
        
        # If approaching rate limit, add delay
        if RATE_LIMIT_STATE[api_type]['request_count'] >= RATE_LIMIT_STATE[api_type]['max_requests_per_minute']:
            # Calculate time until window resets
            time_to_reset = 60 - (current_time - RATE_LIMIT_STATE[api_type]['window_start'])
            logging.warning(f"Approaching rate limit for {api_type}. Sleeping {time_to_reset:.1f} seconds.")
            await asyncio.sleep(time_to_reset)
            
            # Reset window
            RATE_LIMIT_STATE[api_type]['window_start'] = time.time()
            RATE_LIMIT_STATE[api_type]['request_count'] = 1
    
    # Add small delay between consecutive requests to the same API
    if api_type and current_time - RATE_LIMIT_STATE[api_type]['last_request_time'] < 0.5:
        # Add small jitter to prevent request bursts
        await asyncio.sleep(random.uniform(0.3, 0.7))
    
    # Perform request with retries
    try:
        async with aiohttp.ClientSession() as session:
            for attempt in range(max_retries):
                try:
                    if method.upper() == 'POST':
                        async with session.post(
                            url, 
                            headers=headers, 
                            params=params, 
                            json=json_data, 
                            timeout=30
                        ) as response:
                            # Check for rate limiting response
                            if response.status == 429:
                                logging.warning(f"Rate limited by {url}, waiting for retry")
                                
                                # Apply exponential backoff with jitter
                                if api_type:
                                    RATE_LIMIT_STATE[api_type]['consecutive_limits'] += 1
                                    backoff_seconds = min(900, base_delay * (2 ** RATE_LIMIT_STATE[api_type]['consecutive_limits']))
                                    jitter = random.uniform(0.8, 1.2)  # Add 20% jitter
                                    wait_time = int(backoff_seconds * jitter)
                                    
                                    # Set backoff timestamp
                                    RATE_LIMIT_STATE[api_type]['backoff_until'] = current_time + wait_time
                                    
                                    logging.warning(f"Rate limited by {api_type}, waiting {wait_time} seconds")
                                    await asyncio.sleep(wait_time)
                                else:
                                    # Generic backoff if API type not recognized
                                    wait_time = base_delay * (2 ** attempt)
                                    await asyncio.sleep(wait_time)
                                
                                continue
                            
                            # Reset consecutive limit counter on successful non-429 response
                            if api_type and response.status != 429:
                                RATE_LIMIT_STATE[api_type]['consecutive_limits'] = 0
                            
                            # For all other responses
                            response.raise_for_status()
                            try:
                                data = await response.json()
                                return data
                            except Exception as e:
                                logging.error(f"Error parsing JSON response: {e}")
                                text_response = await response.text()
                                logging.error(f"Response content: {text_response[:200]}")
                                return None
                    else:
                        async with session.get(
                            url, 
                            headers=headers, 
                            params=params, 
                            timeout=30
                        ) as response:
                            # Check for rate limiting response
                            if response.status == 429:
                                logging.warning(f"Rate limited by {url}, waiting for retry")
                                
                                # Apply exponential backoff with jitter
                                if api_type:
                                    RATE_LIMIT_STATE[api_type]['consecutive_limits'] += 1
                                    backoff_seconds = min(900, base_delay * (2 ** RATE_LIMIT_STATE[api_type]['consecutive_limits']))
                                    jitter = random.uniform(0.8, 1.2)  # Add 20% jitter
                                    wait_time = int(backoff_seconds * jitter)
                                    
                                    # Set backoff timestamp
                                    RATE_LIMIT_STATE[api_type]['backoff_until'] = current_time + wait_time
                                    
                                    logging.warning(f"Rate limited by {api_type}, waiting {wait_time} seconds")
                                    await asyncio.sleep(wait_time)
                                else:
                                    # Generic backoff if API type not recognized
                                    wait_time = base_delay * (2 ** attempt)
                                    await asyncio.sleep(wait_time)
                                
                                continue
                            
                            # Reset consecutive limit counter on successful non-429 response
                            if api_type and response.status != 429:
                                RATE_LIMIT_STATE[api_type]['consecutive_limits'] = 0
                            
                            # For all other responses
                            if response.status == 404:
                                # Special handling for 404 responses
                                logging.warning(f"Resource not found at URL: {url}")
                                # Check if this is DexScreener API with a wrong endpoint
                                if 'dexscreener.com' in url and '/pairs/' in url:
                                    # Try to fix the endpoint and retry
                                    fixed_url = url.replace('/pairs/', '/tokens/')
                                    logging.info(f"Retrying with fixed URL: {fixed_url}")
                                    # Recursive call with fixed URL and reduced retries to avoid deep recursion
                                    return await fetch_with_retries(
                                        fixed_url, method, headers, params, json_data, 
                                        max_retries=2, base_delay=base_delay
                                    )
                                return None
                            
                            response.raise_for_status()
                            try:
                                data = await response.json()
                                return data
                            except Exception as e:
                                logging.error(f"Error parsing JSON response: {e}")
                                text_response = await response.text()
                                logging.error(f"Response content: {text_response[:200]}")
                                return None
                
                except aiohttp.ClientResponseError as e:
                    if e.status == 429:  # Rate limit exceeded
                        # This is now handled in the rate limit check above
                        pass
                    else:
                        logging.warning(f"Request error on attempt {attempt + 1}/{max_retries} for {url}: {e}")
                
                except Exception as e:
                    logging.warning(f"Fetch attempt {attempt + 1}/{max_retries} failed for {url}: {e}")
                
                # Apply exponential backoff with jitter
                if attempt < max_retries - 1:
                    backoff = base_delay * (2 ** attempt)
                    jitter = random.uniform(0.8, 1.2)  # Add 20% jitter
                    wait_time = backoff * jitter
                    await asyncio.sleep(wait_time)
    except Exception as e:
        # Catch any exceptions at the session level, which could cause the recursion error
        logging.error(f"Session-level error fetching {url}: {e}")
        return None
    
    logging.error(f"Failed to fetch {url} after {max_retries} attempts")
    return None

def is_fake_token(contract_address: str) -> bool:
    """
    Check if token address is likely a scam/fake
    
    :param contract_address: Token contract address
    :return: True if likely fake, False otherwise
    """
    # Validate input first
    if not contract_address or not isinstance(contract_address, str):
        logging.warning(f"Invalid contract address in is_fake_token: {contract_address}")
        return True  # Consider invalid addresses as fake
    
    # Convert to lowercase for case-insensitive comparison
    contract_address_lower = contract_address.lower()
    
    # Get control settings
    try:
        with open(BotConfiguration.BOT_CONTROL_FILE, 'r') as f:
            control = json.load(f)
            
        # Skip filtering if disabled in settings
        if not control.get('filter_fake_tokens', True):
            return False
    except:
        # Default to filtering enabled if settings can't be loaded
        pass
    
    # Check for common patterns in fake pump tokens
    if 'pump' in contract_address_lower:
        logging.warning(f"Detected 'pump' in token address: {contract_address}")
        return True
    
    # Check for 'moon' in the address
    if 'moon' in contract_address_lower:
        logging.warning(f"Detected 'moon' in token address: {contract_address}")
        return True
    
    # Additional suspicious terms
    suspicious_terms = ['scam', 'fake', 'elon', 'musk', 'inu', 'shib', 'doge']
    for term in suspicious_terms:
        if term in contract_address_lower:
            logging.warning(f"Detected suspicious term '{term}' in token address: {contract_address}")
            return True
    
    return False

def format_sol_amount(amount: float) -> str:
    """
    Format SOL amount with appropriate precision
    
    :param amount: SOL amount as float
    :return: Formatted SOL amount string
    """
    if amount >= 1:
        return f"{amount:.4f}"
    elif amount >= 0.0001:
        return f"{amount:.6f}"
    else:
        return f"{amount:.8f}"

def format_price_change(change: float) -> str:
    """
    Format price change with color indicator
    
    :param change: Price change as percentage
    :return: Formatted price change string
    """
    if change > 0:
        return f"+{change:.2f}%"
    elif change < 0:
        return f"{change:.2f}%"
    else:
        return "0.00%"

def parse_timeframe(timeframe: str) -> Optional[datetime]:
    """
    Parse human-readable timeframe to datetime
    
    :param timeframe: Timeframe string (e.g., '1h', '1d', '7d')
    :return: Datetime object or None if invalid
    """
    try:
        now = datetime.now(UTC)
        value = int(timeframe[:-1])
        unit = timeframe[-1].lower()
        
        if unit == 'm':
            return now - timedelta(minutes=value)
        elif unit == 'h':
            return now - timedelta(hours=value)
        elif unit == 'd':
            return now - timedelta(days=value)
        elif unit == 'w':
            return now - timedelta(weeks=value)
        else:
            return None
    except (ValueError, IndexError):
        return None

def truncate_address(address: str, chars: int = 4) -> str:
    """
    Truncate address for display
    
    :param address: Full address
    :param chars: Number of characters to keep at each end
    :return: Truncated address
    """
    if not address or len(address) <= chars * 2 + 2:
        return address
    return f"{address[:chars]}...{address[-chars:]}"

def calculate_profit_loss(buy_price: float, current_price: float) -> Dict:
    """
    Calculate profit/loss metrics
    
    :param buy_price: Buy price
    :param current_price: Current price
    :return: Dictionary with profit/loss metrics
    """
    if buy_price <= 0:
        return {'percentage': 0, 'multiple': 1}
    
    percentage = ((current_price - buy_price) / buy_price) * 100
    multiple = current_price / buy_price
    
    return {
        'percentage': percentage,
        'multiple': multiple
    }

#################################
# BIRDEYE API (DEX SCREENER FALLBACK)
#################################

class BirdeyeAPI:
    """
    Helper class that uses DexScreener API as a fallback for Birdeye
    This is a drop-in replacement that maintains the same interface
    """
    
    def __init__(self):
        """
        Initialize the API client
        """
        self.api_key = BotConfiguration.API_KEYS.get('BIRDEYE_API_KEY', '')
        self.base_url = "https://public-api.birdeye.so"
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
        
        # Set to True to use DexScreener exclusively and skip Birdeye attempts
        self.use_dexscreener_only = True
        
        # DexScreener base URL
        self.dexscreener_url = "https://api.dexscreener.com/latest/dex"
        
        # Rate limiting for DexScreener
        self.last_dexscreener_request = 0
        self.min_request_interval = 0.5  # Minimum time between requests (500ms)
        
        logging.info("BirdeyeAPI initialized with DexScreener fallback enabled")
    
    async def _wait_for_rate_limit(self):
        """
        Ensure we don't exceed rate limits for the DexScreener API
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_dexscreener_request
        
        if time_since_last_request < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last_request + random.uniform(0.1, 0.3))
        
        self.last_dexscreener_request = time.time()
    
    async def _get_from_dexscreener(self, contract_address: str) -> Optional[Dict]:
        """
        Get token data from DexScreener
        
        :param contract_address: Token contract address
        :return: Token data dictionary or None
        """
        try:
            # Ensure we respect rate limits
            await self._wait_for_rate_limit()
            
            # According to DexScreener docs, this is the correct endpoint format
            url = f"{self.dexscreener_url}/tokens/{contract_address}"
            
            # Use fetch_with_retries instead of direct aiohttp call
            data = await fetch_with_retries(url)
            
            if not data or 'pairs' not in data or not data['pairs']:
                logging.warning(f"No DexScreener data for {contract_address}")
                return None
            
            # Use first (typically most liquid) pair
            pair = data['pairs'][0]
            
            # According to the docs, baseToken contains the token info,
            # quoteToken is typically the token it's paired with (like USDC)
            if 'baseToken' not in pair or not pair['baseToken']:
                logging.warning(f"No baseToken data for {contract_address}")
                return None
            
            # Build a response that matches our expected format
            return {
                'address': contract_address,
                'symbol': pair.get('baseToken', {}).get('symbol', 'UNKNOWN'),
                'name': pair.get('baseToken', {}).get('name', 'UNKNOWN'),
                'price': {
                    'value': float(pair.get('priceUsd', 0.0))
                },
                'volume': {
                    'value': float(pair.get('volume', {}).get('h24', 0.0))
                },
                'liquidity': {
                    'value': float(pair.get('liquidity', {}).get('usd', 0.0))
                },
                'priceChange': {
                    '24H': float(pair.get('priceChange', {}).get('h24', 0.0)),
                    '6H': float(pair.get('priceChange', {}).get('h6', 0.0)) if 'h6' in pair.get('priceChange', {}) else 0.0,
                    '1H': float(pair.get('priceChange', {}).get('h1', 0.0)) if 'h1' in pair.get('priceChange', {}) else 0.0
                },
                'mc': {
                    'value': float(pair.get('mcap', 0.0) if 'mcap' in pair else 0.0)
                },
                'fdv': {
                    'value': float(pair.get('fdv', 0.0) if 'fdv' in pair else 0.0)
                },
                'holdersCount': int(pair.get('holders', 0) if 'holders' in pair else 0)
            }
        
        except Exception as e:
            logging.error(f"Error getting token from DexScreener: {e}")
            return None
    
    async def get_token_info(self, contract_address: str) -> Optional[Dict]:
        """
        Get detailed token information
        
        :param contract_address: Token contract address
        :return: Token information dictionary or None
        """
        # Validate contract address
        if not contract_address or not isinstance(contract_address, str):
            logging.warning(f"Invalid contract address in get_token_info: {contract_address}")
            return None
        
        # Check if token is likely fake
        if is_fake_token(contract_address):
            logging.warning(f"Skipping likely fake token in get_token_info: {contract_address}")
            return None
        
        # Check cache first
        cache_key = f"token_info_{contract_address}"
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.cache_duration:
                return cache_entry['data']
        
        # Use DexScreener
        token_info = await self._get_from_dexscreener(contract_address)
        
        if token_info:
            # Cache the result
            self.cache[cache_key] = {
                'timestamp': time.time(),
                'data': token_info
            }
            return token_info
        
        logging.warning(f"Failed to get token info for {contract_address}")
        return None
    
    async def get_token_price(self, contract_address: str) -> Optional[float]:
        """
        Get token price in USD
        
        :param contract_address: Token contract address
        :return: Token price in USD or None
        """
        token_info = await self.get_token_info(contract_address)
        if token_info and 'price' in token_info and 'value' in token_info['price']:
            return float(token_info['price']['value'])
        
        # Try CoinGecko for popular tokens
        if contract_address == "So11111111111111111111111111111111111111112":  # SOL
            try:
                # Using fetch_with_retries for consistency
                url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
                data = await fetch_with_retries(url)
                if data and 'solana' in data and 'usd' in data['solana']:
                    return float(data['solana']['usd'])
            except Exception as e:
                logging.error(f"Error getting SOL price from CoinGecko: {e}")
        
        return None
    
    async def get_token_volume(self, contract_address: str) -> Optional[float]:
        """
        Get 24h trading volume in USD
        
        :param contract_address: Token contract address
        :return: 24h volume in USD or None
        """
        token_info = await self.get_token_info(contract_address)
        if token_info and 'volume' in token_info and 'value' in token_info['volume']:
            return float(token_info['volume']['value'])
        return None
    
    async def get_token_liquidity(self, contract_address: str) -> Optional[float]:
        """
        Get token liquidity in USD
        
        :param contract_address: Token contract address
        :return: Liquidity in USD or None
        """
        token_info = await self.get_token_info(contract_address)
        if token_info and 'liquidity' in token_info and 'value' in token_info['liquidity']:
            return float(token_info['liquidity']['value'])
        return None
    
    async def get_holders_count(self, contract_address: str) -> Optional[int]:
        """
        Get number of token holders
        
        :param contract_address: Token contract address
        :return: Number of holders or None
        """
        token_info = await self.get_token_info(contract_address)
        if token_info and 'holdersCount' in token_info:
            return int(token_info['holdersCount'])
        return None
    
    async def get_market_cap(self, contract_address: str) -> Optional[float]:
        """
        Get market cap in USD
        
        :param contract_address: Token contract address
        :return: Market cap in USD or None
        """
        token_info = await self.get_token_info(contract_address)
        if token_info and 'mc' in token_info and 'value' in token_info['mc']:
            return float(token_info['mc']['value'])
        return None
    
    async def get_price_change(self, contract_address: str, timeframe: str) -> Optional[float]:
        """
        Get price change percentage for a given timeframe
        
        :param contract_address: Token contract address
        :param timeframe: Timeframe (1h, 6h, 24h)
        :return: Price change percentage or None
        """
        token_info = await self.get_token_info(contract_address)
        if not token_info or 'priceChange' not in token_info:
            return None
        
        price_change = token_info['priceChange']
        
        if timeframe == '1h' and '1H' in price_change:
            return float(price_change['1H'])
        elif timeframe == '6h' and '6H' in price_change:
            return float(price_change['6H'])
        elif timeframe == '24h' and '24H' in price_change:
            return float(price_change['24H'])
        
        return None
    
    async def _get_tokens_from_dexscreener(self, limit: int = 50) -> List[Dict]:
        """
        Get tokens list from DexScreener
        
        :param limit: Maximum number of tokens to return
        :return: List of tokens
        """
        try:
            # Ensure we respect rate limits
            await self._wait_for_rate_limit()
            
            # This is the correct endpoint for getting tokens
            url = f"{self.dexscreener_url}/tokens/solana"
            
            # Use fetch_with_retries instead of direct aiohttp call
            data = await fetch_with_retries(url)
            
            if not data or 'tokens' not in data or not data['tokens']:
                logging.warning("No tokens data from DexScreener")
                return []
            
            tokens = []
            for token in data['tokens'][:limit*2]:  # Get more to filter out potential fakes
                if 'pairs' not in token or not token['pairs']:
                    continue
                
                # Skip likely fake tokens
                if is_fake_token(token.get('address', '')):
                    continue
                
                # Get the most liquid pair
                pair = token['pairs'][0]
                
                # Create consistent token data structure
                token_data = {
                    'address': token.get('address'),
                    'symbol': pair.get('baseToken', {}).get('symbol', 'UNKNOWN'),
                    'name': pair.get('baseToken', {}).get('name', 'UNKNOWN'),
                    'price': {'value': float(pair.get('priceUsd', 0.0))},
                    'volume': {'value': float(pair.get('volume', {}).get('h24', 0.0))},
                    'liquidity': {'value': float(pair.get('liquidity', {}).get('usd', 0.0))},
                    'priceChange': {
                        '24H': float(pair.get('priceChange', {}).get('h24', 0.0)),
                        '6H': float(pair.get('priceChange', {}).get('h6', 0.0)) if 'h6' in pair.get('priceChange', {}) else 0.0,
                        '1H': float(pair.get('priceChange', {}).get('h1', 0.0)) if 'h1' in pair.get('priceChange', {}) else 0.0
                    },
                    'mc': {'value': float(pair.get('mcap', 0.0)) if 'mcap' in pair else 0.0},
                    'fdv': {'value': float(pair.get('fdv', 0.0)) if 'fdv' in pair else 0.0},
                    'holdersCount': int(pair.get('holders', 0)) if 'holders' in pair else 0,
                    'trendingScore': 0.0  # Calculated below
                }
                
                # Calculate a trending score based on volume and price activity
                volume_24h = float(pair.get('volume', {}).get('h24', 0.0))
                price_change_24h = abs(float(pair.get('priceChange', {}).get('h24', 0.0)))
                
                volume_score = min(100, volume_24h / 1000)  # Max score at $100K volume
                price_score = min(100, price_change_24h * 2)  # Max score at 50% price change
                token_data['trendingScore'] = (volume_score * 0.7) + (price_score * 0.3)
                
                tokens.append(token_data)
                
                # Limit to requested number of tokens
                if len(tokens) >= limit:
                    break
            
            logging.info(f"Retrieved {len(tokens)} tokens from DexScreener")
            return tokens
        
        except Exception as e:
            logging.error(f"Error fetching tokens from DexScreener: {e}")
            return []
    
    async def get_top_gainers(self, timeframe: str = '24h', limit: int = 10) -> List[Dict]:
        """
        Get list of top gaining tokens
        
        :param timeframe: Timeframe (1h, 6h, 24h)
        :param limit: Maximum number of tokens to return
        :return: List of top gainers
        """
        # Check cache
        cache_key = f"top_gainers_{timeframe}_{limit}"
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.cache_duration:
                return cache_entry['data']
        
        # Get tokens from DexScreener
        tokens = await self._get_tokens_from_dexscreener(50)  # Get more to filter from
        
        if not tokens:
            logging.warning(f"No tokens found for top gainers ({timeframe})")
            return []
        
        # Map timeframe to key in priceChange
        timeframe_key = '24H'
        if timeframe == '1h':
            timeframe_key = '1H'
        elif timeframe == '6h':
            timeframe_key = '6H'
        
        # Filter and sort by price change
        gainers = []
        for token in tokens:
            if 'priceChange' in token and timeframe_key in token['priceChange']:
                price_change = token['priceChange'][timeframe_key]
                if price_change > 0:
                    # Format token for consistent API response
                    gainers.append({
                        'contract_address': token['address'],
                        'ticker': token['symbol'],
                        'name': token['name'],
                        'price_change': price_change,
                        'price_usd': token['price']['value'],
                        'volume_24h': token['volume']['value'],
                        'liquidity_usd': token['liquidity']['value'],
                        'price_change_24h': token['priceChange'].get('24H', 0.0),
                        'price_change_6h': token['priceChange'].get('6H', 0.0),
                        'price_change_1h': token['priceChange'].get('1H', 0.0),
                        'mcap': token['mc']['value'],
                        'holders': token['holdersCount'],
                        'fdv': token['fdv']['value']
                    })
        
        # Sort by price change for the requested timeframe
        gainers.sort(key=lambda x: x['price_change'], reverse=True)
        
        # Limit to requested count
        result = gainers[:limit]
        
        # Cache result
        self.cache[cache_key] = {
            'timestamp': time.time(),
            'data': result
        }
        
        logging.info(f"Found {len(result)} top gainers for {timeframe}")
        return result
    
    async def get_trending_tokens(self, limit: int = 10) -> List[Dict]:
        """
        Get list of trending tokens based on volume and activity
        
        :param limit: Maximum number of tokens to return
        :return: List of trending tokens
        """
        # Check cache
        cache_key = f"trending_tokens_{limit}"
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.cache_duration:
                return cache_entry['data']
        
        # Get tokens from DexScreener and calculate trending score
        tokens = await self._get_tokens_from_dexscreener(50)
        
        if not tokens:
            logging.warning("No tokens found for trending tokens")
            return []
        
        # Format tokens for consistent API response
        trending_tokens = []
        for token in tokens:
            trending_tokens.append({
                'contract_address': token['address'],
                'ticker': token['symbol'],
                'name': token['name'],
                'volume_24h': token['volume']['value'],
                'price_usd': token['price']['value'],
                'price_change_24h': token['priceChange'].get('24H', 0.0),
                'liquidity_usd': token['liquidity']['value'],
                'trending_score': token.get('trendingScore', 0.0),
                'mcap': token['mc']['value'],
                'holders': token['holdersCount'],
                'fdv': token['fdv']['value']
            })
        
        # Sort by trending score
        trending_tokens.sort(key=lambda x: x.get('trending_score', 0), reverse=True)
        
        # Limit to requested count
        result = trending_tokens[:limit]
        
        # Cache result
        self.cache[cache_key] = {
            'timestamp': time.time(),
            'data': result
        }
        
        logging.info(f"Found {len(result)} trending tokens")
        return result
    
    async def get_token_security_info(self, contract_address: str) -> Optional[Dict]:
        """
        Get security information for a token (DexScreener doesn't provide this)
        
        :param contract_address: Token contract address
        :return: Security information or None
        """
        # DexScreener doesn't provide security info, so create a basic check
        token_info = await self.get_token_info(contract_address)
        
        if not token_info:
            return None
        
        # Calculate a basic security score based on liquidity, holders, etc.
        liquidity = token_info.get('liquidity', {}).get('value', 0.0)
        holders = token_info.get('holdersCount', 0)
        volume = token_info.get('volume', {}).get('value', 0.0)
        
        # Higher values are better
        liquidity_score = min(40, (liquidity / 10000))  # 40 points max for liquidity
        holders_score = min(30, (holders / 10))         # 30 points max for holders
        volume_score = min(30, (volume / 5000))         # 30 points max for volume
        
        security_score = liquidity_score + holders_score + volume_score
        
        # Basic security info
        return {
            'securityScore': security_score,
            'liquidityLocked': liquidity > 100000,  # Assume locked if high liquidity
            'mintingDisabled': False,               # Unknown from DexScreener
            'isMemeToken': 'meme' in token_info.get('name', '').lower() or 'meme' in token_info.get('symbol', '').lower()
        }

#################################
# TOKEN ANALYZER
#################################

class TokenAnalyzer:
    """
    Analyzes tokens for trading potential
    """
    def __init__(self, db=None):
        """
        Initialize token analyzer
        
        :param db: Database instance for storage (optional)
        """
        self.db = db
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self.twitter_client = self._setup_twitter_client()
        
        # Enhanced rate limiting for Twitter API
        self.twitter_requests_this_window = 0
        self.twitter_window_reset = int(time.time()) + 900  # 15-minute window
        self.twitter_rate_limit_max = 400  # Conservative limit (actual is 450)
        self.twitter_rate_limit_buffer = 50  # Buffer to prevent hitting limit
        self.backoff_duration = 5  # Start with 5 seconds
        self.consecutive_rate_limits = 0
        self.rate_limited_until = 0  # Timestamp when we can resume requests
        
        self.social_media_cache = {}
        self.price_cache = {}  # Cache for token prices
        self.social_media_disabled = False  # Flag to disable social media checks if too many rate limits
        
        # Initialize Birdeye API
        self.use_birdeye = BotConfiguration.TRADING_PARAMETERS.get('USE_BIRDEYE_API', False)
        self.birdeye = BirdeyeAPI()
        
    def _setup_twitter_client(self) -> Optional[tweepy.Client]:
        """
        Set up Twitter API client
        
        :return: Configured Twitter client or None
        """
        try:
            bearer_token = BotConfiguration.API_KEYS['TWITTER_BEARER_TOKEN']
            if not bearer_token:
                logging.warning("Twitter bearer token not provided")
                return None
            
            client = tweepy.Client(bearer_token=bearer_token)
            logging.debug("Twitter client initialized for token analyzer")
            return client
        
        except Exception as e:
            logging.error(f"Failed to set up Twitter client for token analyzer: {e}")
            return None

    def _check_twitter_rate_limit(self) -> bool:
        """
        Check if we should proceed with Twitter API request
        
        :return: True if we can proceed, False otherwise
        """
        current_time = int(time.time())
        
        # Check if we're currently in a backoff period
        if current_time < self.rate_limited_until:
            return False
        
        # Reset counter if window expired
        if current_time > self.twitter_window_reset:
            self.twitter_requests_this_window = 0
            self.twitter_window_reset = current_time + 900  # 15 minutes
            self.consecutive_rate_limits = 0  # Reset consecutive counter
        
        # If we're approaching the rate limit, don't proceed
        available_requests = self.twitter_rate_limit_max - self.twitter_requests_this_window
        if available_requests < self.twitter_rate_limit_buffer:
            logging.warning(f"Approaching Twitter API rate limit. {available_requests} requests left in window.")
            
            # Calculate time until window resets
            time_until_reset = self.twitter_window_reset - current_time
            logging.info(f"Waiting {time_until_reset} seconds until rate limit reset.")
            
            # Set backoff until window resets
            self.rate_limited_until = self.twitter_window_reset
            return False
        
        return True

    def _handle_rate_limit(self):
        """
        Handle rate limit hit with exponential backoff
        """
        self.consecutive_rate_limits += 1
        
        # Exponential backoff with jitter
        backoff = min(900, self.backoff_duration * (2 ** self.consecutive_rate_limits))
        jitter = random.uniform(0.8, 1.2)  # Add 20% jitter
        wait_time = int(backoff * jitter)
        
        # Set timestamp when we can resume requests
        current_time = int(time.time())
        self.rate_limited_until = current_time + wait_time
        
        logging.warning(f"Rate limited by Twitter API. Backing off for {wait_time} seconds.")
        
        # If we've hit rate limits too many times, disable social media temporarily
        if self.consecutive_rate_limits >= 5:
            logging.warning("Too many consecutive rate limits. Disabling social media analysis temporarily.")
            self.social_media_disabled = True
            # Disable for 30 minutes
            self.rate_limited_until = current_time + 1800

    async def get_top_gainers(self, timeframe: str = '24h', limit: int = 10) -> List[Dict]:
        """
        Get top gaining tokens for a given timeframe
        
        :param timeframe: Timeframe to check ('1h', '6h', '24h')
        :param limit: Maximum number of tokens to return
        :return: List of top gainer tokens
        """
        # Try Birdeye API
        try:
            tokens = await self.birdeye.get_top_gainers(timeframe, limit)
            if tokens:
                logging.info(f"Retrieved {len(tokens)} top gainers from API")
                return tokens
        except Exception as e:
            logging.error(f"Error getting top gainers: {e}")
            return []
    
    async def get_trending_tokens(self, limit: int = 10) -> List[Dict]:
        """
        Get trending tokens based on volume and social activity
        
        :param limit: Maximum number of tokens to return
        :return: List of trending tokens
        """
        # Try Birdeye API
        try:
            tokens = await self.birdeye.get_trending_tokens(limit)
            if tokens:
                logging.info(f"Retrieved {len(tokens)} trending tokens from API")
                return tokens
        except Exception as e:
            logging.error(f"Error getting trending tokens: {e}")
            return []

    async def evaluate_trading_potential(self, contract_address: str) -> Dict:
        """
        Evaluate trading potential of token
        
        :param contract_address: Token contract address
        :return: Trading evaluation dictionary
        """
        # Get token data from fetch_token_data method
        token_data = await self.fetch_token_data(contract_address)
        
        if not token_data:
            return {'tradable': False, 'reason': 'No data available'}
        
        # Get trading parameters
        params = BotConfiguration.TRADING_PARAMETERS
        
        # Calculate safety score if not already included
        safety_score = await self.calculate_safety_score(contract_address)
        
        # Apply screening filters
        
        # Check safety score threshold
        if safety_score < params['MIN_SAFETY_SCORE']:
            return {
                'tradable': False,
                'reason': f"Safety score too low: {safety_score:.2f}",
                'token_data': token_data
            }
        
        # Check volume threshold
        if token_data['volume_24h'] < params.get('MIN_VOLUME', 10000):  # $10K
            return {
                'tradable': False,
                'reason': f"24h volume too low: ${token_data['volume_24h']:.2f}",
                'token_data': token_data
            }
        
        # Check liquidity threshold
        if token_data['liquidity_usd'] < params.get('MIN_LIQUIDITY', 50000):  # $50K
            return {
                'tradable': False,
                'reason': f"Liquidity too low: ${token_data['liquidity_usd']:.2f}",
                'token_data': token_data
            }
        
        # Check market cap threshold
        if token_data['mcap'] < params.get('MIN_MCAP', 100000):  # $100K
            return {
                'tradable': False,
                'reason': f"Market cap too low: ${token_data['mcap']:.2f}",
                'token_data': token_data
            }
        
        # Check holders threshold
        if token_data['holders'] < params.get('MIN_HOLDERS', 50):  # 50 holders
            return {
                'tradable': False,
                'reason': f"Not enough holders: {token_data['holders']}",
                'token_data': token_data
            }
        
        # Check if top gainer (1h, 6h, or 24h)
        is_top_gainer = (
            token_data['price_change_1h'] > params.get('MIN_PRICE_CHANGE_1H', 5.0) or
            token_data['price_change_6h'] > params.get('MIN_PRICE_CHANGE_6H', 10.0) or
            token_data['price_change_24h'] > params.get('MIN_PRICE_CHANGE_24H', 20.0)
        )
        
        # Token passes all checks
        return {
            'tradable': True,
            'reason': 'Meets trading criteria',
            'token_data': token_data,
            'is_top_gainer': is_top_gainer,
            'recommendation': {
                'action': 'BUY',
                'confidence': min(100, safety_score),
                'max_investment': params['MAX_INVESTMENT_PER_TOKEN'],
                'take_profit': params['TAKE_PROFIT_TARGET'],
                'stop_loss': params['STOP_LOSS_PERCENTAGE']
            }
        }

    async def fetch_token_data(self, contract_address: str) -> Optional[Dict]:
        """
        Fetch token data from Birdeye, DexScreener, or other sources
        
        :param contract_address: Token contract address
        :return: Token data dictionary or None
        """
        try:
            # Get token info from Birdeye
            token_info = await self.birdeye.get_token_info(contract_address)
            
            if token_info:
                # Calculate social media score
                social_media_score = await self.calculate_social_media_score(contract_address)
                
                # Get price changes using direct calls
                price_change_24h = 0.0
                price_change_6h = 0.0
                price_change_1h = 0.0
                
                try:
                    price_change_24h = await self.birdeye.get_price_change(contract_address, '24h') or 0.0
                    price_change_6h = await self.birdeye.get_price_change(contract_address, '6h') or 0.0
                    price_change_1h = await self.birdeye.get_price_change(contract_address, '1h') or 0.0
                except Exception as e:
                    logging.error(f"Error getting price changes: {e}")
                
                # Get other metrics with direct calls
                try:
                    price_usd = token_info.get('price', {}).get('value', 0.0)
                    volume_24h = token_info.get('volume', {}).get('value', 0.0)
                    liquidity_usd = token_info.get('liquidity', {}).get('value', 0.0)
                    holders = token_info.get('holdersCount', 0)
                    mcap = token_info.get('mc', {}).get('value', 0.0)
                    fdv = token_info.get('fdv', {}).get('value', 0.0)
                except Exception as e:
                    logging.error(f"Error extracting token metrics: {e}")
                    price_usd = 0.0
                    volume_24h = 0.0
                    liquidity_usd = 0.0
                    holders = 0
                    mcap = 0.0
                    fdv = 0.0
                
                # Update price cache
                self.price_cache[contract_address] = {
                    'price_usd': price_usd,
                    'timestamp': datetime.now(UTC).timestamp()
                }
                
                # Return formatted token data
                return {
                    'contract_address': contract_address,
                    'ticker': token_info.get('symbol', 'UNKNOWN'),
                    'name': token_info.get('name', 'UNKNOWN'),
                    'volume_24h': volume_24h,
                    'liquidity_usd': liquidity_usd,
                    'price_usd': price_usd,
                    'price_change_24h': price_change_24h,
                    'price_change_6h': price_change_6h,
                    'price_change_1h': price_change_1h,
                    'social_media_score': social_media_score,
                    'fdv': fdv,
                    'mcap': mcap,
                    'holders': holders
                }
            
            # If we get here, we couldn't fetch token data
            return None
            
        except Exception as e:
            logging.error(f"Error fetching token data: {e}")
            return None

    async def calculate_social_media_score(self, contract_address: str) -> float:
        """
        Calculate social media score for token based on Twitter activity
        
        :param contract_address: Token contract address
        :return: Social media score (0-100)
        """
        # Check if social media analysis is disabled due to rate limits
        if self.social_media_disabled:
            current_time = int(time.time())
            # Re-enable after timeout period
            if current_time > self.rate_limited_until:
                self.social_media_disabled = False
            else:
                logging.debug(f"Social media analysis disabled. Using default score for {contract_address}")
                return 50.0  # Default score when disabled
        
        # Check if score is cached and recent (within 24 hours)
        cache_key = contract_address
        current_time = time.time()
        
        if (cache_key in self.social_media_cache and 
            current_time - self.social_media_cache[cache_key]['timestamp'] < 86400):  # 24 hours
            return self.social_media_cache[cache_key]['score']
        
        # If no Twitter client, return default score
        if not self.twitter_client:
            return 50.0
        
        try:
            # Get token data to find ticker
            token_info = await self.birdeye.get_token_info(contract_address)
            if not token_info:
                return 50.0
                
            ticker = token_info.get('symbol', 'UNKNOWN')
            if ticker == 'UNKNOWN':
                return 50.0
            
            # Check if we should proceed with Twitter API request
            if not self._check_twitter_rate_limit():
                logging.debug(f"Skipping Twitter API request due to rate limit. Using default score for {ticker}")
                return 50.0
            
            # Search for tweets about this token
            search_term = f"{ticker} solana"  # Changed from ${ticker} to just ticker
            
            # Make API request and increment counter
            try:
                tweets = self.twitter_client.search_recent_tweets(
                    query=search_term,
                    max_results=10,  # Reduced from 20 to limit data usage
                    tweet_fields=['public_metrics', 'created_at']
                )
                self.twitter_requests_this_window += 1
                logging.debug(f"Twitter API request successful. Requests this window: {self.twitter_requests_this_window}")
                
            except tweepy.TooManyRequests:
                logging.warning(f"Twitter API rate limit exceeded for {ticker}")
                self._handle_rate_limit()
                return 50.0  # Default score when rate limited
            
            except Exception as e:
                logging.error(f"Twitter API error: {e}")
                return 50.0
            
            if not hasattr(tweets, 'data') or not tweets.data:
                # No tweets found
                score = 40.0
            else:
                # Calculate score based on engagement
                total_engagement = 0
                sentiment_scores = []
                
                for tweet in tweets.data:
                    # Calculate engagement
                    engagement = (
                        tweet.public_metrics.get('retweet_count', 0) +
                        tweet.public_metrics.get('like_count', 0) +
                        tweet.public_metrics.get('reply_count', 0) * 2
                    )
                    
                    total_engagement += engagement
                    
                    # Calculate sentiment
                    sentiment = self.sentiment_analyzer.polarity_scores(tweet.text)
                    sentiment_scores.append(sentiment['compound'])
                
                # Calculate average sentiment
                avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
                
                # Calculate volume score (based on total engagement)
                volume_score = min(100, total_engagement / 10)
                
                # Calculate sentiment score (0-100)
                sentiment_score = (avg_sentiment + 1) * 50
                
                # Combine scores (70% volume, 30% sentiment)
                score = (volume_score * 0.7) + (sentiment_score * 0.3)
            
            # Cache score for 24 hours
            self.social_media_cache[cache_key] = {
                'score': score,
                'timestamp': current_time
            }
            
            return score
        
        except Exception as e:
            logging.error(f"Error calculating social media score: {e}")
            return 50.0  # Default score on error

    async def calculate_safety_score(self, contract_address: str) -> float:
        """
        Calculate safety score for token
        
        :param contract_address: Token contract address
        :return: Safety score (0-100)
        """
        try:
            # Filter out likely fake tokens
            if is_fake_token(contract_address):
                logging.warning(f"Potentially fake token identified: {contract_address}")
                return 0.0
            
            # Get security info from Birdeye
            security_info = await self.birdeye.get_token_security_info(contract_address)
                
            # If we have specific security scoring from Birdeye, use it
            if security_info and 'securityScore' in security_info:
                security_score = float(security_info['securityScore'])
                logging.info(f"Using Birdeye security score for {contract_address}: {security_score}")
                return security_score
            
            # Get token data for calculating score
            token_info = await self.birdeye.get_token_info(contract_address)
            if not token_info:
                return 0.0
            
            # Extract metrics for scoring
            liquidity_usd = token_info.get('liquidity', {}).get('value', 0.0)
            holders = token_info.get('holdersCount', 0)
            volume_24h = token_info.get('volume', {}).get('value', 0.0)
            
            # Initialize score components
            liquidity_score = 0
            volume_score = 0
            holders_score = 0
            social_score = 0
            
            # Liquidity score (40%)
            # Higher liquidity = safer
            if liquidity_usd > 1000000:  # $1M+
                liquidity_score = 40
            elif liquidity_usd > 500000:  # $500K+
                liquidity_score = 35
            elif liquidity_usd > 250000:  # $250K+
                liquidity_score = 30
            elif liquidity_usd > 100000:  # $100K+
                liquidity_score = 25
            elif liquidity_usd > 50000:   # $50K+
                liquidity_score = 20
            elif liquidity_usd > 25000:   # $25K+
                liquidity_score = 15
            elif liquidity_usd > 10000:   # $10K+
                liquidity_score = 10
            else:
                liquidity_score = 5
            
            # Volume score (20%)
            # Higher volume = safer
            if volume_24h > 500000:  # $500K+
                volume_score = 20
            elif volume_24h > 250000:  # $250K+
                volume_score = 18
            elif volume_24h > 100000:  # $100K+
                volume_score = 16
            elif volume_24h > 50000:   # $50K+
                volume_score = 14
            elif volume_24h > 25000:   # $25K+
                volume_score = 12
            elif volume_24h > 10000:   # $10K+
                volume_score = 10
            else:
                volume_score = 5
            
            # Holders score (20%)
            # More holders = safer
            if holders > 1000:  # 1000+
                holders_score = 20
            elif holders > 500:  # 500+
                holders_score = 18
            elif holders > 250:  # 250+
                holders_score = 16
            elif holders > 100:  # 100+
                holders_score = 14
            elif holders > 50:   # 50+
                holders_score = 12
            elif holders > 25:   # 25+
                holders_score = 10
            else:
                holders_score = 5
            
            # If social media is disabled, we weight other factors more
            if self.social_media_disabled:
                # Distribute social media weight to other factors proportionally
                liquidity_score = liquidity_score * 1.25  # 40% -> 50%
                volume_score = volume_score * 1.25        # 20% -> 25%
                holders_score = holders_score * 1.25      # 20% -> 25%
                social_score = 0
            else:
                # Social score (20%)
                # Higher social activity = safer
                social_media_score = await self.calculate_social_media_score(contract_address)
                social_score = social_media_score * 0.2
            
            # Calculate total score
            total_score = liquidity_score + volume_score + holders_score + social_score
            
            # Bonus points from security info if available
            if security_info:
                # Adjust score based on security flags
                if security_info.get('liquidityLocked', False):
                    total_score += 5  # Bonus for locked liquidity
                
                if security_info.get('mintingDisabled', False):
                    total_score += 5  # Bonus for disabled minting
                
                if not security_info.get('isMemeToken', True):
                    total_score += 3  # Bonus for non-meme tokens
            
            return min(total_score, 100)
        
        except Exception as e:
            logging.error(f"Error calculating safety score: {e}")
            return 0.0

    async def get_current_price(self, contract_address: str) -> float:
        """
        Get current price of token in USD
        
        :param contract_address: Token contract address
        :return: Current price in USD
        """
        try:
            # Check cache first (valid for 5 minutes)
            cache_key = contract_address
            current_time = datetime.now(UTC).timestamp()
            
            if (cache_key in self.price_cache and 
                current_time - self.price_cache[cache_key]['timestamp'] < 300):
                return self.price_cache[cache_key]['price_usd']
            
            # Get price from API
            price_usd = await self.birdeye.get_token_price(contract_address)
            if price_usd is not None and price_usd > 0:
                # Update cache
                self.price_cache[contract_address] = {
                    'price_usd': price_usd,
                    'timestamp': current_time
                }
                return price_usd
            
            return 0.0  # Default if price not available
        
        except Exception as e:
            logging.error(f"Error getting current price: {e}")
            return 0.0

    async def get_sol_price(self) -> float:
        """
        Get current SOL price in USD
        
        :return: SOL price in USD
        """
        try:
            # Try multiple sources for SOL price
            # 1. Try Birdeye first
            sol_address = "So11111111111111111111111111111111111111112"
            price_usd = await self.birdeye.get_token_price(sol_address)
            if price_usd is not None and price_usd > 0:
                return price_usd
            
            # 2. Try CoinGecko API
            try:
                url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
                data = await fetch_with_retries(url)
                if data and 'solana' in data and 'usd' in data['solana']:
                    return float(data['solana']['usd'])
            except Exception as e:
                logging.error(f"Error getting SOL price from CoinGecko: {e}")
            
            # Default fallback price
            return 171.41  # Update with a reasonable default price
        
        except Exception as e:
            logging.error(f"Error getting SOL price: {e}")
            return 171.41  # Default fallback

#################################
# TOKEN SCANNER
#################################

class TokenScanner:
    """
    Scans various sources to discover potential tokens for trading
    """

    def __init__(self):
        """
        Initialize token scanner
        """
        self.db = Database()
        self.analyzer = TokenAnalyzer(self.db)
        self.api_cache = {}
        self.twitter_client = self._setup_twitter_client()
        self.twitter_requests_this_window = 0
        self.twitter_window_reset = int(time.time()) + 900
        self.discovered_tokens = set()

    def _setup_twitter_client(self) -> Optional[tweepy.Client]:
        try:
            bearer_token = BotConfiguration.API_KEYS['TWITTER_BEARER_TOKEN']
            if not bearer_token:
                logging.warning("Twitter bearer token not provided")
                return None
            client = tweepy.Client(bearer_token=bearer_token)
            logging.info("Twitter client initialized")
            return client
        except Exception as e:
            logging.error(f"Failed to set up Twitter client: {e}")
            return None

    def _check_twitter_rate_limit(self):
        current_time = int(time.time())
        if current_time > self.twitter_window_reset:
            self.twitter_requests_this_window = 0
            self.twitter_window_reset = current_time + 900
        buffer = BotConfiguration.TRADING_PARAMETERS.get('TWITTER_RATE_LIMIT_BUFFER', 5)
        if self.twitter_requests_this_window >= 175 - buffer:
            wait_time = self.twitter_window_reset - current_time + 5
            logging.warning(f"Twitter rate limit approaching. Sleeping for {wait_time} seconds.")
            time.sleep(wait_time)
            self.twitter_requests_this_window = 0
            self.twitter_window_reset = current_time + 900

    async def scan_twitter_for_tokens(self) -> Set[str]:
        discovered_contracts = set()
        if not self.twitter_client:
            logging.warning("Twitter client not initialized. Skipping Twitter scan.")
            return discovered_contracts
        try:
            self._check_twitter_rate_limit()
            query = "solana memecoin -is:retweet"
            tweets = self.twitter_client.search_recent_tweets(
                query=query,
                max_results=50,
                tweet_fields=['public_metrics', 'created_at']
            )
            self.twitter_requests_this_window += 1
            if not tweets.data:
                logging.info("No recent relevant tweets found.")
                return discovered_contracts
            for tweet in tweets.data:
                words = tweet.text.split()
                for i, word in enumerate(words):
                    word = word.strip('.,!?:;"\'()[]{}')
                    if is_valid_solana_address(word):
                        if is_fake_token(word):
                            logging.debug(f"Skipping likely fake token from Twitter: {word}")
                            continue
                        ticker = "UNKNOWN"
                        for j in range(max(0, i-5), min(len(words), i+6)):
                            w = words[j].strip('.,!?:;"\'()[]{}')
                            if w.startswith('
                        engagement = (
                            tweet.public_metrics.get('retweet_count', 0) +
                            tweet.public_metrics.get('like_count', 0) +
                            tweet.public_metrics.get('reply_count', 0) * 2
                        )
                        self.db.store_token(
                            contract_address=word,
                            ticker=ticker,
                            name="UNKNOWN",
                            launch_date=tweet.created_at.isoformat(),
                            safety_score=50.0 + (engagement / 10),
                            volume_24h=0.0,
                            liquidity_locked=False
                        )
                        discovered_contracts.add(word)
                        logging.debug(f"Discovered token from Twitter: {ticker} ({word})")
            logging.info(f"Discovered {len(discovered_contracts)} tokens from Twitter")
            return discovered_contracts
        except Exception as e:
            logging.error(f"Twitter scan failed: {e}")
            return discovered_contracts

    async def scan_top_gainers(self) -> List[Dict]:
        gainers = []
        try:
            gainers_24h = await self.analyzer.get_top_gainers(timeframe='24h', limit=5)
            seen_contracts = set()
            for token in gainers_24h:
                contract = token.get('contract_address')
                if not contract or is_fake_token(contract):
                    continue
                if contract not in seen_contracts:
                    seen_contracts.add(contract)
                    gainers.append(token)
            logging.info(f"Found {len(gainers)} top gainer tokens")
            for token in gainers:
                self.db.store_token(
                    contract_address=token.get('contract_address'),
                    ticker=token.get('ticker', 'UNKNOWN'),
                    name=token.get('name', 'UNKNOWN'),
                    launch_date=datetime.now(UTC).isoformat(),
                    volume_24h=token.get('volume_24h', 0.0),
                    safety_score=70.0,
                    liquidity_locked=False
                )
            return gainers
        except Exception as e:
            logging.error(f"Error scanning for top gainers: {e}")
            return []

    async def scan_trending_tokens(self) -> List[Dict]:
        trending = []
        try:
            trending = await self.analyzer.get_trending_tokens(10)
            if not trending:
                logging.info("No trending tokens found")
                return []
            filtered = [t for t in trending if t.get('contract_address') and not is_fake_token(t.get('contract_address'))]
            logging.info(f"Found {len(filtered)} trending tokens")
            for token in filtered:
                self.db.store_token(
                    contract_address=token.get('contract_address'),
                    ticker=token.get('ticker', 'UNKNOWN'),
                    name=token.get('name', 'UNKNOWN'),
                    launch_date=datetime.now(UTC).isoformat(),
                    volume_24h=token.get('volume_24h', 0.0),
                    safety_score=65.0,
                    liquidity_locked=False
                )
            return filtered
        except Exception as e:
            logging.error(f"Error scanning for trending tokens: {e}")
            return []

    async def analyze_tokens(self) -> List[Dict]:
        tradable_tokens = []
        try:
            min_safety = BotConfiguration.TRADING_PARAMETERS['MIN_SAFETY_SCORE']
            tokens_df = self.db.get_tokens(limit=20, min_safety_score=min_safety)
            if tokens_df.empty:
                logging.info("No tokens to analyze")
                return tradable_tokens
            for _, token in tokens_df.iterrows():
                contract = token['contract_address']
                if contract in self.discovered_tokens or not isinstance(contract, str) or 'pump' in contract.lower() or is_fake_token(contract):
                    continue
                try:
                    evaluation = await self.analyzer.evaluate_trading_potential(contract)
                    if evaluation['tradable']:
                        tradable_tokens.append(evaluation)
                        logging.info(f"Tradable token found: {token['ticker']} ({contract})")
                except Exception as e:
                    logging.error(f"Error evaluating {contract}: {e}")
                    continue
                self.discovered_tokens.add(contract)
                await asyncio.sleep(1)
            if len(self.discovered_tokens) > 100:
                self.discovered_tokens = set(list(self.discovered_tokens)[-100:])
            return tradable_tokens
        except Exception as e:
            logging.error(f"Token analysis failed: {e}")
            return []

    async def get_tokens_by_criteria(self) -> List[Dict]:
        qualified = []
        try:
            params = BotConfiguration.TRADING_PARAMETERS
            top = await self.scan_top_gainers()
            trend = await self.scan_trending_tokens()
            all_tokens = top + trend
            for token in all_tokens:
                contract = token.get('contract_address')
                if not contract or not isinstance(contract, str) or is_fake_token(contract):
                    continue
                token_data = await self.analyzer.fetch_token_data(contract)
                if not token_data:
                    continue
                if (token_data.get('volume_24h', 0) >= params['MIN_VOLUME'] and
                    token_data.get('liquidity_usd', 0) >= params['MIN_LIQUIDITY'] and
                    token_data.get('mcap', 0) >= params['MIN_MCAP'] and
                    token_data.get('holders', 0) >= params['MIN_HOLDERS']):
                    score = await self.analyzer.calculate_safety_score(contract)
                    token_data['safety_score'] = score
                    qualified.append({
                        'token_data': token_data,
                        'tradable': True,
                        'reason': 'Meets screening criteria',
                        'recommendation': {
                            'action': 'BUY',
                            'confidence': min(100, score),
                            'max_investment': params['MAX_INVESTMENT_PER_TOKEN'],
                            'take_profit': params['TAKE_PROFIT_TARGET'],
                            'stop_loss': params['STOP_LOSS_PERCENTAGE']
                        }
                    })
                    logging.info(f"Qualified token found: {token_data.get('ticker')} ({contract})")
            return qualified
        except Exception as e:
            logging.error(f"Error filtering tokens by criteria: {e}")
            return []

    async def start_scanning(self):
        logging.info("Starting token scanner")
        while True:
            try:
                if not BotConfiguration.load_trading_parameters():
                    logging.info("Bot paused by control settings")
                    await asyncio.sleep(60)
                    continue
                logging.info("Scanning Twitter for tokens...")
                await self.scan_twitter_for_tokens()
                logging.info("Analyzing tokens by screening criteria...")
                qualified = await self.get_tokens_by_criteria()
                logging.info("Analyzing other discovered tokens...")
                others = await self.analyze_tokens()
                all_tradable = qualified + others
                interval = BotConfiguration.TRADING_PARAMETERS['SCAN_INTERVAL']
                logging.info(f"Scan complete, waiting {interval} seconds for next scan")
                await asyncio.sleep(interval)
            except Exception as e:
                logging.error(f"Error during token scanning: {e}")
                await asyncio.sleep(60)

#################################
# SOLANA TRADER
#################################

class SolanaTrader:
    """
    Manages Solana trading operations
    """
    
    def __init__(self):
        """
        Initialize Solana trader
        """
        self.db = Database()
        self.client = None
        self.keypair = self._setup_wallet()
        self.active_orders = {}
        self.connected = False
        self.last_connection_attempt = 0
        self.token_analyzer = TokenAnalyzer(db=self.db)
        
        # Get simulation mode from config
        control = self._load_control_settings()
        self.simulation_mode = control.get('simulation_mode', True)
        self.simulation_success_rate = 0.95  # 95% success rate for simulated trades
        
        # Log simulation status
        if self.simulation_mode:
            logging.info("Trading bot running in SIMULATION MODE - no real trades will be executed")
        else:
            logging.warning("Trading bot running in REAL TRADING MODE - actual trades will be executed!")
        
        # Load active orders
        self._load_active_orders()
    
    def _load_control_settings(self):
        """Load control settings from file"""
        try:
            with open(BotConfiguration.BOT_CONTROL_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading control settings: {e}")
            return {'simulation_mode': True}  # Default to simulation mode
    
    def _setup_wallet(self) -> Keypair:
        """
        Set up Solana wallet from private key
        
        :return: Solana keypair
        """
        try:
            private_key = BotConfiguration.API_KEYS['WALLET_PRIVATE_KEY']
            if not private_key:
                raise ValueError("Wallet private key not provided")
            
            keypair = Keypair.from_bytes(bytes.fromhex(private_key))
            logging.info(f"Wallet initialized: {keypair.pubkey()}")
            return keypair
        
        except Exception as e:
            logging.critical(f"Wallet setup failed: {e}")
            raise
    
    def _load_active_orders(self):
        """
        Load active orders from database
        """
        try:
            orders_df = self.db.get_active_orders()
            for _, row in orders_df.iterrows():
                contract_address = row['contract_address']
                self.active_orders[contract_address] = {
                    'amount': row['amount'],
                    'buy_price': row['buy_price'],
                    'timestamp': row['timestamp']
                }
            logging.info(f"Loaded {len(self.active_orders)} active orders")
        
        except Exception as e:
            logging.error(f"Failed to load active orders: {e}")
    
    async def connect(self, force=False) -> bool:
        """
        Connect to Solana RPC endpoint
        
        :param force: Force reconnection even if recently connected
        :return: True if connected, False otherwise
        """
        current_time = time.time()
        
        # Skip if already connected recently
        if (self.connected and 
            current_time - self.last_connection_attempt < 60 and 
            not force):
            return True
        
        self.last_connection_attempt = current_time
        
        # Connection parameters
        rpc_endpoint = BotConfiguration.API_KEYS['SOLANA_RPC_ENDPOINT']
        max_retries = 5
        base_delay = 2
        
        # Attempt connection with retries
        for attempt in range(max_retries):
            try:
                # Close existing client if any
                if self.client:
                    await self.client.close()
                
                # Create new client
                self.client = AsyncClient(rpc_endpoint, timeout=30)
                
                # Check connection
                if await self.client.is_connected():
                    self.connected = True
                    logging.info("Connected to Solana RPC")
                    return True
            
            except Exception as e:
                self.connected = False
                logging.error(f"Connection attempt {attempt + 1}/{max_retries} failed: {e}")
                
                # Exponential backoff
                if attempt < max_retries - 1:
                    await asyncio.sleep(base_delay * (2 ** attempt))
        
        logging.critical("Failed to connect to Solana RPC")
        return False
    
    async def get_wallet_balance(self) -> Tuple[float, float]:
        """
        Get wallet SOL balance
        
        :return: (SOL balance, USD value)
        """
        # In simulation mode, return a simulated balance
        if self.simulation_mode:
            # Return a simulated balance of 5 SOL
            simulated_balance_sol = 5.0
            # Get SOL/USD price for USD conversion
            sol_price_usd = await self.get_sol_price()
            # Calculate USD value
            simulated_balance_usd = simulated_balance_sol * sol_price_usd
            
            logging.debug(f"Simulation mode: Using simulated wallet balance: {simulated_balance_sol:.4f} SOL (${simulated_balance_usd:.2f})")
            return simulated_balance_sol, simulated_balance_usd
        
        # Real balance retrieval for non-simulation mode
        if not await self.connect():
            return 0.0, 0.0
        
        try:
            # Get SOL balance in lamports
            balance_response = await self.client.get_balance(self.keypair.pubkey())
            balance_lamports = balance_response.value
            
            # Convert to SOL
            balance_sol = balance_lamports / 1_000_000_000
            
            # Get SOL/USD price
            sol_price_usd = await self.get_sol_price()
            
            # Calculate USD value
            balance_usd = balance_sol * sol_price_usd
            
            logging.debug(f"Wallet balance: {balance_sol:.4f} SOL (${balance_usd:.2f})")
            return balance_sol, balance_usd
        
        except Exception as e:
            logging.error(f"Error fetching wallet balance: {e}")
            return 0.0, 0.0
    
    async def get_sol_price(self) -> float:
        """
        Get current SOL/USD price
        
        :return: SOL price in USD
        """
        sources = [
            # Multiple price sources for redundancy
            self._get_sol_price_coingecko,
            self._get_sol_price_jupiter,
            self._get_sol_price_coinbase
        ]
        
        # Try each source until successful
        for source_func in sources:
            try:
                price = await source_func()
                if price > 0:
                    return price
            except Exception as e:
                logging.warning(f"Price source failed: {e}")
        
        # Fall back to default price
        logging.warning("All SOL price sources failed. Using default price.")
        return 171.41  # Updated default price
    
    async def _get_sol_price_coingecko(self) -> float:
        """Get SOL price from CoinGecko"""
        url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
        data = await fetch_with_retries(url)
        if data and 'solana' in data and 'usd' in data['solana']:
            return float(data['solana']['usd'])
        return 0.0
    
    async def _get_sol_price_jupiter(self) -> float:
        """Get SOL price from Jupiter"""
        url = "https://price.jup.ag/v4/price?ids=SOL"
        data = await fetch_with_retries(url)
        if data and 'data' in data and 'SOL' in data['data']:
            return float(data['data']['SOL']['price'])
        return 0.0
    
    async def _get_sol_price_coinbase(self) -> float:
        """Get SOL price from Coinbase"""
        url = "https://api.coinbase.com/v2/prices/SOL-USD/spot"
        data = await fetch_with_retries(url)
        if data and 'data' in data and 'amount' in data['data']:
            return float(data['data']['amount'])
        return 0.0
    
    async def get_token_balance(self, token_address: str) -> int:
        """
        Get token balance for wallet
        
        :param token_address: Token contract address
        :return: Token balance in smallest units
        """
        # In simulation mode, return a fake balance for active orders
        if self.simulation_mode and token_address in self.active_orders:
            logging.debug(f"Simulation mode: Returning fake token balance for {token_address}")
            return 1000000  # Fake 1 token
            
        if not await self.connect():
            return 0
        
        try:
            pubkey = self.keypair.pubkey()
            
            # Get token accounts for owner
            response = await self.client.get_token_accounts_by_owner(
                pubkey,
                {"mint": Pubkey.from_string(token_address)},
                commitment=Confirmed
            )
            
            # Check if any accounts found
            if response.value:
                account = response.value[0]
                
                # Get token account balance
                balance_info = await self.client.get_token_account_balance(
                    account.pubkey
                )
                
                # Return balance amount
                balance = int(balance_info.value.amount)
                logging.debug(f"Token balance for {token_address}: {balance}")
                return balance
            
            logging.debug(f"No token accounts found for {token_address}")
            return 0
        
        except Exception as e:
            logging.error(f"Error getting token balance for {token_address}: {e}")
            return 0
    
    async def get_token_price(self, token_address: str) -> Optional[float]:
        """
        Get token price in SOL
        
        :param token_address: Token contract address
        :return: Token price in SOL or None if error
        """
        # In simulation mode, use real price data instead of artificial values
        if self.simulation_mode and token_address in self.active_orders:
            # Get real price from TokenAnalyzer
            real_price = await self.token_analyzer.get_current_price(token_address)
            if real_price > 0:
                logging.debug(f"Simulation mode: Using real price for {token_address}: ${real_price}")
                sol_price = await self.get_sol_price()
                # Convert USD price to SOL
                price_sol = real_price / sol_price if sol_price > 0 else 0
                return price_sol
            
            # Fall back to stored price if unable to get current
            buy_price = self.active_orders[token_address]['buy_price']
            # Add a small random price movement
            price_movement = random.uniform(0.9, 1.1)  # ±10%
            return buy_price * price_movement
            
        try:
            # Check if address is valid
            if not is_valid_solana_address(token_address):
                logging.warning(f"Invalid token address: {token_address}")
                return None
                
            # Use Jupiter API to get quote
            sol_mint = "So11111111111111111111111111111111111111112"
            
            # Request for 1 token
            quote_params = {
                'inputMint': token_address,
                'outputMint': sol_mint,
                'amount': "1000000",  # 1 token in smallest units
                'slippageBps': "50"   # 0.5% slippage
            }
            
            # Get quote from Jupiter
            quote_url = BotConfiguration.API_KEYS['JUPITER_QUOTE_API']
            quote_data = await fetch_with_retries(quote_url, params=quote_params)
            
            # Calculate price from quote
            if quote_data and 'outAmount' in quote_data:
                # Convert lamports to SOL
                price_sol = int(quote_data['outAmount']) / 1_000_000_000
                return price_sol
            
            logging.warning(f"Failed to get price for {token_address}")
            return None
        
        except Exception as e:
            logging.error(f"Error getting token price for {token_address}: {e}")
            return None
    
    async def execute_trade(self, contract_address: str, action: str, amount: float) -> Optional[str]:
        """
        Execute a token trade
        
        :param contract_address: Token contract address
        :param action: Trade action (BUY/SELL)
        :param amount: Trade amount in SOL
        :return: Transaction signature or None if failed
        """
        # Check action type
        if action.upper() == 'BUY':
            return await self._buy_token(contract_address, amount)
        elif action.upper() == 'SELL':
            return await self._sell_token(contract_address, amount)
        else:
            logging.error(f"Invalid trade action: {action}")
            return None
    
    async def _buy_token(self, contract_address: str, amount_sol: float) -> Optional[str]:
        """
        Buy token with SOL
        
        :param contract_address: Token contract address
        :param amount_sol: Amount in SOL to spend
        :return: Transaction signature or None if failed
        """
        # Handle simulation mode with real prices
        if self.simulation_mode:
            logging.info(f"Simulation mode: Executing simulated buy for {contract_address}")
            
            # Simulate success most of the time
            if random.random() <= self.simulation_success_rate:
                # Get real token price if possible
                token_price_usd = await self.token_analyzer.get_current_price(contract_address)
                sol_price_usd = await self.get_sol_price()
                
                # Calculate token price in SOL
                if token_price_usd > 0 and sol_price_usd > 0:
                    token_price_sol = token_price_usd / sol_price_usd
                else:
                    # Fallback to reasonable simulation value
                    token_price_sol = 0.00005  # Typical small token price
                
                timestamp = datetime.now(UTC).isoformat()
                
                # Record in database
                self.db.record_trade(contract_address, 'BUY', amount_sol, token_price_sol)
                
                # Update active orders
                self.active_orders[contract_address] = {
                    'amount': amount_sol,
                    'buy_price': token_price_sol,
                    'timestamp': timestamp
                }
                
                # Return simulated tx signature
                return "SIM_" + "".join(random.choices("0123456789abcdef", k=60))
            else:
                logging.warning(f"Simulation mode: Buy failed for {contract_address}")
                return None
        
        # Real trading logic for non-simulation mode
        # Check connection
        if not await self.connect():
            logging.error("Failed to connect to Solana for buy")
            return None
        
        # Check wallet balance
        balance_sol, _ = await self.get_wallet_balance()
        if balance_sol < amount_sol:
            logging.warning(f"Insufficient balance: {balance_sol} SOL < {amount_sol} SOL")
            return None
        
        # Get trading parameters
        params = BotConfiguration.TRADING_PARAMETERS
        max_retries = params['MAX_BUY_RETRIES']
        slippage = params['SLIPPAGE_TOLERANCE']
        
        # SOL mint address
        sol_mint = "So11111111111111111111111111111111111111112"
        
        # Convert SOL to lamports
        amount_lamports = int(amount_sol * 1_000_000_000)
        
        # Attempt to buy with retries
        for attempt in range(max_retries):
            try:
                # Get quote from Jupiter
                quote_params = {
                    'inputMint': sol_mint,
                    'outputMint': contract_address,
                    'amount': str(amount_lamports),
                    'slippageBps': str(int(slippage * 10000))
                }
                
                quote_url = BotConfiguration.API_KEYS['JUPITER_QUOTE_API']
                quote = await fetch_with_retries(quote_url, params=quote_params)
                
                if not quote:
                    logging.warning(f"Buy attempt {attempt + 1}/{max_retries}: No quote received")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)
                    continue
                
                # Execute swap transaction
                swap_url = BotConfiguration.API_KEYS['JUPITER_SWAP_API']
                swap_payload = {
                    'quoteResponse': quote,
                    'userPublicKey': str(self.keypair.pubkey()),
                    'prioritizationFeeLamports': 1000000  # 0.001 SOL fee
                }
                
                swap_data = await fetch_with_retries(
                    swap_url, 
                    method='POST', 
                    json_data=swap_payload
                )
                
                if not swap_data or 'swapTransaction' not in swap_data:
                    logging.error(f"Invalid swap data on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)
                    continue
                
                # Get transaction data
                transaction_data = base64.b64decode(swap_data['swapTransaction'])
                
                # Send transaction
                send_tx_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "sendTransaction",
                    "params": [
                        swap_data['swapTransaction'],
                        {
                            "encoding": "base64", 
                            "skipPreflight": True, 
                            "preflightCommitment": "confirmed", 
                            "maxRetries": 5
                        }
                    ]
                }
                
                tx_response = await fetch_with_retries(
                    BotConfiguration.API_KEYS['SOLANA_RPC_ENDPOINT'], 
                    method='POST',
                    headers={'Content-Type': 'application/json'},
                    json_data=send_tx_payload
                )
                
                # Extract transaction signature
                if tx_response and 'result' in tx_response:
                    txid = tx_response['result']
                    
                    # Calculate token price
                    out_amount = int(quote.get('outAmount', 1))
                    buy_price = amount_lamports / out_amount if out_amount > 0 else 0
                    
                    # Record trade in database
                    timestamp = datetime.now(UTC).isoformat()
                    self.db.record_trade(contract_address, 'BUY', amount_sol, buy_price)
                    
                    # Update active orders dict
                    self.active_orders[contract_address] = {
                        'amount': amount_sol, 
                        'buy_price': buy_price, 
                        'timestamp': timestamp
                    }
                    
                    logging.info(f"Buy executed: {txid} for {contract_address} - {amount_sol} SOL")
                    return txid
                
                logging.warning(f"Transaction failed on attempt {attempt + 1}")
                
            except Exception as e:
                logging.error(f"Buy attempt {attempt + 1}/{max_retries} failed for {contract_address}: {e}")
            
            # Wait before next attempt
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
        
        logging.error(f"All buy attempts failed for {contract_address}")
        return None
    
    async def _sell_token(self, contract_address: str, amount_sol: Optional[float] = None) -> Optional[str]:
        """
        Sell token for SOL
        
        :param contract_address: Token contract address
        :param amount_sol: Amount in SOL equivalent to sell (if None, sell all)
        :return: Transaction signature or None if failed
        """
        # Handle simulation mode with real prices
        if self.simulation_mode:
            logging.info(f"Simulation mode: Executing simulated sell for {contract_address}")
            
            # Simulate success most of the time
            if random.random() <= self.simulation_success_rate:
                # Only proceed if we have this token in active orders
                if contract_address in self.active_orders:
                    buy_amount = self.active_orders[contract_address]['amount']
                    buy_price = self.active_orders[contract_address]['buy_price']
                    
                    # Get real token price for more accurate simulation
                    token_price_usd = await self.token_analyzer.get_current_price(contract_address)
                    sol_price_usd = await self.get_sol_price()
                    
                    # Calculate token price in SOL
                    if token_price_usd > 0 and sol_price_usd > 0:
                        sell_price = token_price_usd / sol_price_usd
                    else:
                        # Random price movement for simulation if real price unavailable
                        price_movement = random.uniform(0.8, 1.2)  # ±20%
                        sell_price = buy_price * price_movement
                    
                    # Record sell in database
                    self.db.record_trade(contract_address, 'SELL', buy_amount, sell_price)
                    
                    # Remove from active orders
                    del self.active_orders[contract_address]
                    
                    # Return simulated tx signature
                    return "SIM_" + "".join(random.choices("0123456789abcdef", k=60))
                else:
                    logging.warning(f"No active order found for {contract_address}")
                    return None
            else:
                logging.warning(f"Simulation mode: Sell failed for {contract_address}")
                return None
                
        # Real trading logic for non-simulation mode
        # Check if we have this token
        if (contract_address not in self.active_orders and 
            not await self.get_token_balance(contract_address)):
            logging.warning(f"No tokens to sell for {contract_address}")
            return None
        
        # Check connection
        if not await self.connect():
            logging.error("Failed to connect to Solana for sell")
            return None
        
        # Get trading parameters
        params = BotConfiguration.TRADING_PARAMETERS
        max_retries = params['MAX_SELL_RETRIES']
        slippage = params['SLIPPAGE_TOLERANCE']
        moonbag_pct = params['MOONBAG_PERCENTAGE']
        
        # SOL mint address
        sol_mint = "So11111111111111111111111111111111111111112"
        
        # Get actual token balance
        token_balance = await self.get_token_balance(contract_address)
        if token_balance <= 0:
            logging.warning(f"No token balance for {contract_address}")
            return None
        
        # Determine amount to sell (keep moonbag if configured)
        sell_all = amount_sol is None
        amount_to_sell = token_balance
        
        if not sell_all and moonbag_pct > 0:
            # Calculate percentage to sell
            amount_to_sell = int(token_balance * (1 - moonbag_pct))
        
        # Attempt to sell with retries
        for attempt in range(max_retries):
            try:
                # Get quote from Jupiter
                quote_params = {
                    'inputMint': contract_address,
                    'outputMint': sol_mint,
                    'amount': str(amount_to_sell),
                    'slippageBps': str(int(slippage * 10000))
                }
                
                quote_url = BotConfiguration.API_KEYS['JUPITER_QUOTE_API']
                quote = await fetch_with_retries(quote_url, params=quote_params)
                
                if not quote:
                    logging.warning(f"Sell attempt {attempt + 1}/{max_retries}: No quote received")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)
                    continue
                
                # Execute swap transaction
                swap_url = BotConfiguration.API_KEYS['JUPITER_SWAP_API']
                swap_payload = {
                    'quoteResponse': quote,
                    'userPublicKey': str(self.keypair.pubkey()),
                    'prioritizationFeeLamports': 1000000  # 0.001 SOL fee
                }
                
                swap_data = await fetch_with_retries(
                    swap_url, 
                    method='POST', 
                    json_data=swap_payload
                )
                
                if not swap_data or 'swapTransaction' not in swap_data:
                    logging.error(f"Invalid swap data on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)
                    continue
                
                # Get transaction data
                transaction_data = base64.b64decode(swap_data['swapTransaction'])
                
                # Send transaction
                send_tx_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "sendTransaction",
                    "params": [
                        swap_data['swapTransaction'],
                        {
                            "encoding": "base64", 
                            "skipPreflight": True, 
                            "preflightCommitment": "confirmed", 
                            "maxRetries": 5
                        }
                    ]
                }
                
                tx_response = await fetch_with_retries(
                    BotConfiguration.API_KEYS['SOLANA_RPC_ENDPOINT'], 
                    method='POST',
                    headers={'Content-Type': 'application/json'},
                    json_data=send_tx_payload
                )
                
                # Extract transaction signature
                if tx_response and 'result' in tx_response:
                    txid = tx_response['result']
                    
                    # Calculate sell price
                    out_amount_lamports = int(quote.get('outAmount', 0))
                    out_amount_sol = out_amount_lamports / 1_000_000_000
                    sell_price = out_amount_sol / (amount_to_sell / 1_000_000)
                    
                    # Record trade in database
                    self.db.record_trade(contract_address, 'SELL', out_amount_sol, sell_price)
                    
                    # Update active orders
                    if sell_all or moonbag_pct == 0:
                        # Remove from active orders if selling all
                        if contract_address in self.active_orders:
                            del self.active_orders[contract_address]
                    else:
                        # Update remaining amount if keeping moonbag
                        if contract_address in self.active_orders:
                            original_amount = self.active_orders[contract_address]['amount']
                            remaining = original_amount * moonbag_pct
                            self.active_orders[contract_address]['amount'] = remaining
                    
                    logging.info(f"Sell executed: {txid} for {contract_address} - {out_amount_sol} SOL received")
                    return txid
                
                logging.warning(f"Transaction failed on attempt {attempt + 1}")
                
            except Exception as e:
                logging.error(f"Sell attempt {attempt + 1}/{max_retries} failed for {contract_address}: {e}")
            
            # Wait before next attempt
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
        
        logging.error(f"All sell attempts failed for {contract_address}")
        return None
    
    async def monitor_positions(self):
        """
        Monitor active positions for take profit or stop loss
        """
        logging.info("Starting position monitor")
        
        while True:
            try:
                # Load current trading parameters
                BotConfiguration.load_trading_parameters()
                params = BotConfiguration.TRADING_PARAMETERS
                take_profit = params['TAKE_PROFIT_TARGET']
                stop_loss = params['STOP_LOSS_PERCENTAGE']
                
                # Get active orders from database (to ensure we have the latest)
                orders_df = self.db.get_active_orders()
                
                # Skip if no active orders
                if orders_df.empty:
                    logging.debug("No active positions to monitor")
                    await asyncio.sleep(60)
                    continue
                
                # Iterate through active positions
                for _, position in orders_df.iterrows():
                    contract_address = position['contract_address']
                    buy_price = position['buy_price']
                    buy_amount = position['amount']
                    
                    # Skip if invalid data
                    if buy_price <= 0:
                        continue
                    
                    # Get current price
                    current_price = await self.get_token_price(contract_address)
                    if not current_price:
                        logging.warning(f"Could not get current price for {contract_address}")
                        continue
                    
                    # Calculate profit/loss percentage
                    price_change_pct = ((current_price - buy_price) / buy_price) * 100
                    
                    # Log position status
                    logging.debug(f"Position {contract_address}: Price change {price_change_pct:.2f}%")
                    
                    # Check take profit condition
                    if price_change_pct >= ((take_profit - 1) * 100):
                        logging.info(f"Take profit triggered for {contract_address}: {price_change_pct:.2f}%")
                        await self._sell_token(contract_address)
                        continue
                    
                    # Check stop loss condition
                    if price_change_pct <= -(stop_loss * 100):
                        logging.info(f"Stop loss triggered for {contract_address}: {price_change_pct:.2f}%")
                        await self._sell_token(contract_address)
                        continue
                
                # Wait before next check
                await asyncio.sleep(60)
            
            except Exception as e:
                logging.error(f"Position monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def close(self):
        """
        Close connections and cleanup
        """
        if self.client:
            try:
                await self.client.close()
                logging.info("Solana RPC client closed")
            except Exception as e:
                logging.error(f"Error closing Solana RPC client: {e}")

#################################
# TRADING BOT
#################################

class TradingBot:
    """
    Main trading bot class
    """
    def __init__(self):
        """
        Initialize trading bot
        """
        self.running = True
        self.trader = SolanaTrader()
        self.scanner = TokenScanner()
        self.db = Database()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """
        Setup graceful shutdown signal handlers
        """
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """
        Handle shutdown signals
        """
        logging.critical(f"Received signal {signum}. Initiating graceful shutdown...")
        self.running = False
    
    async def _discover_and_trade(self):
        """
        Discover and trade tokens
        """
        logging.info("Starting token discovery and trading process")
        while self.running:
            try:
                balance_sol, balance_usd = await self.trader.get_wallet_balance()
                logging.info(f"Current wallet balance: {balance_sol:.4f} SOL (${balance_usd:.2f})")
                qualified_tokens = await self.scanner.get_tokens_by_criteria()
                if not qualified_tokens:
                    logging.info("No tokens found meeting screening criteria, analyzing other tokens...")
                    other_tradable = await self.scanner.analyze_tokens()
                    qualified_tokens = other_tradable
                
                for token in qualified_tokens:
                    token_data = token['token_data']
                    contract = token_data['contract_address']
                    ticker = token_data['ticker']
                    recommendation = token['recommendation']
                    max_investment = recommendation['max_investment']
                    
                    active_orders = self.db.get_active_orders()
                    if not active_orders.empty and contract in active_orders['contract_address'].values:
                        logging.info(f"Already have position in {ticker} ({contract}), skipping")
                        continue
                    
                    logging.info(f"Token {ticker} qualified for trading:")
                    logging.info(f"  - Volume 24h: ${token_data.get('volume_24h', 0):,.2f}")
                    logging.info(f"  - Liquidity: ${token_data.get('liquidity_usd', 0):,.2f}")
                    logging.info(f"  - Market Cap: ${token_data.get('mcap', 0):,.2f}")
                    logging.info(f"  - Holders: {token_data.get('holders', 0):,}")
                    logging.info(f"  - Price Change 24h: {token_data.get('price_change_24h', 0):.2f}%")
                    logging.info(f"  - Security Score: {token_data.get('safety_score', 0):.1f}/100")
                    
                    if balance_sol < max_investment:
                        logging.warning(f"Insufficient balance ({balance_sol} SOL) for trade of {max_investment} SOL")
                        continue
                    
                    logging.info(f"Trading {ticker} ({contract}) for {max_investment} SOL")
                    txid = await self.trader.execute_trade(contract, 'BUY', max_investment)
                    if txid:
                        logging.info(f"Successfully traded {ticker}: {txid}")
                        balance_sol -= max_investment
                    else:
                        logging.error(f"Failed to trade {ticker}")
                
                logging.debug("Waiting for next discovery cycle")
                await asyncio.sleep(300)
            except Exception as e:
                logging.error(f"Error during discovery and trading: {e}")
                logging.error(traceback.format_exc())
                await asyncio.sleep(60)
    
    async def run(self):
        """
        Main bot execution method
        """
        logging.info("="*50)
        logging.info("   Solana Trading Bot Starting")
        logging.info("="*50)
        try:
            BotConfiguration.setup_bot_controls()
            balance_sol, balance_usd = await self.trader.get_wallet_balance()
            logging.info(f"Initial Wallet Balance: {balance_sol:.4f} SOL (${balance_usd:.2f})")
            tasks = [
                asyncio.create_task(self.scanner.start_scanning()),
                asyncio.create_task(self.trader.monitor_positions()),
                asyncio.create_task(self._discover_and_trade())
            ]
            while self.running:
                done, pending = await asyncio.wait(tasks, timeout=60, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    try:
                        task.result()
                        logging.warning(f"Task {task.get_name()} completed unexpectedly")
                    except asyncio.CancelledError:
                        logging.info(f"Task {task.get_name()} was cancelled")
                    except Exception as e:
                        logging.error(f"Task {task.get_name()} failed with error: {e}")
                        logging.error(traceback.format_exc())
                    tasks.remove(task)
                    if "scanner.start_scanning" in str(task):
                        tasks.append(asyncio.create_task(self.scanner.start_scanning()))
                    elif "trader.monitor_positions" in str(task):
                        tasks.append(asyncio.create_task(self.trader.monitor_positions()))
                    elif "discover_and_trade" in str(task):
                        tasks.append(asyncio.create_task(self._discover_and_trade()))
                if not self.running:
                    break
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        except KeyboardInterrupt:
            logging.info("Bot stopped by user")
        except Exception as e:
            logging.critical(f"Bot execution failed: {e}")
            logging.critical(traceback.format_exc())
        finally:
            logging.info("Closing connections")
            await self.trader.close()
            logging.info("="*50)
            logging.info("   Solana Trading Bot Shutdown Complete")
            logging.info("="*50)

#################################
# MAIN ENTRY POINT
#################################

def setup_logging():
    """
    Configure logging
    """
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with daily rotation
    file_handler = logging.handlers.RotatingFileHandler(
        f'logs/trading_bot_{datetime.now(UTC).strftime("%Y%m%d_%H%M%S")}.log',
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

def main():
    """
    Entry point for the trading bot
    """
    try:
        # Configure Python's recursion limit to be higher
        sys.setrecursionlimit(3000)  # Increased from default
        
        # Set a conservative thread stack size to help with recursion
        try:
            import threading
            threading.stack_size(16*1024*1024)  # 16MB stack size
        except (ImportError, AttributeError, RuntimeError):
            pass
        
        # Setup directories
        os.makedirs('data', exist_ok=True)
        
        # Setup logging
        logger = setup_logging()
        logger.info(f"Python recursion limit set to {sys.getrecursionlimit()}")
        
        # Initialize and run the bot
        bot = TradingBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.critical(f"Unhandled bot initialization error: {e}")
        logging.critical(traceback.format_exc())
    finally:
        logging.info("Bot execution completed")

if __name__ == "__main__":
    main()) and w[1:].isalpha():
                                ticker = w[1:]
                                break
                            elif w.isupper() and 2 <= len(w) <= 8 and w.isalpha():
                                ticker = w
                                break
                        engagement = (
                            tweet.public_metrics.get('retweet_count', 0) +
                            tweet.public_metrics.get('like_count', 0) +
                            tweet.public_metrics.get('reply_count', 0) * 2
                        )
                        self.db.store_token(
                            contract_address=word,
                            ticker=ticker,
                            name="UNKNOWN",
                            launch_date=tweet.created_at.isoformat(),
                            safety_score=50.0 + (engagement / 10),
                            volume_24h=0.0,
                            liquidity_locked=False
                        )
                        discovered_contracts.add(word)
                        logging.debug(f"Discovered token from Twitter: {ticker} ({word})")
            logging.info(f"Discovered {len(discovered_contracts)} tokens from Twitter")
            return discovered_contracts
        except Exception as e:
            logging.error(f"Twitter scan failed: {e}")
            return discovered_contracts

    async def scan_top_gainers(self) -> List[Dict]:
        gainers = []
        try:
            gainers_24h = await self.analyzer.get_top_gainers(timeframe='24h', limit=5)
            seen_contracts = set()
            for token in gainers_24h:
                contract = token.get('contract_address')
                if not contract or is_fake_token(contract):
                    continue
                if contract not in seen_contracts:
                    seen_contracts.add(contract)
                    gainers.append(token)
            logging.info(f"Found {len(gainers)} top gainer tokens")
            for token in gainers:
                self.db.store_token(
                    contract_address=token.get('contract_address'),
                    ticker=token.get('ticker', 'UNKNOWN'),
                    name=token.get('name', 'UNKNOWN'),
                    launch_date=datetime.now(UTC).isoformat(),
                    volume_24h=token.get('volume_24h', 0.0),
                    safety_score=70.0,
                    liquidity_locked=False
                )
            return gainers
        except Exception as e:
            logging.error(f"Error scanning for top gainers: {e}")
            return []

    async def scan_trending_tokens(self) -> List[Dict]:
        trending = []
        try:
            trending = await self.analyzer.get_trending_tokens(10)
            if not trending:
                logging.info("No trending tokens found")
                return []
            filtered = [t for t in trending if t.get('contract_address') and not is_fake_token(t.get('contract_address'))]
            logging.info(f"Found {len(filtered)} trending tokens")
            for token in filtered:
                self.db.store_token(
                    contract_address=token.get('contract_address'),
                    ticker=token.get('ticker', 'UNKNOWN'),
                    name=token.get('name', 'UNKNOWN'),
                    launch_date=datetime.now(UTC).isoformat(),
                    volume_24h=token.get('volume_24h', 0.0),
                    safety_score=65.0,
                    liquidity_locked=False
                )
            return filtered
        except Exception as e:
            logging.error(f"Error scanning for trending tokens: {e}")
            return []

    async def analyze_tokens(self) -> List[Dict]:
        tradable_tokens = []
        try:
            min_safety = BotConfiguration.TRADING_PARAMETERS['MIN_SAFETY_SCORE']
            tokens_df = self.db.get_tokens(limit=20, min_safety_score=min_safety)
            if tokens_df.empty:
                logging.info("No tokens to analyze")
                return tradable_tokens
            for _, token in tokens_df.iterrows():
                contract = token['contract_address']
                if contract in self.discovered_tokens or not isinstance(contract, str) or 'pump' in contract.lower() or is_fake_token(contract):
                    continue
                try:
                    evaluation = await self.analyzer.evaluate_trading_potential(contract)
                    if evaluation['tradable']:
                        tradable_tokens.append(evaluation)
                        logging.info(f"Tradable token found: {token['ticker']} ({contract})")
                except Exception as e:
                    logging.error(f"Error evaluating {contract}: {e}")
                    continue
                self.discovered_tokens.add(contract)
                await asyncio.sleep(1)
            if len(self.discovered_tokens) > 100:
                self.discovered_tokens = set(list(self.discovered_tokens)[-100:])
            return tradable_tokens
        except Exception as e:
            logging.error(f"Token analysis failed: {e}")
            return []

    async def get_tokens_by_criteria(self) -> List[Dict]:
        qualified = []
        try:
            params = BotConfiguration.TRADING_PARAMETERS
            top = await self.scan_top_gainers()
            trend = await self.scan_trending_tokens()
            all_tokens = top + trend
            for token in all_tokens:
                contract = token.get('contract_address')
                if not contract or not isinstance(contract, str) or is_fake_token(contract):
                    continue
                token_data = await self.analyzer.fetch_token_data(contract)
                if not token_data:
                    continue
                if (token_data.get('volume_24h', 0) >= params['MIN_VOLUME'] and
                    token_data.get('liquidity_usd', 0) >= params['MIN_LIQUIDITY'] and
                    token_data.get('mcap', 0) >= params['MIN_MCAP'] and
                    token_data.get('holders', 0) >= params['MIN_HOLDERS']):
                    score = await self.analyzer.calculate_safety_score(contract)
                    token_data['safety_score'] = score
                    qualified.append({
                        'token_data': token_data,
                        'tradable': True,
                        'reason': 'Meets screening criteria',
                        'recommendation': {
                            'action': 'BUY',
                            'confidence': min(100, score),
                            'max_investment': params['MAX_INVESTMENT_PER_TOKEN'],
                            'take_profit': params['TAKE_PROFIT_TARGET'],
                            'stop_loss': params['STOP_LOSS_PERCENTAGE']
                        }
                    })
                    logging.info(f"Qualified token found: {token_data.get('ticker')} ({contract})")
            return qualified
        except Exception as e:
            logging.error(f"Error filtering tokens by criteria: {e}")
            return []

    async def start_scanning(self):
        logging.info("Starting token scanner")
        while True:
            try:
                if not BotConfiguration.load_trading_parameters():
                    logging.info("Bot paused by control settings")
                    await asyncio.sleep(60)
                    continue
                logging.info("Scanning Twitter for tokens...")
                await self.scan_twitter_for_tokens()
                logging.info("Analyzing tokens by screening criteria...")
                qualified = await self.get_tokens_by_criteria()
                logging.info("Analyzing other discovered tokens...")
                others = await self.analyze_tokens()
                all_tradable = qualified + others
                interval = BotConfiguration.TRADING_PARAMETERS['SCAN_INTERVAL']
                logging.info(f"Scan complete, waiting {interval} seconds for next scan")
                await asyncio.sleep(interval)
            except Exception as e:
                logging.error(f"Error during token scanning: {e}")
                await asyncio.sleep(60)

#################################
# SOLANA TRADER
#################################

class SolanaTrader:
    """
    Manages Solana trading operations
    """
    
    def __init__(self):
        """
        Initialize Solana trader
        """
        self.db = Database()
        self.client = None
        self.keypair = self._setup_wallet()
        self.active_orders = {}
        self.connected = False
        self.last_connection_attempt = 0
        self.token_analyzer = TokenAnalyzer(db=self.db)
        
        # Get simulation mode from config
        control = self._load_control_settings()
        self.simulation_mode = control.get('simulation_mode', True)
        self.simulation_success_rate = 0.95  # 95% success rate for simulated trades
        
        # Log simulation status
        if self.simulation_mode:
            logging.info("Trading bot running in SIMULATION MODE - no real trades will be executed")
        else:
            logging.warning("Trading bot running in REAL TRADING MODE - actual trades will be executed!")
        
        # Load active orders
        self._load_active_orders()
    
    def _load_control_settings(self):
        """Load control settings from file"""
        try:
            with open(BotConfiguration.BOT_CONTROL_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading control settings: {e}")
            return {'simulation_mode': True}  # Default to simulation mode
    
    def _setup_wallet(self) -> Keypair:
        """
        Set up Solana wallet from private key
        
        :return: Solana keypair
        """
        try:
            private_key = BotConfiguration.API_KEYS['WALLET_PRIVATE_KEY']
            if not private_key:
                raise ValueError("Wallet private key not provided")
            
            keypair = Keypair.from_bytes(bytes.fromhex(private_key))
            logging.info(f"Wallet initialized: {keypair.pubkey()}")
            return keypair
        
        except Exception as e:
            logging.critical(f"Wallet setup failed: {e}")
            raise
    
    def _load_active_orders(self):
        """
        Load active orders from database
        """
        try:
            orders_df = self.db.get_active_orders()
            for _, row in orders_df.iterrows():
                contract_address = row['contract_address']
                self.active_orders[contract_address] = {
                    'amount': row['amount'],
                    'buy_price': row['buy_price'],
                    'timestamp': row['timestamp']
                }
            logging.info(f"Loaded {len(self.active_orders)} active orders")
        
        except Exception as e:
            logging.error(f"Failed to load active orders: {e}")
    
    async def connect(self, force=False) -> bool:
        """
        Connect to Solana RPC endpoint
        
        :param force: Force reconnection even if recently connected
        :return: True if connected, False otherwise
        """
        current_time = time.time()
        
        # Skip if already connected recently
        if (self.connected and 
            current_time - self.last_connection_attempt < 60 and 
            not force):
            return True
        
        self.last_connection_attempt = current_time
        
        # Connection parameters
        rpc_endpoint = BotConfiguration.API_KEYS['SOLANA_RPC_ENDPOINT']
        max_retries = 5
        base_delay = 2
        
        # Attempt connection with retries
        for attempt in range(max_retries):
            try:
                # Close existing client if any
                if self.client:
                    await self.client.close()
                
                # Create new client
                self.client = AsyncClient(rpc_endpoint, timeout=30)
                
                # Check connection
                if await self.client.is_connected():
                    self.connected = True
                    logging.info("Connected to Solana RPC")
                    return True
            
            except Exception as e:
                self.connected = False
                logging.error(f"Connection attempt {attempt + 1}/{max_retries} failed: {e}")
                
                # Exponential backoff
                if attempt < max_retries - 1:
                    await asyncio.sleep(base_delay * (2 ** attempt))
        
        logging.critical("Failed to connect to Solana RPC")
        return False
    
    async def get_wallet_balance(self) -> Tuple[float, float]:
        """
        Get wallet SOL balance
        
        :return: (SOL balance, USD value)
        """
        # In simulation mode, return a simulated balance
        if self.simulation_mode:
            # Return a simulated balance of 5 SOL
            simulated_balance_sol = 5.0
            # Get SOL/USD price for USD conversion
            sol_price_usd = await self.get_sol_price()
            # Calculate USD value
            simulated_balance_usd = simulated_balance_sol * sol_price_usd
            
            logging.debug(f"Simulation mode: Using simulated wallet balance: {simulated_balance_sol:.4f} SOL (${simulated_balance_usd:.2f})")
            return simulated_balance_sol, simulated_balance_usd
        
        # Real balance retrieval for non-simulation mode
        if not await self.connect():
            return 0.0, 0.0
        
        try:
            # Get SOL balance in lamports
            balance_response = await self.client.get_balance(self.keypair.pubkey())
            balance_lamports = balance_response.value
            
            # Convert to SOL
            balance_sol = balance_lamports / 1_000_000_000
            
            # Get SOL/USD price
            sol_price_usd = await self.get_sol_price()
            
            # Calculate USD value
            balance_usd = balance_sol * sol_price_usd
            
            logging.debug(f"Wallet balance: {balance_sol:.4f} SOL (${balance_usd:.2f})")
            return balance_sol, balance_usd
        
        except Exception as e:
            logging.error(f"Error fetching wallet balance: {e}")
            return 0.0, 0.0
    
    async def get_sol_price(self) -> float:
        """
        Get current SOL/USD price
        
        :return: SOL price in USD
        """
        sources = [
            # Multiple price sources for redundancy
            self._get_sol_price_coingecko,
            self._get_sol_price_jupiter,
            self._get_sol_price_coinbase
        ]
        
        # Try each source until successful
        for source_func in sources:
            try:
                price = await source_func()
                if price > 0:
                    return price
            except Exception as e:
                logging.warning(f"Price source failed: {e}")
        
        # Fall back to default price
        logging.warning("All SOL price sources failed. Using default price.")
        return 171.41  # Updated default price
    
    async def _get_sol_price_coingecko(self) -> float:
        """Get SOL price from CoinGecko"""
        url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
        data = await fetch_with_retries(url)
        if data and 'solana' in data and 'usd' in data['solana']:
            return float(data['solana']['usd'])
        return 0.0
    
    async def _get_sol_price_jupiter(self) -> float:
        """Get SOL price from Jupiter"""
        url = "https://price.jup.ag/v4/price?ids=SOL"
        data = await fetch_with_retries(url)
        if data and 'data' in data and 'SOL' in data['data']:
            return float(data['data']['SOL']['price'])
        return 0.0
    
    async def _get_sol_price_coinbase(self) -> float:
        """Get SOL price from Coinbase"""
        url = "https://api.coinbase.com/v2/prices/SOL-USD/spot"
        data = await fetch_with_retries(url)
        if data and 'data' in data and 'amount' in data['data']:
            return float(data['data']['amount'])
        return 0.0
    
    async def get_token_balance(self, token_address: str) -> int:
        """
        Get token balance for wallet
        
        :param token_address: Token contract address
        :return: Token balance in smallest units
        """
        # In simulation mode, return a fake balance for active orders
        if self.simulation_mode and token_address in self.active_orders:
            logging.debug(f"Simulation mode: Returning fake token balance for {token_address}")
            return 1000000  # Fake 1 token
            
        if not await self.connect():
            return 0
        
        try:
            pubkey = self.keypair.pubkey()
            
            # Get token accounts for owner
            response = await self.client.get_token_accounts_by_owner(
                pubkey,
                {"mint": Pubkey.from_string(token_address)},
                commitment=Confirmed
            )
            
            # Check if any accounts found
            if response.value:
                account = response.value[0]
                
                # Get token account balance
                balance_info = await self.client.get_token_account_balance(
                    account.pubkey
                )
                
                # Return balance amount
                balance = int(balance_info.value.amount)
                logging.debug(f"Token balance for {token_address}: {balance}")
                return balance
            
            logging.debug(f"No token accounts found for {token_address}")
            return 0
        
        except Exception as e:
            logging.error(f"Error getting token balance for {token_address}: {e}")
            return 0
    
    async def get_token_price(self, token_address: str) -> Optional[float]:
        """
        Get token price in SOL
        
        :param token_address: Token contract address
        :return: Token price in SOL or None if error
        """
        # In simulation mode, use real price data instead of artificial values
        if self.simulation_mode and token_address in self.active_orders:
            # Get real price from TokenAnalyzer
            real_price = await self.token_analyzer.get_current_price(token_address)
            if real_price > 0:
                logging.debug(f"Simulation mode: Using real price for {token_address}: ${real_price}")
                sol_price = await self.get_sol_price()
                # Convert USD price to SOL
                price_sol = real_price / sol_price if sol_price > 0 else 0
                return price_sol
            
            # Fall back to stored price if unable to get current
            buy_price = self.active_orders[token_address]['buy_price']
            # Add a small random price movement
            price_movement = random.uniform(0.9, 1.1)  # ±10%
            return buy_price * price_movement
            
        try:
            # Check if address is valid
            if not is_valid_solana_address(token_address):
                logging.warning(f"Invalid token address: {token_address}")
                return None
                
            # Use Jupiter API to get quote
            sol_mint = "So11111111111111111111111111111111111111112"
            
            # Request for 1 token
            quote_params = {
                'inputMint': token_address,
                'outputMint': sol_mint,
                'amount': "1000000",  # 1 token in smallest units
                'slippageBps': "50"   # 0.5% slippage
            }
            
            # Get quote from Jupiter
            quote_url = BotConfiguration.API_KEYS['JUPITER_QUOTE_API']
            quote_data = await fetch_with_retries(quote_url, params=quote_params)
            
            # Calculate price from quote
            if quote_data and 'outAmount' in quote_data:
                # Convert lamports to SOL
                price_sol = int(quote_data['outAmount']) / 1_000_000_000
                return price_sol
            
            logging.warning(f"Failed to get price for {token_address}")
            return None
        
        except Exception as e:
            logging.error(f"Error getting token price for {token_address}: {e}")
            return None
    
    async def execute_trade(self, contract_address: str, action: str, amount: float) -> Optional[str]:
        """
        Execute a token trade
        
        :param contract_address: Token contract address
        :param action: Trade action (BUY/SELL)
        :param amount: Trade amount in SOL
        :return: Transaction signature or None if failed
        """
        # Check action type
        if action.upper() == 'BUY':
            return await self._buy_token(contract_address, amount)
        elif action.upper() == 'SELL':
            return await self._sell_token(contract_address, amount)
        else:
            logging.error(f"Invalid trade action: {action}")
            return None
    
    async def _buy_token(self, contract_address: str, amount_sol: float) -> Optional[str]:
        """
        Buy token with SOL
        
        :param contract_address: Token contract address
        :param amount_sol: Amount in SOL to spend
        :return: Transaction signature or None if failed
        """
        # Handle simulation mode with real prices
        if self.simulation_mode:
            logging.info(f"Simulation mode: Executing simulated buy for {contract_address}")
            
            # Simulate success most of the time
            if random.random() <= self.simulation_success_rate:
                # Get real token price if possible
                token_price_usd = await self.token_analyzer.get_current_price(contract_address)
                sol_price_usd = await self.get_sol_price()
                
                # Calculate token price in SOL
                if token_price_usd > 0 and sol_price_usd > 0:
                    token_price_sol = token_price_usd / sol_price_usd
                else:
                    # Fallback to reasonable simulation value
                    token_price_sol = 0.00005  # Typical small token price
                
                timestamp = datetime.now(UTC).isoformat()
                
                # Record in database
                self.db.record_trade(contract_address, 'BUY', amount_sol, token_price_sol)
                
                # Update active orders
                self.active_orders[contract_address] = {
                    'amount': amount_sol,
                    'buy_price': token_price_sol,
                    'timestamp': timestamp
                }
                
                # Return simulated tx signature
                return "SIM_" + "".join(random.choices("0123456789abcdef", k=60))
            else:
                logging.warning(f"Simulation mode: Buy failed for {contract_address}")
                return None
        
        # Real trading logic for non-simulation mode
        # Check connection
        if not await self.connect():
            logging.error("Failed to connect to Solana for buy")
            return None
        
        # Check wallet balance
        balance_sol, _ = await self.get_wallet_balance()
        if balance_sol < amount_sol:
            logging.warning(f"Insufficient balance: {balance_sol} SOL < {amount_sol} SOL")
            return None
        
        # Get trading parameters
        params = BotConfiguration.TRADING_PARAMETERS
        max_retries = params['MAX_BUY_RETRIES']
        slippage = params['SLIPPAGE_TOLERANCE']
        
        # SOL mint address
        sol_mint = "So11111111111111111111111111111111111111112"
        
        # Convert SOL to lamports
        amount_lamports = int(amount_sol * 1_000_000_000)
        
        # Attempt to buy with retries
        for attempt in range(max_retries):
            try:
                # Get quote from Jupiter
                quote_params = {
                    'inputMint': sol_mint,
                    'outputMint': contract_address,
                    'amount': str(amount_lamports),
                    'slippageBps': str(int(slippage * 10000))
                }
                
                quote_url = BotConfiguration.API_KEYS['JUPITER_QUOTE_API']
                quote = await fetch_with_retries(quote_url, params=quote_params)
                
                if not quote:
                    logging.warning(f"Buy attempt {attempt + 1}/{max_retries}: No quote received")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)
                    continue
                
                # Execute swap transaction
                swap_url = BotConfiguration.API_KEYS['JUPITER_SWAP_API']
                swap_payload = {
                    'quoteResponse': quote,
                    'userPublicKey': str(self.keypair.pubkey()),
                    'prioritizationFeeLamports': 1000000  # 0.001 SOL fee
                }
                
                swap_data = await fetch_with_retries(
                    swap_url, 
                    method='POST', 
                    json_data=swap_payload
                )
                
                if not swap_data or 'swapTransaction' not in swap_data:
                    logging.error(f"Invalid swap data on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)
                    continue
                
                # Get transaction data
                transaction_data = base64.b64decode(swap_data['swapTransaction'])
                
                # Send transaction
                send_tx_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "sendTransaction",
                    "params": [
                        swap_data['swapTransaction'],
                        {
                            "encoding": "base64", 
                            "skipPreflight": True, 
                            "preflightCommitment": "confirmed", 
                            "maxRetries": 5
                        }
                    ]
                }
                
                tx_response = await fetch_with_retries(
                    BotConfiguration.API_KEYS['SOLANA_RPC_ENDPOINT'], 
                    method='POST',
                    headers={'Content-Type': 'application/json'},
                    json_data=send_tx_payload
                )
                
                # Extract transaction signature
                if tx_response and 'result' in tx_response:
                    txid = tx_response['result']
                    
                    # Calculate token price
                    out_amount = int(quote.get('outAmount', 1))
                    buy_price = amount_lamports / out_amount if out_amount > 0 else 0
                    
                    # Record trade in database
                    timestamp = datetime.now(UTC).isoformat()
                    self.db.record_trade(contract_address, 'BUY', amount_sol, buy_price)
                    
                    # Update active orders dict
                    self.active_orders[contract_address] = {
                        'amount': amount_sol, 
                        'buy_price': buy_price, 
                        'timestamp': timestamp
                    }
                    
                    logging.info(f"Buy executed: {txid} for {contract_address} - {amount_sol} SOL")
                    return txid
                
                logging.warning(f"Transaction failed on attempt {attempt + 1}")
                
            except Exception as e:
                logging.error(f"Buy attempt {attempt + 1}/{max_retries} failed for {contract_address}: {e}")
            
            # Wait before next attempt
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
        
        logging.error(f"All buy attempts failed for {contract_address}")
        return None
    
    async def _sell_token(self, contract_address: str, amount_sol: Optional[float] = None) -> Optional[str]:
        """
        Sell token for SOL
        
        :param contract_address: Token contract address
        :param amount_sol: Amount in SOL equivalent to sell (if None, sell all)
        :return: Transaction signature or None if failed
        """
        # Handle simulation mode with real prices
        if self.simulation_mode:
            logging.info(f"Simulation mode: Executing simulated sell for {contract_address}")
            
            # Simulate success most of the time
            if random.random() <= self.simulation_success_rate:
                # Only proceed if we have this token in active orders
                if contract_address in self.active_orders:
                    buy_amount = self.active_orders[contract_address]['amount']
                    buy_price = self.active_orders[contract_address]['buy_price']
                    
                    # Get real token price for more accurate simulation
                    token_price_usd = await self.token_analyzer.get_current_price(contract_address)
                    sol_price_usd = await self.get_sol_price()
                    
                    # Calculate token price in SOL
                    if token_price_usd > 0 and sol_price_usd > 0:
                        sell_price = token_price_usd / sol_price_usd
                    else:
                        # Random price movement for simulation if real price unavailable
                        price_movement = random.uniform(0.8, 1.2)  # ±20%
                        sell_price = buy_price * price_movement
                    
                    # Record sell in database
                    self.db.record_trade(contract_address, 'SELL', buy_amount, sell_price)
                    
                    # Remove from active orders
                    del self.active_orders[contract_address]
                    
                    # Return simulated tx signature
                    return "SIM_" + "".join(random.choices("0123456789abcdef", k=60))
                else:
                    logging.warning(f"No active order found for {contract_address}")
                    return None
            else:
                logging.warning(f"Simulation mode: Sell failed for {contract_address}")
                return None
                
        # Real trading logic for non-simulation mode
        # Check if we have this token
        if (contract_address not in self.active_orders and 
            not await self.get_token_balance(contract_address)):
            logging.warning(f"No tokens to sell for {contract_address}")
            return None
        
        # Check connection
        if not await self.connect():
            logging.error("Failed to connect to Solana for sell")
            return None
        
        # Get trading parameters
        params = BotConfiguration.TRADING_PARAMETERS
        max_retries = params['MAX_SELL_RETRIES']
        slippage = params['SLIPPAGE_TOLERANCE']
        moonbag_pct = params['MOONBAG_PERCENTAGE']
        
        # SOL mint address
        sol_mint = "So11111111111111111111111111111111111111112"
        
        # Get actual token balance
        token_balance = await self.get_token_balance(contract_address)
        if token_balance <= 0:
            logging.warning(f"No token balance for {contract_address}")
            return None
        
        # Determine amount to sell (keep moonbag if configured)
        sell_all = amount_sol is None
        amount_to_sell = token_balance
        
        if not sell_all and moonbag_pct > 0:
            # Calculate percentage to sell
            amount_to_sell = int(token_balance * (1 - moonbag_pct))
        
        # Attempt to sell with retries
        for attempt in range(max_retries):
            try:
                # Get quote from Jupiter
                quote_params = {
                    'inputMint': contract_address,
                    'outputMint': sol_mint,
                    'amount': str(amount_to_sell),
                    'slippageBps': str(int(slippage * 10000))
                }
                
                quote_url = BotConfiguration.API_KEYS['JUPITER_QUOTE_API']
                quote = await fetch_with_retries(quote_url, params=quote_params)
                
                if not quote:
                    logging.warning(f"Sell attempt {attempt + 1}/{max_retries}: No quote received")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)
                    continue
                
                # Execute swap transaction
                swap_url = BotConfiguration.API_KEYS['JUPITER_SWAP_API']
                swap_payload = {
                    'quoteResponse': quote,
                    'userPublicKey': str(self.keypair.pubkey()),
                    'prioritizationFeeLamports': 1000000  # 0.001 SOL fee
                }
                
                swap_data = await fetch_with_retries(
                    swap_url, 
                    method='POST', 
                    json_data=swap_payload
                )
                
                if not swap_data or 'swapTransaction' not in swap_data:
                    logging.error(f"Invalid swap data on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)
                    continue
                
                # Get transaction data
                transaction_data = base64.b64decode(swap_data['swapTransaction'])
                
                # Send transaction
                send_tx_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "sendTransaction",
                    "params": [
                        swap_data['swapTransaction'],
                        {
                            "encoding": "base64", 
                            "skipPreflight": True, 
                            "preflightCommitment": "confirmed", 
                            "maxRetries": 5
                        }
                    ]
                }
                
                tx_response = await fetch_with_retries(
                    BotConfiguration.API_KEYS['SOLANA_RPC_ENDPOINT'], 
                    method='POST',
                    headers={'Content-Type': 'application/json'},
                    json_data=send_tx_payload
                )
                
                # Extract transaction signature
                if tx_response and 'result' in tx_response:
                    txid = tx_response['result']
                    
                    # Calculate sell price
                    out_amount_lamports = int(quote.get('outAmount', 0))
                    out_amount_sol = out_amount_lamports / 1_000_000_000
                    sell_price = out_amount_sol / (amount_to_sell / 1_000_000)
                    
                    # Record trade in database
                    self.db.record_trade(contract_address, 'SELL', out_amount_sol, sell_price)
                    
                    # Update active orders
                    if sell_all or moonbag_pct == 0:
                        # Remove from active orders if selling all
                        if contract_address in self.active_orders:
                            del self.active_orders[contract_address]
                    else:
                        # Update remaining amount if keeping moonbag
                        if contract_address in self.active_orders:
                            original_amount = self.active_orders[contract_address]['amount']
                            remaining = original_amount * moonbag_pct
                            self.active_orders[contract_address]['amount'] = remaining
                    
                    logging.info(f"Sell executed: {txid} for {contract_address} - {out_amount_sol} SOL received")
                    return txid
                
                logging.warning(f"Transaction failed on attempt {attempt + 1}")
                
            except Exception as e:
                logging.error(f"Sell attempt {attempt + 1}/{max_retries} failed for {contract_address}: {e}")
            
            # Wait before next attempt
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
        
        logging.error(f"All sell attempts failed for {contract_address}")
        return None
    
    async def monitor_positions(self):
        """
        Monitor active positions for take profit or stop loss
        """
        logging.info("Starting position monitor")
        
        while True:
            try:
                # Load current trading parameters
                BotConfiguration.load_trading_parameters()
                params = BotConfiguration.TRADING_PARAMETERS
                take_profit = params['TAKE_PROFIT_TARGET']
                stop_loss = params['STOP_LOSS_PERCENTAGE']
                
                # Get active orders from database (to ensure we have the latest)
                orders_df = self.db.get_active_orders()
                
                # Skip if no active orders
                if orders_df.empty:
                    logging.debug("No active positions to monitor")
                    await asyncio.sleep(60)
                    continue
                
                # Iterate through active positions
                for _, position in orders_df.iterrows():
                    contract_address = position['contract_address']
                    buy_price = position['buy_price']
                    buy_amount = position['amount']
                    
                    # Skip if invalid data
                    if buy_price <= 0:
                        continue
                    
                    # Get current price
                    current_price = await self.get_token_price(contract_address)
                    if not current_price:
                        logging.warning(f"Could not get current price for {contract_address}")
                        continue
                    
                    # Calculate profit/loss percentage
                    price_change_pct = ((current_price - buy_price) / buy_price) * 100
                    
                    # Log position status
                    logging.debug(f"Position {contract_address}: Price change {price_change_pct:.2f}%")
                    
                    # Check take profit condition
                    if price_change_pct >= ((take_profit - 1) * 100):
                        logging.info(f"Take profit triggered for {contract_address}: {price_change_pct:.2f}%")
                        await self._sell_token(contract_address)
                        continue
                    
                    # Check stop loss condition
                    if price_change_pct <= -(stop_loss * 100):
                        logging.info(f"Stop loss triggered for {contract_address}: {price_change_pct:.2f}%")
                        await self._sell_token(contract_address)
                        continue
                
                # Wait before next check
                await asyncio.sleep(60)
            
            except Exception as e:
                logging.error(f"Position monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def close(self):
        """
        Close connections and cleanup
        """
        if self.client:
            try:
                await self.client.close()
                logging.info("Solana RPC client closed")
            except Exception as e:
                logging.error(f"Error closing Solana RPC client: {e}")

#################################
# TRADING BOT
#################################

class TradingBot:
    """
    Main trading bot class
    """
    def __init__(self):
        """
        Initialize trading bot
        """
        self.running = True
        self.trader = SolanaTrader()
        self.scanner = TokenScanner()
        self.db = Database()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """
        Setup graceful shutdown signal handlers
        """
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """
        Handle shutdown signals
        """
        logging.critical(f"Received signal {signum}. Initiating graceful shutdown...")
        self.running = False
    
    async def _discover_and_trade(self):
        """
        Discover and trade tokens
        """
        logging.info("Starting token discovery and trading process")
        while self.running:
            try:
                balance_sol, balance_usd = await self.trader.get_wallet_balance()
                logging.info(f"Current wallet balance: {balance_sol:.4f} SOL (${balance_usd:.2f})")
                qualified_tokens = await self.scanner.get_tokens_by_criteria()
                if not qualified_tokens:
                    logging.info("No tokens found meeting screening criteria, analyzing other tokens...")
                    other_tradable = await self.scanner.analyze_tokens()
                    qualified_tokens = other_tradable
                
                for token in qualified_tokens:
                    token_data = token['token_data']
                    contract = token_data['contract_address']
                    ticker = token_data['ticker']
                    recommendation = token['recommendation']
                    max_investment = recommendation['max_investment']
                    
                    active_orders = self.db.get_active_orders()
                    if not active_orders.empty and contract in active_orders['contract_address'].values:
                        logging.info(f"Already have position in {ticker} ({contract}), skipping")
                        continue
                    
                    logging.info(f"Token {ticker} qualified for trading:")
                    logging.info(f"  - Volume 24h: ${token_data.get('volume_24h', 0):,.2f}")
                    logging.info(f"  - Liquidity: ${token_data.get('liquidity_usd', 0):,.2f}")
                    logging.info(f"  - Market Cap: ${token_data.get('mcap', 0):,.2f}")
                    logging.info(f"  - Holders: {token_data.get('holders', 0):,}")
                    logging.info(f"  - Price Change 24h: {token_data.get('price_change_24h', 0):.2f}%")
                    logging.info(f"  - Security Score: {token_data.get('safety_score', 0):.1f}/100")
                    
                    if balance_sol < max_investment:
                        logging.warning(f"Insufficient balance ({balance_sol} SOL) for trade of {max_investment} SOL")
                        continue
                    
                    logging.info(f"Trading {ticker} ({contract}) for {max_investment} SOL")
                    txid = await self.trader.execute_trade(contract, 'BUY', max_investment)
                    if txid:
                        logging.info(f"Successfully traded {ticker}: {txid}")
                        balance_sol -= max_investment
                    else:
                        logging.error(f"Failed to trade {ticker}")
                
                logging.debug("Waiting for next discovery cycle")
                await asyncio.sleep(300)
            except Exception as e:
                logging.error(f"Error during discovery and trading: {e}")
                logging.error(traceback.format_exc())
                await asyncio.sleep(60)
    
    async def run(self):
        """
        Main bot execution method
        """
        logging.info("="*50)
        logging.info("   Solana Trading Bot Starting")
        logging.info("="*50)
        try:
            BotConfiguration.setup_bot_controls()
            balance_sol, balance_usd = await self.trader.get_wallet_balance()
            logging.info(f"Initial Wallet Balance: {balance_sol:.4f} SOL (${balance_usd:.2f})")
            tasks = [
                asyncio.create_task(self.scanner.start_scanning()),
                asyncio.create_task(self.trader.monitor_positions()),
                asyncio.create_task(self._discover_and_trade())
            ]
            while self.running:
                done, pending = await asyncio.wait(tasks, timeout=60, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    try:
                        task.result()
                        logging.warning(f"Task {task.get_name()} completed unexpectedly")
                    except asyncio.CancelledError:
                        logging.info(f"Task {task.get_name()} was cancelled")
                    except Exception as e:
                        logging.error(f"Task {task.get_name()} failed with error: {e}")
                        logging.error(traceback.format_exc())
                    tasks.remove(task)
                    if "scanner.start_scanning" in str(task):
                        tasks.append(asyncio.create_task(self.scanner.start_scanning()))
                    elif "trader.monitor_positions" in str(task):
                        tasks.append(asyncio.create_task(self.trader.monitor_positions()))
                    elif "discover_and_trade" in str(task):
                        tasks.append(asyncio.create_task(self._discover_and_trade()))
                if not self.running:
                    break
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        except KeyboardInterrupt:
            logging.info("Bot stopped by user")
        except Exception as e:
            logging.critical(f"Bot execution failed: {e}")
            logging.critical(traceback.format_exc())
        finally:
            logging.info("Closing connections")
            await self.trader.close()
            logging.info("="*50)
            logging.info("   Solana Trading Bot Shutdown Complete")
            logging.info("="*50)

#################################
# MAIN ENTRY POINT
#################################

def setup_logging():
    """
    Configure logging
    """
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with daily rotation
    file_handler = logging.handlers.RotatingFileHandler(
        f'logs/trading_bot_{datetime.now(UTC).strftime("%Y%m%d_%H%M%S")}.log',
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

def main():
    """
    Entry point for the trading bot
    """
    try:
        # Configure Python's recursion limit to be higher
        sys.setrecursionlimit(3000)  # Increased from default
        
        # Set a conservative thread stack size to help with recursion
        try:
            import threading
            threading.stack_size(16*1024*1024)  # 16MB stack size
        except (ImportError, AttributeError, RuntimeError):
            pass
        
        # Setup directories
        os.makedirs('data', exist_ok=True)
        
        # Setup logging
        logger = setup_logging()
        logger.info(f"Python recursion limit set to {sys.getrecursionlimit()}")
        
        # Initialize and run the bot
        bot = TradingBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.critical(f"Unhandled bot initialization error: {e}")
        logging.critical(traceback.format_exc())
    finally:
        logging.info("Bot execution completed")

if __name__ == "__main__":
    main()