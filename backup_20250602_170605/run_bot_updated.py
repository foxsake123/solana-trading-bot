"""
Bot integration script with simplified components for real trading
"""
import os
import sys
import logging
import time
import asyncio
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('bot_integration')

# Import necessary components
try:
    from core.simplified_solana_trader import SolanaTrader
    from core.simplified_token_scanner import TokenScanner
    from core.simplified_trading_bot import TradingBot
    from core.database import Database
    from core.database_adapter import DatabaseAdapter
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
            with open(control_file, 'r') as f:
                return json.load(f)
        else:
            logger.warning(f"Bot control file not found: {control_file}")
            return {
                "running": True,
                "simulation_mode": True,  # Default to simulation for safety
                "filter_fake_tokens": True,
                "use_birdeye_api": True,
                "use_machine_learning": False,
                "take_profit_target": 1.15,  # 15% profit
                "stop_loss_percentage": 0.05,  # 5% stop loss
                "max_investment_per_token": 0.05,
                "min_investment_per_token": 0.01,
                "slippage_tolerance": 0.10,
                "MIN_SAFETY_SCORE": 15.0,
                "MIN_VOLUME": 10000.0,
                "MIN_LIQUIDITY": 50000.0,
                "MIN_MCAP": 100000.0,
                "MIN_HOLDERS": 100,
                "MIN_PRICE_CHANGE_1H": 2.0,
                "MIN_PRICE_CHANGE_6H": 5.0,
                "MIN_PRICE_CHANGE_24H": 10.0,
                "starting_simulation_balance": 10.0
            }
    except Exception as e:
        logger.error(f"Error loading bot control: {e}")
        return {
            "running": True,
            "simulation_mode": True
        }

async def run_bot():
    """Initialize and run the bot with simplified components"""
    logger.info("Starting bot with simplified components")
    
    # Load control settings
    control = load_bot_control()
    
    # Get simulation mode from control
    simulation_mode = control.get('simulation_mode', True)
    
    logger.info(f"Bot control settings: running={control.get('running', True)}, simulation_mode={simulation_mode}")
    
    # Create and initialize database
    db = Database(db_path='data/sol_bot.db')
    
    # Create database adapter
    db_adapter = DatabaseAdapter(db)
    logger.info("Database initialized with adapter")
    
    # Create and initialize trader with simulation mode
    trader = SolanaTrader(
        db=db_adapter,
        simulation_mode=simulation_mode
    )
    logger.info(f"SolanaTrader initialized (simulation_mode={simulation_mode})")
    
    # Connect to the Solana network
    await trader.connect()
    
    # Get wallet balance
    balance_sol, balance_usd = await trader.get_wallet_balance()
    logger.info(f"Wallet balance: {balance_sol:.4f} SOL (${balance_usd:.2f})")
    
    # Create and initialize token scanner
    token_scanner = TokenScanner(db=db_adapter)
    logger.info("TokenScanner initialized")
    
    # Create and initialize trading bot
    # Check which parameters TradingBot actually accepts
    try:
        # Try the standard initialization first
        trading_bot = TradingBot(
            config=control,
            db=db_adapter,
            token_scanner=token_scanner,
            trader=trader
        )
        logger.info("TradingBot initialized with config")
    except TypeError:
        try:
            # Try alternative initialization
            trading_bot = TradingBot(
                trader=trader,
                token_scanner=token_scanner,
                params=control
            )
            logger.info("TradingBot initialized with trader/scanner/params")
        except TypeError:
            try:
                # Try another alternative
                trading_bot = TradingBot(
                    trader=trader,
                    token_scanner=token_scanner
                )
                # Set simulation mode after initialization if possible
                if hasattr(trading_bot, 'simulation_mode'):
                    trading_bot.simulation_mode = simulation_mode
                logger.info("TradingBot initialized with trader/scanner")
            except Exception as e:
                logger.error(f"Failed to initialize TradingBot: {e}")
                logger.error("Please check TradingBot constructor signature")
                return
    
    # Set simulation mode on trading bot if not already set
    if hasattr(trading_bot, 'simulation_mode'):
        trading_bot.simulation_mode = simulation_mode
        logger.info(f"Set trading bot simulation_mode to {simulation_mode}")
    
    # Start the bot if running is enabled
    if control.get('running', True):
        logger.info("Starting TradingBot")
        await trading_bot.start()
        
        # Keep the main thread running
        try:
            mode_str = "SIMULATION" if simulation_mode else "REAL TRADING"
            logger.info(f"Bot running in {mode_str} MODE. Press Ctrl+C to stop.")
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            if hasattr(trading_bot, 'stop'):
                await trading_bot.stop()
    else:
        logger.info("Bot not started because running=False in settings")
    
    # Close connections
    if hasattr(trader, 'close'):
        await trader.close()
    logger.info("Bot shutdown complete")

def main():
    """Main function to run the bot"""
    # Create event loop and run the bot
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
