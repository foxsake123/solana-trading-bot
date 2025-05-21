"""
Updated SolanaTrader_adapter for the actual SolanaTrader parameters
"""
import os
import sys
import logging
import sqlite3

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

# Create an adapter that matches the actual SolanaTrader parameters
class SolanaTrader:
    """
    Adapter class for SolanaTrader that handles the actual required parameters
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
        self.rpc_url = rpc_url
        
        # Create a database instance
        if database_available:
            db = Database()
        else:
            db = Database()  # Mock database
        
        # Set simulation mode (prioritize the one from kwargs if provided)
        simulation_mode = kwargs.get('simulation_mode', False)
        
        try:
            # Initialize the original SolanaTrader with the correct parameters
            logger.info(f"Initializing SolanaTrader with db and simulation_mode={simulation_mode}")
            self.trader = OriginalSolanaTrader(db=db, simulation_mode=simulation_mode)
            
            # Add the parameters as attributes of this adapter for reference
            self.db = db
            self.simulation_mode = simulation_mode
            
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
            return getattr(self.trader, name)
        raise AttributeError(f"'SolanaTrader' object has no attribute '{name}'")