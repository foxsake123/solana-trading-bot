import logging
import asyncio
import os
import json
from datetime import datetime

logger = logging.getLogger('trading_bot')

class TradingBot:
    """
    A simplified version of the TradingBot class for debugging
    """
    def __init__(self, config, db=None, token_scanner=None, token_analyzer=None, trader=None):
        """Initialize the trading bot"""
        self.config = config
        self.db = db
        self.token_scanner = token_scanner
        self.token_analyzer = token_analyzer
        self.trader = trader
        
        # Get simulation mode from trader, but make sure we use the correct value
        if trader and hasattr(trader, 'simulation_mode'):
            self.simulation_mode = trader.simulation_mode
            logger.info(f"Using trader's simulation mode: {self.simulation_mode}")
        elif hasattr(config, 'TRADING_PARAMETERS') and 'simulation_mode' in config.TRADING_PARAMETERS:
            self.simulation_mode = config.TRADING_PARAMETERS.get('simulation_mode', True)
            logger.info(f"Using config's simulation mode: {self.simulation_mode}")
        else:
            # Get simulation mode from control file
            self.simulation_mode = self._get_simulation_mode_from_control_file()
            logger.info(f"Using control file's simulation mode: {self.simulation_mode}")
        
        # Override trader's simulation mode to match ours
        if trader and hasattr(trader, 'simulation_mode'):
            if trader.simulation_mode != self.simulation_mode:
                logger.info(f"Overriding trader's simulation mode from {trader.simulation_mode} to {self.simulation_mode}")
                trader.simulation_mode = self.simulation_mode
        
        # Log the mode
        logger.info(f"Trading bot initialized in {'SIMULATION' if self.simulation_mode else 'REAL TRADING'} mode")
    
    def _get_simulation_mode_from_control_file(self):
        """Get simulation mode from control file"""
        control_file = os.path.join(self.config.DATA_DIR, 'bot_control.json')
        if not os.path.exists(control_file):
            control_file = 'bot_control.json'
        
        if os.path.exists(control_file):
            try:
                with open(control_file, 'r') as f:
                    control = json.load(f)
                    return control.get('simulation_mode', True)
            except Exception as e:
                logger.error(f"Error loading control file: {e}")
        
        # Default to simulation mode
        return True
    
    async def start(self):
        """Start the trading bot"""
        logger.info("==================================================")
        logger.info("   Solana Trading Bot Starting")
        logger.info("==================================================")
        
        # Connect to the network
        if self.trader:
            await self.trader.connect()
            
            # Get the wallet balance
            balance_sol, balance_usd = await self.trader.get_wallet_balance()
            logger.info(f"Initial Wallet Balance: {balance_sol:.4f} SOL (${balance_usd:.2f})")
            
            # Start the trading process
            logger.info("Starting token discovery and trading process")
            
            # Check if the bot is paused
            if hasattr(self.config, 'BOT_CONTROL_FILE') and os.path.exists(self.config.BOT_CONTROL_FILE):
                try:
                    with open(self.config.BOT_CONTROL_FILE, 'r') as f:
                        control = json.load(f)
                        if not control.get('running', True):
                            logger.info("Bot paused by control settings")
                except Exception as e:
                    logger.error(f"Error reading control file: {e}")
            else:
                logger.info("Bot paused by control settings")
            
            # Start position monitoring
            if self.trader:
                await self.trader.start_position_monitoring()
                
            # Start token scanning
            if self.token_scanner:
                logger.info("Starting token scanner")
                
                # Check for different possible methods
                if hasattr(self.token_scanner, 'start'):
                    logger.info("Using token_scanner.start()")
                    self.token_scanner.start()
                elif hasattr(self.token_scanner, 'scan_tokens'):
                    logger.info("Using token_scanner.scan_tokens()")
                    asyncio.create_task(self.token_scanner.scan_tokens())
                elif hasattr(self.token_scanner, 'scan'):
                    logger.info("Using token_scanner.scan()")
                    asyncio.create_task(self.token_scanner.scan())
                else:
                    logger.warning("TokenScanner has no recognized start method. Available methods:")
                    for method in dir(self.token_scanner):
                        if not method.startswith('__') and callable(getattr(self.token_scanner, method)):
                            logger.info(f"- {method}")