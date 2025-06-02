# test_dexscreener_raw.py
import asyncio
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('dexscreener_test')

async def test_raw_dexscreener():
    """Test DexScreener API without any filters"""
    
    url = "https://api.dexscreener.com/latest/dex/search?q=solana"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                data = await response.json()
                
                if 'pairs' in data:
                    # Get Solana pairs
                    solana_pairs = [p for p in data['pairs'] if p.get('chainId') == 'solana']
                    
                    logger.info(f"Found {len(solana_pairs)} Solana pairs")
                    
                    # Show first 10
                    for i, pair in enumerate(solana_pairs[:10]):
                        token = pair.get('baseToken', {})
                        address = token.get('address', '')
                        symbol = token.get('symbol', '')
                        name = token.get('name', '')
                        price_change = pair.get('priceChange', {}).get('h24', 0)
                        volume = pair.get('volume', {}).get('h24', 0)
                        liquidity = pair.get('liquidity', {}).get('usd', 0)
                        
                        has_pump = 'pump' in address.lower()
                        
                        logger.info(f"\n{i+1}. {symbol} ({name})")
                        logger.info(f"   Address: {address}")
                        logger.info(f"   24h Change: {price_change}%")
                        logger.info(f"   24h Volume: ${volume:,.0f}")
                        logger.info(f"   Liquidity: ${liquidity:,.0f}")
                        logger.info(f"   Has 'pump': {has_pump}")

asyncio.run(test_raw_dexscreener())