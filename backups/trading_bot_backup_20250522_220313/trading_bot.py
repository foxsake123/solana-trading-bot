# trading_bot.py - Updated to properly handle real vs simulation trading

import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Setup logging
logger = logging.getLogger('trading_bot')

class TradingBot:
    def __init__(self, config=None, db=None, token_scanner=None, token_analyzer=None, trader=None):
        """
        Initialize the trading bot
        
        :param config: Configuration object
        :param db: Database instance
        :param token_scanner: TokenScanner instance
        :param token_analyzer: TokenAnalyzer instance
        :param trader: SolanaTrader instance
        """
        # Import configuration if not provided
        if config is None:
            from config import BotConfiguration
            self.config = BotConfiguration
        else:
            self.config = config
            
        # Store component instances
        self.db = db
        self.token_scanner = token_scanner
        self.token_analyzer = token_analyzer
        self.trader = trader
        
        # Load control settings
        self.simulation_mode = True  # Default to simulation mode
        self.control = self.load_control()
        
        # Set simulation mode from control
        if 'simulation_mode' in self.control:
            self.simulation_mode = self.control['simulation_mode']
            
        # Log the mode
        mode_str = "SIMULATION" if self.simulation_mode else "REAL TRADING"
        logger.info(f"Trading bot initialized in {mode_str} mode")
        
    def load_control(self) -> Dict[str, Any]:
        """
        Load control settings from the control file
        
        :return: Dictionary of control settings
        """
        default_control = {
            'running': False,
            'simulation_mode': True,
            'use_machine_learning': False,
            'take_profit_target': 15.0,
            'stop_loss_percentage': 0.25,
            'max_investment_per_token': 10.0,
            'slippage_tolerance': 0.30,
            'MIN_SAFETY_SCORE': 15.0,
            'MIN_VOLUME': 10.0,
            'MIN_LIQUIDITY': 5000.0,
            'MIN_MCAP': 10000.0,
            'MIN_HOLDERS': 10,
            'MIN_PRICE_CHANGE_1H': 10.0,
            'MIN_PRICE_CHANGE_6H': 2.0,
            'MIN_PRICE_CHANGE_24H': 5.0
        }
        
        if os.path.exists(self.config.BOT_CONTROL_FILE):
            try:
                with open(self.config.BOT_CONTROL_FILE, 'r') as f:
                    control = json.load(f)
                    
                # Update default with loaded values
                default_control.update(control)
            except Exception as e:
                logger.error(f"Error loading control settings: {e}")
                
        return default_control
        
    async def start(self):
        """Start the trading bot"""
        # Log startup
        logger.info("=" * 50)
        logger.info("   Solana Trading Bot Starting")
        logger.info("=" * 50)
        
        # Update control settings
        self.control = self.load_control()
        self.simulation_mode = self.control.get('simulation_mode', True)
        
        # Connect to Solana
        if self.trader:
            await self.trader.connect()
            
            # Get initial wallet balance
            sol_balance, usd_balance = await self.trader.get_wallet_balance()
            logger.info(f"Initial Wallet Balance: {sol_balance:.4f} SOL (${usd_balance:.2f})")
            
            # Start position monitoring
            asyncio.create_task(self.trader.start_position_monitoring())
        
        # Start token scanner
        if self.token_scanner:
            asyncio.create_task(self.token_scanner.start_scanning())
        
        # Start main trading process
        await self.start_trading()
        
    async def start_trading(self):
        """Start the token discovery and trading process"""
        logger.info("Starting token discovery and trading process")
        
        # Main trading loop
        while True:
            try:
                # Update control settings
                self.control = self.load_control()
                
                # Check if bot is running
                if not self.control.get('running', False):
                    logger.info("Bot paused by control settings")
                    await asyncio.sleep(60)  # Check again in 60 seconds
                    continue
                
                # Update simulation mode
                self.simulation_mode = self.control.get('simulation_mode', True)
                
                # Get current wallet balance
                if self.trader:
                    sol_balance, usd_balance = await self.trader.get_wallet_balance()
                    logger.info(f"Current wallet balance: {sol_balance:.4f} SOL (${usd_balance:.2f})")
                
                # Discover new tokens
                new_tokens = await self.discover_tokens()
                
                # Process each discovered token
                for token in new_tokens:
                    # Skip simulation tokens in real mode
                    if not self.simulation_mode and self.is_simulation_token(token.get('contract_address')):
                        logger.info(f"Skipping simulation token {token.get('ticker')} in real trading mode")
                        continue
                    
                    # Analyze and evaluate the token
                    if await self.evaluate_token(token):
                        # Trade the token if it meets criteria
                        await self.trade_token(token)
                
                # Wait before next cycle
                await asyncio.sleep(60)  # Run every 60 seconds
                
            except Exception as e:
                logger.error(f"Error in trading process: {e}")
                await asyncio.sleep(30)  # Shorter wait after error
                
    def is_simulation_token(self, contract_address: str) -> bool:
        """
        Check if a token is a simulation token
        
        :param contract_address: Token contract address
        :return: True if simulation token, False otherwise
        """
        if contract_address is None:
            return False
            
        # Check common simulation token patterns
        sim_patterns = ["sim", "test", "demo", "mock", "fake", "dummy"]
        lower_address = contract_address.lower()
        
        for pattern in sim_patterns:
            if pattern in lower_address:
                return True
                
        # Check for specific simulation token format in our system
        if contract_address.startswith(("Sim0", "Sim1", "Sim2", "Sim3", "Sim4")) and "TopGainer" in contract_address:
            return True
            
        return False
                
    async def discover_tokens(self) -> List[Dict[str, Any]]:
        """
        Discover new tokens to potentially trade
        
        :return: List of discovered tokens
        """
        discovered_tokens = []
        
        # If in simulation mode, generate some simulation tokens
        if self.simulation_mode:
            # Check if we're due to generate a new batch of simulation tokens
            # This could be based on time or other factors
            
            # Example: Generate 5 simulation tokens if we have fewer than 5 active positions
            active_positions = self.db.get_active_orders() if self.db else []
            active_count = len(active_positions) if not isinstance(active_positions, list) else 0
            
            if active_count < 5:
                # Generate simulation tokens
                import random
                import time
                
                for i in range(5):
                    timestamp = int(time.time())
                    token = {
                        'contract_address': f"Sim{i}TopGainer{timestamp}",
                        'ticker': f"SIMSim{i}",
                        'name': f"Top Gainer {i}",
                        'price_usd': random.uniform(0.0000001, 0.001),
                        'volume_24h': 50000.0,  # $50k volume
                        'liquidity_usd': 25000.0,  # $25k liquidity
                        'market_cap': 500000.0,  # $500k market cap
                        'holders': 100,
                        'price_change_1h': random.uniform(5.0, 15.0),
                        'price_change_6h': random.uniform(10.0, 25.0),
                        'price_change_24h': random.uniform(20.0, 50.0)
                    }
                    discovered_tokens.append(token)
        else:
            # In real mode, use the token scanner to discover real tokens
            if self.token_scanner:
                # Get tokens from various sources
                top_gainers = await self.token_scanner.get_top_gainers()
                trending_tokens = await self.token_scanner.get_trending_tokens()
                
                # Add real tokens to the discovered list
                discovered_tokens.extend(top_gainers)
                discovered_tokens.extend(trending_tokens)
                
                # Filter out any simulation tokens that might have slipped through
                discovered_tokens = [
                    token for token in discovered_tokens 
                    if not self.is_simulation_token(token.get('contract_address'))
                ]
        
        return discovered_tokens
        
    async def evaluate_token(self, token: Dict[str, Any]) -> bool:
        """
        Evaluate a token to determine if it meets trading criteria
        
        :param token: Token information
        :return: True if token meets criteria, False otherwise
        """
        # Get evaluation parameters from control settings
        min_safety_score = self.control.get('MIN_SAFETY_SCORE', 15.0)
        min_volume = self.control.get('MIN_VOLUME', 10.0)
        min_liquidity = self.control.get('MIN_LIQUIDITY', 5000.0)
        min_mcap = self.control.get('MIN_MCAP', 10000.0)
        min_holders = self.control.get('MIN_HOLDERS', 10)
        min_price_change_1h = self.control.get('MIN_PRICE_CHANGE_1H', 10.0)
        min_price_change_6h = self.control.get('MIN_PRICE_CHANGE_6H', 2.0)
        min_price_change_24h = self.control.get('MIN_PRICE_CHANGE_24H', 5.0)
        
        # Get token safety score from token analyzer
        safety_score = 0.0
        if self.token_analyzer:
            safety_score = await self.token_analyzer.get_safety_score(token.get('contract_address'))
            
        # Get token metrics
        volume_24h = token.get('volume_24h', 0.0)
        liquidity_usd = token.get('liquidity_usd', 0.0)
        market_cap = token.get('market_cap', 0.0)
        holders = token.get('holders', 0)
        price_change_1h = token.get('price_change_1h', 0.0)
        price_change_6h = token.get('price_change_6h', 0.0)
        price_change_24h = token.get('price_change_24h', 0.0)
        
        # Check if the token meets all criteria
        if (safety_score >= min_safety_score and
            volume_24h >= min_volume and
            liquidity_usd >= min_liquidity and
            market_cap >= min_mcap and
            holders >= min_holders and
            price_change_1h >= min_price_change_1h and
            price_change_6h >= min_price_change_6h and
            price_change_24h >= min_price_change_24h):
            
            # Log that the token qualifies for trading
            ticker = token.get('ticker')
            logger.info(f"Token {ticker} qualified for trading:")
            logger.info(f"  - Volume 24h: ${volume_24h:,.2f}")
            logger.info(f"  - Liquidity: ${liquidity_usd:,.2f}")
            logger.info(f"  - Market Cap: ${market_cap:,.2f}")
            logger.info(f"  - Holders: {holders}")
            logger.info(f"  - Price Change 24h: {price_change_24h:.2f}%")
            logger.info(f"  - Security Score: {safety_score:.1f}/100")
            
            return True
            
        return False
        
    async def trade_token(self, token: Dict[str, Any]):
        """
        Execute a trade for a token
        
        :param token: Token information
        """
        if not self.trader:
            logger.error("No trader available for trading")
            return
            
        # Get trading parameters
        max_investment = self.control.get('max_investment_per_token', 10.0)
        
        # Get token info
        contract_address = token.get('contract_address')
        ticker = token.get('ticker')
        
        # Check if it's a simulation token and we're in real mode
        if not self.simulation_mode and self.is_simulation_token(contract_address):
            logger.warning(f"Attempted to trade simulation token {ticker} in real trading mode")
            return
            
        # Calculate investment amount (can be improved with position sizing algorithms)
        # For now, just use the maximum investment amount
        investment_amount = max_investment
        
        # Execute the trade
        logger.info(f"Trading {ticker} ({contract_address}) for {investment_amount} SOL")
        tx_hash = await self.trader.buy_token(contract_address, investment_amount)
        
        if tx_hash and not tx_hash.startswith("ERROR"):
            logger.info(f"Successfully traded {ticker}: {tx_hash}")
        else:
            logger.error(f"Failed to trade {ticker}: {tx_hash}")
            
    async def process_active_positions(self):
        """Process and monitor active trading positions"""
        # This would handle monitoring active positions, checking for take profit and stop loss conditions
        # For now, we'll leave it as a placeholder for future implementation
        pass
