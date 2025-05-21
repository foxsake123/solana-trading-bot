#!/usr/bin/env python3
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
    # Import the SoldersAdapter class
    try:
        from core.SoldersAdapter import SoldersAdapter
        logger.info("Successfully imported SoldersAdapter from SoldersAdapter.py")
    except ImportError as e:
        logger.error(f"Failed to import SoldersAdapter: {e}")
        logger.error("Please create the SoldersAdapter.py file in the core directory")
        sys.exit(1)

    # Import database adapter
    try:
        from core.database import Database
        logger.info("Imported Database from core.database")
    except ImportError as e:
        logger.error(f"Failed to import Database: {e}")
        sys.exit(1)

    # Import wallet handling
    wallet_adapter = SoldersAdapter()

    # Import environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Get wallet private key from environment
    WALLET_PRIVATE_KEY = os.getenv('WALLET_PRIVATE_KEY', '')
    MAINNET_RPC_URL = os.getenv('SOLANA_RPC_ENDPOINT', 'https://api.mainnet-beta.solana.com')

    # Check if wallet can be initialized
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

    # Setup database
    try:
        db = Database()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        logger.error("Cannot proceed without database")
        sys.exit(1)

    # Import SolanaTrader
    try:
        try:
            from core.AsyncSolanaTrader_adapter import SolanaTrader
            logger.info("Imported SolanaTrader from AsyncSolanaTrader_adapter")
        except ImportError:
            try:
                from core.SolanaTrader_adapter import SolanaTrader
                logger.info("Imported SolanaTrader from SolanaTrader_adapter")
            except ImportError:
                from core.solana_trader import SolanaTrader
                logger.info("Imported SolanaTrader directly")
    except ImportError as e:
        logger.error(f"Failed to import SolanaTrader: {e}")
        logger.error("Please make sure solana_trader.py or an adapter is available")
        sys.exit(1)

    # Import token scanner
    try:
        from core.token_scanner import TokenScanner
        token_scanner = TokenScanner()
        logger.info("Using TokenScanner")
    except ImportError:
        try:
            from core.birdeye_api import BirdeyeAPI
            token_scanner = BirdeyeAPI()
            logger.info("Using BirdeyeAPI as token scanner")
        except ImportError:
            try:
                from core.birdeye import BirdeyeAPI
                token_scanner = BirdeyeAPI()
                logger.info("Using birdeye.BirdeyeAPI as token scanner")
            except ImportError:
                logger.error("No token scanner available. Please install token_scanner or birdeye_api.")
                sys.exit(1)

    # Import TradingBot
    try:
        try:
            from core.TradingBot_adapter import TradingBot
            logger.info("Imported TradingBot from adapter")
        except ImportError:
            try:
                from core.trading_bot import TradingBot
                logger.info("Imported TradingBot from trading_bot")
            except ImportError:
                try:
                    from core.simple_trading_bot import TradingBot
                    logger.info("Imported TradingBot from simple_trading_bot")
                except ImportError:
                    logger.error("Failed to import TradingBot from any source")
                    sys.exit(1)
    except ImportError as e:
        logger.error(f"Failed to import TradingBot: {e}")
        sys.exit(1)

    def main():
        """Main entry point for the bot"""
        # Initialize the solana trader
        try:
            solana_trader = SolanaTrader(
                private_key=WALLET_PRIVATE_KEY,
                rpc_url=MAINNET_RPC_URL,
                simulation_mode=SIMULATION_MODE,
                db=db
            )
            logger.info("Created SolanaTrader successfully")
        except Exception as e:
            logger.error(f"Error creating SolanaTrader: {e}")
            logger.error("Cannot proceed without SolanaTrader")
            return
        
        # Initialize the trading bot
        try:
            bot = TradingBot(
                trader=solana_trader,
                token_scanner=token_scanner,
                simulation_mode=SIMULATION_MODE
            )
            logger.info("Created TradingBot successfully")
        except Exception as e:
            logger.error(f"Error creating TradingBot: {e}")
            logger.error("Cannot proceed without TradingBot")
            return
        
        # Start the bot if enabled
        if BOT_RUNNING:
            logger.info("Starting bot in active mode")
            
            # Start the bot with error handling
            try:
                bot.start()
                logger.info("Bot started successfully")
            except Exception as e:
                logger.error(f"Error starting bot: {e}")
                logger.error("Bot will not be started")
                return
            
            # Keep the main thread running
            try:
                logger.info("Bot running indefinitely, press CTRL+C to stop")
                # Use a loop instead of a single sleep
                while True:
                    time.sleep(60)  # Check every 60 seconds if we should continue
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                try:
                    bot.stop()
                except Exception as e:
                    logger.error(f"Error stopping bot: {e}")
        else:
            logger.info("Bot not started due to configuration setting")
            logger.info("Set 'running': true in bot_control.json to start the bot")
        
        logger.info("Bot execution completed")

    if __name__ == "__main__":
        main()

except Exception as e:
    logger.error(f"Unexpected error in main script: {e}")
    logger.error(traceback.format_exc())
