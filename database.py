import os
import sqlite3
import logging
import pandas as pd
from datetime import datetime, timezone

# Set up timezone
UTC = timezone.utc

# Set up logging
logger = logging.getLogger(__name__)

class Database:
    """
    Database class for storing token information and trades
    """
    
    def __init__(self, db_path='data/sol_bot.db'):
        """
        Initialize database connection
        
        :param db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._initialize_db()
        
    def _initialize_db(self):
        """
        Initialize database tables
        """
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Check if the database exists
        db_exists = os.path.exists(self.db_path)
        
        # Create database connection
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            # If database exists, check if we need to upgrade the schema
            if db_exists:
                # Check if we need to add new columns to trades table
                cursor.execute("PRAGMA table_info(trades)")
                columns = [info[1] for info in cursor.fetchall()]
                
                if 'gain_loss_sol' not in columns:
                    logger.info("Upgrading database schema: Adding gain_loss_sol column to trades table")
                    cursor.execute("ALTER TABLE trades ADD COLUMN gain_loss_sol REAL DEFAULT 0.0")
                
                if 'percentage_change' not in columns:
                    logger.info("Upgrading database schema: Adding percentage_change column to trades table")
                    cursor.execute("ALTER TABLE trades ADD COLUMN percentage_change REAL DEFAULT 0.0")
                
                if 'price_multiple' not in columns:
                    logger.info("Upgrading database schema: Adding price_multiple column to trades table")
                    cursor.execute("ALTER TABLE trades ADD COLUMN price_multiple REAL DEFAULT 1.0")
                    
                conn.commit()
            
            # Create tokens table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                contract_address TEXT PRIMARY KEY,
                ticker TEXT,
                name TEXT,
                launch_date TEXT,
                safety_score REAL,
                volume_24h REAL,
                price_usd REAL,
                liquidity_usd REAL,
                mcap REAL,
                holders INTEGER,
                liquidity_locked BOOLEAN,
                last_updated TEXT
            )
            ''')
            
            # Create trades table with new columns for gain/loss tracking
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_address TEXT,
                action TEXT,
                amount REAL,
                price REAL,
                timestamp TEXT,
                tx_hash TEXT,
                gain_loss_sol REAL DEFAULT 0.0,
                percentage_change REAL DEFAULT 0.0,
                price_multiple REAL DEFAULT 1.0
            )
            ''')
            
            # Create social_mentions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_address TEXT,
                platform TEXT,
                post_id TEXT,
                author TEXT,
                content TEXT,
                timestamp TEXT,
                engagement_score REAL
            )
            ''')
            
            conn.commit()
            logger.info("Database tables initialized")
        
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
        
        finally:
            conn.close()

    def record_trade(self, contract_address, action, amount, price, tx_hash=None, gain_loss_sol=0.0, percentage_change=0.0, price_multiple=1.0):
        """
        Record a trade in the database
        
        :param contract_address: Token contract address
        :param action: Trade action (BUY/SELL)
        :param amount: Trade amount in SOL
        :param price: Token price in SOL
        :param tx_hash: Transaction hash (optional)
        :param gain_loss_sol: Profit/loss in SOL for SELL trades
        :param percentage_change: Percentage change for SELL trades
        :param price_multiple: Price multiple for SELL trades (current_price / buy_price)
        :return: True if operation successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            timestamp = datetime.now(UTC).isoformat()
            
            # For SELL trades, calculate gain/loss metrics if not provided
            if action.upper() == 'SELL' and (gain_loss_sol == 0.0 or percentage_change == 0.0 or price_multiple == 1.0):
                # Find the corresponding BUY trade
                cursor.execute('''
                SELECT amount, price FROM trades 
                WHERE contract_address = ? AND action = 'BUY' 
                ORDER BY timestamp ASC LIMIT 1
                ''', (contract_address,))
                
                buy_trade = cursor.fetchone()
                
                if buy_trade:
                    buy_amount, buy_price = buy_trade
                    
                    # Calculate metrics
                    if buy_price > 0:
                        price_multiple = price / buy_price
                        percentage_change = (price_multiple - 1) * 100
                    
                    # Calculate gain/loss in SOL
                    buy_value = buy_amount * buy_price
                    sell_value = amount * price
                    gain_loss_sol = sell_value - buy_value
            
            cursor.execute('''
            INSERT INTO trades (
                contract_address, action, amount, price, timestamp, tx_hash,
                gain_loss_sol, percentage_change, price_multiple
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                contract_address, action.upper(), amount, price, timestamp, tx_hash,
                gain_loss_sol, percentage_change, price_multiple
            ))
            
            conn.commit()
            
            return True
        
        except Exception as e:
            logger.error(f"Error recording trade for {contract_address}: {e}")
            return False
        
        finally:
            conn.close()
            
    def store_token(self, token_data=None, **kwargs):
        """
        Store token information in the database
        
        :param token_data: Dictionary containing token data (optional)
        :param kwargs: Individual token attributes as keyword arguments
        :return: True if operation successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            # Handle both dictionary and keyword arguments
            if token_data is None:
                token_data = kwargs
            elif kwargs:
                # If both are provided, merge them with kwargs taking precedence
                merged_data = token_data.copy()
                merged_data.update(kwargs)
                token_data = merged_data
            
            # Check if contract_address is present
            if 'contract_address' not in token_data:
                logger.error("Missing required field: contract_address")
                return False
                
            # Set last_updated timestamp if not provided
            if 'last_updated' not in token_data:
                token_data['last_updated'] = datetime.now(UTC).isoformat()
            
            # Get column names from tokens table
            cursor.execute("PRAGMA table_info(tokens)")
            columns = [info[1] for info in cursor.fetchall()]
            
            # Filter token_data to include only valid columns
            filtered_data = {k: v for k, v in token_data.items() if k in columns}
            
            # Prepare SQL command
            placeholders = ', '.join(['?'] * len(filtered_data))
            columns_str = ', '.join(filtered_data.keys())
            values = list(filtered_data.values())
            
            # Use INSERT OR REPLACE to handle both insert and update
            cursor.execute(f'''
            INSERT OR REPLACE INTO tokens ({columns_str})
            VALUES ({placeholders})
            ''', values)
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error storing token data for {token_data.get('contract_address', 'unknown')}: {e}")
            return False
            
        finally:
            conn.close()
    
    def get_token(self, contract_address):
        """
        Get token information from the database
        
        :param contract_address: Token contract address
        :return: Token data as dictionary, or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM tokens WHERE contract_address = ?", (contract_address,))
            row = cursor.fetchone()
            
            if row:
                # Get column names
                cursor.execute("PRAGMA table_info(tokens)")
                columns = [info[1] for info in cursor.fetchall()]
                
                # Create dictionary from row data
                token_data = {columns[i]: row[i] for i in range(len(columns))}
                return token_data
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error fetching token data for {contract_address}: {e}")
            return None
            
        finally:
            conn.close()
    
    def get_trade_history(self, contract_address=None, limit=None):
        """
        Get trade history from the database
        
        :param contract_address: Token contract address (optional)
        :param limit: Maximum number of trades to return (optional)
        :return: List of trade records as dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            query = "SELECT * FROM trades"
            params = []
            
            if contract_address:
                query += " WHERE contract_address = ?"
                params.append(contract_address)
                
            query += " ORDER BY timestamp DESC"
            
            if limit and isinstance(limit, int) and limit > 0:
                query += " LIMIT ?"
                params.append(limit)
                
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Get column names
            cursor.execute("PRAGMA table_info(trades)")
            columns = [info[1] for info in cursor.fetchall()]
            
            # Create list of dictionaries
            trades = []
            for row in rows:
                trade_data = {columns[i]: row[i] for i in range(len(columns))}
                trades.append(trade_data)
                
            return trades
                
        except Exception as e:
            logger.error(f"Error fetching trade history: {e}")
            return []
            
        finally:
            conn.close()

    def get_active_orders(self):
        """
        Get active orders (open positions) as a DataFrame
        
        :return: Pandas DataFrame containing active positions
        """
        try:
            # Get all trades
            trades = self.get_trade_history()
            if not trades:
                return pd.DataFrame()  # Return empty DataFrame if no trades
                
            # Convert to pandas DataFrame for easier manipulation
            df = pd.DataFrame(trades)
            
            # Process only if we have data
            if not df.empty:
                # Create dictionary to track positions by contract address
                positions = {}
                
                # Group by contract address
                for contract, group in df.groupby('contract_address'):
                    buys = group[group['action'] == 'BUY']
                    sells = group[group['action'] == 'SELL']
                    
                    # Calculate total buy and sell amounts
                    total_bought = buys['amount'].sum()
                    total_sold = sells['amount'].sum()
                    
                    # Only include positions where we still have tokens (bought > sold)
                    if total_bought > total_sold:
                        # Calculate the remaining position
                        remaining = total_bought - total_sold
                        
                        # Calculate average buy price
                        weighted_prices = (buys['amount'] * buys['price']).sum()
                        avg_buy_price = weighted_prices / total_bought if total_bought > 0 else 0
                        
                        # Get the token name and ticker
                        token_info = self.get_token(contract)
                        ticker = token_info.get('ticker', 'UNKNOWN') if token_info else 'UNKNOWN'
                        name = token_info.get('name', 'UNKNOWN') if token_info else 'UNKNOWN'
                        
                        # Store in positions dictionary
                        positions[contract] = {
                            'contract_address': contract,
                            'ticker': ticker,
                            'name': name,
                            'amount': remaining,
                            'buy_price': avg_buy_price,
                            'entry_time': buys['timestamp'].min()
                        }
                
                # Convert positions to DataFrame
                if positions:
                    positions_df = pd.DataFrame(list(positions.values()))
                    return positions_df
                    
            # Return empty DataFrame if no active positions
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting active orders: {e}")
            return pd.DataFrame()  # Return empty DataFrame on error

    def get_tokens(self, limit=None, min_safety_score=None):
        """
        Get tokens from the database
        
        :param limit: Maximum number of tokens to return (optional)
        :param min_safety_score: Minimum safety score filter (optional)
        :return: DataFrame of tokens
        """
        conn = sqlite3.connect(self.db_path)
        try:
            query = "SELECT * FROM tokens"
            params = []
            
            # Add safety score filter if provided
            if min_safety_score is not None:
                query += " WHERE safety_score >= ?"
                params.append(min_safety_score)
                
            # Add ordering by last updated
            query += " ORDER BY last_updated DESC"
            
            # Add limit if provided
            if limit and isinstance(limit, int) and limit > 0:
                query += " LIMIT ?"
                params.append(limit)
                
            # Execute query
            df = pd.read_sql_query(query, conn, params=params)
            return df
                
        except Exception as e:
            logger.error(f"Error fetching tokens: {e}")
            return pd.DataFrame()  # Return empty DataFrame on error
            
        finally:
            conn.close()

    def get_trading_history(self, limit=None):
        """
        Get trading history as a DataFrame
        
        :param limit: Maximum number of trades to return (optional)
        :return: Pandas DataFrame of trade history
        """
        conn = sqlite3.connect(self.db_path)
        try:
            query = "SELECT * FROM trades ORDER BY timestamp DESC"
            
            if limit and isinstance(limit, int) and limit > 0:
                query += f" LIMIT {limit}"
                
            # Execute query
            df = pd.read_sql_query(query, conn)
            return df
                
        except Exception as e:
            logger.error(f"Error fetching trading history: {e}")
            return pd.DataFrame()  # Return empty DataFrame on error
            
        finally:
            conn.close()

    def reset_database(self):
        """
        Reset the database by dropping and recreating all tables
        
        :return: True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            # Drop all tables
            cursor.execute("DROP TABLE IF EXISTS tokens")
            cursor.execute("DROP TABLE IF EXISTS trades")
            cursor.execute("DROP TABLE IF EXISTS social_mentions")
            conn.commit()
            
            # Reinitialize the database
            self._initialize_db()
            
            logger.info("Database reset successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            return False
            
        finally:
            conn.close()