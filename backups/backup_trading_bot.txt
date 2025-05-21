import asyncio
import logging
import logging.handlers
import signal
import os
import sys
import traceback
from datetime import datetime, UTC

from config import BotConfiguration
from database import Database
from solana_trader import SolanaTrader
from token_scanner import TokenScanner

logger = logging.getLogger('trading_bot')
logger.setLevel(logging.INFO)

file_handler = logging.handlers.RotatingFileHandler(
    f'logs/trading_bot_{datetime.now(UTC).strftime("%Y%m%d_%H%M%S")}.log',
    maxBytes=10*1024*1024,
    backupCount=5
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

class TradingBot:
    """
    Main trading bot class
    """
    def __init__(self):
        """
        Initialize trading bot
        """
        self.running = True
        
        # Initialize the database first
        self.db = Database()
        
        # Then initialize trader with the database instance
        self.trader = SolanaTrader(db=self.db, simulation_mode=True)
        
        # Initialize scanner (we might need to modify scanner to also take db)
        self.scanner = TokenScanner()
        
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """
        Setup graceful shutdown signal handlers
        """
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """
        Handle shutdown signals
        """
        logger.critical(f"Received signal {signum}. Initiating graceful shutdown...")
        self.running = False
    
    async def _discover_and_trade(self):
        """
        Discover and trade tokens
        """
        logger.info("Starting token discovery and trading process")
        while self.running:
            try:
                # Get trading parameters
                params = BotConfiguration.TRADING_PARAMETERS
                max_investment = params.get('MAX_INVESTMENT_PER_TOKEN', 1.0)
                min_investment = params.get('MIN_INVESTMENT_PER_TOKEN', 0.1)
                
                # Get wallet balance
                balance_sol, balance_usd = await self.trader.get_wallet_balance()
                logger.info(f"Current wallet balance: {balance_sol:.4f} SOL (${balance_usd:.2f})")
                
                # Skip if balance is less than minimum investment
                if balance_sol < min_investment:
                    logger.warning(f"Wallet balance ({balance_sol:.4f} SOL) is below minimum investment size ({min_investment} SOL). Skipping discovery cycle.")
                    await asyncio.sleep(300)
                    continue
                
                # Find qualified tokens
                qualified_tokens = await self.scanner.get_tokens_by_criteria()
                if not qualified_tokens:
                    logger.info("No tokens found meeting screening criteria, analyzing other tokens...")
                    other_tradable = await self.scanner.analyze_tokens()
                    qualified_tokens = other_tradable
                
                for token in qualified_tokens:
                    token_data = token['token_data']
                    contract = token_data['contract_address']
                    ticker = token_data['ticker']
                    recommendation = token['recommendation']
                    
                    # Determine investment amount based on max and min parameters
                    recommended_investment = recommendation['max_investment']
                    
                    # Cap the investment to the max parameter
                    investment_amount = min(recommended_investment, max_investment)
                    
                    # Ensure the investment is at least the minimum
                    if investment_amount < min_investment:
                        logger.info(f"Calculated investment for {ticker} ({investment_amount} SOL) is below minimum threshold ({min_investment} SOL), adjusting to minimum")
                        investment_amount = min_investment
                    
                    # Check if we already have a position in this token
                    active_orders = self.db.get_active_orders()
                    if not active_orders.empty and contract in active_orders['contract_address'].values:
                        logger.info(f"Already have position in {ticker} ({contract}), skipping")
                        continue
                    
                    # Ensure we have enough balance for investment
                    if balance_sol < investment_amount:
                        logger.warning(f"Insufficient balance ({balance_sol} SOL) for trade of {investment_amount} SOL")
                        if balance_sol >= min_investment:
                            # If we have enough for minimum investment, use all available balance
                            logger.info(f"Adjusting investment amount to available balance: {balance_sol:.4f} SOL")
                            investment_amount = balance_sol
                        else:
                            # Skip this token if we can't meet minimum investment
                            continue
                    
                    logger.info(f"Token {ticker} qualified for trading:")
                    logger.info(f"  - Volume 24h: ${token_data.get('volume_24h', 0):,.2f}")
                    logger.info(f"  - Liquidity: ${token_data.get('liquidity_usd', 0):,.2f}")
                    logger.info(f"  - Market Cap: ${token_data.get('mcap', 0):,.2f}")
                    logger.info(f"  - Holders: {token_data.get('holders', 0):,}")
                    logger.info(f"  - Price Change 24h: {token_data.get('price_change_24h', 0):.2f}%")
                    logger.info(f"  - Security Score: {token_data.get('safety_score', 0):.1f}/100")
                    
                    logger.info(f"Trading {ticker} ({contract}) for {investment_amount} SOL")
                    txid = await self.trader.execute_trade(contract, 'BUY', investment_amount)
                    if txid:
                        logger.info(f"Successfully traded {ticker}: {txid}")
                        balance_sol -= investment_amount
                    else:
                        logger.error(f"Failed to trade {ticker}")
                
                logger.debug("Waiting for next discovery cycle")
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"Error during discovery and trading: {e}")
                logger.error(traceback.format_exc())
                await asyncio.sleep(60)
    
    async def run(self):
        """
        Main bot execution method
        """
        logger.info("="*50)
        logger.info("   Solana Trading Bot Starting")
        logger.info("="*50)
        try:
            BotConfiguration.setup_bot_controls()
            balance_sol, balance_usd = await self.trader.get_wallet_balance()
            logger.info(f"Initial Wallet Balance: {balance_sol:.4f} SOL (${balance_usd:.2f})")
            tasks = [
                asyncio.create_task(self.scanner.start_scanning()),
                asyncio.create_task(self.trader.monitor_positions()),
                asyncio.create_task(self._discover_and_trade())
            ]
            while self.running:
                done, pending = await asyncio.wait(tasks, timeout=60, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    try:
                        task.result()
                        logger.warning(f"Task {task.get_name()} completed unexpectedly")
                    except asyncio.CancelledError:
                        logger.info(f"Task {task.get_name()} was cancelled")
                    except Exception as e:
                        logger.error(f"Task {task.get_name()} failed with error: {e}")
                        logger.error(traceback.format_exc())
                    tasks.remove(task)
                    if "scanner.start_scanning" in str(task):
                        tasks.append(asyncio.create_task(self.scanner.start_scanning()))
                    elif "trader.monitor_positions" in str(task):
                        tasks.append(asyncio.create_task(self.trader.monitor_positions()))
                    elif "discover_and_trade" in str(task):
                        tasks.append(asyncio.create_task(self._discover_and_trade()))
                if not self.running:
                    break
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.critical(f"Bot execution failed: {e}")
            logger.critical(traceback.format_exc())
        finally:
            logger.info("Closing connections")
            await self.trader.close()
            logger.info("="*50)
            logger.info("   Solana Trading Bot Shutdown Complete")
            logger.info("="*50)

def main():
    """
    Entry point for the trading bot
    """
    try:
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        bot = TradingBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Unhandled bot initialization error: {e}")
        logger.critical(traceback.format_exc())
    finally:
        logger.info("Bot execution completed")

if __name__ == "__main__":
    main()