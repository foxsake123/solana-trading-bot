"""
Enhanced Trading Bot with AI Algorithm Integration
"""
import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import pandas as pd
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the AI algorithm
try:
    from enhanced_ai_trading_algorithm import ai_algorithm
except ImportError:
    print("Warning: Enhanced AI algorithm not found, using basic logic")
    ai_algorithm = None

logger = logging.getLogger('trading_bot')

class TradingBot:
    def __init__(self, config, db=None, token_scanner=None, token_analyzer=None, trader=None):
        """Initialize the enhanced trading bot"""
        self.config = config if config else self._load_config()
        self.db = db
        self.token_scanner = token_scanner
        self.token_analyzer = token_analyzer
        self.trader = trader
        
        # Set simulation mode with 10 SOL starting balance
        self.simulation_mode = self.config.get('simulation_mode', True)
        self.simulation_balance = self.config.get('starting_simulation_balance', 10.0)
        
        # Load control settings
        self.control = self.load_control()
        
        # Track active trades
        self.active_positions = {}
        
        logger.info(f"Trading bot initialized in {'SIMULATION' if self.simulation_mode else 'REAL'} mode")
        logger.info(f"Starting balance: {self.simulation_balance} SOL")
        
    def _load_config(self):
        """Load configuration"""
        try:
            from config import BotConfiguration
            return BotConfiguration
        except:
            return {}
    
    def load_control(self) -> Dict[str, Any]:
        """Load control settings from the control file"""
        default_control = {
            'running': False,
            'simulation_mode': True,
            'starting_simulation_balance': 10.0,
            'use_machine_learning': True,
            'take_profit_target': 1.15,
            'stop_loss_percentage': 0.05,
            'max_investment_per_token': 0.5,
            'slippage_tolerance': 0.10,
            'MIN_SAFETY_SCORE': 15.0,
            'MIN_VOLUME': 50000.0,
            'MIN_LIQUIDITY': 100000.0,
            'MIN_MCAP': 1000000.0,
            'MIN_HOLDERS': 500,
            'MIN_PRICE_CHANGE_1H': 2.0,
            'MIN_PRICE_CHANGE_6H': 5.0,
            'MIN_PRICE_CHANGE_24H': 10.0
        }
        
        control_file = 'bot_control.json'
        if not os.path.exists(control_file):
            control_file = os.path.join(self.config.DATA_DIR if hasattr(self.config, 'DATA_DIR') else 'data', 'bot_control.json')
        
        if os.path.exists(control_file):
            try:
                with open(control_file, 'r') as f:
                    control = json.load(f)
                    default_control.update(control)
            except Exception as e:
                logger.error(f"Error loading control settings: {e}")
                
        return default_control
        
    async def start(self):
        """Start the trading bot"""
        logger.info("=" * 50)
        logger.info("   Enhanced AI Trading Bot Starting")
        logger.info("=" * 50)
        
        # Update control settings
        self.control = self.load_control()
        self.simulation_mode = self.control.get('simulation_mode', True)
        
        # Connect to Solana if trader available
        if self.trader:
            await self.trader.connect()
            
            # Get initial wallet balance
            if self.simulation_mode:
                logger.info(f"Simulation Balance: {self.simulation_balance:.4f} SOL")
            else:
                sol_balance, usd_balance = await self.trader.get_wallet_balance()
                logger.info(f"Wallet Balance: {sol_balance:.4f} SOL (${usd_balance:.2f})")
        
        # Start token scanner if available
        if self.token_scanner:
            asyncio.create_task(self.token_scanner.start_scanning())
        
        # Start main trading process
        await self.start_trading()
        
    async def start_trading(self):
        """Start the token discovery and trading process with AI algorithm"""
        logger.info("Starting AI-enhanced token discovery and trading process")
        
        while True:
            try:
                # Update control settings
                self.control = self.load_control()
                
                # Check if bot is running
                if not self.control.get('running', False):
                    logger.info("Bot paused by control settings")
                    await asyncio.sleep(60)
                    continue
                
                # Update simulation mode
                self.simulation_mode = self.control.get('simulation_mode', True)
                
                # Get current balance
                current_balance = self.simulation_balance
                if self.trader and not self.simulation_mode:
                    sol_balance, _ = await self.trader.get_wallet_balance()
                    current_balance = sol_balance
                
                logger.info(f"Current balance: {current_balance:.4f} SOL")
                
                # Check for position exits first
                await self.check_position_exits()
                
                # Discover new tokens
                new_tokens = await self.discover_tokens()
                
                # Process each discovered token with AI algorithm
                for token in new_tokens:
                    # Skip if we already have a position
                    if token.get('contract_address') in self.active_positions:
                        continue
                    
                    # Get price history if available
                    price_history = await self.get_token_price_history(token)
                    
                    # Use AI algorithm to evaluate
                    if ai_algorithm and price_history is not None:
                        should_enter, position_size, reason = ai_algorithm.should_enter_position(
                            token, price_history
                        )
                        
                        if should_enter:
                            logger.info(f"AI Signal: {reason} for {token.get('ticker')} - Size: {position_size:.3f} SOL")
                            
                            # Execute trade
                            success = await self.execute_trade(token, position_size, 'BUY')
                            
                            if success:
                                # Track position
                                self.active_positions[token['contract_address']] = {
                                    'token': token,
                                    'entry_price': token.get('price_usd', 0),
                                    'entry_time': datetime.now(),
                                    'position_size': position_size,
                                    'highest_price': token.get('price_usd', 0)
                                }
                    else:
                        # Fallback to basic evaluation
                        if await self.evaluate_token(token):
                            await self.trade_token(token)
                
                # Display performance
                if ai_algorithm:
                    performance = ai_algorithm.get_performance_summary()
                    logger.info(f"AI Performance - Trades: {performance['total_trades']}, "
                              f"Win Rate: {performance['win_rate']:.1f}%, "
                              f"P&L: {performance['total_pnl_sol']:.4f} SOL")
                
                # Wait before next cycle
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in trading process: {e}")
                await asyncio.sleep(30)
    
    async def check_position_exits(self):
        """Check if any positions should be exited"""
        if not ai_algorithm:
            return
        
        positions_to_close = []
        
        for address, position in self.active_positions.items():
            # Get current price
            current_price = await self.get_current_token_price(address)
            
            if current_price:
                should_exit, reason = ai_algorithm.should_exit_position(position, current_price)
                
                if should_exit:
                    positions_to_close.append((address, position, reason))
        
        # Execute exits
        for address, position, reason in positions_to_close:
            logger.info(f"Exiting position: {reason} for {position['token'].get('ticker')}")
            
            success = await self.execute_trade(
                position['token'], 
                position['position_size'], 
                'SELL'
            )
            
            if success:
                # Calculate P&L
                entry_price = position['entry_price']
                exit_price = await self.get_current_token_price(address)
                pnl = (exit_price / entry_price - 1) * position['position_size'] if entry_price > 0 else 0
                
                # Update AI algorithm performance
                ai_algorithm.update_performance_metrics({
                    'pnl': pnl,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'position_size': position['position_size']
                })
                
                # Remove from active positions
                del self.active_positions[address]
    
    async def get_token_price_history(self, token: Dict) -> Optional[pd.DataFrame]:
        """Get token price history for AI analysis"""
        # In a real implementation, this would fetch from API or database
        # For now, return None to use fallback logic
        return None
    
    async def get_current_token_price(self, contract_address: str) -> Optional[float]:
        """Get current token price"""
        # In a real implementation, this would fetch from API
        # For now, return the stored price
        if contract_address in self.active_positions:
            return self.active_positions[contract_address]['token'].get('price_usd', 0)
        return None
    
    async def execute_trade(self, token: Dict, amount: float, action: str) -> bool:
        """Execute a trade"""
        try:
            if self.simulation_mode:
                # Simulate trade execution
                if action == 'BUY':
                    self.simulation_balance -= amount
                    logger.info(f"SIM: Bought {amount:.3f} SOL of {token.get('ticker')}")
                else:
                    self.simulation_balance += amount
                    logger.info(f"SIM: Sold {amount:.3f} SOL of {token.get('ticker')}")
                
                # Record in database if available
                if self.db:
                    self.db.record_trade(
                        contract_address=token.get('contract_address'),
                        action=action,
                        amount=amount,
                        price=token.get('price_usd', 0),
                        is_simulation=True
                    )
                
                return True
            else:
                # Real trade execution
                if self.trader:
                    if action == 'BUY':
                        tx_hash = await self.trader.buy_token(token.get('contract_address'), amount)
                    else:
                        tx_hash = await self.trader.sell_token(token.get('contract_address'), amount)
                    
                    return tx_hash and not tx_hash.startswith("ERROR")
                
            return False
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return False
    
    # Keep existing methods for compatibility
    async def discover_tokens(self) -> List[Dict[str, Any]]:
        """Discover new tokens to potentially trade"""
        discovered_tokens = []
        
        if self.simulation_mode:
            # Generate some simulation tokens for testing
            import random
            import time
            
            for i in range(3):
                timestamp = int(time.time())
                token = {
                    'contract_address': f"Sim{i}TopGainer{timestamp}",
                    'ticker': f"SIM{i}",
                    'name': f"Simulation Token {i}",
                    'price_usd': random.uniform(0.0000001, 0.001),
                    'volume_24h': random.uniform(50000, 200000),
                    'liquidity_usd': random.uniform(100000, 500000),
                    'market_cap': random.uniform(1000000, 5000000),
                    'holders': random.randint(500, 2000),
                    'price_change_1h': random.uniform(2.0, 10.0),
                    'price_change_6h': random.uniform(5.0, 20.0),
                    'price_change_24h': random.uniform(10.0, 50.0)
                }
                discovered_tokens.append(token)
        else:
            # Real token discovery
            if self.token_scanner:
                top_gainers = await self.token_scanner.get_top_gainers()
                trending_tokens = await self.token_scanner.get_trending_tokens()
                
                discovered_tokens.extend(top_gainers)
                discovered_tokens.extend(trending_tokens)
        
        return discovered_tokens
    
    async def evaluate_token(self, token: Dict[str, Any]) -> bool:
        """Basic token evaluation for fallback"""
        # Use control settings for evaluation
        return (
            token.get('volume_24h', 0) >= self.control.get('MIN_VOLUME', 50000) and
            token.get('liquidity_usd', 0) >= self.control.get('MIN_LIQUIDITY', 100000) and
            token.get('market_cap', 0) >= self.control.get('MIN_MCAP', 1000000) and
            token.get('holders', 0) >= self.control.get('MIN_HOLDERS', 500) and
            token.get('price_change_24h', 0) >= self.control.get('MIN_PRICE_CHANGE_24H', 10.0)
        )
    
    async def trade_token(self, token: Dict[str, Any]):
        """Execute a basic trade for a token"""
        max_investment = self.control.get('max_investment_per_token', 0.5)
        await self.execute_trade(token, max_investment, 'BUY')
