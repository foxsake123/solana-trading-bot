import time
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
    Helper class that uses DexScreener API as a fallback for Birdeye
    This is a drop-in replacement that maintains the same interface
    """
    
    def __init__(self):
        """
        Initialize the API client
        """
        self.api_key = BotConfiguration.API_KEYS.get('BIRDEYE_API_KEY', '')
        self.base_url = "https://public-api.birdeye.so"
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
        
        # Set to True to use DexScreener exclusively and skip Birdeye attempts
        self.use_dexscreener_only = True
        
        # DexScreener base URL
        self.dexscreener_url = "https://api.dexscreener.com/latest/dex"
        
        # Rate limiting for DexScreener
        self.last_dexscreener_request = 0
        self.min_request_interval = 0.5  # Minimum time between requests (500ms)
        
        logger.info("BirdeyeAPI initialized with DexScreener fallback enabled")
    
    async def _wait_for_rate_limit(self):
        """
        Ensure we don't exceed rate limits for the DexScreener API
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_dexscreener_request
        
        if time_since_last_request < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last_request + random.uniform(0.1, 0.3))
        
        self.last_dexscreener_request = time.time()
    
    async def _get_from_dexscreener(self, contract_address: str) -> Optional[Dict]:
        """
        Get token data from DexScreener
        
        :param contract_address: Token contract address
        :return: Token data dictionary or None
        """
        try:
            # Ensure we respect rate limits
            await self._wait_for_rate_limit()
            
            # According to DexScreener docs, this is the correct endpoint format
            url = f"{self.dexscreener_url}/tokens/{contract_address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        logger.warning(f"DexScreener API returned status {response.status} for {contract_address}")
                        return None
                    
                    data = await response.json()
                    
                    if not data or 'pairs' not in data or not data['pairs']:
                        logger.warning(f"No DexScreener data for {contract_address}")
                        return None
                    
                    # Filter for Solana pairs only
                    solana_pairs = [pair for pair in data['pairs'] if pair.get('chainId') == 'solana']
                    
                    if not solana_pairs:
                        logger.warning(f"No Solana pairs found for {contract_address}")
                        return None
                    
                    # Sort by liquidity to use the most liquid pair
                    solana_pairs.sort(key=lambda x: float(x.get('liquidity', {}).get('usd', 0)), reverse=True)
                    
                    # Use first (most liquid) pair
                    pair = solana_pairs[0]
                    
                    # Build a response that matches our expected format
                    return {
                        'address': contract_address,
                        'symbol': pair.get('baseToken', {}).get('symbol', 'UNKNOWN'),
                        'name': pair.get('baseToken', {}).get('name', 'UNKNOWN'),
                        'price': {
                            'value': float(pair.get('priceUsd', 0.0))
                        },
                        'volume': {
                            'value': float(pair.get('volume', {}).get('h24', 0.0))
                        },
                        'liquidity': {
                            'value': float(pair.get('liquidity', {}).get('usd', 0.0))
                        },
                        'priceChange': {
                            '24H': float(pair.get('priceChange', {}).get('h24', 0.0)),
                            '6H': float(pair.get('priceChange', {}).get('h6', 0.0)) if 'h6' in pair.get('priceChange', {}) else 0.0,
                            '1H': float(pair.get('priceChange', {}).get('h1', 0.0)) if 'h1' in pair.get('priceChange', {}) else 0.0
                        },
                        'mc': {
                            'value': float(pair.get('mcap', 0.0) if 'mcap' in pair else 0.0)
                        },
                        'fdv': {
                            'value': float(pair.get('fdv', 0.0) if 'fdv' in pair else 0.0)
                        },
                        'holdersCount': int(pair.get('holders', 0) if 'holders' in pair else 0)
                    }
        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error getting token from DexScreener: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting token from DexScreener: {e}")
            return None
    
    async def get_token_info(self, contract_address: str) -> Optional[Dict]:
        """
        Get detailed token information
        
        :param contract_address: Token contract address
        :return: Token information dictionary or None
        """
        # Validate contract address
        if not contract_address or not isinstance(contract_address, str):
            logger.warning(f"Invalid contract address in get_token_info: {contract_address}")
            return None
        
        # Check if token is likely fake
        if is_fake_token(contract_address):
            logger.warning(f"Skipping likely fake token in get_token_info: {contract_address}")
            return None
        
        # Check cache first
        cache_key = f"token_info_{contract_address}"
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.cache_duration:
                return cache_entry['data']
        
        # Use DexScreener
        token_info = await self._get_from_dexscreener(contract_address)
        
        if token_info:
            # Cache the result
            self.cache[cache_key] = {
                'timestamp': time.time(),
                'data': token_info
            }
            return token_info
        
        logger.warning(f"Failed to get token info for {contract_address}")
        return None
    
    async def get_token_price(self, contract_address: str) -> Optional[float]:
        """
        Get token price in USD
        
        :param contract_address: Token contract address
        :return: Token price in USD or None
        """
        token_info = await self.get_token_info(contract_address)
        if token_info and 'price' in token_info and 'value' in token_info['price']:
            return float(token_info['price']['value'])
        
        # Try CoinGecko for popular tokens
        if contract_address == "So11111111111111111111111111111111111111112":  # SOL
            try:
                # Direct HTTP call to CoinGecko
                url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=30) as response:
                        response.raise_for_status()
                        data = await response.json()
                        if data and 'solana' in data and 'usd' in data['solana']:
                            return float(data['solana']['usd'])
            except Exception as e:
                logger.error(f"Error getting SOL price from CoinGecko: {e}")
        
        return None
    
    async def get_token_volume(self, contract_address: str) -> Optional[float]:
        """
        Get 24h trading volume in USD
        
        :param contract_address: Token contract address
        :return: 24h volume in USD or None
        """
        token_info = await self.get_token_info(contract_address)
        if token_info and 'volume' in token_info and 'value' in token_info['volume']:
            return float(token_info['volume']['value'])
        return None
    
    async def get_token_liquidity(self, contract_address: str) -> Optional[float]:
        """
        Get token liquidity in USD
        
        :param contract_address: Token contract address
        :return: Liquidity in USD or None
        """
        token_info = await self.get_token_info(contract_address)
        if token_info and 'liquidity' in token_info and 'value' in token_info['liquidity']:
            return float(token_info['liquidity']['value'])
        return None
    
    async def get_holders_count(self, contract_address: str) -> Optional[int]:
        """
        Get number of token holders
        
        :param contract_address: Token contract address
        :return: Number of holders or None
        """
        token_info = await self.get_token_info(contract_address)
        if token_info and 'holdersCount' in token_info:
            return int(token_info['holdersCount'])
        return None
    
    async def get_market_cap(self, contract_address: str) -> Optional[float]:
        """
        Get market cap in USD
        
        :param contract_address: Token contract address
        :return: Market cap in USD or None
        """
        token_info = await self.get_token_info(contract_address)
        if token_info and 'mc' in token_info and 'value' in token_info['mc']:
            return float(token_info['mc']['value'])
        return None
    
    async def get_price_change(self, contract_address: str, timeframe: str) -> Optional[float]:
        """
        Get price change percentage for a given timeframe
        
        :param contract_address: Token contract address
        :param timeframe: Timeframe (1h, 6h, 24h)
        :return: Price change percentage or None
        """
        token_info = await self.get_token_info(contract_address)
        if not token_info or 'priceChange' not in token_info:
            return None
        
        price_change = token_info['priceChange']
        
        if timeframe == '1h' and '1H' in price_change:
            return float(price_change['1H'])
        elif timeframe == '6h' and '6H' in price_change:
            return float(price_change['6H'])
        elif timeframe == '24h' and '24H' in price_change:
            return float(price_change['24H'])
        
        return None
    
    async def _get_tokens_from_dexscreener(self, limit: int = 50) -> List[Dict]:
        """
        Get tokens list from DexScreener
        
        :param limit: Maximum number of tokens to return
        :return: List of tokens
        """
        try:
            # Ensure we respect rate limits
            await self._wait_for_rate_limit()
            
            # Use solana search query to get recent tokens
            url = f"{self.dexscreener_url}/search?q=solana"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        logger.warning(f"DexScreener API returned status {response.status} for search endpoint")
                        return []
                    
                    data = await response.json()
                    
                    if not data or 'pairs' not in data:
                        logger.warning("No pairs data from DexScreener")
                        return []
                    
                    tokens = []
                    seen_addresses = set()
                    
                    # Process pairs and extract token data
                    for pair in data.get('pairs', [])[:limit*2]:  # Get more pairs to ensure we have enough unique tokens
                        if 'baseToken' not in pair or not pair['baseToken']:
                            continue
                        
                        address = pair['baseToken'].get('address')
                        
                        # Skip duplicates
                        if not address or address in seen_addresses:
                            continue
                        
                        # Only include Solana tokens
                        if pair.get('chainId') != 'solana':
                            continue
                            
                        seen_addresses.add(address)
                        
                        # Skip likely fake tokens
                        if is_fake_token(address):
                            continue
                        
                        # Create consistent token data structure
                        token_data = {
                            'address': address,
                            'symbol': pair['baseToken'].get('symbol', 'UNKNOWN'),
                            'name': pair['baseToken'].get('name', 'UNKNOWN'),
                            'price': {'value': float(pair.get('priceUsd', 0.0))},
                            'volume': {'value': float(pair.get('volume', {}).get('h24', 0.0))},
                            'liquidity': {'value': float(pair.get('liquidity', {}).get('usd', 0.0))},
                            'priceChange': {
                                '24H': float(pair.get('priceChange', {}).get('h24', 0.0)),
                                '6H': float(pair.get('priceChange', {}).get('h6', 0.0)) if 'h6' in pair.get('priceChange', {}) else 0.0,
                                '1H': float(pair.get('priceChange', {}).get('h1', 0.0)) if 'h1' in pair.get('priceChange', {}) else 0.0
                            },
                            'mc': {'value': float(pair.get('mcap', 0.0) if 'mcap' in pair else 0.0)},
                            'fdv': {'value': float(pair.get('fdv', 0.0) if 'fdv' in pair else 0.0)},
                            'holdersCount': int(pair.get('holders', 0) if 'holders' in pair else 0),
                            'trendingScore': 0.0  # Calculated below
                        }
                        
                        # Calculate a trending score based on volume and price activity
                        volume_24h = float(pair.get('volume', {}).get('h24', 0.0))
                        price_change_24h = abs(float(pair.get('priceChange', {}).get('h24', 0.0)))
                        
                        volume_score = min(100, volume_24h / 1000)  # Max score at $100K volume
                        price_score = min(100, price_change_24h * 2)  # Max score at 50% price change
                        token_data['trendingScore'] = (volume_score * 0.7) + (price_score * 0.3)
                        
                        tokens.append(token_data)
                        
                        # Stop if we have enough tokens
                        if len(tokens) >= limit:
                            break
                    
                    logger.info(f"Retrieved {len(tokens)} tokens from DexScreener")
                    return tokens
        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error fetching tokens from DexScreener: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching tokens from DexScreener: {e}")
            return []
    
    async def get_top_gainers(self, timeframe: str = '24h', limit: int = 10) -> List[Dict]:
        """
        Get list of top gaining tokens
        
        :param timeframe: Timeframe (1h, 6h, 24h)
        :param limit: Maximum number of tokens to return
        :return: List of top gainers
        """
        # Check cache
        cache_key = f"top_gainers_{timeframe}_{limit}"
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.cache_duration:
                return cache_entry['data']
        
        # Get tokens from DexScreener
        tokens = await self._get_tokens_from_dexscreener(50)  # Get more to filter from
        
        if not tokens:
            logger.warning(f"No tokens found for top gainers ({timeframe})")
            return []
        
        # Map timeframe to key in priceChange
        timeframe_key = '24H'
        if timeframe == '1h':
            timeframe_key = '1H'
        elif timeframe == '6h':
            timeframe_key = '6H'
        
        # Filter and sort by price change
        gainers = []
        for token in tokens:
            if 'priceChange' in token and timeframe_key in token['priceChange']:
                price_change = token['priceChange'][timeframe_key]
                if price_change > 0:
                    # Format token for consistent API response
                    gainers.append({
                        'contract_address': token['address'],
                        'ticker': token['symbol'],
                        'name': token['name'],
                        'price_change': price_change,
                        'price_usd': token['price']['value'],
                        'volume_24h': token['volume']['value'],
                        'liquidity_usd': token['liquidity']['value'],
                        'price_change_24h': token['priceChange'].get('24H', 0.0),
                        'price_change_6h': token['priceChange'].get('6H', 0.0),
                        'price_change_1h': token['priceChange'].get('1H', 0.0),
                        'mcap': token['mc']['value'],
                        'holders': token['holdersCount'],
                        'fdv': token['fdv']['value']
                    })
        
        # Sort by price change for the requested timeframe
        gainers.sort(key=lambda x: x['price_change'], reverse=True)
        
        # Limit to requested count
        result = gainers[:limit]
        
        # Cache result
        self.cache[cache_key] = {
            'timestamp': time.time(),
            'data': result
        }
        
        logger.info(f"Found {len(result)} top gainers for {timeframe}")
        return result
    
    async def get_trending_tokens(self, limit: int = 10) -> List[Dict]:
        """
        Get list of trending tokens based on volume and activity
        
        :param limit: Maximum number of tokens to return
        :return: List of trending tokens
        """
        # Check cache
        cache_key = f"trending_tokens_{limit}"
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.cache_duration:
                return cache_entry['data']
        
        # Get tokens from DexScreener and calculate trending score
        tokens = await self._get_tokens_from_dexscreener(50)
        
        if not tokens:
            logger.warning("No tokens found for trending tokens")
            return []
        
        # Format tokens for consistent API response
        trending_tokens = []
        for token in tokens:
            trending_tokens.append({
                'contract_address': token['address'],
                'ticker': token['symbol'],
                'name': token['name'],
                'volume_24h': token['volume']['value'],
                'price_usd': token['price']['value'],
                'price_change_24h': token['priceChange'].get('24H', 0.0),
                'liquidity_usd': token['liquidity']['value'],
                'trending_score': token.get('trendingScore', 0.0),
                'mcap': token['mc']['value'],
                'holders': token['holdersCount'],
                'fdv': token['fdv']['value']
            })
        
        # Sort by trending score
        trending_tokens.sort(key=lambda x: x.get('trending_score', 0), reverse=True)
        
        # Limit to requested count
        result = trending_tokens[:limit]
        
        # Cache result
        self.cache[cache_key] = {
            'timestamp': time.time(),
            'data': result
        }
        
        logger.info(f"Found {len(result)} trending tokens")
        return result
    
    async def get_token_security_info(self, contract_address: str) -> Optional[Dict]:
        """
        Get security information for a token (DexScreener doesn't provide this)
        
        :param contract_address: Token contract address
        :return: Security information or None
        """
        # DexScreener doesn't provide security info, so create a basic check
        token_info = await self.get_token_info(contract_address)
        
        if not token_info:
            return None
        
        # Calculate a basic security score based on liquidity, holders, etc.
        liquidity = token_info.get('liquidity', {}).get('value', 0.0)
        holders = token_info.get('holdersCount', 0)
        volume = token_info.get('volume', {}).get('value', 0.0)
        
        # Higher values are better
        liquidity_score = min(40, (liquidity / 10000))  # 40 points max for liquidity
        holders_score = min(30, (holders / 10))         # 30 points max for holders
        volume_score = min(30, (volume / 5000))         # 30 points max for volume
        
        security_score = liquidity_score + holders_score + volume_score
        
        # Basic security info
        return {
            'securityScore': security_score,
            'liquidityLocked': liquidity > 100000,  # Assume locked if high liquidity
            'mintingDisabled': False,               # Unknown from DexScreener
            'isMemeToken': 'meme' in token_info.get('name', '').lower() or 'meme' in token_info.get('symbol', '').lower()
        }