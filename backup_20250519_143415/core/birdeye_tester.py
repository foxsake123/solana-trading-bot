"""
Birdeye API tester - Checks if the API can find real tokens on Solana
"""
import logging
import sys
import os

# Add the parent directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('birdeye_tester')

# Import the Birdeye API
try:
    from core.birdeye_api import BirdeyeAPI
except ImportError:
    # Try alternative import paths
    try:
        from trading_bot.birdeye_api import BirdeyeAPI
    except ImportError:
        try:
            from birdeye_api import BirdeyeAPI
        except ImportError:
            logger.error("Failed to import BirdeyeAPI. Check your import paths.")
            sys.exit(1)

def test_birdeye_api():
    """Test the Birdeye API by fetching and displaying token data"""
    # Initialize the Birdeye API
    birdeye = BirdeyeAPI()
    logger.info("Initialized Birdeye API for testing")
    
    # Test top gainers API
    logger.info("\n=== TESTING TOP GAINERS API ===")
    
    # 1h gainers
    logger.info("\nFetching 1h gainers...")
    gainers_1h = birdeye.get_top_gainers(timeframe='1h', limit=5)
    logger.info(f"Found {len(gainers_1h)} 1h gainers")
    
    # Display the top gainer
    if gainers_1h:
        logger.info("\nGainer #1:")
        logger.info(f"  Name: {gainers_1h[0].get('name', 'Unknown')}")
        logger.info(f"  Symbol: {gainers_1h[0].get('symbol', 'Unknown')}")
        logger.info(f"  Address: {gainers_1h[0].get('address', 'Unknown')}")
        logger.info(f"  Price: ${gainers_1h[0].get('price', 0)}")
        logger.info(f"  1h Change: {gainers_1h[0].get('priceChange1h', 0):.2f}%")
        logger.info(f"  Volume 24h: ${gainers_1h[0].get('volume24h', 0):.2f}")
        logger.info(f"  Liquidity: ${gainers_1h[0].get('liquidity', 0):.2f}")
    
    # 24h gainers
    logger.info("\nFetching 24h gainers...")
    gainers_24h = birdeye.get_top_gainers(timeframe='24h', limit=5)
    logger.info(f"Found {len(gainers_24h)} 24h gainers")
    
    # Display the top 24h gainer
    if gainers_24h:
        logger.info("\nTop 24h Gainer:")
        logger.info(f"  Name: {gainers_24h[0].get('name', 'Unknown')}")
        logger.info(f"  Symbol: {gainers_24h[0].get('symbol', 'Unknown')}")
        logger.info(f"  Address: {gainers_24h[0].get('address', 'Unknown')}")
        logger.info(f"  Price: ${gainers_24h[0].get('price', 0)}")
        logger.info(f"  24h Change: {gainers_24h[0].get('priceChange24h', 0):.2f}%")
    
    # Test trending tokens API
    logger.info("\n=== TESTING TRENDING TOKENS API ===")
    trending = birdeye.get_trending_tokens(limit=5)
    logger.info(f"Found {len(trending)} trending tokens")
    
    # Display the top trending token
    if trending:
        logger.info("\nTrending #1:")
        logger.info(f"  Name: {trending[0].get('name', 'Unknown')}")
        logger.info(f"  Symbol: {trending[0].get('symbol', 'Unknown')}")
        logger.info(f"  Address: {trending[0].get('address', 'Unknown')}")
        logger.info(f"  Score: {trending[0].get('score', 0)}")
        logger.info(f"  Volume: ${trending[0].get('volume24h', 0):.2f}")
    
    # Test token info API
    logger.info("\n=== TESTING TOKEN INFO API ===")
    
    # Get details for the first trending token
    if trending:
        token_address = trending[0].get('address')
        logger.info(f"Getting detailed info for token: {token_address}")
        token_info = birdeye.get_token_info(token_address)
        
        logger.info("\nToken Info:")
        logger.info(f"  Name: {token_info.get('name', 'Unknown')}")
        logger.info(f"  Symbol: {token_info.get('symbol', 'Unknown')}")
        logger.info(f"  Price: ${token_info.get('price', 0)}")
        logger.info(f"  Volume: ${token_info.get('volume24h', 0):.2f}")
        logger.info(f"  Liquidity: ${token_info.get('liquidity', 0):.2f}")
        logger.info(f"  Market Cap: ${token_info.get('marketCap', 0):.1f}")
        logger.info(f"  Holders Count: {token_info.get('holderCount', 0)}")
        
        # Get security info
        logger.info("\nGetting security info...")
        security_info = birdeye.get_token_security_info(token_address)
        
        logger.info("\nSecurity Info:")
        logger.info(f"  Security Score: {security_info.get('totalScore', 0)}")
        logger.info(f"  Liquidity Locked: {security_info.get('isLiquidityLocked', False)}")
        logger.info(f"  Minting Disabled: {security_info.get('isMintingDisabled', False)}")
        logger.info(f"  Is Meme Token: {security_info.get('isMemeToken', False)}")
    
    logger.info("\nBirdeye API Test Complete")

if __name__ == "__main__":
    test_birdeye_api()
