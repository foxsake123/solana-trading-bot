# main.py - Updated to work with the new TradingBot implementation

import os
import sys
import json
import asyncio
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('root')

# Increase Python recursion limit for complex operations
sys.setrecursionlimit(3000)
logger.info(f"Python recursion limit set to {sys.getrecursionlimit()}")

# Import configuration
from config import BotConfiguration

# Import components
from database import Database
from solana_trader import SolanaTrader
from token_analyzer import TokenAnalyzer
from token_scanner import TokenScanner
from birdeye import BirdeyeAPI
from trading_bot import TradingBot

async def run_bot():
    """Run the trading bot"""
    try:
        # Initialize components
        db = Database()
        
        # Load control file to check simulation mode
        simulation_mode = True
        if os.path.exists(BotConfiguration.BOT_CONTROL_FILE):
            try:
                with open(BotConfiguration.BOT_CONTROL_FILE, 'r') as f:
                    control = json.load(f)
                    simulation_mode = control.get('simulation_mode', True)
            except Exception as e:
                logger.error(f"Error loading control file: {e}")
        
        # Initialize components with simulation mode
        trader = SolanaTrader(db=db, simulation_mode=simulation_mode)
        birdeye_api = BirdeyeAPI()
        token_analyzer = TokenAnalyzer(db=db, birdeye_api=birdeye_api)
        token_scanner = TokenScanner(db=db, trader=trader, token_analyzer=token_analyzer, birdeye_api=birdeye_api)
        
        # Initialize the bot
        bot = TradingBot(
            config=BotConfiguration,
            db=db,
            token_scanner=token_scanner,
            token_analyzer=token_analyzer,
            trader=trader
        )
        
        # Start the bot - using the start() method, not run()
        await bot.start()
        
    except Exception as e:
        logger.critical(f"Unhandled bot initialization error: {e}")
        import traceback
        logger.critical(traceback.format_exc())

def main():
    """Main entry point"""
    try:
        # Run the bot with asyncio
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Unhandled error: {e}")
        import traceback
        logger.critical(traceback.format_exc())
    finally:
        logger.info("Bot execution completed")

if __name__ == "__main__":
    main()
