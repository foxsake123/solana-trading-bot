import asyncio
import logging
from token_analyzer import TokenAnalyzer
from config import BotConfiguration
from database import Database
from logging_setup import setup_logging

logger = setup_logging()
logger.setLevel(logging.DEBUG)

async def test_token_analyzer():
    BotConfiguration.setup_bot_controls()
    db = Database()
    analyzer = TokenAnalyzer()
    
    logger.info("Testing trending tokens...")
    try:
        trending_tokens = await analyzer.get_trending_tokens(limit=5) or []
        logger.info(f"Found {len(trending_tokens)} trending tokens:")
        for i, token in enumerate(trending_tokens, 1):
            logger.info(f"{i}. {token['ticker']} ({token['contract_address']}) - "
                       f"Score: {token['trending_score']:.1f}, "
                       f"Price: ${token['price_usd']:.6f}, "
                       f"Volume: ${token['volume_24h']:,.0f}")
    except Exception as e:
        logger.error(f"Error testing trending tokens: {e}")
    
    # Test only 24h timeframe for top gainers
    timeframe = '24h'
    logger.info(f"Testing top gainers for {timeframe}...")
    try:
        gainers = await analyzer.get_top_gainers(timeframe=timeframe, limit=5) or []
        logger.info(f"Found {len(gainers)} top gainers for {timeframe}:")
        for i, token in enumerate(gainers, 1):
            logger.info(f"{i}. {token['ticker']} ({token['contract_address']}) - "
                       f"Change: {token['price_change']:.2f}%, "
                       f"Price: ${token['price_usd']:.6f}, "
                       f"Volume: ${token['volume_24h']:,.0f}")
    except Exception as e:
        logger.error(f"Error testing top gainers for {timeframe}: {e}")
    
    db.close()

if __name__ == "__main__":
    asyncio.run(test_token_analyzer())