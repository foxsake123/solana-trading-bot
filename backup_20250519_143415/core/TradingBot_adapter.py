"""
Updated TradingBot adapter with async handling for start/stop methods
"""
import os
import sys
import logging
import time
import threading
import asyncio

# Configure logging
logger = logging.getLogger(__name__)

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import the actual TradingBot with flexible error handling
try:
    try:
        from simple_trading_bot import TradingBot as OriginalTradingBot
        logger.info("Imported OriginalTradingBot from simple_trading_bot")
    except ImportError:
        from core.simple_trading_bot import TradingBot as OriginalTradingBot
        logger.info("Imported OriginalTradingBot from core.simple_trading_bot")
except ImportError as e:
    logger.error(f"Failed to import OriginalTradingBot: {e}")
    # Create a placeholder class if import fails
    class OriginalTradingBot:
        def __init__(self, *args, **kwargs):
            logger.error("Using placeholder TradingBot")
            
        def start(self):
            logger.error("Cannot start placeholder TradingBot")
            return False
            
        def stop(self):
            logger.error("Cannot stop placeholder TradingBot")
            return False

# Create an adapter that handles different initialization
class TradingBot:
    """
    Adapter class for TradingBot with flexible initialization and async handling
    """
    
    def __init__(self, trader, token_scanner, simulation_mode=False, params=None):
        """
        Initialize a TradingBot with flexible parameter handling
        
        Args:
            trader: SolanaTrader instance
            token_scanner: TokenScanner instance
            simulation_mode: Whether to run in simulation mode
            params: Trading parameters
        """
        self.trader = trader
        self.token_scanner = token_scanner
        self.simulation_mode = simulation_mode
        self.params = params or {}
        self.running = False
        
        try:
            # First try initializing with just trader and token_scanner
            try:
                logger.info("Trying to initialize TradingBot with trader and token_scanner")
                self.bot = OriginalTradingBot(trader, token_scanner)
                logger.info("Successfully initialized TradingBot with 2 parameters")
            except TypeError as e:
                logger.warning(f"Failed to initialize TradingBot with 2 parameters: {e}")
                
                # Try with trader, token_scanner, and params
                try:
                    logger.info("Trying to initialize TradingBot with trader, token_scanner, and params")
                    self.bot = OriginalTradingBot(trader, token_scanner, params)
                    logger.info("Successfully initialized TradingBot with 3 parameters")
                except TypeError as e:
                    logger.warning(f"Failed to initialize TradingBot with 3 parameters: {e}")
                    
                    # Try with just trader (some implementations use this)
                    try:
                        logger.info("Trying to initialize TradingBot with just trader")
                        self.bot = OriginalTradingBot(trader)
                        # Set the token scanner separately
                        if hasattr(self.bot, 'token_scanner'):
                            self.bot.token_scanner = token_scanner
                        logger.info("Successfully initialized TradingBot with 1 parameter")
                    except TypeError as e:
                        logger.error(f"Failed to initialize TradingBot with 1 parameter: {e}")
                        raise
            
            # Set simulation mode if the bot has this attribute
            if hasattr(self.bot, 'simulation_mode'):
                self.bot.simulation_mode = simulation_mode
                logger.info(f"Set simulation_mode={simulation_mode} on TradingBot")
                
            # Set params if the bot has this attribute
            if hasattr(self.bot, 'params') and params:
                self.bot.params = params
                logger.info("Set params on TradingBot")
                
            logger.info("Successfully initialized TradingBot adapter")
        except Exception as e:
            logger.error(f"Error initializing TradingBot: {e}")
            raise
    
    def start(self):
        """Start the trading bot (handles both sync and async start methods)"""
        if self.running:
            logger.warning("Trading bot is already running")
            return
            
        try:
            # Check if the start method is an async coroutine
            if hasattr(self.bot, 'start'):
                start_method = getattr(self.bot, 'start')
                
                # If it's an async method, run it in a new event loop
                if asyncio.iscoroutinefunction(start_method):
                    logger.info("Starting TradingBot using async method...")
                    result = asyncio.run(start_method())
                else:
                    logger.info("Starting TradingBot using sync method...")
                    result = start_method()
                    
                self.running = True
                logger.info("TradingBot started successfully")
                return result
            else:
                logger.error("TradingBot has no start method")
                return False
        except Exception as e:
            logger.error(f"Error starting TradingBot: {e}")
            return False
    
    def stop(self):
        """Stop the trading bot (handles both sync and async stop methods)"""
        if not self.running:
            logger.warning("Trading bot is not running")
            return
            
        try:
            # Check if the stop method is an async coroutine
            if hasattr(self.bot, 'stop'):
                stop_method = getattr(self.bot, 'stop')
                
                # If it's an async method, run it in a new event loop
                if asyncio.iscoroutinefunction(stop_method):
                    logger.info("Stopping TradingBot using async method...")
                    result = asyncio.run(stop_method())
                else:
                    logger.info("Stopping TradingBot using sync method...")
                    result = stop_method()
                    
                self.running = False
                logger.info("TradingBot stopped successfully")
                return result
            else:
                logger.error("TradingBot has no stop method")
                return False
        except Exception as e:
            logger.error(f"Error stopping TradingBot: {e}")
            return False
    
    def __getattr__(self, name):
        """
        Forward attribute access to the original bot
        
        Args:
            name: Attribute name
            
        Returns:
            The attribute from the original bot
        """
        # Forward attribute access to the original bot
        if hasattr(self, 'bot') and hasattr(self.bot, name):
            attr = getattr(self.bot, name)
            
            # If the attribute is an async method, wrap it to handle async/sync conversion
            if callable(attr) and asyncio.iscoroutinefunction(attr):
                def wrapper(*args, **kwargs):
                    # Run the async method in a new event loop
                    try:
                        return asyncio.run(attr(*args, **kwargs))
                    except Exception as e:
                        logger.error(f"Error in async wrapper for {name}: {e}")
                        return None
                return wrapper
            else:
                return attr
                
        raise AttributeError(f"'TradingBot' object has no attribute '{name}'")