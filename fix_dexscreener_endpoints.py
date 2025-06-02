# fix_dexscreener_endpoints.py
import os

def fix_dexscreener_endpoints():
    """Fix DexScreener to use search endpoint for getting tokens"""
    
    birdeye_content = '''import time
import logging
import aiohttp
import asyncio
import random
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, UTC

logger = logging.getLogger('trading_bot.birdeye_api')

class BirdeyeAPI:
    """
    Helper class that uses DexScreener API
    """
    
    def __init__(self):
        from config import BotConfiguration
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
    
    def _is_fake_token(self, address: str) -> bool:
        """Simple fake token check"""
        if not address or not isinstance(address, str):
            return True
        
        lower_address = address.lower()
        
        # Check for suspicious patterns
        suspicious_terms = ['scam', 'fake', 'test', 'demo']
        for term in suspicious_terms:
            if term in lower_address:
                return True
        
        return False
    
    async def _get_tokens_from_dexscreener(self, limit: int = 50) -> List[Dict]:
        """Get trending tokens from DexScreener using search"""
        try:
            await self._wait_for_rate_limit()
            
            # Use search endpoint to get Solana tokens
            url = f"{self.dexscreener_url}/search?q=solana"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        logger.warning(f"DexScreener API returned status {response.status}")
                        return []
                    
                    data = await response.json()
                    
                    # DexScreener search returns pairs
                    if not isinstance(data, dict) or 'pairs' not in data:
                        logger.warning(f"Unexpected response format from search")
                        return []
                    
                    pairs = data.get('pairs', [])
                    if not pairs:
                        logger.warning("No pairs found in search results")
                        return []
                    
                    tokens = []
                    seen_addresses = set()
                    
                    # Process pairs and extract unique tokens
                    for pair in pairs:
                        if not isinstance(pair, dict):
                            continue
                        
                        # Only process Solana pairs
                        if pair.get('chainId') != 'solana':
                            continue
                        
                        # Get base token info
                        base_token = pair.get('baseToken', {})
                        address = base_token.get('address')
                        
                        if not address or address in seen_addresses:
                            continue
                        
                        seen_addresses.add(address)
                        
                        # Skip fake tokens
                        if self._is_fake_token(address):
                            continue
                        
                        # Build consistent token structure
                        price_change = pair.get('priceChange', {})
                        volume = pair.get('volume', {})
                        liquidity = pair.get('liquidity', {})
                        
                        token = {
                            'address': address,
                            'contract_address': address,
                            'symbol': base_token.get('symbol', 'UNKNOWN'),
                            'ticker': base_token.get('symbol', 'UNKNOWN'),
                            'name': base_token.get('name', 'UNKNOWN'),
                            'price': {'value': float(pair.get('priceUsd', 0))},
                            'price_usd': float(pair.get('priceUsd', 0)),
                            'volume': {'value': float(volume.get('h24', 0))},
                            'volume_24h': float(volume.get('h24', 0)),
                            'liquidity': {'value': float(liquidity.get('usd', 0))},
                            'liquidity_usd': float(liquidity.get('usd', 0)),
                            'priceChange': {
                                '24H': float(price_change.get('h24', 0)),
                                '6H': float(price_change.get('h6', 0)),
                                '1H': float(price_change.get('h1', 0))
                            },
                            'price_change_24h': float(price_change.get('h24', 0)),
                            'price_change_6h': float(price_change.get('h6', 0)),
                            'price_change_1h': float(price_change.get('h1', 0)),
                            'mc': {'value': float(pair.get('marketCap', 0) if 'marketCap' in pair else 0)},
                            'market_cap': float(pair.get('marketCap', 0) if 'marketCap' in pair else 0),
                            'mcap': float(pair.get('marketCap', 0) if 'marketCap' in pair else 0),
                            'fdv': {'value': float(pair.get('fdv', 0) if 'fdv' in pair else 0)},
                            'holders': 100,  # Default value
                            'holdersCount': 100  # Default value
                        }
                        
                        tokens.append(token)
                        
                        if len(tokens) >= limit:
                            break
                    
                    logger.info(f"Retrieved {len(tokens)} tokens from DexScreener search")
                    return tokens
        
        except Exception as e:
            logger.error(f"Error fetching tokens from DexScreener: {e}")
            return []
    
    async def _get_trending_pairs(self) -> List[Dict]:
        """Get trending pairs from DexScreener"""
        try:
            await self._wait_for_rate_limit()
            
            # Get trending pairs
            url = f"{self.dexscreener_url}/pairs/solana"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        logger.warning(f"DexScreener pairs API returned status {response.status}")
                        return []
                    
                    data = await response.json()
                    
                    if isinstance(data, dict) and data.get('pairs') is None:
                        # Try alternative endpoint - get specific popular tokens
                        return await self._get_popular_tokens()
                    
                    return data if isinstance(data, list) else []
                    
        except Exception as e:
            logger.error(f"Error fetching trending pairs: {e}")
            return []
    
    async def _get_popular_tokens(self) -> List[Dict]:
        """Get popular tokens by searching for known ones"""
        popular_searches = ['bonk', 'wif', 'jup', 'ray', 'orca']
        all_tokens = []
        seen_addresses = set()
        
        for search_term in popular_searches:
            try:
                await self._wait_for_rate_limit()
                
                url = f"{self.dexscreener_url}/search?q={search_term}"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=30) as response:
                        if response.status != 200:
                            continue
                        
                        data = await response.json()
                        pairs = data.get('pairs', [])
                        
                        for pair in pairs:
                            if pair.get('chainId') != 'solana':
                                continue
                            
                            base_token = pair.get('baseToken', {})
                            address = base_token.get('address')
                            
                            if address and address not in seen_addresses:
                                seen_addresses.add(address)
                                
                                # Build token structure
                                price_change = pair.get('priceChange', {})
                                volume = pair.get('volume', {})
                                liquidity = pair.get('liquidity', {})
                                
                                token = {
                                    'address': address,
                                    'contract_address': address,
                                    'symbol': base_token.get('symbol', 'UNKNOWN'),
                                    'ticker': base_token.get('symbol', 'UNKNOWN'),
                                    'name': base_token.get('name', 'UNKNOWN'),
                                    'price': {'value': float(pair.get('priceUsd', 0))},
                                    'price_usd': float(pair.get('priceUsd', 0)),
                                    'volume': {'value': float(volume.get('h24', 0))},
                                    'volume_24h': float(volume.get('h24', 0)),
                                    'liquidity': {'value': float(liquidity.get('usd', 0))},
                                    'liquidity_usd': float(liquidity.get('usd', 0)),
                                    'priceChange': {
                                        '24H': float(price_change.get('h24', 0)),
                                        '6H': float(price_change.get('h6', 0)),
                                        '1H': float(price_change.get('h1', 0))
                                    },
                                    'price_change_24h': float(price_change.get('h24', 0)),
                                    'price_change_6h': float(price_change.get('h6', 0)),
                                    'price_change_1h': float(price_change.get('h1', 0)),
                                    'mc': {'value': float(pair.get('marketCap', 0) if 'marketCap' in pair else 0)},
                                    'market_cap': float(pair.get('marketCap', 0) if 'marketCap' in pair else 0),
                                    'mcap': float(pair.get('marketCap', 0) if 'marketCap' in pair else 0),
                                    'fdv': {'value': float(pair.get('fdv', 0) if 'fdv' in pair else 0)},
                                    'holders': 100,
                                    'holdersCount': 100
                                }
                                
                                all_tokens.append(token)
                                
            except Exception as e:
                logger.error(f"Error searching for {search_term}: {e}")
                continue
        
        return all_tokens
    
    async def get_token_info(self, contract_address: str) -> Optional[Dict]:
        """Get detailed token information"""
        if not contract_address or not isinstance(contract_address, str):
            return None
        
        if self._is_fake_token(contract_address):
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
                    price_change = pair.get('priceChange', {})
                    volume = pair.get('volume', {})
                    liquidity = pair.get('liquidity', {})
                    
                    token_info = {
                        'address': contract_address,
                        'contract_address': contract_address,
                        'symbol': base_token.get('symbol', 'UNKNOWN'),
                        'ticker': base_token.get('symbol', 'UNKNOWN'),
                        'name': base_token.get('name', 'UNKNOWN'),
                        'price': {'value': float(pair.get('priceUsd', 0))},
                        'price_usd': float(pair.get('priceUsd', 0)),
                        'volume': {'value': float(volume.get('h24', 0))},
                        'volume_24h': float(volume.get('h24', 0)),
                        'liquidity': {'value': float(liquidity.get('usd', 0))},
                        'liquidity_usd': float(liquidity.get('usd', 0)),
                        'priceChange': price_change,
                        'price_change_24h': float(price_change.get('h24', 0)),
                        'price_change_6h': float(price_change.get('h6', 0)),
                        'price_change_1h': float(price_change.get('h1', 0)),
                        'mc': {'value': float(pair.get('marketCap', 0) if 'marketCap' in pair else 0)},
                        'market_cap': float(pair.get('marketCap', 0) if 'marketCap' in pair else 0),
                        'mcap': float(pair.get('marketCap', 0) if 'marketCap' in pair else 0),
                        'fdv': {'value': float(pair.get('fdv', 0) if 'fdv' in pair else 0)},
                        'holdersCount': 100,
                        'holders': 100
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
        
        # Get tokens from multiple sources
        search_tokens = await self._get_tokens_from_dexscreener(100)
        popular_tokens = await self._get_popular_tokens()
        
        # Combine all tokens
        all_tokens = search_tokens + popular_tokens
        
        if not all_tokens:
            logger.warning("No tokens found for top gainers")
            return []
        
        # Remove duplicates
        unique_tokens = {}
        for token in all_tokens:
            address = token.get('contract_address')
            if address and address not in unique_tokens:
                unique_tokens[address] = token
        
        tokens = list(unique_tokens.values())
        
        # Filter by price change and volume
        gainers = []
        for token in tokens:
            price_change = 0
            if timeframe == '1h':
                price_change = token.get('price_change_1h', 0)
            elif timeframe == '6h':
                price_change = token.get('price_change_6h', 0)
            else:  # 24h
                price_change = token.get('price_change_24h', 0)
            
            # Include positive gainers with decent volume
            if price_change > 1 and token.get('volume_24h', 0) > 5000:
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
        
        # Get tokens from multiple sources
        search_tokens = await self._get_tokens_from_dexscreener(50)
        popular_tokens = await self._get_popular_tokens()
        
        # Combine all tokens
        all_tokens = search_tokens + popular_tokens
        
        if not all_tokens:
            logger.warning("No tokens found for trending")
            return []
        
        # Remove duplicates
        unique_tokens = {}
        for token in all_tokens:
            address = token.get('contract_address')
            if address and address not in unique_tokens:
                unique_tokens[address] = token
        
        tokens = list(unique_tokens.values())
        
        # Filter by volume and liquidity
        trending = []
        for token in tokens:
            if (token.get('volume_24h', 0) > 10000 and 
                token.get('liquidity_usd', 0) > 10000):
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
            print(f"✅ Fixed DexScreener endpoints in {file_path}")

if __name__ == "__main__":
    fix_dexscreener_endpoints()