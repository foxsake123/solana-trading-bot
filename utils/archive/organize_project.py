"""
Directory cleanup and organization script for the Solana trading bot
"""
import os
import sys
import shutil
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('organize_project')

def ensure_dir_exists(dir_path):
    """Ensure a directory exists, creating it if necessary"""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        logger.info(f"Created directory: {dir_path}")

def copy_file_if_exists(src, dest):
    """Copy a file if it exists"""
    if os.path.exists(src):
        # Create destination directory if needed
        dest_dir = os.path.dirname(dest)
        ensure_dir_exists(dest_dir)
        
        # Copy the file
        shutil.copy2(src, dest)
        logger.info(f"Copied {src} to {dest}")
        return True
    return False

def main():
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Create archive directory for old files
    archive_dir = os.path.join(project_root, 'archive')
    ensure_dir_exists(archive_dir)
    
    # Create necessary directories
    core_dir = os.path.join(project_root, 'core')
    ensure_dir_exists(core_dir)
    
    data_dir = os.path.join(project_root, 'data')
    ensure_dir_exists(data_dir)
    
    dashboard_dir = os.path.join(project_root, 'dashboard')
    ensure_dir_exists(dashboard_dir)
    
    utils_dir = os.path.join(project_root, 'utils')
    ensure_dir_exists(utils_dir)
    
    tests_dir = os.path.join(project_root, 'tests')
    ensure_dir_exists(tests_dir)
    
    # Create a list of core files that should be in the core directory
    core_files = [
        'SoldersAdapter.py',
        'solders_adapter.py',
        'solana_trader.py',
        'SolanaTrader_adapter.py',
        'AsyncSolanaTrader_adapter.py',
        'TradingBot_adapter.py',
        'database.py',
        'token_scanner.py',
        'token_analyzer.py',
        'birdeye.py',
        'utils.py',
        'config.py',
        'trading_bot.py',
        'ml_model.py',
    ]
    
    # Create __init__.py files in each directory
    for dir_path in [core_dir, data_dir, dashboard_dir, utils_dir, tests_dir]:
        init_file = os.path.join(dir_path, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write(f"# {os.path.basename(dir_path)} package\n")
            logger.info(f"Created {init_file}")
    
    # Move core files to core directory
    for file in core_files:
        src = os.path.join(project_root, file)
        dest = os.path.join(core_dir, file)
        if os.path.exists(src):
            shutil.copy2(src, dest)
            logger.info(f"Moved {file} to core directory")
            
            # Move original to archive
            archive_dest = os.path.join(archive_dir, file)
            shutil.copy2(src, archive_dest)
            os.remove(src)
            logger.info(f"Archived original {file}")
    
    # Move dashboard files
    dashboard_files = [
        'new_dashboard.py',
        'advanced_dashboard.py',
        'simple_status.py',
        'status_monitor.py',
    ]
    
    for file in dashboard_files:
        src = os.path.join(project_root, file)
        dest = os.path.join(dashboard_dir, file)
        if os.path.exists(src):
            shutil.copy2(src, dest)
            logger.info(f"Moved {file} to dashboard directory")
            
            # Move original to archive
            archive_dest = os.path.join(archive_dir, file)
            shutil.copy2(src, archive_dest)
            os.remove(src)
            logger.info(f"Archived original {file}")
    
    # Move test files
    test_files = [
        'test_real_trading.py',
        'check_trades.py',
        'check_real_trades.py',
        'wallet_test.py',
        'solana_connection_test.py',
        'test_solana.py',
        'test_solders.py',
    ]
    
    for file in test_files:
        src = os.path.join(project_root, file)
        dest = os.path.join(tests_dir, file)
        if os.path.exists(src):
            shutil.copy2(src, dest)
            logger.info(f"Moved {file} to tests directory")
            
            # Move original to archive
            archive_dest = os.path.join(archive_dir, file)
            shutil.copy2(src, archive_dest)
            os.remove(src)
            logger.info(f"Archived original {file}")
    
    # Move utility scripts
    util_files = [
        'fix_structure.py',
        'fix_jupiter.py',
        'setup_real_trading.py',
        'update_settings.py',
        'cleanup.py',
    ]
    
    for file in util_files:
        src = os.path.join(project_root, file)
        dest = os.path.join(utils_dir, file)
        if os.path.exists(src):
            shutil.copy2(src, dest)
            logger.info(f"Moved {file} to utils directory")
            
            # Move original to archive
            archive_dest = os.path.join(archive_dir, file)
            shutil.copy2(src, archive_dest)
            os.remove(src)
            logger.info(f"Archived original {file}")
    
    # Copy bot_control.json to data directory if it exists
    src = os.path.join(project_root, 'bot_control.json')
    dest = os.path.join(data_dir, 'bot_control.json')
    if os.path.exists(src):
        shutil.copy2(src, dest)
        logger.info(f"Moved bot_control.json to data directory")
    
    # Create a symlink to bot_control.json in the root directory
    if os.path.exists(dest) and not os.path.exists(src):
        try:
            os.symlink(dest, src)
            logger.info("Created symlink to bot_control.json in root directory")
        except Exception as e:
            # On Windows, symlinks might not work without admin privileges
            logger.warning(f"Could not create symlink: {e}")
            # Just copy the file instead
            shutil.copy2(dest, src)
            logger.info("Copied bot_control.json to root directory")
    
    # Create an improved main.py in the root directory that imports from the core directory
    with open(os.path.join(project_root, 'main.py'), 'w') as f:
        f.write("""#!/usr/bin/env python3
\"\"\"
Solana Trading Bot - Main Entry Point
\"\"\"
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
        \"\"\"Main entry point for the bot\"\"\"
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

    if __name__ == \"__main__\":
        main()

except Exception as e:
    logger.error(f"Unexpected error in main script: {e}")
    logger.error(traceback.format_exc())
""")
    logger.info("Created improved main.py in the root directory")
    
    # Create an improved README.md in the root directory
    with open(os.path.join(project_root, 'README.md'), 'w') as f:
        f.write("""# Solana Trading Bot

A trading bot for the Solana blockchain. This bot can automatically identify and trade tokens on Solana-based decentralized exchanges.

## Directory Structure

- `core/` - Core functionality (trading, token scanning, etc.)
- `data/` - Data storage (database, control settings)
- `dashboard/` - Monitoring dashboards
- `tests/` - Test scripts
- `utils/` - Utility scripts
- `logs/` - Log files

## Setup

1. Install the dependencies
2. Configure your environment variables
3. Run the bot

### Prerequisites

- Python 3.9+
- pip
- Git

### Installation

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\\Scripts\\activate
# On macOS/Linux:
source venv/bin/activate

# Install the dependencies
pip install -r requirements.txt
```

### Configuration

1. Create a `.env` file in the root directory with the following variables:

```
WALLET_PRIVATE_KEY=your_private_key_here
SOLANA_RPC_ENDPOINT=https://api.mainnet-beta.solana.com
BIRDEYE_API_KEY=your_birdeye_api_key_here (optional)
TWITTER_API_KEY=your_twitter_api_key_here (optional)
TWITTER_API_SECRET=your_twitter_api_secret_here (optional)
TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here (optional)
```

2. Edit the `bot_control.json` file to configure the bot's behavior:

```json
{
    "running": false,
    "simulation_mode": true,
    "filter_fake_tokens": true,
    "use_birdeye_api": true,
    "use_machine_learning": false,
    "take_profit_target": 15.0,
    "stop_loss_percentage": 0.25,
    "max_investment_per_token": 0.1,
    "min_investment_per_token": 0.02,
    "slippage_tolerance": 0.3,
    "MIN_SAFETY_SCORE": 0.0,
    "MIN_VOLUME": 0.0,
    "MIN_LIQUIDITY": 0.0,
    "MIN_MCAP": 0.0,
    "MIN_HOLDERS": 0,
    "MIN_PRICE_CHANGE_1H": 0.0,
    "MIN_PRICE_CHANGE_6H": 0.0,
    "MIN_PRICE_CHANGE_24H": 0.0
}
```

### Testing

Before running the bot in real mode, you should test it thoroughly:

```bash
# Test real trading functionality
python tests/test_real_trading.py

# Check current trades and positions
python tests/check_trades.py

# Setup real trading mode
python utils/setup_real_trading.py

# Monitor the bot with a dashboard
python dashboard/new_dashboard.py
```

### Running the Bot

To start the bot:

1. Set `"running": true` in `bot_control.json`
2. For real trading, set `"simulation_mode": false` in `bot_control.json`
3. Run the main script:

```bash
python main.py
```

## Disclaimer

This is experimental software. Use at your own risk. Never invest more than you can afford to lose.

When running in real trading mode, the bot will use real SOL tokens from your wallet. Always start with small amounts when testing.
""")
    logger.info("Created improved README.md in the root directory")
    
    # Move all other Python scripts to the archive directory
    for file in os.listdir(project_root):
        if file.endswith('.py') and file not in ['main.py', 'setup.py']:
            # Skip files we already moved
            skip = False
            for dir_path in [core_dir, dashboard_dir, tests_dir, utils_dir]:
                if os.path.exists(os.path.join(dir_path, file)):
                    skip = True
                    break
            
            if not skip:
                src = os.path.join(project_root, file)
                dest = os.path.join(archive_dir, file)
                if os.path.exists(src) and os.path.isfile(src):
                    shutil.copy2(src, dest)
                    os.remove(src)
                    logger.info(f"Archived {file}")
    
    logger.info("Project reorganization complete!")

if __name__ == "__main__":
    main()
