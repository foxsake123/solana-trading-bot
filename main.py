"""
Solana Trading Bot - Main Entry Point
"""
import os
import sys
import logging
import time
from datetime import datetime
import traceback

# Configure logging with timestamps
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, f"bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('solana_bot')

# Add the project root and core directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

core_dir = os.path.join(project_root, 'core')
if core_dir not in sys.path:
    sys.path.insert(0, core_dir)

# Banner
logger.info("=" * 60)
logger.info("          SOLANA TRADING BOT - STARTING          ")
logger.info("=" * 60)

# Load control settings first
try:
    import json
    control_file = os.path.join(project_root, 'bot_control.json')
    if not os.path.exists(control_file):
        control_file = os.path.join(project_root, 'data', 'bot_control.json')
    
    if os.path.exists(control_file):
        with open(control_file, 'r') as f:
            control_data = json.load(f)
        
        BOT_RUNNING = control_data.get('running', False)
        SIMULATION_MODE = control_data.get('simulation_mode', True)
        logger.info(f"Bot control settings: running={BOT_RUNNING}, simulation_mode={SIMULATION_MODE}")
    else:
        logger.warning("Control file not found, using default settings")
        BOT_RUNNING = False
        SIMULATION_MODE = True
except Exception as e:
    logger.error(f"Error loading control settings: {e}")
    logger.error(traceback.format_exc())
    BOT_RUNNING = False
    SIMULATION_MODE = True

try:
    # Try to import the SoldersAdapter class
    try:
        from core.SoldersAdapter import SoldersAdapter
        logger.info("Successfully imported SoldersAdapter from core.SoldersAdapter")
    except ImportError:
        try:
            from SoldersAdapter import SoldersAdapter
            logger.info("Successfully imported SoldersAdapter from SoldersAdapter")
        except ImportError as e:
            logger.error(f"Failed to import SoldersAdapter: {e}")
            logger.error("Please create the SoldersAdapter.py file in the core directory")
            sys.exit(1)

    # Try to import database
    try:
        from core.database import Database
        logger.info("Imported Database from core.database")
    except ImportError:
        try:
            from database import Database
            logger.info("Imported Database from database")
        except ImportError as e:
            logger.error(f"Failed to import Database: {e}")
            logger.error("Please make sure database.py exists")
            sys.exit(1)

    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        logger.warning("python-dotenv not installed, environment variables may not be loaded")

    # Initialize wallet
    wallet_adapter = SoldersAdapter()
    WALLET_PRIVATE_KEY = os.getenv('WALLET_PRIVATE_KEY', '')
    MAINNET_RPC_URL = os.getenv('SOLANA_RPC_ENDPOINT', 'https://api.mainnet-beta.solana.com')

    # Initialize wallet
    wallet_initialized = wallet_adapter.init_wallet(WALLET_PRIVATE_KEY)
    
    if wallet_initialized:
        wallet_address = wallet_adapter.get_wallet_address()
        logger.info(f"Wallet initialized: {wallet_address}")
        
        # Get wallet balance
        balance_sol = wallet_adapter.get_wallet_balance()
        sol_price = wallet_adapter.get_sol_price()
        balance_usd = balance_sol * sol_price
        logger.info(f"Wallet balance: {balance_sol:.4f} SOL (${balance_usd:.2f})")
    else:
        logger.warning("Wallet not initialized. Only simulation mode will be available.")
        SIMULATION_MODE = True

    # Initialize database
    try:
        db = Database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        sys.exit(1)

    # Import SolanaTrader
    try:
        try:
            from core.AsyncSolanaTrader_adapter import SolanaTrader
            logger.info("Imported SolanaTrader from AsyncSolanaTrader_adapter")
        except ImportError:
            try:
                from AsyncSolanaTrader_adapter import SolanaTrader
                logger.info("Imported SolanaTrader from AsyncSolanaTrader_adapter")
            except ImportError:
                try:
                    from core.solana_trader import SolanaTrader
                    logger.info("Imported SolanaTrader from solana_trader")
                except ImportError:
                    from solana_trader import SolanaTrader
                    logger.info("Imported SolanaTrader directly")
    except ImportError as e:
        logger.error(f"Failed to import SolanaTrader: {e}")
        sys.exit(1)

    # Main function
    def main():
        logger.info("Starting bot main function")
        
        # Log settings
        logger.info(f"Bot running setting: {BOT_RUNNING}")
        logger.info(f"Simulation mode: {SIMULATION_MODE}")
        
        # Initialize SolanaTrader
        try:
            solana_trader = SolanaTrader(
                private_key=WALLET_PRIVATE_KEY,
                rpc_url=MAINNET_RPC_URL,
                simulation_mode=SIMULATION_MODE,
                db=db
            )
            logger.info("SolanaTrader initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing SolanaTrader: {e}")
            return
        
        # Check if bot is running
        if not BOT_RUNNING:
            logger.info("Bot is not running. Set 'running': true in bot_control.json to start trading.")
            return
        
        # In a real implementation, this would start the trading bot
        logger.info("Bot would start trading here. This is a placeholder implementation.")
        
        # Keep the process running
        try:
            logger.info("Bot running in monitoring mode. Press Ctrl+C to stop.")
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")

    if __name__ == "__main__":
        main()

except Exception as e:
    logger.error(f"Unexpected error: {e}")
    logger.error(traceback.format_exc())