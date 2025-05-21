
# solana_wrapper.py - Compatibility layer for Solana API

import logging
import asyncio
from datetime import datetime
import os
import sys

# Set up logging
logger = logging.getLogger('solana_wrapper')

# Check if Solana libraries are available
try:
    from solders.pubkey import Pubkey
    from solders.keypair import Keypair
    from solana.rpc.async_api import AsyncClient
    from solana.transaction import Transaction
    HAS_SOLANA_LIBS = True
    logger.info("Solana libraries are available")
except ImportError:
    HAS_SOLANA_LIBS = False
    logger.warning("Solana libraries not available, using simulated connection")

async def get_recent_blockhash_compatible(client):
    """Compatibility function for get_recent_blockhash"""
    try:
        # Try new API first
        if hasattr(client, 'get_latest_blockhash'):
            logger.info("Using get_latest_blockhash")
            response = await client.get_latest_blockhash()
            if hasattr(response, 'value'):
                return response.value.blockhash, response.value.last_valid_block_height
            return response, 0
        
        # Fall back to old API
        elif hasattr(client, 'get_recent_blockhash'):
            logger.info("Using get_recent_blockhash")
            return await client.get_recent_blockhash()
        
        # Last resort - mock response
        else:
            logger.warning("Neither get_latest_blockhash nor get_recent_blockhash available, using mock data")
            # Need to create proper mock data
            try:
                from solders.hash import Hash
                mock_hash = Hash([0] * 32)
                return mock_hash, 0
            except ImportError:
                logger.error("Could not create mock hash")
                return None, 0
    except Exception as e:
        logger.error(f"Error getting blockhash: {e}")
        try:
            from solders.hash import Hash
            mock_hash = Hash([0] * 32)
            return mock_hash, 0
        except ImportError:
            logger.error("Could not create mock hash")
            return None, 0

def create_keypair_from_private_key(private_key):
    """Create a keypair from a private key in various formats"""
    if not HAS_SOLANA_LIBS:
        logger.warning("Solana libraries not available, cannot create keypair")
        return None
    
    if not private_key:
        logger.error("No private key provided")
        return None
    
    logger.info(f"Creating keypair from private key (first 6 chars): {private_key[:6]}...")
    
    # Try different methods
    try:
        # Try from_seed with hex string
        if len(private_key) == 64 and all(c in '0123456789abcdefABCDEF' for c in private_key):
            logger.info("Trying from_seed with hex...")
            seed = bytes.fromhex(private_key)
            return Keypair.from_seed(seed[:32])
    except Exception as e:
        logger.warning(f"from_seed with hex failed: {e}")
    
    try:
        # Try from_bytes
        import base58
        try:
            logger.info("Trying from_bytes with base58...")
            seed = base58.b58decode(private_key)
            return Keypair.from_bytes(seed)
        except Exception as e:
            logger.warning(f"from_bytes with base58 failed: {e}")
    except ImportError:
        logger.warning("base58 module not available")
    
    try:
        # Try from_base58_string if available
        if hasattr(Keypair, 'from_base58_string'):
            logger.info("Trying from_base58_string...")
            return Keypair.from_base58_string(private_key)
    except Exception as e:
        logger.warning(f"from_base58_string failed: {e}")
    
    # Last resort - try to create a simulated keypair
    logger.warning("Could not create keypair from private key, using simulated keypair")
    try:
        return Keypair()
    except Exception as e:
        logger.error(f"Error creating simulated keypair: {e}")
        return None

async def connect_to_solana(rpc_endpoint=None):
    """Create a connection to the Solana network"""
    if not HAS_SOLANA_LIBS:
        logger.warning("Solana libraries not available, using simulated connection")
        return "SIMULATED_CONNECTION"
    
    # Use default endpoint if none provided
    if not rpc_endpoint:
        rpc_endpoint = "https://api.mainnet-beta.solana.com"
    
    logger.info(f"Connecting to Solana via {rpc_endpoint}")
    
    try:
        # Create the client with reasonable timeout
        client = AsyncClient(rpc_endpoint, timeout=30)
        
        # Test the connection with a simple request
        try:
            is_connected = await client.is_connected()
            if is_connected:
                logger.info("Successfully connected to Solana network")
                return client
            else:
                logger.error("Failed to connect to Solana network")
                return None
        except Exception as e:
            logger.error(f"Error testing Solana connection: {e}")
            return None
    except Exception as e:
        logger.error(f"Error creating Solana client: {e}")
        return None

async def get_sol_price():
    """Get the current SOL price in USD"""
    try:
        import httpx
        
        # Try CoinGecko API first (more reliable)
        url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            data = response.json()
            price = float(data['solana']['usd'])
            logger.info(f"Got SOL price from CoinGecko: ${price}")
            return price
    except Exception as e:
        logger.error(f"Error getting SOL price from CoinGecko: {e}")
        
        try:
            # Fallback to Binance API
            url = "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                data = response.json()
                price = float(data['price'])
                logger.info(f"Got SOL price from Binance: ${price}")
                return price
        except Exception as e:
            logger.error(f"Error getting SOL price from Binance: {e}")
            
            # Fallback to a reasonable default price
            default_price = 173.0
            logger.warning(f"Using default SOL price: ${default_price}")
            return default_price
