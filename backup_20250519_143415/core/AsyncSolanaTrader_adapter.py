"""
Improved AsyncSolanaTrader_adapter with better wallet balance handling
"""
import os
import sys
import logging
import sqlite3
import asyncio
import time

# Configure logging
logger = logging.getLogger(__name__)

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import the actual SolanaTrader with flexible error handling
try:
    try:
        from solana_trader import SolanaTrader as OriginalSolanaTrader
    except ImportError:
        from core.solana_trader import SolanaTrader as OriginalSolanaTrader
    logger.info("Successfully imported original SolanaTrader")
except ImportError as e:
    logger.error(f"Failed to import original SolanaTrader: {e}")
    # Create a placeholder for SolanaTrader if the import fails
    class OriginalSolanaTrader:
        def __init__(self, **kwargs):
            logger.error("Using placeholder SolanaTrader")

# Try to import the database module to pass to SolanaTrader
try:
    from database import Database
    database_available = True
except ImportError:
    logger.warning("Database module not available, using mock database")
    database_available = False
    
    # Create a simple mock Database class if the real one isn't available
    class Database:
        def __init__(self, db_path='data/sol_bot.db'):
            self.db_path = db_path
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
        def _initialize_db(self):
            # Create a minimal database structure
            conn = sqlite3.connect(self.db_path)
            conn.close()
            return True

# Import solders for direct wallet access if available
try:
    from solders.keypair import Keypair
    from solana.rpc.async_api import AsyncClient
    has_solders = True
    logger.info("Successfully imported solders for direct wallet access")
except ImportError:
    has_solders = False
    logger.warning("Could not import solders for direct wallet access")

