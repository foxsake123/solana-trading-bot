"""
test_real_trading.py - Test real trading functionality
"""
import os
import sys
import logging
import asyncio
import time
import traceback
import json
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('test_real_trading')

# Get the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Add core directory to path
core_dir = os.path.join(project_root, 'core')
if core_dir not in sys.path:
    sys.path.insert(0, core_dir)

# Try to import SoldersAdapter
try:
    try:
        from core.SoldersAdapter import SoldersAdapter
    except ImportError:
        from SoldersAdapter import SoldersAdapter
except ImportError as e:
    logger.error(f"Failed to import SoldersAdapter: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("Failed to import dotenv. Environment variables may not be loaded.")

async def test_real_trading():
    """Test connection to Solana and wallet initialization"""
    logger.info("=== SOLANA TRADING BOT - REAL TRADING TEST ===")
    
    # Initialize SoldersAdapter
    adapter = SoldersAdapter()
    
    # Get wallet private key
    private_key = os.getenv('WALLET_PRIVATE_KEY', '')
    if not private_key:
        logger.warning("WALLET_PRIVATE_KEY environment variable not set")
    
    # Initialize wallet
    wallet_initialized = adapter.init_wallet(private_key)
    
    if wallet_initialized:
        wallet_address = adapter.get_wallet_address()
        logger.info(f"Wallet initialized successfully: {wallet_address}")
        
        # Get wallet balance
        balance = adapter.get_wallet_balance()
        logger.info(f"Wallet balance: {balance:.6f} SOL")
        
        # Get SOL price
        sol_price = adapter.get_sol_price()
        logger.info(f"Current SOL price: ${sol_price:.2f}")
        
        # Calculate USD value
        usd_value = balance * sol_price
        logger.info(f"Wallet value: ${usd_value:.2f}")
    else:
        logger.warning("Wallet initialization failed")
    
    # Test Jupiter API
    logger.info("Testing Jupiter API integration...")
    
    try:
        # Manually test a simple quote request
        usdc_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        sol_address = "So11111111111111111111111111111111111111112"
        amount = "1000000"  # 0.001 SOL in lamports
        slippage_bps = 100  # 1% slippage
        
        # Build query parameters
        params = {
            "inputMint": sol_address,
            "outputMint": usdc_address,
            "amount": amount,
            "slippageBps": slippage_b	ps
        }
        
        quote_endpoint = "https://quote-api.jup.ag/v6/quote"
        
        logger.info(f"Getting Jupiter quote: {sol_address} → {usdc_address}, amount: {amount}, slippage: 1.0%")
        
        response = requests.get(quote_endpoint, params=params, timeout=30)
        
        if response.status_code == 200:
            quote = response.json()
            
            # Extract quote details
            in_amount = quote.get('inAmount', '0')
            out_amount = quote.get('outAmount', '0')
            
            logger.info(f"Quote received: {in_amount} lamports SOL → {out_amount} USDC microtokens")
            logger.info("Jupiter integration working correctly!")
        else:
            logger.error(f"Jupiter API request failed: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error testing Jupiter API: {e}")
        logger.error(traceback.format_exc())
    
    logger.info("=== TEST COMPLETED ===")

if __name__ == "__main__":
    asyncio.run(test_real_trading())