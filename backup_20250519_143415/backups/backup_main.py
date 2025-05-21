import asyncio
import os
import logging
import logging.handlers
import sys
from trading_bot import TradingBot

# Setup logging
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)

# Configure root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# File handler for all logs
file_handler = logging.handlers.RotatingFileHandler(
    f'logs/trading_bot.log',
    maxBytes=10*1024*1024,
    backupCount=5
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

def main():
    """Entry point for the bot"""
    try:
        # Configure Python's recursion limit to be higher
        # Try increasing the recursion limit, but this is just a temporary fix
        # The real solution is to eliminate recursive calls in the codebase
        sys.setrecursionlimit(3000)  # Increased from 2000 to 3000
        
        # Set a conservative thread stack size to help with recursion
        # This is only available on some platforms
        try:
            import threading
            threading.stack_size(16*1024*1024)  # 16MB stack size
        except (ImportError, AttributeError, RuntimeError):
            pass
        
        logger.info(f"Python recursion limit set to {sys.getrecursionlimit()}")
        
        # Initialize and run the bot
        bot = TradingBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Unhandled bot initialization error: {e}")
        import traceback
        logger.critical(traceback.format_exc())
    finally:
        logger.info("Bot execution completed")

if __name__ == "__main__":
    main()