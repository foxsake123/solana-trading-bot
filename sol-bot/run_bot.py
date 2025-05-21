#!/usr/bin/env python3
"""
Launch script for Solana Trading Bot
"""
import os
import sys
import logging
import json
import traceback
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger('solana_trading_bot')

def check_dependencies():
    """Check if all required dependencies are installed"""
    try:
        import asyncio
        try:
            import solders
            logger.info("Solders module found")
        except ImportError:
            logger.warning("Solders module not found, simulation mode only")
        
        import pandas
        return True
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.info("Please install required dependencies using: pip install -r requirements.txt")
        return False

def load_bot_control():
    """Load bot control settings from bot_control.json"""
    control_files = [
        'sol-bot/data/bot_control.json',
        'data/bot_control.json',
        'bot_control.json'
    ]
    
    for control_file in control_files:
        if os.path.exists(control_file):
            try:
                with open(control_file, 'r') as f:
                    control = json.load(f)
                    logger.info(f"Loaded configuration from {control_file}")
                    return control
            except Exception as e:
                logger.error(f"Error loading {control_file}: {e}")
    
    # Default settings if no file found
    return {
        "running": False,
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

def ensure_bot_control(control):
    """Ensure bot_control.json exists with proper settings"""
    # Create data directory if it doesn't exist
    os.makedirs('sol-bot/data', exist_ok=True)
    
    control_file = 'sol-bot/data/bot_control.json'
    
    # Create or update the control file
    with open(control_file, 'w') as f:
        json.dump(control, f, indent=4)
        
    logger.info(f"Updated configuration in {control_file}")
    return True

def start_bot():
    """Start the trading bot"""
    try:
        # Load the control settings
        control = load_bot_control()
        
        # Log important settings
        logger.info(f"Bot running: {control.get('running', False)}")
        logger.info(f"Simulation mode: {control.get('simulation_mode', True)}")
        
        # Warn if real trading is enabled
        if not control.get('simulation_mode', True):
            logger.warning("REAL TRADING MODE ENABLED - Bot will execute actual trades!")
        
        # Update control settings
        ensure_bot_control(control)
        
        # Try to import and run main from different possible locations
        try:
            # First try from sol-bot
            sys.path.insert(0, os.path.abspath('.'))
            from sol-bot.main import main
            logger.info("Using sol-bot package")
        except ImportError:
            try:
                # Try from core directory
                from core.main import main
                logger.info("Using core.main")
            except ImportError:
                # Fall back to standard import
                from main import main
                logger.info("Using direct module import")
        
        # Run the bot
        logger.info("Starting Solana Trading Bot...")
        main()
        return True
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        logger.error(traceback.format_exc())
        return False
    
def run_simplified_bot():
    """Run a simplified version of the bot"""
    try:
        # Import the required modules
        try:
            from sol-bot.database.database import Database
        except ImportError:
            try:
                from sol-bot.database import Database
            except ImportError:
                from database import Database
        
        try:
            from sol-bot.core.simplified_solana_trader import SolanaTrader
            from sol-bot.core.simplified_token_scanner import TokenScanner
            from sol-bot.core.simplified_trading_bot import TradingBot
        except ImportError:
            try:
                from core.simplified_solana_trader import SolanaTrader
                from core.simplified_token_scanner import TokenScanner
                from core.simplified_trading_bot import TradingBot
            except ImportError:
                from simplified_solana_trader import SolanaTrader
                from simplified_token_scanner import TokenScanner
                from simplified_trading_bot import TradingBot
        
        import asyncio
        
        # Load control settings
        control = load_bot_control()
        
        # Create database
        db = Database()
        
        # Create and initialize trader
        trader = SolanaTrader(
            db=db,
            simulation_mode=control.get('simulation_mode', True)
        )
        
        # Create token scanner
        token_scanner = TokenScanner(db=db)
        
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
        
        # Create trading bot
        trading_bot = TradingBot(
            trader=trader,
            token_scanner=token_scanner,
            simulation_mode=control.get('simulation_mode', True),
            params=trading_params
        )
        
        # Run the bot
        asyncio.run(run_trading_bot(trader, trading_bot, control))
        
        return True
    except Exception as e:
        logger.error(f"Error running simplified bot: {e}")
        logger.error(traceback.format_exc())
        return False

async def run_trading_bot(trader, trading_bot, control):
    """Run the trading bot asynchronously"""
    # Connect to the Solana network
    await trader.connect()
    
    # Get initial wallet balance
    sol_balance, usd_balance = await trader.get_wallet_balance()
    logger.info(f"Initial Wallet Balance: {sol_balance:.4f} SOL (${usd_balance:.2f})")
    
    # Start the bot if enabled
    if control.get('running', False):
        logger.info("Starting trading bot")
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

if __name__ == "__main__":
    logger.info("Solana Trading Bot initialization")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Try to start the bot
    logger.info("Attempting to start bot...")
    
    if start_bot():
        logger.info("Bot started successfully using main entry point")
    else:
        logger.warning("Failed to start using main entry point, trying simplified approach...")
        if run_simplified_bot():
            logger.info("Bot started successfully using simplified approach")
        else:
            logger.error("Failed to start bot with all methods")
            sys.exit(1)

$runBotContent | Set-Content -Path run_bot.py