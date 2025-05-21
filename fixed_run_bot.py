"""
Fixed bot integration script - uses the updated database adapter to fix is_simulation parameter issue
"""
import os
import sys
import logging
import time
import asyncio
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('bot_integration')

# Add core directory to path if needed
core_dir = 'core'
if os.path.exists(core_dir) and core_dir not in sys.path:
    sys.path.insert(0, core_dir)

# Import necessary components
try:
    # Try to import from core directory first
    try:
        from core.simplified_solana_trader import SolanaTrader
        from core.simplified_token_scanner import TokenScanner
        from core.simplified_trading_bot import TradingBot
        from core.database import Database
        # Import the fixed database adapter
        from core.database_adapter_fix import DatabaseAdapter
    except ImportError:
        # Try to import from current directory
        from simplified_solana_trader import SolanaTrader
        from simplified_token_scanner import TokenScanner
        from simplified_trading_bot import TradingBot
        from database import Database
        from database_adapter_fix import DatabaseAdapter
except ImportError as e:
    logger.error(f"Error importing required modules: {e}")
    logger.error("Please make sure they are available in the core directory")
    sys.exit(1)

def load_bot_control():
    """Load bot control settings from bot_control.json"""
    try:
        control_file = 'bot_control.json'
        if not os.path.exists(control_file):
            control_file = os.path.join('data', 'bot_control.json')
            
        if os.path.exists(control_file):
            import json
            with open(control_file, 'r') as f:
                return json.load(f)
        else:
            logger.warning(f"Bot control file not found: {control_file}")
            return {
                "running": True,
                "simulation_mode": True,
                "filter_fake_tokens": True,
                "use_birdeye_api": True,
                "use_machine_learning": False,
                "take_profit_target": 15.0,
                "stop_loss_percentage": 0.25,
                "max_investment_per_token": 0.1,
                "min_investment_per_token": 0.02,
                "slippage_tolerance": 0.3,
                "MIN_SAFETY_SCORE": 15.0,
                "MIN_VOLUME": 10.0,
                "MIN_LIQUIDITY": 5000.0,
                "MIN_MCAP": 10000.0,
                "MIN_HOLDERS": 10,
                "MIN_PRICE_CHANGE_1H": 1.0,
                "MIN_PRICE_CHANGE_6H": 2.0,
                "MIN_PRICE_CHANGE_24H": 5.0
            }
    except Exception as e:
        logger.error(f"Error loading bot control: {e}")
        return {
            "running": True,
            "simulation_mode": True
        }

async def run_bot():
    """Initialize and run the bot with simplified components and fixed database adapter"""
    logger.info("Starting bot with simplified components and fixed database adapter")
    
    # Load control settings
    control = load_bot_control()
    logger.info(f"Bot control settings: running={control.get('running', True)}, simulation_mode={control.get('simulation_mode', True)}")
    
    # Create and initialize database
    db_path = os.path.join('data', 'sol_bot.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = Database(db_path=db_path)
    
    # Create database adapter with the fixed implementation
    db_adapter = DatabaseAdapter(db)
    logger.info("Database initialized with fixed adapter")
    
    # Create and initialize trader
    trader = SolanaTrader(
        db=db_adapter,  # Use the adapter instead of direct DB
        simulation_mode=control.get('simulation_mode', True)
    )
    logger.info(f"SolanaTrader initialized (simulation_mode={control.get('simulation_mode', True)})")
    
    # Connect to the Solana network (simulated)
    await trader.connect()
    
    # Get wallet balance
    balance_sol, balance_usd = await trader.get_wallet_balance()
    logger.info(f"Wallet balance: {balance_sol:.4f} SOL (${balance_usd:.2f})")
    
    # Create and initialize token scanner
    token_scanner = TokenScanner(db=db_adapter)  # Use the adapter instead of direct DB
    logger.info("TokenScanner initialized")
    
    # Create trading parameters from control settings
    trading_params = {
        "take_profit_target": control.get('take_profit_target', 15.0),
        "stop_loss_percentage": control.get('stop_loss_percentage', 0.25),
        "max_investment_per_token": control.get('max_investment_per_token', 0.1),
        "min_investment_per_token": control.get('min_investment_per_token', 0.02),
        "slippage_tolerance": control.get('slippage_tolerance', 0.3),
        "MIN_SAFETY_SCORE": control.get('MIN_SAFETY_SCORE', 15.0),
        "MIN_VOLUME": control.get('MIN_VOLUME', 10.0),
        "MIN_LIQUIDITY": control.get('MIN_LIQUIDITY', 5000.0),
        "MIN_MCAP": control.get('MIN_MCAP', 10000.0),
        "MIN_HOLDERS": control.get('MIN_HOLDERS', 10),
        "MIN_PRICE_CHANGE_1H": control.get('MIN_PRICE_CHANGE_1H', 1.0),
        "MIN_PRICE_CHANGE_6H": control.get('MIN_PRICE_CHANGE_6H', 2.0),
        "MIN_PRICE_CHANGE_24H": control.get('MIN_PRICE_CHANGE_24H', 5.0)
    }
    
    # Create and initialize trading bot
    trading_bot = TradingBot(
        trader=trader,
        token_scanner=token_scanner,
        simulation_mode=control.get('simulation_mode', True),
        params=trading_params
    )
    logger.info("TradingBot initialized")
    
    # Start the bot if running is enabled
    if control.get('running', True):
        logger.info("Starting TradingBot")
        await trading_bot.start()
        
        # Keep the main thread running
        try:
            logger.info("Bot running. Press Ctrl+C to stop.")
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            await trading_bot.stop()
    else:
        logger.info("Bot not started because running=False in settings")
    
    # Close connections
    await trader.close()
    logger.info("Bot shutdown complete")

def main():
    """Main function to run the bot"""
    # Create event loop and run the bot
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
