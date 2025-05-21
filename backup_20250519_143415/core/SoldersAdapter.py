"""
SoldersAdapter class that works with your existing solders_adapter.py
"""
import os
import sys
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Make sure we can find the solders_adapter module
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import from your existing solders_adapter module
try:
    import solders_adapter
    from solders_adapter import (
        HAS_SOLDERS, 
        PublicKey,
        create_keypair_from_secret,
        get_balance,
        get_sol_price
    )
    logger.info("Successfully imported from solders_adapter module")
except ImportError as e:
    logger.error(f"Failed to import from solders_adapter module: {e}")
    # Define fallbacks for critical elements if import fails
    HAS_SOLDERS = False
    
    class PublicKey:
        def __init__(self, address):
            self.address = address
            
        def __str__(self):
            return self.address
    
# Create the SoldersAdapter class that's expected by main.py
class SoldersAdapter:
    """
    Adapter for Solders packages to interact with Solana blockchain
    """
    
    def __init__(self):
        """Initialize the adapter"""
        self.client = None
        self.keypair = None
        self.wallet_address = None
        
    def init_wallet(self, private_key=None):
        """Initialize wallet from private key"""
        if not private_key:
            logger.warning("No private key provided")
            return False
            
        try:
            # Use the create_keypair_from_secret function from solders_adapter
            self.keypair = create_keypair_from_secret(private_key)
            
            if self.keypair:
                self.wallet_address = str(self.keypair.pubkey())
                return True
            else:
                logger.error("Failed to create keypair")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize wallet: {e}")
            return False
    
    def get_wallet_address(self):
        """Get wallet address"""
        return self.wallet_address
    
    def get_wallet_balance(self):
        """Get wallet SOL balance"""
        if not self.wallet_address:
            return 0.0
            
        try:
            # Use the get_balance function from solders_adapter
            # We'll use a default RPC URL if none is provided
            rpc_endpoint = "https://api.mainnet-beta.solana.com"
            return get_balance(self.wallet_address, rpc_endpoint)
        except Exception as e:
            logger.error(f"Failed to get wallet balance: {e}")
            return 0.0
    
    def get_sol_price(self):
        """Get current SOL price in USD"""
        try:
            # Use the get_sol_price function from solders_adapter
            return get_sol_price()
        except Exception as e:
            logger.error(f"Failed to get SOL price: {e}")
            return 0.0

# Test the adapter if run directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Testing SoldersAdapter...")
    
    adapter = SoldersAdapter()
    print(f"Created SoldersAdapter instance: {adapter}")
    
    # Test SOL price
    price = adapter.get_sol_price()
    print(f"Current SOL price: ${price}")
    
    print("Adapter test completed")