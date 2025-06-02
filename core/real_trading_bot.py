# real_trading_bot.py
import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger('trading_bot')

class TradingBot:
    """Trading bot that trades real Solana tokens"""
    
    def __init__(self, config: Dict, db: Any, token_scanner: Any, trader: Any):
        self.config = config
        self.db = db
        self.token_scanner = token_scanner
        self.trader = trader
        self.balance = config.get('starting_simulation_balance', 10.0)
        self.simulation_mode = config.get('simulation_mode', True)
        self.positions = {}
        self.running = False
        
        logger.info(f"Trading bot initialized in {'SIMULATION' if self.simulation_mode else 'REAL'} mode")
        logger.info(f"Starting balance: {self.balance} SOL")
    
    async def start(self):
        """Start the trading bot"""
        logger.info("="*50)
        logger.info("   Real Token Trading Bot Starting")
        logger.info("="*50)
        
        self.running = True
        
        # Start token scanner in background
        asyncio.create_task(self.token_scanner.start_scanning())
        
        # Start main trading loop
        await self.trading_loop()
    
    async def trading_loop(self):
        """Main trading loop"""
        logger.info("Starting trading loop - looking for real tokens only")
        
        scan_interval = self.config.get('scan_interval', 60)
        
        while self.running:
            try:
                # Update balance
                balance_sol, balance_usd = await self.trader.get_wallet_balance()
                self.balance = balance_sol
                logger.info(f"Current balance: {self.balance:.4f} SOL")
                
                # Get real tokens to analyze
                await self.find_and_trade_tokens()
                
                # Monitor existing positions
                await self.monitor_positions()
                
                # Wait before next iteration
                await asyncio.sleep(scan_interval)
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(30)
    
    async def find_and_trade_tokens(self):
        """Find and trade real tokens"""
        try:
            # Get top gainers and trending tokens
            top_gainers = await self.token_scanner.get_top_gainers()
            trending = await self.token_scanner.get_trending_tokens()
            
            # Combine and deduplicate
            all_tokens = []
            seen = set()
            
            for token in top_gainers + trending:
                address = token.get('contract_address', token.get('address', ''))
                
                # Skip if already seen or if it's a simulation token
                if address in seen or address.startswith('Sim'):
                    continue
                    
                seen.add(address)
                all_tokens.append(token)
            
            logger.info(f"Found {len(all_tokens)} unique real tokens to analyze")
            
            # Analyze each token
            for token in all_tokens:
                await self.analyze_and_trade_token(token)
                
        except Exception as e:
            logger.error(f"Error finding tokens: {e}")
    
    async def analyze_and_trade_token(self, token: Dict):
        """Analyze a token and decide whether to trade"""
        try:
            address = token.get('contract_address', token.get('address', ''))
            ticker = token.get('ticker', token.get('symbol', 'UNKNOWN'))
            
            # Skip if we already have a position
            if address in self.positions:
                return
            
            # Skip if not enough balance
            max_investment = self.config.get('max_investment_per_token', 0.1)
            if self.balance < max_investment:
                return
            
            # Analyze token
            if self.token_scanner.token_analyzer:
                analysis = await self.token_scanner.token_analyzer.analyze_token(address)
                
                if analysis.get('buy_recommendation', False):
                    logger.info(f"✅ Buy signal for {ticker} ({address[:8]}...)")
                    logger.info(f"   Reasons: {', '.join(analysis.get('reasons', []))}")
                    
                    # Execute buy
                    amount = min(max_investment, self.balance * 0.1)  # Max 10% of balance
                    await self.buy_token(address, amount)
                else:
                    logger.debug(f"❌ No buy signal for {ticker}")
            else:
                # If no analyzer, use simple criteria
                price_change_24h = token.get('price_change_24h', 0)
                volume_24h = token.get('volume_24h', 0)
                
                if price_change_24h > 5 and volume_24h > 10000:
                    logger.info(f"✅ Simple buy signal for {ticker} (24h: +{price_change_24h:.1f}%)")
                    amount = min(max_investment, self.balance * 0.1)
                    await self.buy_token(address, amount)
                    
        except Exception as e:
            logger.error(f"Error analyzing token: {e}")
    
    async def buy_token(self, address: str, amount: float):
        """Buy a token"""
        try:
            # Execute trade
            tx_hash = await self.trader.buy_token(address, amount)
            
            if tx_hash:
                # Update balance
                self.balance -= amount
                
                # Track position
                self.positions[address] = {
                    'amount': amount,
                    'entry_time': datetime.now(timezone.utc),
                    'entry_price': 0.0001  # Would get from token data
                }
                
                logger.info(f"✅ Successfully bought {amount} SOL of {address[:8]}...")
                logger.info(f"   TX: {tx_hash}")
                
        except Exception as e:
            logger.error(f"Error buying token: {e}")
    
    async def monitor_positions(self):
        """Monitor existing positions for exit signals"""
        try:
            if not self.positions:
                return
            
            for address, position in list(self.positions.items()):
                # Get current token data
                if self.token_scanner.birdeye_api:
                    token_info = await self.token_scanner.birdeye_api.get_token_info(address)
                    
                    if token_info:
                        current_price = token_info.get('price_usd', 0)
                        entry_price = position.get('entry_price', 0.0001)
                        
                        if entry_price > 0:
                            pnl_pct = ((current_price / entry_price) - 1) * 100
                            
                            # Check exit conditions
                            take_profit = self.config.get('take_profit_target', 1.15)
                            stop_loss = self.config.get('stop_loss_percentage', 0.05)
                            
                            if current_price >= entry_price * take_profit:
                                logger.info(f"🎯 Take profit hit for {address[:8]}... (+{pnl_pct:.1f}%)")
                                await self.sell_token(address, position['amount'])
                            elif current_price <= entry_price * (1 - stop_loss):
                                logger.info(f"🛑 Stop loss hit for {address[:8]}... ({pnl_pct:.1f}%)")
                                await self.sell_token(address, position['amount'])
                                
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
    
    async def sell_token(self, address: str, amount: float):
        """Sell a token"""
        try:
            tx_hash = await self.trader.sell_token(address, amount)
            
            if tx_hash:
                # Update balance (simplified - would calculate actual return)
                self.balance += amount * 1.1  # Assume 10% profit for simulation
                
                # Remove position
                if address in self.positions:
                    del self.positions[address]
                
                logger.info(f"✅ Successfully sold {amount} SOL of {address[:8]}...")
                
        except Exception as e:
            logger.error(f"Error selling token: {e}")
    
    async def stop(self):
        """Stop the trading bot"""
        logger.info("Stopping trading bot...")
        self.running = False
