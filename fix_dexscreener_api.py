# fix_dexscreener_api.py
import os

def fix_birdeye_api():
    """Fix the BirdeyeAPI to properly fetch tokens from DexScreener"""
    
    birdeye_content = '''import time
import logging
import aiohttp
import asyncio
import random
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, UTC

from config import BotConfiguration
from utils import fetch_with_retries, is_fake_token

logger = logging.getLogger('trading_bot.birdeye_api')

class BirdeyeAPI:
    """
    Helper class that uses DexScreener API
    """
    
    def __init__(self):
        self.api_key = BotConfiguration.API_KEYS.get('BIRDEYE_API_KEY', '')
        self.base_url = "https://public-api.birdeye.so"
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
        
        # DexScreener base URL
        self.dexscreener_url = "https://api.dexscreener.com/latest/dex"
        
        # Rate limiting
        self.last_dexscreener_request = 0
        self.min_request_interval = 1.0  # 1 second between requests
        
        logger.info("BirdeyeAPI initialized with DexScreener")
    
    async def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_dexscreener_request
        
        if time_since_last_request < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last_request + random.uniform(0.1, 0.3))
        
        self.last_dexscreener_request = time.time()
    
    async def _get_tokens_from_dexscreener(self, limit: int = 50) -> List[Dict]:
        """Get trending tokens from DexScreener"""
        try:
            await self._wait_for_rate_limit()
            
            # Get trending tokens from Solana
            url = f"{self.dexscreener_url}/tokens/solana"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        logger.warning(f"DexScreener API returned status {response.status}")
                        return []
                    
                    data = await response.json()
                    
                    if not isinstance(data, list):
                        logger.warning(f"Unexpected response format: {type(data)}")
                        return []
                    
                    tokens = []
                    seen_addresses = set()
                    
                    # Process tokens
                    for token_data in data[:limit * 2]:  # Get more to filter
                        if not isinstance(token_data, dict):
                            continue
                        
                        # Get the token address
                        address = token_data.get('tokenAddress') or token_data.get('address')
                        if not address or address in seen_addresses:
                            continue
                        
                        seen_addresses.add(address)
                        
                        # Skip fake tokens
                        if is_fake_token(address):
                            continue
                        
                        # Extract token info
                        info = token_data.get('info', {})
                        price_change = token_data.get('priceChange', {})
                        
                        # Build consistent token structure
                        token = {
                            'address': address,
                            'contract_address': address,
                            'symbol': info.get('symbol', 'UNKNOWN'),
                            'ticker': info.get('symbol', 'UNKNOWN'),
                            'name': info.get('name', 'UNKNOWN'),
                            'price': {'value': float(token_data.get('priceUsd', 0))},
                            'price_usd': float(token_data.get('priceUsd', 0)),
                            'volume': {'value': float(token_data.get('volume', {}).get('h24', 0))},
                            'volume_24h': float(token_data.get('volume', {}).get('h24', 0)),
                            'liquidity': {'value': float(token_data.get('liquidity', {}).get('usd', 0))},
                            'liquidity_usd': float(token_data.get('liquidity', {}).get('usd', 0)),
                            'priceChange': {
                                '24H': float(price_change.get('h24', 0)),
                                '6H': float(price_change.get('h6', 0)),
                                '1H': float(price_change.get('h1', 0))
                            },
                            'price_change_24h': float(price_change.get('h24', 0)),
                            'price_change_6h': float(price_change.get('h6', 0)),
                            'price_change_1h': float(price_change.get('h1', 0)),
                            'mc': {'value': float(token_data.get('marketCap', 0))},
                            'market_cap': float(token_data.get('marketCap', 0)),
                            'mcap': float(token_data.get('marketCap', 0)),
                            'fdv': {'value': float(token_data.get('fdv', 0))},
                            'holders': int(token_data.get('holders', 0)),
                            'holdersCount': int(token_data.get('holders', 0))
                        }
                        
                        tokens.append(token)
                        
                        if len(tokens) >= limit:
                            break
                    
                    logger.info(f"Retrieved {len(tokens)} tokens from DexScreener")
                    return tokens
        
        except Exception as e:
            logger.error(f"Error fetching tokens from DexScreener: {e}")
            return []
    
    async def get_token_info(self, contract_address: str) -> Optional[Dict]:
        """Get detailed token information"""
        if not contract_address or not isinstance(contract_address, str):
            return None
        
        if is_fake_token(contract_address):
            return None
        
        # Check cache
        cache_key = f"token_info_{contract_address}"
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.cache_duration:
                return cache_entry['data']
        
        try:
            await self._wait_for_rate_limit()
            
            # Get specific token data
            url = f"{self.dexscreener_url}/tokens/{contract_address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    
                    if not data or 'pairs' not in data:
                        return None
                    
                    # Get the most liquid Solana pair
                    solana_pairs = [p for p in data['pairs'] if p.get('chainId') == 'solana']
                    if not solana_pairs:
                        return None
                    
                    # Sort by liquidity
                    solana_pairs.sort(key=lambda x: float(x.get('liquidity', {}).get('usd', 0)), reverse=True)
                    pair = solana_pairs[0]
                    
                    # Build token info
                    base_token = pair.get('baseToken', {})
                    token_info = {
                        'address': contract_address,
                        'contract_address': contract_address,
                        'symbol': base_token.get('symbol', 'UNKNOWN'),
                        'ticker': base_token.get('symbol', 'UNKNOWN'),
                        'name': base_token.get('name', 'UNKNOWN'),
                        'price': {'value': float(pair.get('priceUsd', 0))},
                        'price_usd': float(pair.get('priceUsd', 0)),
                        'volume': {'value': float(pair.get('volume', {}).get('h24', 0))},
                        'volume_24h': float(pair.get('volume', {}).get('h24', 0)),
                        'liquidity': {'value': float(pair.get('liquidity', {}).get('usd', 0))},
                        'liquidity_usd': float(pair.get('liquidity', {}).get('usd', 0)),
                        'priceChange': pair.get('priceChange', {}),
                        'price_change_24h': float(pair.get('priceChange', {}).get('h24', 0)),
                        'price_change_6h': float(pair.get('priceChange', {}).get('h6', 0)),
                        'price_change_1h': float(pair.get('priceChange', {}).get('h1', 0)),
                        'mc': {'value': float(pair.get('marketCap', 0) if 'marketCap' in pair else 0)},
                        'market_cap': float(pair.get('marketCap', 0) if 'marketCap' in pair else 0),
                        'mcap': float(pair.get('marketCap', 0) if 'marketCap' in pair else 0),
                        'fdv': {'value': float(pair.get('fdv', 0) if 'fdv' in pair else 0)},
                        'holdersCount': 0,
                        'holders': 0
                    }
                    
                    # Cache the result
                    self.cache[cache_key] = {
                        'timestamp': time.time(),
                        'data': token_info
                    }
                    
                    return token_info
        
        except Exception as e:
            logger.error(f"Error getting token info for {contract_address}: {e}")
            return None
    
    async def get_top_gainers(self, timeframe: str = '24h', limit: int = 10) -> List[Dict]:
        """Get top gaining tokens"""
        cache_key = f"top_gainers_{timeframe}_{limit}"
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.cache_duration:
                return cache_entry['data']
        
        # Get tokens from DexScreener
        tokens = await self._get_tokens_from_dexscreener(100)  # Get more to filter
        
        if not tokens:
            logger.warning("No tokens found for top gainers")
            return []
        
        # Filter by price change
        gainers = []
        for token in tokens:
            price_change = 0
            if timeframe == '1h':
                price_change = token.get('price_change_1h', 0)
            elif timeframe == '6h':
                price_change = token.get('price_change_6h', 0)
            else:  # 24h
                price_change = token.get('price_change_24h', 0)
            
            # Only include positive gainers with decent volume
            if price_change > 5 and token.get('volume_24h', 0) > 10000:
                gainers.append(token)
        
        # Sort by price change
        gainers.sort(key=lambda x: x.get(f'price_change_{timeframe[:-1]}h', 0), reverse=True)
        
        # Limit results
        result = gainers[:limit]
        
        # Cache result
        self.cache[cache_key] = {
            'timestamp': time.time(),
            'data': result
        }
        
        logger.info(f"Found {len(result)} top gainers for {timeframe}")
        return result
    
    async def get_trending_tokens(self, limit: int = 10) -> List[Dict]:
        """Get trending tokens"""
        cache_key = f"trending_tokens_{limit}"
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.cache_duration:
                return cache_entry['data']
        
        # Get tokens from DexScreener
        tokens = await self._get_tokens_from_dexscreener(50)
        
        if not tokens:
            logger.warning("No tokens found for trending")
            return []
        
        # Filter by volume and liquidity
        trending = []
        for token in tokens:
            if (token.get('volume_24h', 0) > 50000 and 
                token.get('liquidity_usd', 0) > 25000):
                trending.append(token)
        
        # Sort by volume
        trending.sort(key=lambda x: x.get('volume_24h', 0), reverse=True)
        
        # Limit results
        result = trending[:limit]
        
        # Cache result
        self.cache[cache_key] = {
            'timestamp': time.time(),
            'data': result
        }
        
        logger.info(f"Found {len(result)} trending tokens")
        return result
    
    async def get_token_price(self, contract_address: str) -> Optional[float]:
        """Get token price"""
        token_info = await self.get_token_info(contract_address)
        if token_info:
            return token_info.get('price_usd', 0)
        return None
    
    async def get_token_volume(self, contract_address: str) -> Optional[float]:
        """Get 24h volume"""
        token_info = await self.get_token_info(contract_address)
        if token_info:
            return token_info.get('volume_24h', 0)
        return None
    
    async def get_token_liquidity(self, contract_address: str) -> Optional[float]:
        """Get liquidity"""
        token_info = await self.get_token_info(contract_address)
        if token_info:
            return token_info.get('liquidity_usd', 0)
        return None
    
    async def get_holders_count(self, contract_address: str) -> Optional[int]:
        """Get holders count (not available from DexScreener)"""
        return 100  # Default value since DexScreener doesn't provide this
    
    async def get_market_cap(self, contract_address: str) -> Optional[float]:
        """Get market cap"""
        token_info = await self.get_token_info(contract_address)
        if token_info:
            return token_info.get('market_cap', 0)
        return None
    
    async def get_price_change(self, contract_address: str, timeframe: str) -> Optional[float]:
        """Get price change"""
        token_info = await self.get_token_info(contract_address)
        if not token_info:
            return None
        
        if timeframe == '1h':
            return token_info.get('price_change_1h', 0)
        elif timeframe == '6h':
            return token_info.get('price_change_6h', 0)
        elif timeframe == '24h':
            return token_info.get('price_change_24h', 0)
        
        return None
    
    async def get_token_security_info(self, contract_address: str) -> Optional[Dict]:
        """Get basic security info"""
        token_info = await self.get_token_info(contract_address)
        
        if not token_info:
            return None
        
        # Calculate basic security score
        liquidity = token_info.get('liquidity_usd', 0)
        volume = token_info.get('volume_24h', 0)
        
        liquidity_score = min(40, liquidity / 2500)
        volume_score = min(30, volume / 3333)
        holders_score = 20  # Default since we don't have real data
        
        security_score = liquidity_score + volume_score + holders_score
        
        return {
            'securityScore': security_score,
            'liquidityLocked': liquidity > 100000,
            'mintingDisabled': False,
            'isMemeToken': False
        }
'''
    
    # Write the fixed file
    files_to_update = ['birdeye.py', 'core/birdeye.py']
    
    for file_path in files_to_update:
        if os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(birdeye_content)
            print(f"✅ Updated {file_path}")

if __name__ == "__main__":
    fix_birdeye_api()