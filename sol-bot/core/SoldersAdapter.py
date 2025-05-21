"""
SoldersAdapter.py - Wrapper for Solders functionality for Solana blockchain interaction
"""

import os
import json
import base58
import logging
from typing import Dict, Optional, Any, Union, Tuple
import traceback

# Set up logging
logger = logging.getLogger(__name__)

# Import Solders modules with robust error handling
try:
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    HAS_SOLDERS = True
    logger.info("Successfully imported Solders packages")
except ImportError as e:
    logger.warning(f"Solders import error: {e}")
    HAS_SOLDERS = False
    
class SoldersAdapter:
    """
    Adapter class for Solders functionality to interact with Solana blockchain
    """
    
    def __init__(self):
        """Initialize the adapter"""
        self.keypair = None
        self.wallet_address = None
        self.rpc_endpoint = os.getenv('SOLANA_RPC_ENDPOINT', 'https://api.mainnet-beta.solana.com')
    
    def init_wallet(self, private_key: str) -> bool:
        """
        Initialize wallet from private key
        
        Args:
            private_key: Private key as string (hex or base58)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not private_key:
            logger.warning("No private key provided")
            return False
            
        if not HAS_SOLDERS:
            logger.warning("Solders not available, wallet initialization skipped")
            self.wallet_address = "SIMULATED_WALLET"
            return False
            
        try:
            # First try to handle as base58 encoded private key
            try:
                if len(private_key) == 88:  # Base58 encoded
                    seed = base58.b58decode(private_key)
                    self.keypair = Keypair.from_bytes(seed)
                elif len(private_key) == 64:  # Hex string
                    # Try as seed first
                    seed = bytes.fromhex(private_key)
                    self.keypair = Keypair.from_seed(seed)
                else:
                    raise ValueError(f"Unsupported private key format, length: {len(private_key)}")
                    
                # Set wallet address
                self.wallet_address = str(self.keypair.pubkey())
                logger.info(f"Wallet initialized with address: {self.wallet_address}")
                return True
                
            except Exception as e:
                logger.error(f"Error initializing wallet: {e}")
                logger.error(traceback.format_exc())
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error in init_wallet: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def get_wallet_address(self) -> str:
        """
        Get wallet address
        
        Returns:
            str: Wallet public key as string
        """
        if self.wallet_address:
            return self.wallet_address
            
        if self.keypair and HAS_SOLDERS:
            return str(self.keypair.pubkey())
            
        return "WALLET_NOT_INITIALIZED"
    
    def get_wallet_balance(self) -> float:
        """
        Get wallet balance in SOL
        
        Returns:
            float: Wallet balance in SOL
        """
        if not HAS_SOLDERS or not self.wallet_address:
            logger.warning("Cannot get wallet balance, Solders not available or wallet not initialized")
            return 0.0
            
        try:
            import requests
            
            # Query balance using RPC endpoint
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [self.wallet_address]
            }
            
            headers = {"Content-Type": "application/json"}
            response = requests.post(self.rpc_endpoint, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data and 'value' in data['result']:
                    # Convert lamports to SOL (1 SOL = 10^9 lamports)
                    balance_sol = data['result']['value'] / 10**9
                    return balance_sol
            
            logger.warning(f"Failed to get wallet balance: {response.text if response else 'No response'}")
            return 0.0
        
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            logger.error(traceback.format_exc())
            return 0.0
            
    def get_sol_price(self) -> float:
        """
        Get current SOL price in USD
        
        Returns:
            float: SOL price in USD
        """
        try:
            import requests
            
            # Try CoinGecko API
            response = requests.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd",
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'solana' in data and 'usd' in data['solana']:
                    return float(data['solana']['usd'])
            
            # Try Binance API as backup
            response = requests.get(
                "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT",
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'price' in data:
                    return float(data['price'])
            
            # Fallback value
            logger.warning("Could not fetch SOL price, using fallback value")
            return 175.0
            
        except Exception as e:
            logger.error(f"Error getting SOL price: {e}")
            logger.error(traceback.format_exc())
            return 175.0  # Fallback value