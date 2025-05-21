import os
import time
import random
import logging
import asyncio
from datetime import datetime, timedelta, timezone

# Import your configuration
from config import BotConfiguration

# Simulation-only version without real trading dependencies
# This will work even if Solana packages aren't installed

# Set up logging
logger = logging.getLogger(__name__)

class SolanaTrader:
    """
    SolanaTrader class for executing trades on Solana blockchain
    """
    
    def __init__(self, db, simulation_mode=True):
        """
        Initialize Solana trader
        
        :param db: Database instance
        :param simulation_mode: Whether to run in simulation mode (default: True)
        """
        self.db = db
        # Force simulation mode as this is a simulation-only version
        self.simulation_mode = True
        if not simulation_mode:
            logger.warning("Requested real trading mode, but using simulation-only version.")
            logger.warning("Install Solana packages to enable real trading mode.")
            
        self.connected = False
        self.cached_token_info = {}
        self.wallet_balance_sol = 10.0  # Default starting balance in simulation mode
        self.last_wallet_update = datetime.now(timezone.utc)
        
    async def connect(self):
        """
        Connect to Solana network
        """
        try:
            # In simulation mode, just pretend to connect
            logger.info("SIMULATION: Connected to Solana network")
            self.connected = True
            return True
                
        except Exception as e:
            logger.error(f"Error connecting to Solana network: {e}")
            self.connected = False
            return False
    
    async def get_sol_price(self):
        """
        Get current SOL price in USD
        
        :return: SOL price in USD
        """
        try:
            # Return a simulated SOL price between $20-100
            return random.uniform(20, 100)
                
        except Exception as e:
            logger.error(f"Error getting SOL price: {e}")
            return 50.0  # default fallback
    
    async def get_wallet_balance(self):
        """
        Get wallet balance in SOL and USD
        
        :return: Tuple (sol_balance, usd_balance)
        """
        try:
            # In simulation mode, calculate balance based on trades
            now = datetime.now(timezone.utc)
            
            # If it's been more than an hour since last update, simulate market movements
            if (now - self.last_wallet_update).total_seconds() > 3600:
                # Simulate small random change in balance (±5%)
                change_pct = random.uniform(-0.05, 0.05)
                self.wallet_balance_sol += self.wallet_balance_sol * change_pct
                self.last_wallet_update = now
            
            # Get SOL price for USD conversion
            sol_price_usd = await self.get_sol_price()
            usd_balance = self.wallet_balance_sol * sol_price_usd
            
            return self.wallet_balance_sol, usd_balance
        
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            return 0.0, 0.0  # default fallback
    
    async def monitor_positions(self):
        """
        Monitor positions for take profit and stop loss conditions
        """
        logger.info("Starting position monitoring")
        try:
            while True:
                if not self.connected:
                    await self.connect()
                
                # Get active positions
                positions = self.get_active_positions()
                if positions:
                    logger.info(f"Monitoring {len(positions)} active positions")
                    
                    for contract_address, position in positions.items():
                        # Get current token info to check price
                        token_info = await self.get_token_info(contract_address)
                        if not token_info:
                            logger.warning(f"Could not get info for token {contract_address}")
                            continue
                        
                        buy_price = position.get('buy_price', 0)
                        buy_amount = position.get('amount', 0)
                        
                        if buy_price <= 0 or buy_amount <= 0:
                            logger.warning(f"Invalid position data for {contract_address}")
                            continue
                        
                        # Check if take profit or stop loss conditions are met
                        if self.is_take_profit(contract_address):
                            logger.info(f"Take profit triggered for {contract_address}")
                            # Execute sell
                            await self.execute_trade(contract_address, 'SELL', buy_amount)
                            
                        elif self.is_stop_loss(contract_address):
                            logger.info(f"Stop loss triggered for {contract_address}")
                            # Execute sell
                            await self.execute_trade(contract_address, 'SELL', buy_amount)
                
                # Sleep before next check
                await asyncio.sleep(60)  # Check every minute
                
        except asyncio.CancelledError:
            logger.info("Position monitoring task cancelled")
        except Exception as e:
            logger.error(f"Error in monitor_positions: {e}")
    
    async def close(self):
        """
        Close connections and clean up resources
        """
        logger.info("Closing SolanaTrader connections")
        try:
            self.connected = False
            return True
        except Exception as e:
            logger.error(f"Error closing connections: {e}")
            return False
    
    def get_active_positions(self):
        """
        Get active trading positions
        
        :return: Dictionary of active positions
        """
        try:
            # Get trade history from database
            trades = self.db.get_trade_history()
            
            # Track active positions
            positions = {}
            
            for trade in trades:
                contract_address = trade.get('contract_address')
                action = trade.get('action')
                amount = trade.get('amount', 0)
                price = trade.get('price', 0)
                
                if action == 'BUY':
                    # Add to position
                    if contract_address not in positions:
                        positions[contract_address] = {
                            'amount': amount,
                            'buy_price': price,
                            'timestamp': trade.get('timestamp')
                        }
                    else:
                        # Average out the buy price
                        current = positions[contract_address]
                        total_amount = current['amount'] + amount
                        avg_price = ((current['amount'] * current['buy_price']) + (amount * price)) / total_amount
                        positions[contract_address] = {
                            'amount': total_amount,
                            'buy_price': avg_price,
                            'timestamp': trade.get('timestamp')
                        }
                        
                elif action == 'SELL':
                    # Remove from position
                    if contract_address in positions:
                        current = positions[contract_address]
                        remaining = current['amount'] - amount
                        
                        if remaining <= 0:
                            # Position closed
                            del positions[contract_address]
                        else:
                            # Update remaining position
                            positions[contract_address]['amount'] = remaining
            
            return positions
            
        except Exception as e:
            logger.error(f"Error getting active positions: {e}")
            return {}
    
    def is_take_profit(self, contract_address):
        """
        Check if a take profit condition is met
        
        :param contract_address: Token contract address
        :return: True if take profit condition is met, False otherwise
        """
        # In simulation mode, use random chance
        return random.random() < 0.25  # 25% chance of take profit
    
    def is_stop_loss(self, contract_address):
        """
        Check if a stop loss condition is met
        
        :param contract_address: Token contract address
        :return: True if stop loss condition is met, False otherwise
        """
        # In simulation mode, use random chance
        return random.random() < 0.15  # 15% chance of stop loss
            
    async def execute_trade(self, contract_address, action, amount=None):
        """
        Execute a trade transaction
        
        :param contract_address: Token contract address
        :param action: Trade action (BUY/SELL)
        :param amount: Trade amount in SOL (optional, will use configured range if not specified)
        :return: Transaction hash or None if failed
        """
        if not self.connected:
            await self.connect()
        
        try:
            # Override the amount if not specified
            if action.upper() == 'BUY' and amount is None:
                # Use random value between min and max configured investment
                min_investment = BotConfiguration.TRADING_PARAMETERS['MIN_INVESTMENT_PER_TOKEN']
                max_investment = BotConfiguration.TRADING_PARAMETERS['MAX_INVESTMENT_PER_TOKEN']
                amount = random.uniform(min_investment, max_investment)
                amount = round(amount, 4)  # Round to 4 decimal places
            
            # For SELL actions, if amount is not specified, use 
            # all available tokens (from positions)
            if action.upper() == 'SELL' and amount is None:
                positions = self.get_active_positions()
                if contract_address in positions:
                    pos = positions[contract_address]
                    amount = pos.get('amount', 0.5)
                else:
                    # Default to 0.5 if no position found
                    amount = 0.5
            
            # Generate price simulation for buy or sell
            token_price = None
            gain_loss_sol = 0.0
            percentage_change = 0.0
            price_multiple = 1.0
            
            if action.upper() == 'BUY':
                # Use realistic token price based on SOL price
                token_price = random.uniform(1e-9, 1e-6)
                
                # Update wallet balance
                self.wallet_balance_sol -= amount
                
            elif action.upper() == 'SELL':
                # For sell, need to look up the buy price from positions
                positions = self.get_active_positions()
                if contract_address in positions:
                    pos = positions[contract_address]
                    buy_price = pos.get('buy_price', 0.0)
                    
                    # If we have a take profit, calculate price based on that
                    if self.is_take_profit(contract_address):
                        # Calculate a selling price based on take profit
                        tp_multiple = BotConfiguration.TRADING_PARAMETERS['TAKE_PROFIT_TARGET']
                        token_price = buy_price * random.uniform(tp_multiple, tp_multiple * 1.2)
                        
                        # Calculate gain/loss
                        price_multiple = token_price / buy_price if buy_price > 0 else 1.0
                        percentage_change = (price_multiple - 1) * 100
                        buy_value = amount * buy_price
                        sell_value = amount * token_price
                        gain_loss_sol = sell_value - buy_value
                        
                    # If we have a stop loss, calculate price based on that
                    elif self.is_stop_loss(contract_address):
                        # Calculate a selling price based on stop loss
                        sl_percentage = BotConfiguration.TRADING_PARAMETERS['STOP_LOSS_PERCENTAGE']
                        token_price = buy_price * (1 - random.uniform(sl_percentage, sl_percentage * 1.2))
                        
                        # Calculate gain/loss
                        price_multiple = token_price / buy_price if buy_price > 0 else 1.0
                        percentage_change = (price_multiple - 1) * 100
                        buy_value = amount * buy_price
                        sell_value = amount * token_price
                        gain_loss_sol = sell_value - buy_value
                    else:
                        # Random price movement between 0.5x and 3x
                        token_price = buy_price * random.uniform(0.5, 3.0)
                        
                        # Calculate gain/loss
                        price_multiple = token_price / buy_price if buy_price > 0 else 1.0
                        percentage_change = (price_multiple - 1) * 100
                        buy_value = amount * buy_price
                        sell_value = amount * token_price
                        gain_loss_sol = sell_value - buy_value
                        
                    # Update wallet balance
                    self.wallet_balance_sol += amount + gain_loss_sol
                else:
                    # No position found, use a random price
                    token_price = random.uniform(1e-9, 1e-6)
            
            # Create a simulated transaction hash
            timestamp = int(time.time())
            tx_hash = f"SIM_{action.upper()}_{contract_address[:10]}_{timestamp}"
            
            # Log the simulation
            ticker = "Unknown"
            if contract_address in self.cached_token_info:
                ticker = self.cached_token_info[contract_address].get('ticker', 'Unknown')
            
            logger.info(f"SIMULATION: {action.upper()} {amount} SOL of ${ticker} ({contract_address}) at {token_price} tokens/SOL")
            
            # Record in database
            self.db.record_trade(
                contract_address=contract_address,
                action=action.upper(),
                amount=amount,
                price=token_price,
                tx_hash=tx_hash,
                gain_loss_sol=gain_loss_sol,
                percentage_change=percentage_change,
                price_multiple=price_multiple
            )
            
            # Return the simulated tx hash
            return tx_hash
                
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return None
            
    async def get_token_info(self, contract_address):
        """
        Get information about a token
        
        :param contract_address: Token contract address
        :return: Dictionary containing token information
        """
        try:
            # First check cache
            if contract_address in self.cached_token_info:
                return self.cached_token_info[contract_address]
                
            # Check database
            token_info = self.db.get_token(contract_address)
            if token_info:
                self.cached_token_info[contract_address] = token_info
                return token_info
                
            # Generate random token data
            ticker = f"${contract_address[:4].upper()}"
            name = f"Simulated Token {contract_address[:6]}"
            
            # Generate launch date between 1-90 days ago
            days_ago = random.randint(1, 90)
            launch_date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
            
            # Generate random metrics
            safety_score = random.uniform(0, 100)
            volume_24h = random.uniform(1000, 1000000)
            price_usd = random.uniform(1e-9, 1e-6)
            liquidity_usd = random.uniform(10000, 1000000)
            mcap = random.uniform(100000, 10000000)
            holders = random.randint(100, 10000)
            liquidity_locked = random.choice([True, False])
            
            token_info = {
                'contract_address': contract_address,
                'ticker': ticker,
                'name': name,
                'launch_date': launch_date,
                'safety_score': safety_score,
                'volume_24h': volume_24h,
                'price_usd': price_usd,
                'liquidity_usd': liquidity_usd,
                'mcap': mcap,
                'holders': holders,
                'liquidity_locked': liquidity_locked,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            # Store in database and cache
            self.db.store_token(token_info)
            self.cached_token_info[contract_address] = token_info
            
            return token_info
                
        except Exception as e:
            logger.error(f"Error getting token info for {contract_address}: {e}")
            return None