# Create an adapter that handles async methods
class SolanaTrader:
    """
    Adapter class for SolanaTrader that handles async methods
    """
    
    def __init__(self, private_key=None, rpc_url=None, **kwargs):
        """
        Initialize a SolanaTrader with the parameters it actually expects
        
        Args:
            private_key: Not used directly, but saved for reference
            rpc_url: Not used directly, but saved for reference
            **kwargs: Any additional parameters
        """
        # Save the parameters for reference
        self.private_key = private_key
        self.rpc_url = rpc_url or "https://api.mainnet-beta.solana.com"
        
        # Create a database instance
        if database_available:
            self.db = Database()
        else:
            self.db = Database()  # Mock database
        
        # Set simulation mode (prioritize the one from kwargs if provided)
        self.simulation_mode = kwargs.get('simulation_mode', False)
        
        # Initialize direct wallet access if possible
        self.direct_keypair = None
        self.direct_client = None
        if has_solders and private_key:
            try:
                # Create keypair for direct access
                key_bytes = bytes.fromhex(private_key)
                self.direct_keypair = Keypair.from_seed(key_bytes[:32])
                logger.info(f"Created direct keypair for wallet: {self.direct_keypair.pubkey()}")
                
                # Create client for direct access
                self.direct_client = AsyncClient(self.rpc_url)
                logger.info(f"Created direct client for RPC: {self.rpc_url}")
            except Exception as e:
                logger.error(f"Error setting up direct wallet access: {e}")
        
        try:
            # Initialize the original SolanaTrader with the correct parameters
            logger.info(f"Initializing SolanaTrader with db and simulation_mode={self.simulation_mode}")
            self.trader = OriginalSolanaTrader(db=self.db, simulation_mode=self.simulation_mode)
            
            # Set data directory attribute needed by TradingBot
            self.DATA_DIR = 'data'
            if not os.path.exists(self.DATA_DIR):
                os.makedirs(self.DATA_DIR, exist_ok=True)
            
            # Import necessary configurations
            self._configure_trader()
            
            logger.info("Successfully initialized SolanaTrader")
        except Exception as e:
            logger.error(f"Error initializing SolanaTrader: {e}")
            raise
    
    def _configure_trader(self):
        """Configure the trader with private key and RPC URL"""
        # Set private key if available
        if hasattr(self.trader, 'set_private_key') and self.private_key:
            try:
                self.trader.set_private_key(self.private_key)
                logger.info("Set private key in trader")
            except Exception as e:
                logger.error(f"Error setting private key: {e}")
        
        # Set RPC URL if available
        if hasattr(self.trader, 'set_rpc_url') and self.rpc_url:
            try:
                self.trader.set_rpc_url(self.rpc_url)
                logger.info("Set RPC URL in trader")
            except Exception as e:
                logger.error(f"Error setting RPC URL: {e}")
    
    # Method for getting wallet address that works with sync code
    def get_wallet_address(self):
        """Get wallet address (sync wrapper for async method)"""
        try:
            # First try direct keypair if available
            if self.direct_keypair:
                return str(self.direct_keypair.pubkey())
            
            # Next try trader.wallet_address if it exists
            if hasattr(self.trader, 'wallet_address'):
                return self.trader.wallet_address
                
            # Try get_wallet_address method
            elif hasattr(self.trader, 'get_wallet_address'):
                # If it's an async method, run it in a new event loop
                if asyncio.iscoroutinefunction(self.trader.get_wallet_address):
                    address = asyncio.run(self.trader.get_wallet_address())
                    logger.info(f"Retrieved wallet address via async method: {address}")
                    return address
                else:
                    address = self.trader.get_wallet_address()
                    logger.info(f"Retrieved wallet address via sync method: {address}")
                    return address
            else:
                logger.warning("No way to get wallet address")
                return "Unknown wallet address"
        except Exception as e:
            logger.error(f"Error getting wallet address: {e}")
            return "Error getting wallet address"
    
    # Method for getting wallet balance that works with sync code
    def get_wallet_balance(self):
        """Get wallet balance (sync wrapper for async method)"""
        try:
            # Try direct balance retrieval if keypair and client are available
            if self.direct_keypair and self.direct_client:
                try:
                    logger.info("Attempting direct balance retrieval...")
                    
                    # Use a separate event loop for the direct balance check
                    async def get_direct_balance():
                        balance_response = await self.direct_client.get_balance(self.direct_keypair.pubkey())
                        if balance_response and hasattr(balance_response, 'value') and balance_response.value is not None:
                            sol_balance = balance_response.value / 1_000_000_000  # Convert lamports to SOL
                            logger.info(f"Direct balance retrieval successful: {sol_balance} SOL")
                            return sol_balance
                        else:
                            logger.warning("Direct balance response invalid")
                            return 0.0
                    
                    # Run the async function in a new event loop
                    sol_balance = asyncio.run(get_direct_balance())
                    
                    # Get SOL price for USD value
                    sol_price = self.get_sol_price()
                    usd_balance = sol_balance * sol_price
                    
                    return {'sol': sol_balance, 'usd': usd_balance}
                except Exception as e:
                    logger.warning(f"Direct balance retrieval failed: {e}")
                    # Continue to other methods if direct retrieval fails
            
            # Try through the trader object
            if hasattr(self.trader, 'get_wallet_balance'):
                try:
                    # If it's an async method, run it in a new event loop
                    if asyncio.iscoroutinefunction(self.trader.get_wallet_balance):
                        logger.info("Attempting balance retrieval via async method...")
                        balance_coroutine = self.trader.get_wallet_balance()
                        
                        # Run the coroutine in a new event loop
                        balance = asyncio.run(balance_coroutine)
                        logger.info(f"Async balance result: {balance}")
                    else:
                        logger.info("Attempting balance retrieval via sync method...")
                        balance = self.trader.get_wallet_balance()
                        logger.info(f"Sync balance result: {balance}")
                    
                    # Process the balance result
                    if isinstance(balance, dict) and 'sol' in balance and 'usd' in balance:
                        logger.info(f"Using dict balance: {balance}")
                        return balance
                    elif isinstance(balance, (int, float)):
                        logger.info(f"Converting numeric balance: {balance}")
                        sol_price = self.get_sol_price()
                        return {'sol': float(balance), 'usd': float(balance) * sol_price}
                    elif isinstance(balance, tuple) and len(balance) == 2:
                        logger.info(f"Converting tuple balance: {balance}")
                        return {'sol': float(balance[0]), 'usd': float(balance[1])}
                    else:
                        logger.warning(f"Unrecognized balance format: {balance} ({type(balance)})")
                        return {'sol': 0.0, 'usd': 0.0}
                except Exception as e:
                    logger.error(f"Error in trader balance retrieval: {e}")
            
            # Fallback: return default values
            logger.warning("Using fallback balance values")
            return {'sol': 0.0, 'usd': 0.0}
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            return {'sol': 0.0, 'usd': 0.0}
    
    # Method to get SOL price
    def get_sol_price(self):
        """Get current SOL price in USD"""
        try:
            # Try SoldersAdapter method if available
            try:
                from SoldersAdapter import SoldersAdapter
                adapter = SoldersAdapter()
                price = adapter.get_sol_price()
                logger.info(f"Got SOL price from SoldersAdapter: ${price}")
                return price
            except (ImportError, Exception) as e:
                logger.warning(f"Could not get SOL price from SoldersAdapter: {e}")
            
            # Try using trader method
            if hasattr(self.trader, 'get_sol_price'):
                try:
                    if asyncio.iscoroutinefunction(self.trader.get_sol_price):
                        price = asyncio.run(self.trader.get_sol_price())
                    else:
                        price = self.trader.get_sol_price()
                    
                    logger.info(f"Got SOL price from trader: ${price}")
                    return price
                except Exception as e:
                    logger.warning(f"Error getting SOL price from trader: {e}")
            
            # Fallback: direct CoinGecko API call
            try:
                import requests
                response = requests.get(
                    "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd",
                    timeout=10
                )
                data = response.json()
                price = float(data['solana']['usd'])
                logger.info(f"Got SOL price from CoinGecko directly: ${price}")
                return price
            except Exception as e:
                logger.warning(f"Error getting SOL price from CoinGecko: {e}")
                
            # Final fallback: hardcoded estimate
            logger.warning("Using fallback SOL price: $185.00")
            return 185.0
        except Exception as e:
            logger.error(f"Error getting SOL price: {e}")
            return 185.0
    
    # Method to buy tokens (with sync/async handling)
    def buy_token(self, token_address, amount_sol):
        """Buy a token (sync wrapper for async method)"""
        try:
            if hasattr(self.trader, 'buy_token'):
                # If it's an async method, run it in a new event loop
                if asyncio.iscoroutinefunction(self.trader.buy_token):
                    return asyncio.run(self.trader.buy_token(token_address, amount_sol))
                else:
                    return self.trader.buy_token(token_address, amount_sol)
            else:
                logger.warning("No way to buy tokens")
                return False
        except Exception as e:
            logger.error(f"Error buying token: {e}")
            return False
    
    # Method to sell tokens (with sync/async handling)
    def sell_token(self, token_address, amount=None):
        """Sell a token (sync wrapper for async method)"""
        try:
            if hasattr(self.trader, 'sell_token'):
                # If it's an async method, run it in a new event loop
                if asyncio.iscoroutinefunction(self.trader.sell_token):
                    if amount is None:
                        return asyncio.run(self.trader.sell_token(token_address))
                    else:
                        return asyncio.run(self.trader.sell_token(token_address, amount))
                else:
                    if amount is None:
                        return self.trader.sell_token(token_address)
                    else:
                        return self.trader.sell_token(token_address, amount)
            else:
                logger.warning("No way to sell tokens")
                return False
        except Exception as e:
            logger.error(f"Error selling token: {e}")
            return False
    
    # Wrapper for checking if the trader is paused
    def is_paused(self):
        """Check if trading is paused"""
        try:
            if hasattr(self.trader, 'is_paused'):
                return self.trader.is_paused()
            else:
                return False
        except Exception as e:
            logger.error(f"Error checking if paused: {e}")
            return False
    
    # Wrapper for starting position monitoring
    def start_position_monitoring(self):
        """Start monitoring positions"""
        try:
            if hasattr(self.trader, 'start_position_monitoring'):
                # If it's an async method, run it in a new event loop
                if asyncio.iscoroutinefunction(self.trader.start_position_monitoring):
                    asyncio.run(self.trader.start_position_monitoring())
                else:
                    self.trader.start_position_monitoring()
                return True
            else:
                logger.warning("No way to start position monitoring")
                return False
        except Exception as e:
            logger.error(f"Error starting position monitoring: {e}")
            return False
    
    def __getattr__(self, name):
        """
        Forward attribute access to the original trader
        
        Args:
            name: Attribute name
            
        Returns:
            The attribute from the original trader
        """
        # Forward attribute access to the original trader
        if hasattr(self, 'trader') and hasattr(self.trader, name):
            attr = getattr(self.trader, name)
            
            # If the attribute is an async method, wrap it to handle async/sync conversion
            if callable(attr) and asyncio.iscoroutinefunction(attr):
                def wrapper(*args, **kwargs):
                    # Run the async method in a new event loop
                    try:
                        return asyncio.run(attr(*args, **kwargs))
                    except Exception as e:
                        logger.error(f"Error in async wrapper for {name}: {e}")
                        return None
                return wrapper
            else:
                return attr
                
        raise AttributeError(f"'SolanaTrader' object has no attribute '{name}'")
    
    def __del__(self):
        """Clean up resources when the object is deleted"""
        if hasattr(self, 'direct_client') and self.direct_client:
            try:
                # Close the client if it's open
                asyncio.run(self.direct_client.close())
                logger.info("Closed direct client")
            except Exception as e:
                logger.error(f"Error closing direct client: {e}")