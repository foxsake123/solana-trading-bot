"""
TradingBot_adapter.py - Adapter for trading bot with improved async handling
"""
import os
import sys
import logging
import time
import threading
import asyncio
import traceback

# Configure logging
logger = logging.getLogger(__name__)

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import the actual TradingBot with flexible error handling
try:
    try:
        from trading_bot import TradingBot as OriginalTradingBot
        logger.info("Imported OriginalTradingBot from trading_bot")
    except ImportError:
        try:
            from core.trading_bot import TradingBot as OriginalTradingBot
            logger.info("Imported OriginalTradingBot from core.trading_bot")
        except ImportError:
            try:
                from core.simple_trading_bot import TradingBot as OriginalTradingBot
                logger.info("Imported OriginalTradingBot from core.simple_trading_bot")
            except ImportError:
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
except ImportError as e:
    logger.error(f"Failed to import OriginalTradingBot: {e}")
    logger.error(traceback.format_exc())
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
    
    def __init__(self, trader, token_scanner=None, simulation_mode=False, params=None):
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
            # Try different initialization approaches
            self._initialize_bot()
            logger.info("Successfully initialized TradingBot adapter")
        except Exception as e:
            logger.error(f"Error initializing TradingBot: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def _initialize_bot(self):
        """Initialize the bot with different possible parameter combinations"""
        # First try initializing with just trader and token_scanner
        try:
            logger.info("Trying to initialize TradingBot with trader and token_scanner")
            self.bot = OriginalTradingBot(self.trader, self.token_scanner)
            logger.info("Successfully initialized TradingBot with 2 parameters")
            # Set additional attributes
            self._set_additional_attributes()
            return
        except Exception as e:
            logger.warning(f"Failed to initialize TradingBot with 2 parameters: {e}")
        
        # Try with trader and token_scanner and simulation_mode
        try:
            logger.info("Trying to initialize TradingBot with trader, token_scanner, and simulation_mode")
            self.bot = OriginalTradingBot(self.trader, self.token_scanner, self.simulation_mode)
            logger.info("Successfully initialized TradingBot with 3 parameters")
            # Set additional attributes
            self._set_additional_attributes()
            return
        except Exception as e:
            logger.warning(f"Failed to initialize TradingBot with 3 parameters: {e}")
        
        # Try with trader and token_scanner and params
        try:
            logger.info("Trying to initialize TradingBot with trader, token_scanner, and params")
            self.bot = OriginalTradingBot(self.trader, self.token_scanner, self.params)
            logger.info("Successfully initialized TradingBot with trader, token_scanner, and params")
            # Set additional attributes
            self._set_additional_attributes()
            return
        except Exception as e:
            logger.warning(f"Failed to initialize TradingBot with trader, token_scanner, and params: {e}")
        
        # Try with just trader (some implementations use this)
        try:
            logger.info("Trying to initialize TradingBot with just trader")
            self.bot = OriginalTradingBot(self.trader)
            logger.info("Successfully initialized TradingBot with 1 parameter")
            
            # Set the token scanner separately
            if hasattr(self.bot, 'token_scanner') and self.token_scanner is not None:
                self.bot.token_scanner = self.token_scanner
                logger.info("Set token_scanner on TradingBot")
                
            # Set additional attributes
            self._set_additional_attributes()
            return
        except Exception as e:
            logger.error(f"Failed to initialize TradingBot with 1 parameter: {e}")
            
        # If all initialization attempts failed, try with a config argument
        try:
            logger.info("Trying to initialize TradingBot with config parameter")
            self.bot = OriginalTradingBot(config=self.params)
            
            # Set trader and token_scanner separately
            if hasattr(self.bot, 'trader'):
                self.bot.trader = self.trader
                logger.info("Set trader on TradingBot")
                
            if hasattr(self.bot, 'token_scanner') and self.token_scanner is not None:
                self.bot.token_scanner = self.token_scanner
                logger.info("Set token_scanner on TradingBot")
                
            # Set additional attributes
            self._set_additional_attributes()
            return
        except Exception as e:
            logger.error(f"Failed to initialize TradingBot with config parameter: {e}")
            
        # If all attempts fail, raise an exception
        raise ValueError("Could not initialize TradingBot with any parameter combination")
    
    def _set_additional_attributes(self):
        """Set additional attributes on the bot"""
        # Set simulation mode if the bot has this attribute
        if hasattr(self.bot, 'simulation_mode'):
            self.bot.simulation_mode = self.simulation_mode
            logger.info(f"Set simulation_mode={self.simulation_mode} on TradingBot")
            
        # Set params if the bot has this attribute
        if hasattr(self.bot, 'params') and self.params:
            self.bot.params = self.params
            logger.info("Set params on TradingBot")
            
        # Set control settings if available
        try:
            if os.path.exists('bot_control.json'):
                with open('bot_control.json', 'r') as f:
                    import json
                    control_data = json.load(f)
                
                # If the bot has a control attribute, set it
                if hasattr(self.bot, 'control'):
                    self.bot.control = control_data
                    logger.info("Set control settings from bot_control.json")
        except Exception as e:
            logger.warning(f"Error setting control settings: {e}")
    
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
                    
                    # Create a new event loop in a thread for async operation
                    def start_async_loop():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(start_method())
                        except Exception as e:
                            logger.error(f"Error in async start: {e}")
                            logger.error(traceback.format_exc())
                        finally:
                            loop.close()
                    
                    # Start the async loop in a thread
                    thread = threading.Thread(target=start_async_loop)
                    thread.daemon = True
                    thread.start()
                    
                    self.running = True
                    logger.info("TradingBot started in async mode")
                    return True
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
            logger.error(traceback.format_exc())
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
                    
                    # Create a new event loop for async operation
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(stop_method())
                    finally:
                        loop.close()
                    
                    self.running = False
                    logger.info("TradingBot stopped successfully")
                    return result
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
            logger.error(traceback.format_exc())
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
                def async_wrapper(*args, **kwargs):
                    # Run the async method in a new event loop
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            return loop.run_until_complete(attr(*args, **kwargs))
                        finally:
                            loop.close()
                    except Exception as e:
                        logger.error(f"Error in async wrapper for {name}: {e}")
                        logger.error(traceback.format_exc())
                        return None
                return async_wrapper
            else:
                return attr
                
        raise AttributeError(f"'TradingBot' object has no attribute '{name}'")
