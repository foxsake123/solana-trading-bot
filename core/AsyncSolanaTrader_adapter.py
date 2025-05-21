"""
Simplified AsyncSolanaTrader_adapter that works with the simplified SolanaTrader
"""
import os
import sys
import logging
import asyncio

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('simplified_async_adapter')

# Try to import the SolanaTrader
try:
    from core.simplified_solana_trader import SolanaTrader as OriginalSolanaTrader
    logger.info("Successfully imported simplified SolanaTrader")
except ImportError as e:
    logger.error(f"Failed to import simplified SolanaTrader: {e}")
    
    # Create a placeholder if import fails
    class OriginalSolanaTrader:
        def __init__(self, **kwargs):
            logger.error("Using placeholder SolanaTrader")
            self.simulation_mode = kwargs.get('simulation_mode', True)
            self.db = kwargs.get('db', None)
            self.private_key = kwargs.get('private_key', None)
            self.rpc_endpoint = kwargs.get('rpc_url', None)
            
        async def connect(self):
            logger.error("Placeholder connect method")
            return False
            
        async def get_wallet_balance(self):
            logger.error("Placeholder get_wallet_balance method")
            return 0.0, 0.0
            
        def get_wallet_address(self):
            logger.error("Placeholder get_wallet_address method")
            return "PLACEHOLDER_WALLET_ADDRESS"
            
        async def buy_token(self, contract_address, amount):
            logger.error("Placeholder buy_token method")
            return "PLACEHOLDER_TX_HASH"
            
        async def sell_token(self, contract_address, amount):
            logger.error("Placeholder sell_token method")
            return "PLACEHOLDER_TX_HASH"
            
        async def start_position_monitoring(self):
            logger.error("Placeholder start_position_monitoring method")
            return False
            
        async def close(self):
            logger.error("Placeholder close method")
            return False

class SolanaTrader:
    """
    Adapter class for SolanaTrader
    """
    
    def __init__(self, private_key=None, rpc_url=None, **kwargs):
        """
        Initialize with parameters needed by the simplified SolanaTrader
        """
        self.private_key = private_key
        self.rpc_url = rpc_url
        self.simulation_mode = kwargs.get('simulation_mode', True)
        self.db = kwargs.get('db', None)
        
        # Create the original trader instance
        self.trader = OriginalSolanaTrader(
            db=self.db,
            simulation_mode=self.simulation_mode,
            private_key=private_key,
            rpc_url=rpc_url
        )
        
        logger.info(f"Initialized simplified AsyncSolanaTrader adapter (simulation_mode={self.simulation_mode})")
    
    async def connect(self):
        """Connect to the Solana network"""
        return await self.trader.connect()
    
    async def get_wallet_balance(self):
        """
        Get wallet balance in SOL and USD
        
        :return: Tuple of (SOL balance, USD balance)
        """
        return await self.trader.get_wallet_balance()
    
    def get_wallet_address(self):
        """
        Get the wallet address
        
        :return: Wallet address string
        """
        return self.trader.get_wallet_address()
    
    async def buy_token(self, contract_address, amount):
        """
        Buy a token
        
        :param contract_address: Token contract address
        :param amount: Amount in SOL to spend
        :return: Transaction hash
        """
        return await self.trader.buy_token(contract_address, amount)
    
    async def sell_token(self, contract_address, amount):
        """
        Sell a token
        
        :param contract_address: Token contract address
        :param amount: Amount to sell
        :return: Transaction hash
        """
        return await self.trader.sell_token(contract_address, amount)
    
    async def start_position_monitoring(self):
        """Start position monitoring"""
        return await self.trader.start_position_monitoring()
    
    async def close(self):
        """Close connections"""
        return await self.trader.close()
    
    def __getattr__(self, name):
        """
        Forward attribute access to the original trader
        
        :param name: Attribute name
        :return: Attribute from original trader
        """
        if hasattr(self.trader, name):
            attr = getattr(self.trader, name)
            
            # If it's an async method, ensure we maintain async compatibility
            if callable(attr) and asyncio.iscoroutinefunction(attr):
                return attr
                
            return attr
            
        raise AttributeError(f"'AsyncSolanaTrader' has no attribute '{name}'")
