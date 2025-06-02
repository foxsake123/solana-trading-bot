# test_dexscreener_simple.py
import asyncio
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('dexscreener_test')

async def test_dexscreener_api():
    """Test DexScreener API directly"""
    
    print("\n🔍 Testing DexScreener API Directly...")
    
    # Test the actual DexScreener endpoint
    url = "https://api.dexscreener.com/latest/dex/tokens/solana"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=30) as response:
                print(f"\n📡 API Response Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"✅ Got response! Type: {type(data)}")
                    
                    if isinstance(data, list):
                        print(f"📊 Found {len(data)} tokens")
                        
                        # Show first 5 tokens
                        for i, token in enumerate(data[:5]):
                            if isinstance(token, dict):
                                address = token.get('tokenAddress', 'N/A')
                                info = token.get('info', {})
                                symbol = info.get('symbol', 'UNKNOWN')
                                name = info.get('name', 'UNKNOWN')
                                price = token.get('priceUsd', 0)
                                volume = token.get('volume', {}).get('h24', 0)
                                liquidity = token.get('liquidity', {}).get('usd', 0)
                                
                                print(f"\n{i+1}. {symbol} ({name})")
                                print(f"   Address: {address}")
                                print(f"   Price: ${float(price):.8f}")
                                print(f"   24h Volume: ${float(volume):,.2f}")
                                print(f"   Liquidity: ${float(liquidity):,.2f}")
                    else:
                        print(f"❌ Unexpected response format: {data}")
                else:
                    text = await response.text()
                    print(f"❌ API Error: {text[:200]}")
                    
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_dexscreener_api())