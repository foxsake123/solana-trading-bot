import tweepy
import time
import logging
import asyncio
import json
from typing import Dict, Optional, List
from datetime import datetime, timedelta, UTC
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from config import BotConfiguration
from utils import fetch_with_retries, is_valid_solana_address, is_fake_token

logger = logging.getLogger('trading_bot.token_analyzer')

class TokenAnalyzer:
    """
    Analyzes tokens for trading potential
    """
    def __init__(self):
        """
        Initialize token analyzer
        """
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self.twitter_client = self._setup_twitter_client()
        self.twitter_requests_this_window = 0
        self.twitter_window_reset = int(time.time()) + 900
        self.social_media_cache = {}
        self.price_cache = {}  # Cache for token prices
        
    def _setup_twitter_client(self) -> Optional[tweepy.Client]:
        """
        Set up Twitter API client
        
        :return: Configured Twitter client or None
        """
        try:
            bearer_token = BotConfiguration.API_KEYS['TWITTER_BEARER_TOKEN']
            if not bearer_token:
                logger.warning("Twitter bearer token not provided")
                return None
            
            client = tweepy.Client(bearer_token=bearer_token)
            logger.debug("Twitter client initialized for token analyzer")
            return client
        
        except Exception as e:
            logger.error(f"Failed to set up Twitter client for token analyzer: {e}")
            return None

    async def get_top_gainers(self, timeframe: str = '24h', limit: int = 10) -> List[Dict]:
        """
        Get top gaining tokens for a given timeframe with multiple fallbacks
        
        :param timeframe: Timeframe to check ('1h', '6h', '24h')
        :param limit: Maximum number of tokens to return
        :return: List of top gainer tokens
        """
        # Try DexScreener first
        tokens = await self._get_top_gainers_dexscreener(timeframe, limit)
        
        # If DexScreener fails, try Birdeye
        if not tokens:
            tokens = await self._get_top_gainers_birdeye(timeframe, limit)
        
        # Return whatever tokens we found
        return tokens

    async def _get_top_gainers_dexscreener(self, timeframe: str = '24h', limit: int = 10) -> List[Dict]:
        """
        Get top gaining tokens from DexScreener
        
        :param timeframe: Timeframe to check ('1h', '6h', '24h')
        :param limit: Maximum number of tokens to return
        :return: List of top gainer tokens
        """
        # Fetch top tokens from DexScreener
        dex_url = f"{BotConfiguration.API_KEYS['DEXSCREENER_BASE_URL']}/latest/dex/tokens/solana"
        headers = {
            'accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        data = await fetch_with_retries(dex_url, headers=headers)
        
        if not data or 'tokens' not in data:
            logger.warning("No DexScreener data for top gainers")
            return []
        
        # Process tokens
        tokens = []
        for token in data['tokens']:
            if 'pairs' not in token or not token['pairs']:
                continue
                
            # Get the most liquid pair
            pair = token['pairs'][0]
            
            # Get price change for requested timeframe
            price_change = 0.0
            if timeframe == '1h' and 'h1' in pair.get('priceChange', {}):
                price_change = float(pair['priceChange']['h1'])
            elif timeframe == '6h' and 'h6' in pair.get('priceChange', {}):
                price_change = float(pair['priceChange']['h6'])
            elif timeframe == '24h' and 'h24' in pair.get('priceChange', {}):
                price_change = float(pair['priceChange']['h24'])
            else:
                # Default to 24h if specified timeframe not available
                price_change = float(pair.get('priceChange', {}).get('h24', 0.0))
            
            # Skip tokens with no price change or negative change
            if price_change <= 0:
                continue
                
            # Get token data
            token_data = {
                'contract_address': token.get('address'),
                'ticker': pair.get('baseToken', {}).get('symbol', 'UNKNOWN'),
                'name': pair.get('baseToken', {}).get('name', 'UNKNOWN'),
                'price_change': price_change,
                'price_usd': float(pair.get('priceUsd', 0.0)),
                'volume_24h': float(pair.get('volume', {}).get('h24', 0.0)),
                'liquidity_usd': float(pair.get('liquidity', {}).get('usd', 0.0))
            }
            
            tokens.append(token_data)
        
        # Sort by price change (descending)
        tokens.sort(key=lambda x: x['price_change'], reverse=True)
        
        # Return top tokens
        return tokens[:limit]

    async def _get_top_gainers_birdeye(self, timeframe: str = '24h', limit: int = 10) -> List[Dict]:
        """
        Get top gaining tokens from Birdeye's Gainers/Losers API
        
        :param timeframe: Timeframe to check ('1h', '6h', '24h')
        :param limit: Maximum number of tokens to return
        :return: List of top gainer tokens
        """
        try:
            # Map timeframe to type parameter
            type_param = "1W"  # Default to 1 week
            if timeframe == '1h':
                type_param = "1H"
            elif timeframe == '6h':
                type_param = "6H"
            elif timeframe == '24h':
                type_param = "1D"
            
            # Use the dedicated Gainers/Losers API
            url = "https://public-api.birdeye.so/trader/gainers-losers"
            request_params = {
                "type": type_param,     # Time period (1H, 6H, 1D, 1W)
                "sort_by": "PnL",       # Sort by profit and loss
                "sort_type": "desc",    # Descending order (highest first)
                "offset": 0,
                "limit": limit
            }
            headers = {
                'X-API-KEY': '0c3bf6741a634dd38d4a129b52666d4c',  # Public API key
                'x-chain': 'solana',
                'accept': 'application/json'
            }
            
            data = await fetch_with_retries(url, headers=headers, params=request_params)
            
            if not data or 'data' not in data or not data.get('data'):
                logger.warning(f"No Birdeye data for top gainers ({timeframe})")
                return []
            
            tokens = []
            for token_info in data['data']:
                # Get token data
                token_data = {
                    'contract_address': token_info.get('address'),
                    'ticker': token_info.get('symbol', 'UNKNOWN'),
                    'name': token_info.get('name', 'UNKNOWN'),
                    'price_change': float(token_info.get('priceChange', 0.0)),
                    'price_usd': float(token_info.get('price', 0.0)),
                    'volume_24h': float(token_info.get('volume', 0.0)),
                    'liquidity_usd': float(token_info.get('liquidity', 0.0))
                }
                
                # Only include positive price changes
                if token_data['price_change'] > 0:
                    tokens.append(token_data)
            
            # Double-check sorting by price change (descending)
            tokens.sort(key=lambda x: x['price_change'], reverse=True)
            
            # Return top tokens
            return tokens[:limit]
        
        except Exception as e:
            logger.error(f"Error fetching top gainers from Birdeye: {e}")
            return []    

    async def get_trending_tokens(self, limit: int = 10) -> List[Dict]:
        """
        Get trending tokens based on volume and social activity with multiple fallbacks
        
        :param limit: Maximum number of tokens to return
        :return: List of trending tokens
        """
        # Try Birdeye first (more reliable)
        tokens = await self._get_trending_tokens_birdeye(limit)
        
        # If Birdeye fails, try DexScreener
        if not tokens:
            tokens = await self._get_trending_tokens_dexscreener(limit)
        
        # Return whatever tokens we found
        logger.info(f"Found {len(tokens)} trending tokens")
        return tokens

    async def _get_trending_tokens_birdeye(self, limit: int = 10) -> List[Dict]:
        """
        Get trending tokens from Birdeye API
        
        :param limit: Maximum number of tokens to return
        :return: List of trending tokens
        """
        try:
            url = "https://public-api.birdeye.so/defi/token_trending"
            request_params = {
                "sort_by": "rank",      # As per Birdeye docs
                "sort_type": "asc",     # Ascending order (lower rank = more trending)
                "offset": 0,
                "limit": limit
            }
            headers = {
                'X-API-KEY': '0c3bf6741a634dd38d4a129b52666d4c',  # Your public API key
                'x-chain': 'solana',
                'accept': 'application/json'
            }
            
            data = await fetch_with_retries(url, headers=headers, params=request_params)
            
            if not data or 'data' not in data or 'tokens' not in data.get('data', {}):
                logger.warning("No valid data from Birdeye token trending endpoint")
                return await self._get_trending_tokens_birdeye_alt(limit)
            
            tokens = []
            for token_info in data['data']['tokens']:
                # Skip SOL and stablecoins
                if token_info.get('symbol') in ['SOL', 'USDC', 'USDT']:
                    continue
                    
                volume_24h = float(token_info.get('volume24hUSD', 0.0))
                
                # Skip tokens with very low volume
                if volume_24h < 10000:  # $10K minimum
                    continue
                
                token_data = {
                    'contract_address': token_info.get('address'),
                    'ticker': token_info.get('symbol', 'UNKNOWN'),
                    'name': token_info.get('name', 'UNKNOWN'),
                    'volume_24h': volume_24h,
                    'price_usd': float(token_info.get('price', 0.0)),
                    'price_change_24h': float(token_info.get('volume24hChangePercent', 0.0)),
                    'liquidity_usd': float(token_info.get('liquidity', 0.0)),
                    'trending_score': float(token_info.get('rank', 0.0))  # Using rank as trending score
                }
                
                tokens.append(token_data)
            
            # Sort by rank (ascending - lower rank is more trending)
            tokens.sort(key=lambda x: x['trending_score'])
            
            return tokens[:limit]
        
        except Exception as e:
            logger.error(f"Error fetching trending tokens from Birdeye: {e}")
            return await self._get_trending_tokens_birdeye_alt(limit)

    async def _get_top_gainers_birdeye(self, timeframe: str = '24h', limit: int = 10) -> List[Dict]:
        """
        Get top gaining tokens from Birdeye's Gainers/Losers API
        
        :param timeframe: Timeframe to check ('1h', '6h', '24h')
        :param limit: Maximum number of tokens to return
        :return: List of top gainer tokens
        """
        try:
            # Map timeframe to Birdeye's type parameter
            timeframe_map = {
                '1h': 'hour',
                '6h': '6hour',
                '24h': 'today'
            }
            type_param = timeframe_map.get(timeframe, 'today')  # Default to 24h
            
            url = "https://public-api.birdeye.so/trader/gainers-losers"
            request_params = {
                "type": type_param,     # Correct timeframe parameter
                "sort_by": "PnL",       # Sort by profit and loss
                "sort_type": "desc",    # Descending order (highest gains first)
                "offset": 0,
                "limit": limit
            }
            headers = {
                'X-API-KEY': '0c3bf6741a634dd38d4a129b52666d4c',
                'x-chain': 'solana',
                'accept': 'application/json'
            }
            
            data = await fetch_with_retries(url, headers=headers, params=request_params)
            
            if not data or 'data' not in data or not data.get('data'):
                logger.warning(f"No valid Birdeye data for top gainers ({timeframe})")
                return []
            
            tokens = []
            for token_info in data['data']:
                price_change = float(token_info.get('priceChange', 0.0))
                # Only include positive price changes
                if price_change <= 0:
                    continue
                    
                token_data = {
                    'contract_address': token_info.get('address'),
                    'ticker': token_info.get('symbol', 'UNKNOWN'),
                    'name': token_info.get('name', 'UNKNOWN'),
                    'price_change': price_change,
                    'price_usd': float(token_info.get('price', 0.0)),
                    'volume_24h': float(token_info.get('volume', 0.0)),
                    'liquidity_usd': float(token_info.get('liquidity', 0.0))
                }
                
                tokens.append(token_data)
            
            # Sort by price change (descending)
            tokens.sort(key=lambda x: x['price_change'], reverse=True)
            
            return tokens[:limit]
        
        except Exception as e:
            logger.error(f"Error fetching top gainers from Birdeye: {e}")
            return []
   

    async def _get_trending_tokens_birdeye_alt(self, limit: int = 10) -> List[Dict]:
        """
        Alternative method to get trending tokens from Birdeye
        
        :param limit: Maximum number of tokens to return
        :return: List of trending tokens
        """
        try:
            # Use the V3 token list endpoint
            url = "https://public-api.birdeye.so/defi/tokenlist"
            request_params = {
                "sort_by": "volume24hUSD",  # Sort by 24h volume
                "sort_type": "desc",        # Descending order (highest first)
                "offset": 0,
                "limit": limit
            }
            headers = {
                'X-API-KEY': '0c3bf6741a634dd38d4a129b52666d4c',  # Public API key for development
                'x-chain': 'solana',
                'accept': 'application/json'
            }
            
            data = await fetch_with_retries(url, headers=headers, params=request_params)
            
            if not data or 'data' not in data or 'tokens' not in data.get('data', {}):
                logger.warning("No data from Birdeye token list endpoint")
                return []
            
            tokens = []
            for token_info in data['data']['tokens']:
                # Skip SOL and stablecoins
                if token_info.get('symbol') in ['SOL', 'USDC', 'USDT']:
                    continue
                    
                # Get token data
                volume_24h = float(token_info.get('volume24hUSD', 0.0))
                
                # Skip tokens with very low volume
                if volume_24h < 10000:  # $10K minimum
                    continue
                
                token_data = {
                    'contract_address': token_info.get('address'),
                    'ticker': token_info.get('symbol', 'UNKNOWN'),
                    'name': token_info.get('name', 'UNKNOWN'),
                    'volume_24h': volume_24h,
                    'price_usd': float(token_info.get('price', 0.0)),
                    'price_change_24h': float(token_info.get('priceChange24h', 0.0)),
                    'liquidity_usd': float(token_info.get('liquidity', 0.0)),
                    'trending_score': volume_24h / 1000  # Simple score based on volume
                }
                
                tokens.append(token_data)
            
            # Return top tokens by volume
            return tokens[:limit]
        
        except Exception as e:
            logger.error(f"Error fetching trending tokens from Birdeye alternative method: {e}")
            return []

    async def _get_trending_tokens_dexscreener(self, limit: int = 10) -> List[Dict]:
        """
        Get trending tokens from DexScreener with improved methods
        
        :param limit: Maximum number of tokens to return
        :return: List of trending tokens
        """
        # First try DexScreener's v1 API for pairs
        dex_urls = [
            # First try the latest tokens endpoint (more likely to work)
            f"{BotConfiguration.API_KEYS['DEXSCREENER_BASE_URL']}/latest/dex/tokens/solana",
            # Alternative: try the v1 API
            f"{BotConfiguration.API_KEYS['DEXSCREENER_BASE_URL']}/v1/dex/tokens/solana"
        ]
        
        # Use a more complete browser-like User-Agent to avoid being blocked
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.5',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'origin': 'https://dexscreener.com',
            'referer': 'https://dexscreener.com/solana',
            'connection': 'keep-alive',
            'upgrade-insecure-requests': '1',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'cache-control': 'max-age=0'
        }
        
        data = None
        
        # Try each URL in sequence
        for url in dex_urls:
            try:
                data = await fetch_with_retries(url, headers=headers, max_retries=3, base_delay=2)
                if data and ('pairs' in data or 'tokens' in data):
                    logger.info(f"Successfully fetched DexScreener data from {url}")
                    break
            except Exception as e:
                logger.warning(f"Error fetching from {url}: {e}")
        
        if not data:
            logger.warning("No data from any DexScreener endpoint")
            return []
        
        # Process tokens
        tokens = []
        
        # Handle different API response formats
        if 'tokens' in data:
            # Handle tokens endpoint format
            for token in data['tokens']:
                if 'pairs' not in token or not token['pairs']:
                    continue
                
                # Get the most liquid pair
                pair = token['pairs'][0]
                self._process_pair(tokens, token, pair)
                
        elif 'pairs' in data:
            # Handle pairs endpoint format
            seen_tokens = set()
            
            for pair in data['pairs']:
                # Extract token from baseToken
                if 'baseToken' not in pair or 'address' not in pair['baseToken']:
                    continue
                    
                token_address = pair['baseToken']['address']
                
                # Skip if we've already processed this token
                if token_address in seen_tokens:
                    continue
                    
                seen_tokens.add(token_address)
                
                # Create a token-like object to process
                token = {
                    'address': token_address,
                    'pairs': [pair]
                }
                
                self._process_pair(tokens, token, pair)
        
        # Sort by trending score (descending)
        tokens.sort(key=lambda x: x.get('trending_score', 0), reverse=True)
        
        # Print debug info
        if tokens:
            logger.info(f"Found {len(tokens)} trending tokens from DexScreener")
            for i, token in enumerate(tokens[:3]):
                logger.info(f"  Top token {i+1}: {token.get('ticker')} - Score: {token.get('trending_score'):.1f}")
        
        # Return top tokens
        return tokens[:limit]
    
    def _process_pair(self, tokens_list, token, pair):
        """Helper function to process a pair and extract token data"""
        # Skip tokens with very low volume
        volume_24h = float(pair.get('volume', {}).get('h24', 0.0))
        if volume_24h < 10000:  # $10K minimum
            return
            
        # Get token data
        token_data = {
            'contract_address': token.get('address'),
            'ticker': pair.get('baseToken', {}).get('symbol', 'UNKNOWN'),
            'name': pair.get('baseToken', {}).get('name', 'UNKNOWN'),
            'volume_24h': volume_24h,
            'price_usd': float(pair.get('priceUsd', 0.0)),
            'price_change_24h': float(pair.get('priceChange', {}).get('h24', 0.0)),
            'liquidity_usd': float(pair.get('liquidity', {}).get('usd', 0.0)),
            'trending_score': 0.0  # Will calculate below
        }
        
        # Calculate trending score based on volume and price activity
        volume_score = min(100, volume_24h / 1000)  # Max score at $100K volume
        price_change = abs(token_data['price_change_24h'])
        price_score = min(100, price_change * 2)  # Max score at 50% price change
        
        # Combine scores
        token_data['trending_score'] = (volume_score * 0.7) + (price_score * 0.3)
        
        tokens_list.append(token_data)

    async def get_current_price(self, contract_address: str) -> float:
        """
        Get current price of a token in USD
        
        :param contract_address: Token contract address
        :return: Token price in USD
        """
        try:
            # Check cache first
            cache_time = 300  # 5 minutes
            current_time = time.time()
            
            if contract_address in self.price_cache:
                cache_entry = self.price_cache[contract_address]
                if current_time - cache_entry['timestamp'] < cache_time:
                    return cache_entry['price']
            
            # Try to get price from Birdeye first
            headers = {
                'X-API-KEY': '0c3bf6741a634dd38d4a129b52666d4c',  # Public API key
                'x-chain': 'solana',
                'accept': 'application/json'
            }
            
            url = f"https://public-api.birdeye.so/defi/price?address={contract_address}"
            data = await fetch_with_retries(url, headers=headers)
            
            if data and 'success' in data and data['success'] and 'data' in data:
                price = float(data['data'].get('value', 0.0))
                
                # Store in cache
                self.price_cache[contract_address] = {
                    'price': price,
                    'timestamp': current_time
                }
                
                return price
            
            # Fall back to DexScreener
            url = f"{BotConfiguration.API_KEYS['DEXSCREENER_BASE_URL']}/v1/dex/tokens/{contract_address}"
            data = await fetch_with_retries(url)
            
            if data and 'pairs' in data and data['pairs']:
                price = float(data['pairs'][0].get('priceUsd', 0.0))
                
                # Store in cache
                self.price_cache[contract_address] = {
                    'price': price,
                    'timestamp': current_time
                }
                
                return price
                
            # No price found
            return 0.0
        
        except Exception as e:
            logger.error(f"Error getting current price for {contract_address}: {e}")
            return 0.0

    async def calculate_safety_score(self, contract_address: str) -> float:
        """
        Calculate safety score for a token
        
        :param contract_address: Token contract address
        :return: Safety score (0-100)
        """
        # Base score
        score = 50.0
        
        try:
            # Check for fake tokens
            if is_fake_token(contract_address):
                return 0.0
                
            # Get token data
            token_data = await self.fetch_token_data(contract_address)
            if not token_data:
                return score
                
            # Liquidity factor (higher is better)
            liquidity = token_data.get('liquidity_usd', 0)
            if liquidity >= 1000000:  # $1M+
                score += 20
            elif liquidity >= 250000:  # $250K+
                score += 15
            elif liquidity >= 100000:  # $100K+
                score += 10
            elif liquidity >= 50000:   # $50K+
                score += 5
            else:
                score -= 10  # Low liquidity is risky
                
            # Volume factor (higher is better)
            volume = token_data.get('volume_24h', 0)
            if volume >= 500000:  # $500K+
                score += 15
            elif volume >= 100000:  # $100K+
                score += 10
            elif volume >= 50000:   # $50K+
                score += 5
            elif volume < 10000:    # Very low volume
                score -= 15
                
            # Holders factor (more is better)
            holders = token_data.get('holders', 0)
            if holders >= 1000:
                score += 15
            elif holders >= 500:
                score += 10
            elif holders >= 100:
                score += 5
            elif holders < 50:
                score -= 15
                
            # Age factor (older is better)
            # Skip for now as we don't have reliable launch date
                
            # Cap the score
            score = max(0, min(100, score))
            return score
            
        except Exception as e:
            logger.error(f"Error calculating safety score for {contract_address}: {e}")
            return score

    async def fetch_token_data(self, contract_address: str) -> Optional[Dict]:
        """
        Fetch comprehensive token data from multiple sources
        
        :param contract_address: Token contract address
        :return: Token data dictionary or None
        """
        try:
            # Try to get token from database first
            db_token = self.db.get_token(contract_address)
            
            # Create initial token data
            token_data = {
                'contract_address': contract_address,
                'ticker': 'UNKNOWN',
                'name': 'UNKNOWN',
                'price_usd': 0.0,
                'volume_24h': 0.0,
                'liquidity_usd': 0.0,
                'mcap': 0.0,
                'holders': 0,
                'price_change_1h': 0.0,
                'price_change_6h': 0.0,
                'price_change_24h': 0.0,
                'safety_score': 50.0
            }
            
            # Update with database data if available
            if db_token:
                token_data.update({
                    'ticker': db_token.get('ticker', 'UNKNOWN'),
                    'name': db_token.get('name', 'UNKNOWN'),
                    'launch_date': db_token.get('launch_date'),
                    'safety_score': float(db_token.get('safety_score', 50.0))
                })
            
            # Get additional data from DexScreener
            try:
                url = f"{BotConfiguration.API_KEYS['DEXSCREENER_BASE_URL']}/v1/dex/tokens/{contract_address}"
                dex_data = await fetch_with_retries(url)
                
                if dex_data and 'pairs' in dex_data and dex_data['pairs']:
                    pair = dex_data['pairs'][0]
                    base_token = pair.get('baseToken', {})
                    
                    # Update token data
                    token_data.update({
                        'ticker': base_token.get('symbol', token_data['ticker']),
                        'name': base_token.get('name', token_data['name']),
                        'price_usd': float(pair.get('priceUsd', 0.0)),
                        'volume_24h': float(pair.get('volume', {}).get('h24', 0.0)),
                        'liquidity_usd': float(pair.get('liquidity', {}).get('usd', 0.0)),
                        'price_change_1h': float(pair.get('priceChange', {}).get('h1', 0.0)),
                        'price_change_6h': float(pair.get('priceChange', {}).get('h6', 0.0)),
                        'price_change_24h': float(pair.get('priceChange', {}).get('h24', 0.0))
                    })
                    
                    # Calculate market cap if supply is available
                    if 'fdv' in pair:
                        token_data['mcap'] = float(pair.get('fdv', 0.0))
            except Exception as e:
                logger.warning(f"Error fetching DexScreener data for {contract_address}: {e}")
            
            # Get additional data from Birdeye
            try:
                url = f"https://public-api.birdeye.so/defi/token_metadata?address={contract_address}"
                headers = {
                    'X-API-KEY': '0c3bf6741a634dd38d4a129b52666d4c',  # Public API key
                    'x-chain': 'solana',
                    'accept': 'application/json'
                }
                
                birdeye_data = await fetch_with_retries(url, headers=headers)
                
                if birdeye_data and 'success' in birdeye_data and birdeye_data['success'] and 'data' in birdeye_data:
                    data = birdeye_data['data']
                    
                    # Update token data
                    if 'holdersCount' in data:
                        token_data['holders'] = int(data.get('holdersCount', 0))
                    
                    # Update price if needed
                    if token_data['price_usd'] == 0.0 and 'value' in data:
                        token_data['price_usd'] = float(data.get('value', 0.0))
                    
                    # Update market cap if needed
                    if token_data['mcap'] == 0.0 and 'marketCap' in data:
                        token_data['mcap'] = float(data.get('marketCap', 0.0))
            except Exception as e:
                logger.warning(f"Error fetching Birdeye data for {contract_address}: {e}")
            
            # Update database with fresh data
            self.db.store_token(
                contract_address=token_data['contract_address'],
                ticker=token_data['ticker'],
                name=token_data['name'],
                launch_date=token_data.get('launch_date', datetime.now(UTC).isoformat()),
                volume_24h=token_data['volume_24h'],
                safety_score=token_data['safety_score'],
                liquidity_locked=(token_data['liquidity_usd'] > 25000)  # Assume locked if significant liquidity
            )
            
            return token_data
        
        except Exception as e:
            logger.error(f"Error fetching token data for {contract_address}: {e}")
            return None

    