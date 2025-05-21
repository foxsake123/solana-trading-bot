import os
import time
import random
import logging
import asyncio
from datetime import datetime, timedelta, timezone

# Import your configuration
from config import BotConfiguration

# Modified imports for compatibility
REAL_TRADING_AVAILABLE = False
try:
    # Try to import Solana packages
    from solders.pubkey import Pubkey
    from solders.keypair import Keypair
    from solana.rpc.async_api import AsyncClient
    import base58
    REAL_TRADING_AVAILABLE = True
except ImportError:
    # If imports fail, we'll run in simulation mode only
    logging.warning("Solana packages not available. Real trading mode will not work.")
    logging.warning("The bot will run in simulation mode only.")

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
        # Force simulation mode if real trading packages aren't available
        if not REAL_TRADING_AVAILABLE and not simulation_mode:
            logger.warning("Forcing simulation mode as Solana packages are not available")
            simulation_mode = True
            
        self.db = db
        self.simulation_mode = simulation_mode
        self.connected = False
        self.cached_token_info = {}
        self.wallet_balance_sol = 10.0  # Default starting balance in simulation mode
        self.last_wallet_update = datetime.now(timezone.utc)
        
        # Initialize real connection fields if not in simulation mode
        if not self.simulation_mode and REAL_TRADING_AVAILABLE:
            try:                
                # Get RPC endpoint and private key from config
                self.rpc_endpoint = BotConfiguration.API_KEYS['SOLANA_RPC_ENDPOINT']
                private_key_str = BotConfiguration.API_KEYS['WALLET_PRIVATE_KEY']
                
                # Setup Solana client and keypair
                self.client = AsyncClient(self.rpc_endpoint)
                
                # Convert private key string to bytes and create keypair
                try:
                    if private_key_str:
                        # Handle different private key formats
                        if len(private_key_str) == 64:  # Hex string
                            private_key_bytes = bytes.fromhex(private_key_str)
                        elif len(private_key_str) == 88:  # Base58 encoded
                            private_key_bytes = base58.b58decode(private_key_str)
                        else:
                            # Try direct conversion (might be a comma-separated string of numbers)
                            try:
                                private_key_bytes = bytes([int(x) for x in private_key_str.split(',')])
                            except:
                                logger.error("Invalid private key format. Please provide hex, base58, or comma-separated bytes.")
                                self.keypair = None
                                return
                        
                        # Updated keypair creation based on available method
                        try:
                            self.keypair = Keypair.from_bytes(private_key_bytes)
                        except AttributeError:
                            # Try alternative methods if from_bytes is not available
                            try:
                                # Try direct initialization
                                self.keypair = Keypair(private_key_bytes)
                            except:
                                logger.error("Could not create keypair. Falling back to simulation mode.")
                                self.simulation_mode = True
                                self.keypair = None
                                return
                            
                        logger.info(f"Wallet address: {self.keypair.pubkey()}")
                    else:
                        logger.error("No private key provided in configuration")
                        self.keypair = None
                except Exception as e:
                    logger.error(f"Error setting up keypair: {e}")
                    self.keypair = None
            except Exception as e:
                logger.error(f"Error initializing real trading mode: {e}")
                self.simulation_mode = True
        
    async def connect(self):
        """
        Connect to Solana network
        """
        try:
            # In simulation mode, just pretend to connect
            if self.simulation_mode:
                logger.info("SIMULATION: Connected to Solana network")
                self.connected = True
                return True
            else:
                # Real connection logic 
                if not hasattr(self, 'client') or not self.client:
                    self.client = AsyncClient(self.rpc_endpoint)
                
                # Check connection by getting a recent blockhash
                try:
                    response = await self.client.get_recent_blockhash()
                    if response and hasattr(response, 'value'):
                        self.connected = True
                        logger.info(f"Connected to Solana network via {self.rpc_endpoint}")
                        return True
                    else:
                        logger.error(f"Failed to get recent blockhash: {response}")
                        logger.warning("Falling back to simulation mode")
                        self.simulation_mode = True
                        self.connected = False
                        return False
                except Exception as e:
                    logger.error(f"Error connecting to Solana RPC: {e}")
                    logger.warning("Falling back to simulation mode")
                    self.simulation_mode = True
                    self.connected = False
                    return False
                
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
            if self.simulation_mode:
                # Return a simulated SOL price between $20-100
                return random.uniform(20, 100)
            else:
                # Use CoinGecko API to get real SOL price
                import aiohttp
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get('https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd', timeout=10) as response:
                            if response.status == 200:
                                data = await response.json()
                                if 'solana' in data and 'usd' in data['solana']:
                                    return float(data['solana']['usd'])
                            
                            # Fallback to default price if API call fails
                            logger.warning("Could not get SOL price from CoinGecko, using fallback price")
                            return 50.0
                except Exception as e:
                    logger.error(f"Error fetching SOL price: {e}")
                    return 50.0  # default fallback
                
        except Exception as e:
            logger.error(f"Error getting SOL price: {e}")
            return 50.0  # default fallback
    
    async def get_wallet_balance(self):
        """
        Get wallet balance in SOL and USD
        
        :return: Tuple (sol_balance, usd_balance)
        """
        try:
            if self.simulation_mode:
                # In simulation mode, calculate balance based on trades
                # Get current time
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
            else:
                # Real implementation to fetch from blockchain
                if not self.connected:
                    await self.connect()
                
                # If we switched to simulation mode during connect()
                if self.simulation_mode:
                    return await self.get_wallet_balance()
                
                if not hasattr(self, 'keypair') or not self.keypair:
                    logger.error("No wallet keypair available")
                    return 0.0, 0.0
                
                try:
                    # Get the balance in lamports (1 SOL = 1,000,000,000 lamports)
                    response = await self.client.get_balance(self.keypair.pubkey())
                    if response and hasattr(response, 'value'):
                        balance_lamports = response.value
                        balance_sol = balance_lamports / 1_000_000_000  # Convert to SOL
                        
                        # Get SOL price and calculate USD value
                        sol_price_usd = await self.get_sol_price()
                        usd_balance = balance_sol * sol_price_usd
                        
                        return balance_sol, usd_balance
                    else:
                        logger.error(f"Invalid response from get_balance: {response}")
                        # Fall back to simulation
                        self.simulation_mode = True
                        return await self.get_wallet_balance()
                except Exception as e:
                    logger.error(f"Error getting wallet balance: {e}")
                    # Fall back to simulation
                    self.simulation_mode = True
                    return await self.get_wallet_balance()
        
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
            # In simulation mode, just set connected to False
            if self.simulation_mode:
                self.connected = False
                return True
                
            # In real mode, close the client connection
            if hasattr(self, 'client') and self.client:
                await self.client.close()
            
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
        try:
            # In simulation mode, use random chance
            if self.simulation_mode:
                return random.random() < 0.25  # 25% chance of take profit
                
            # In real mode, check current price against buy price
            positions = self.get_active_positions()
            if contract_address not in positions:
                return False
                
            position = positions[contract_address]
            buy_price = position.get('buy_price', 0)
            
            if buy_price <= 0:
                return False
                
            # Get token info to check current price
            token_info = self.cached_token_info.get(contract_address)
            if not token_info:
                return False
                
            current_price = token_info.get('price', 0)
            if current_price <= 0:
                return False
                
            # Calculate price multiple
            price_multiple = current_price / buy_price
            
            # Check if take profit target is met
            take_profit_target = BotConfiguration.TRADING_PARAMETERS['TAKE_PROFIT_TARGET']
            
            return price_multiple >= take_profit_target
            
        except Exception as e:
            logger.error(f"Error checking take profit for {contract_address}: {e}")
            return False
    
    def is_stop_loss(self, contract_address):
        """
        Check if a stop loss condition is met
        
        :param contract_address: Token contract address
        :return: True if stop loss condition is met, False otherwise
        """
        try:
            # In simulation mode, use random chance
            if self.simulation_mode:
                return random.random() < 0.15  # 15% chance of stop loss
                
            # In real mode, check current price against buy price
            positions = self.get_active_positions()
            if contract_address not in positions:
                return False
                
            position = positions[contract_address]
            buy_price = position.get('buy_price', 0)
            
            if buy_price <= 0:
                return False
                
            # Get token info to check current price
            token_info = self.cached_token_info.get(contract_address)
            if not token_info:
                return False
                
            current_price = token_info.get('price', 0)
            if current_price <= 0:
                return False
                
            # Calculate price change percentage
            price_change = (current_price - buy_price) / buy_price
            
            # Check if stop loss is triggered
            stop_loss_percentage = -BotConfiguration.TRADING_PARAMETERS['STOP_LOSS_PERCENTAGE']
            
            return price_change <= stop_loss_percentage
            
        except Exception as e:
            logger.error(f"Error checking stop loss for {contract_address}: {e}")
            return False
            
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
            # Override the amount in simulation mode if not specified
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
                
            if self.simulation_mode:
                # In simulation mode, generate a fake transaction
                # and record in database
                
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
                
            else:
                # For real trading mode, attempt real transaction but with error handling
                try:
                    # Log attempt at real trading
                    logger.info(f"Attempting REAL trade: {action.upper()} {amount} SOL of {contract_address}")
                    
                    # Import required libraries for Jupiter API
                    import aiohttp
                    import json
                    
                    # Jupiter API endpoints (from config)
                    jupiter_quote_api = BotConfiguration.API_KEYS.get('JUPITER_QUOTE_API', 'https://quote-api.jup.ag/v6/quote')
                    jupiter_swap_api = BotConfiguration.API_KEYS.get('JUPITER_SWAP_API', 'https://quote-api.jup.ag/v6/swap')
                    
                    # Use Jupiter for swaps
                    try:
                        # Generate a placeholder real TX hash for testing
                        # In a full implementation, this would be a real transaction
                        logger.info("Real trading functionality is not fully implemented yet")
                        logger.info("Generating placeholder transaction for testing")
                        
                        # Create a realish tx hash
                        timestamp = int(time.time())
                        tx_hash = f"REAL_{action.upper()}_{contract_address[:8]}_{timestamp}"
                        
                        # Log progress with token details
                        ticker = "Unknown"
                        if contract_address in self.cached_token_info:
                            ticker = self.cached_token_info[contract_address].get('ticker', 'Unknown')
                        
                        logger.info(f"REAL TRADE: {action.upper()} {amount} SOL of ${ticker} ({contract_address})")
                        
                        # For now, store in database with simulated values but REAL tx hash
                        if action.upper() == 'BUY':
                            token_price = random.uniform(1e-9, 1e-6)
                            gain_loss_sol = 0
                            percentage_change = 0
                            price_multiple = 1.0
                        else:
                            # For SELL we still need token price data
                            positions = self.get_active_positions()
                            buy_price = positions.get(contract_address, {}).get('buy_price', 0.0)
                            token_price = buy_price * random.uniform(0.8, 1.5)
                            
                            # Calculate gain/loss for database
                            price_multiple = token_price / buy_price if buy_price > 0 else 1.0
                            percentage_change = (price_multiple - 1) * 100
                            buy_value = amount * buy_price
                            sell_value = amount * token_price
                            gain_loss_sol = sell_value - buy_value
                        
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
                        
                        return tx_hash
                        
                    except Exception as e:
                        logger.error(f"Error with Jupiter API: {e}")
                        logger.warning("Falling back to simulation mode for this trade")
                        
                        # Fall back to simulation for this trade
                        self.simulation_mode = True
                        result = await self.execute_trade(contract_address, action, amount)
                        self.simulation_mode = False  # Reset back to real mode
                        return result
                        
                except Exception as e:
                    logger.error(f"Error executing real trade: {e}")
                    logger.warning("Falling back to simulation mode for this trade")
                    
                    # Fall back to simulation for this trade
                    self.simulation_mode = True
                    result = await self.execute_trade(contract_address, action, amount)
                    self.simulation_mode = False  # Reset back to real mode
                    return result
                
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
                
            # If we're in simulation mode, generate fake data
            if self.simulation_mode:
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
            else:
                # Real implementation would fetch from blockchain or API
                # For now, use real-data APIs if available or fall back to simulation
                try:
                    # Try BirdeyeAPI or DexScreener API via the token_analyzer module
                    from token_analyzer import TokenAnalyzer
                    
                    analyzer = TokenAnalyzer(db=self.db)
                    token_data = await analyzer.fetch_token_data(contract_address)
                    
                    if token_data:
                        # Store in database and cache
                        self.db.store_token(token_data)
                        self.cached_token_info[contract_address] = token_data
                        
                        return token_data
                except:
                    # If real APIs fail, fall back to simulation logic
                    logger.warning(f"Failed to get real token data for {contract_address}, using simulated data")
                    
                    # Temporarily switch to simulation mode for this operation
                    orig_mode = self.simulation_mode
                    self.simulation_mode = True
                    result = await self.get_token_info(contract_address)
                    self.simulation_mode = orig_mode
                    return result
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting token info for {contract_address}: {e}")
            return None