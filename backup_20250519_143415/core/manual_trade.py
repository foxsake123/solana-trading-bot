import os
import sys
import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('manual_trade')

# Import components
sys.path.append('.')  # Add current directory to path
from database import Database
from solana_trader import SolanaTrader
from config import BotConfiguration

async def execute_manual_trade():
    """Execute a manual test trade"""
    # Initialize components
    db = Database()
    trader = SolanaTrader(db=db, simulation_mode=False)
    
    # Connect to network
    await trader.connect()
    
    # Get wallet balance
    balance_sol, balance_usd = await trader.get_wallet_balance()
    logger.info(f"Wallet Balance: {balance_sol:.4f} SOL (${balance_usd:.2f})")
    
    # Test token (a simulation token for safety)
    token_address = "Sim0TopGainer1747172803"
    
    # Use a very small amount
    amount = 0.01  # 0.01 SOL
    
    # Log the execution
    logger.info(f"Executing manual BUY trade:")
    logger.info(f"- Token: {token_address}")
    logger.info(f"- Amount: {amount} SOL")
    logger.info(f"- Simulation mode: {trader.simulation_mode}")
    
    # Execute the trade
    tx_hash = await trader.execute_trade(token_address, amount, action="BUY")
    logger.info(f"Trade result: {tx_hash}")
    
    # Close connection
    await trader.close()
    
    logger.info("Manual trade completed")

# Run the manual trade
if __name__ == "__main__":
    # Force config to real mode
    BotConfiguration.TRADING_PARAMETERS['simulation_mode'] = False
    
    asyncio.run(execute_manual_trade())