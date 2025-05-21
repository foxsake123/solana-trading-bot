import asyncio
import os
import sys
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('test_real_trading')

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.append(project_dir)

# Add core directory to Python path
core_dir = os.path.join(project_dir, 'core')
if core_dir not in sys.path:
    sys.path.insert(0, core_dir)

# Import required modules
try:
    # Try importing from core directory
    try:
        from core.solana_trader import SolanaTrader
        from core.database import Database
    except ImportError:
        # Try importing from root directory
        from solana_trader import SolanaTrader
        from database import Database
    
    # Import from solders_adapter
    try:
        from core.solders_adapter import JupiterClient
    except ImportError:
        try:
            from solders_adapter import JupiterClient
        except ImportError:
            sys.exit("ERROR: JupiterClient not found. Make sure solders_adapter.py has been updated.")
    
except ImportError as e:
    logger.error(f"Import error: {e}")
    sys.exit(1)

async def test_real_trading():
    """
    Test real trading functionality with minimal amounts
    """
    logger.info("=== SOLANA TRADING BOT - REAL TRADING TEST ===")
    
    # Initialize database
    db = Database()
    
    # Load wallet key from .env
    private_key = None
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('WALLET_PRIVATE_KEY='):
                    private_key = line.split('=', 1)[1].strip().strip("'").strip('"')
    
    if not private_key:
        logger.error("No wallet private key found in .env file")
        logger.info("Please add WALLET_PRIVATE_KEY=your_private_key to your .env file")
        return
    
    # Initialize trader
    trader = SolanaTrader(db=db, simulation_mode=False)
    
    if hasattr(trader, 'set_private_key'):
        trader.set_private_key(private_key)
    
    # Connect to Solana network
    logger.info("Connecting to Solana network...")
    await trader.connect()
    
    # Get wallet balance
    sol_balance, usd_balance = await trader.get_wallet_balance()
    logger.info(f"Wallet balance: {sol_balance:.4f} SOL (${usd_balance:.2f})")
    
    # Get a common token for testing (USDC)
    logger.info("Getting quote for a small USDC swap for testing...")
    usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    # Create Jupiter client
    jupiter = JupiterClient()
    
    # Calculate test amount (very small, 0.001 SOL)
    test_amount = 0.001
    test_lamports = int(test_amount * 1e9)  # Convert to lamports
    
    logger.info(f"Testing swap of {test_amount} SOL to USDC...")
    
    # Get a quote
    quote = await jupiter.get_quote(
        input_mint="So11111111111111111111111111111111111111112",  # SOL
        output_mint=usdc_mint,  # USDC
        amount=test_lamports,
        slippage=1.0  # 1% slippage
    )
    
    if not quote:
        logger.error("Could not get quote. Test failed.")
        return
    
    # Calculate expected output
    out_amount = float(quote.get('outAmount', 0)) / 1000000  # USDC has 6 decimals
    
    logger.info(f"Quote obtained!")
    logger.info(f"Input: {test_amount} SOL")
    logger.info(f"Expected output: {out_amount:.6f} USDC")
    
    # Ask for confirmation
    print("\nWARNING: This will execute a real trade on the Solana blockchain.")
    print(f"You will swap {test_amount} SOL for approximately {out_amount:.6f} USDC.")
    confirm = input("Do you want to proceed with this test trade? (yes/no): ")
    
    if confirm.lower() != 'yes':
        logger.info("Test cancelled by user")
        return
    
    # Get wallet address
    wallet_address = trader.get_wallet_address()
    logger.info(f"Preparing transaction for wallet: {wallet_address}")
    
    # Prepare swap transaction
    swap_data = await jupiter.prepare_swap_transaction(
        quote=quote,
        user_public_key=wallet_address
    )
    
    if not swap_data:
        logger.error("Could not prepare swap transaction. Test failed.")
        return
    
    logger.info("Swap transaction prepared successfully")
    
    # Execute the swap
    logger.info("Executing transaction...")
    tx_hash = await jupiter.execute_swap(
        swap_transaction=swap_data,
        keypair=trader.keypair,
        rpc_endpoint=trader.rpc_endpoint
    )
    
    if not tx_hash:
        logger.error("Transaction failed. Test failed.")
        return
    
    logger.info(f"SUCCESS! Transaction executed: {tx_hash}")
    logger.info(f"View transaction: https://solscan.io/tx/{tx_hash}")
    
    # Wait for confirmation
    logger.info("Waiting for transaction confirmation...")
    await asyncio.sleep(5)
    
    # Get updated wallet balance
    new_sol_balance, new_usd_balance = await trader.get_wallet_balance()
    logger.info(f"New wallet balance: {new_sol_balance:.4f} SOL (${new_usd_balance:.2f})")
    logger.info(f"Difference: {new_sol_balance - sol_balance:.6f} SOL")
    
    logger.info("\nTest completed successfully!")
    logger.info("Your bot is now ready for real trading")
    logger.info("\nTo enable real trading:")
    logger.info("1. Edit bot_control.json and set:")
    logger.info("   - 'simulation_mode': false")
    logger.info("   - 'running': true")
    logger.info("2. Adjust trading parameters as needed")
    logger.info("3. Start the bot with: python main.py")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_real_trading())