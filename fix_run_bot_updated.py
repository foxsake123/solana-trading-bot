# fix_run_bot_updated.py
import os

def fix_run_bot():
    """Fix run_bot_updated.py to work with the current TokenScanner"""
    
    content = '''"""
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
    from core.birdeye import BirdeyeAPI
    
    # Also try to import the token analyzer
    try:
        from token_analyzer import TokenAnalyzer
    except ImportError:
        from core.token_analyzer import TokenAnalyzer
        
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
                "simulation_mode": True,
                "filter_fake_tokens": False,
                "use_birdeye_api": True,
                "use_machine_learning": True,
                "take_profit_target": 1.15,
                "stop_loss_percentage": 0.05,
                "max_investment_per_token": 0.05,
                "min_investment_per_token": 0.01,
                "slippage_tolerance": 0.10,
                "MIN_SAFETY_SCORE": 15.0,
                "MIN_VOLUME": 1000.0,
                "MIN_LIQUIDITY": 5000.0,
                "MIN_MCAP": 10000.0,
                "MIN_HOLDERS": 10,
                "MIN_PRICE_CHANGE_1H": -50.0,
                "MIN_PRICE_CHANGE_6H": -50.0,
                "MIN_PRICE_CHANGE_24H": -50.0,
                "starting_simulation_balance": 1.0
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
    
    # Initialize BirdeyeAPI for real token data
    birdeye_api = BirdeyeAPI()
    logger.info("BirdeyeAPI initialized for real token data")
    
    # Initialize token analyzer with BirdeyeAPI
    token_analyzer = TokenAnalyzer(db=db_adapter, birdeye_api=birdeye_api)
    logger.info("TokenAnalyzer initialized")
    
    # Create and initialize token scanner
    # Try to pass all parameters if accepted
    try:
        token_scanner = TokenScanner(
            db=db_adapter, 
            trader=trader,
            token_analyzer=token_analyzer,
            birdeye_api=birdeye_api
        )
        logger.info("TokenScanner initialized with all parameters")
    except TypeError:
        try:
            # Try without birdeye_api
            token_scanner = TokenScanner(
                db=db_adapter,
                trader=trader,
                token_analyzer=token_analyzer
            )
            logger.info("TokenScanner initialized without birdeye_api")
            
            # Set birdeye_api as attribute if possible
            if hasattr(token_scanner, 'birdeye_api'):
                token_scanner.birdeye_api = birdeye_api
                logger.info("Set birdeye_api on token_scanner")
        except TypeError:
            # Try minimal parameters
            token_scanner = TokenScanner(db=db_adapter)
            logger.info("TokenScanner initialized with minimal parameters")
            
            # Set additional attributes if possible
            if hasattr(token_scanner, 'trader'):
                token_scanner.trader = trader
            if hasattr(token_scanner, 'token_analyzer'):
                token_scanner.token_analyzer = token_analyzer
            if hasattr(token_scanner, 'birdeye_api'):
                token_scanner.birdeye_api = birdeye_api
    
    # Create and initialize trading bot
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
                if hasattr(trading_bot, 'params'):
                    trading_bot.params = control
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
        
        # Check if trading bot has async start method
        if hasattr(trading_bot, 'start') and asyncio.iscoroutinefunction(trading_bot.start):
            await trading_bot.start()
        elif hasattr(trading_bot, 'start'):
            trading_bot.start()
        else:
            # If no start method, try run method
            if hasattr(trading_bot, 'run'):
                if asyncio.iscoroutinefunction(trading_bot.run):
                    await trading_bot.run()
                else:
                    trading_bot.run()
            else:
                logger.error("TradingBot has no start or run method")
                return
        
        # Keep the main thread running
        try:
            mode_str = "SIMULATION" if simulation_mode else "REAL TRADING"
            logger.info(f"Bot running in {mode_str} MODE. Press Ctrl+C to stop.")
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            if hasattr(trading_bot, 'stop'):
                if asyncio.iscoroutinefunction(trading_bot.stop):
                    await trading_bot.stop()
                else:
                    trading_bot.stop()
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
'''
    
    with open('run_bot_updated.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed run_bot_updated.py")

if __name__ == "__main__":
    fix_run_bot()