# test_api_direct.py
import asyncio
import logging
from core.birdeye import BirdeyeAPI

logging.basicConfig(level=logging.INFO)

async def test_api():
    """Test the BirdeyeAPI directly"""
    api = BirdeyeAPI()
    
    print("\n🔍 Testing DexScreener API...")
    
    # Test top gainers
    print("\n📈 Fetching top gainers...")
    top_gainers = await api.get_top_gainers(limit=5)
    
    if top_gainers:
        print(f"✅ Found {len(top_gainers)} top gainers:")
        for i, token in enumerate(top_gainers):
            print(f"\n{i+1}. {token.get('ticker')} ({token.get('name')})")
            print(f"   Address: {token.get('contract_address')}")
            print(f"   Price: ${token.get('price_usd', 0):.8f}")
            print(f"   24h Change: {token.get('price_change_24h', 0):.2f}%")
            print(f"   Volume: ${token.get('volume_24h', 0):,.2f}")
            print(f"   Liquidity: ${token.get('liquidity_usd', 0):,.2f}")
    else:
        print("❌ No top gainers found")
    
    # Test trending tokens
    print("\n🔥 Fetching trending tokens...")
    trending = await api.get_trending_tokens(limit=5)
    
    if trending:
        print(f"✅ Found {len(trending)} trending tokens:")
        for i, token in enumerate(trending):
            print(f"\n{i+1}. {token.get('ticker')} ({token.get('name')})")
            print(f"   Volume: ${token.get('volume_24h', 0):,.2f}")
            print(f"   Liquidity: ${token.get('liquidity_usd', 0):,.2f}")
    else:
        print("❌ No trending tokens found")

if __name__ == "__main__":
    asyncio.run(test_api())