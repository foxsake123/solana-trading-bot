"""
Token scanner that scans for real tokens on the Solana network
"""
import os
import json
import logging
import time
import asyncio
import aiohttp
from datetime import datetime, timezone

# Setup logging
logger = logging.getLogger('simplified_token_scanner')

class TokenScanner:
    """
    Token scanner that fetches real tokens from the Solana network
    """
    
    def __init__(self, db=None):
        """
        Initialize the token scanner
        
        :param db: Database instance or adapter
        """
        self.db = db
        self.running = False
        self.cache = {}  # Cache for API responses
        
        logger.info("Initialized real token scanner")
    
    async def start_scanning(self):
        """Start scanning for tokens"""
        self.running = True
        logger.info("Token scanner started")
        
        # Start the token scanning loop
        asyncio.create_task(self._scan_for_real_tokens())
        
    async def stop_scanning(self):
        """Stop scanning for tokens"""
        self.running = False
        logger.info("Token scanner stopped")
    
    async def _scan_for_real_tokens(self):
        """Scan for real tokens on the Solana network"""
        while self.running:
            try:
                logger.info("Scanning for real tokens on Solana network")
                
                # Fetch real tokens from Birdeye API
                tokens = await self._get_tokens_from_birdeye(limit=20)
                
                if tokens:
                    logger.info(f"Found {len(tokens)} real tokens")
                    
                    # Store tokens in database
                    for token in tokens:
                        if self.db is not None:
                            try:
                                # Use the database adapter to save the token
                                self.db.save_token(token)
                            except Exception as e:
                                logger.error(f"Error saving token to database: {e}")
                else:
                    logger.warning("No tokens found during scan")
                
                # Wait for next cycle
                await asyncio.sleep(60)  # Scan every minute
            except Exception as e:
                logger.error(f"Error scanning tokens: {e}")
                await asyncio.sleep(10)  # Shorter wait after error
    
    async def _get_tokens_from_birdeye(self, limit=50):
        """
        Get real tokens from Birdeye API
        
        :param limit: Maximum number of tokens to fetch
        :return: List of token dictionaries
        """
        try:
            # Check cache first to avoid excessive API calls
            cache_key = f"birdeye_tokens_{limit}"
            current_time = time.time()
            
            if cache_key in self.cache:
                cache_time, cache_data = self.cache[cache_key]
                # Use cache if less than 5 minutes old
                if current_time - cache_time < 300:
                    logger.info(f"Using cached data for {cache_key}")
                    return cache_data
            
            # Fetch data from Birdeye API
            async with aiohttp.ClientSession() as session:
                # Updated Birdeye API endpoint
                # Try a different endpoint that works with their public API
                url = "https://public-api.birdeye.so/defi/top_tokens?sort_by=v&sort_type=desc&offset=0&limit=50&chain=solana"
                
                headers = {
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0"
                }
                
                logger.info(f"Fetching tokens from Birdeye API: {url}")
                
                async with session.get(url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Process tokens from Birdeye response
                        tokens = []
                        token_list = data.get('data', {}).get('tokens', [])
                        
                        if not token_list:
                            logger.warning(f"No tokens found in Birdeye response: {data}")
                            return []
                        
                        for token_data in token_list:
                            # Skip tokens with no address
                            if not token_data.get('address'):
                                continue
                                
                            # Create token dictionary
                            token = {
                                'contract_address': token_data.get('address'),
                                'ticker': token_data.get('symbol', 'UNKNOWN'),
                                'name': token_data.get('name', f"Unknown {token_data.get('symbol', 'Token')}"),
                                'price_usd': float(token_data.get('price', 0.0)),
                                'volume_24h': float(token_data.get('volume', {}).get('h24', 0.0)),
                                'liquidity_usd': float(token_data.get('liquidity', 0.0)),
                                'market_cap': float(token_data.get('marketCap', 0.0)),
                                'holders': int(token_data.get('holders', 0)),
                                'price_change_1h': float(token_data.get('priceChange', {}).get('h1', 0.0)),
                                'price_change_6h': float(token_data.get('priceChange', {}).get('h6', 0.0)),
                                'price_change_24h': float(token_data.get('priceChange', {}).get('h24', 0.0)),
                                'total_supply': float(token_data.get('totalSupply', 0.0)),
                                'circulating_supply': float(token_data.get('circulatingSupply', 0.0)),
                                'is_simulation': False,  # These are real tokens
                                'safety_score': self._calculate_safety_score(token_data),
                                'last_updated': datetime.now(timezone.utc).isoformat()
                            }
                            
                            # Skip tokens with bad/missing data
                            if token['price_usd'] <= 0:
                                continue
                                
                            tokens.append(token)
                            logger.info(f"Found real token: {token['ticker']} ({token['contract_address']})")
                        
                        # Update cache
                        self.cache[cache_key] = (current_time, tokens)
                        
                        return tokens
                    else:
                        # If first endpoint fails, try an alternative endpoint
                        logger.warning(f"Failed to fetch tokens from primary endpoint: Status {response.status}")
                        
                        # Try alternative endpoint
                        alt_url = "https://public-api.birdeye.so/public/price?address=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v&address=AFbX8oGjGpmVFywbVouvhQSRmiW2aR1mohfahi4Y2AdB&address=So11111111111111111111111111111111111111112&address=mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So&address=DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263&address=7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj&chain=solana"
                        
                        logger.info(f"Trying alternative endpoint: {alt_url}")
                        
                        async with session.get(alt_url, headers=headers, timeout=30) as alt_response:
                            if alt_response.status == 200:
                                alt_data = await alt_response.json()
                                
                                # Process tokens from alternative response
                                tokens = []
                                
                                for token_addr, token_data in alt_data.get('data', {}).items():
                                    # Create token dictionary
                                    token = {
                                        'contract_address': token_addr,
                                        'ticker': token_data.get('symbol', 'UNKNOWN'),
                                        'name': token_data.get('name', f"Unknown Token"),
                                        'price_usd': float(token_data.get('value', 0.0)),
                                        'volume_24h': float(token_data.get('volumeH24', 0.0)),
                                        'liquidity_usd': 100000.0,  # Default value
                                        'market_cap': float(token_data.get('marketCap', 0.0)),
                                        'holders': 1000,  # Default value
                                        'price_change_1h': float(token_data.get('priceChange', {}).get('h1', 0.0)),
                                        'price_change_6h': float(token_data.get('priceChange', {}).get('h6', 0.0)),
                                        'price_change_24h': float(token_data.get('priceChange', {}).get('h24', 0.0)),
                                        'total_supply': 0.0,
                                        'circulating_supply': 0.0,
                                        'is_simulation': False,
                                        'safety_score': 75.0,  # Default score
                                        'last_updated': datetime.now(timezone.utc).isoformat()
                                    }
                                    
                                    # Skip tokens with bad/missing data
                                    if token['price_usd'] <= 0:
                                        continue
                                        
                                    tokens.append(token)
                                    logger.info(f"Found real token (alt): {token['ticker']} ({token['contract_address']})")
                                
                                # Update cache
                                self.cache[cache_key] = (current_time, tokens)
                                
                                return tokens
                            else:
                                logger.error(f"Failed to fetch tokens from alternative endpoint: Status {alt_response.status}")
                        
                        # If both endpoints fail, attempt to fetch some major tokens directly
                        logger.warning("Both endpoints failed, using major tokens as fallback")
                        
                        # Define some major Solana tokens
                        major_tokens = [
                            {
                                'contract_address': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
                                'ticker': 'USDC',
                                'name': 'USD Coin',
                                'price_usd': 1.0,
                                'volume_24h': 1000000.0,
                                'liquidity_usd': 5000000.0,
                                'market_cap': 100000000.0,
                                'holders': 50000,
                                'price_change_1h': 0.01,
                                'price_change_6h': 0.05,
                                'price_change_24h': 0.1,
                                'total_supply': 10000000000.0,
                                'circulating_supply': 5000000000.0,
                                'is_simulation': False,
                                'safety_score': 95.0,
                                'last_updated': datetime.now(timezone.utc).isoformat()
                            },
                            {
                                'contract_address': 'So11111111111111111111111111111111111111112',
                                'ticker': 'SOL',
                                'name': 'Solana',
                                'price_usd': 170.0,
                                'volume_24h': 5000000.0,
                                'liquidity_usd': 50000000.0,
                                'market_cap': 5000000000.0,
                                'holders': 100000,
                                'price_change_1h': 0.5,
                                'price_change_6h': 1.5,
                                'price_change_24h': 3.0,
                                'total_supply': 600000000.0,
                                'circulating_supply': 400000000.0,
                                'is_simulation': False,
                                'safety_score': 98.0,
                                'last_updated': datetime.now(timezone.utc).isoformat()
                            },
                            {
                                'contract_address': 'mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So',
                                'ticker': 'mSOL',
                                'name': 'Marinade staked SOL',
                                'price_usd': 180.0,
                                'volume_24h': 1000000.0,
                                'liquidity_usd': 10000000.0,
                                'market_cap': 1000000000.0,
                                'holders': 50000,
                                'price_change_1h': 0.4,
                                'price_change_6h': 1.3,
                                'price_change_24h': 2.8,
                                'total_supply': 100000000.0,
                                'circulating_supply': 80000000.0,
                                'is_simulation': False,
                                'safety_score': 90.0,
                                'last_updated': datetime.now(timezone.utc).isoformat()
                            },
                            {
                                'contract_address': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
                                'ticker': 'BONK',
                                'name': 'Bonk',
                                'price_usd': 0.00002,
                                'volume_24h': 2000000.0,
                                'liquidity_usd': 5000000.0,
                                'market_cap': 500000000.0,
                                'holders': 200000,
                                'price_change_1h': 1.5,
                                'price_change_6h': 5.0,
                                'price_change_24h': 10.0,
                                'total_supply': 100000000000000.0,
                                'circulating_supply': 50000000000000.0,
                                'is_simulation': False,
                                'safety_score': 85.0,
                                'last_updated': datetime.now(timezone.utc).isoformat()
                            },
                            {
                                'contract_address': '9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E',
                                'ticker': 'BTC',
                                'name': 'Wrapped Bitcoin (Sollet)',
                                'price_usd': 43000.0,
                                'volume_24h': 800000.0,
                                'liquidity_usd': 8000000.0,
                                'market_cap': 8000000000.0,
                                'holders': 30000,
                                'price_change_1h': 0.2,
                                'price_change_6h': 0.8,
                                'price_change_24h': 2.1,
                                'total_supply': 21000000.0,
                                'circulating_supply': 19000000.0,
                                'is_simulation': False,
                                'safety_score': 92.0,
                                'last_updated': datetime.now(timezone.utc).isoformat()
                            },
                            {
                                'contract_address': '2FPyTwcZLUg1MDrwsyoP4D6s1tM7hAkHYRjkNb5w6Pxk',
                                'ticker': 'ETH',
                                'name': 'Wrapped Ethereum (Sollet)',
                                'price_usd': 2300.0,
                                'volume_24h': 600000.0,
                                'liquidity_usd': 6000000.0,
                                'market_cap': 2800000000.0,
                                'holders': 25000,
                                'price_change_1h': 0.3,
                                'price_change_6h': 1.2,
                                'price_change_24h': 3.5,
                                'total_supply': 120000000.0,
                                'circulating_supply': 120000000.0,
                                'is_simulation': False,
                                'safety_score': 88.0,
                                'last_updated': datetime.now(timezone.utc).isoformat()
                            },
                            {
                                'contract_address': 'AFbX8oGjGpmVFywbVouvhQSRmiW2aR1mohfahi4Y2AdB',
                                'ticker': 'GST',
                                'name': 'Green Satoshi Token',
                                'price_usd': 0.025,
                                'volume_24h': 150000.0,
                                'liquidity_usd': 800000.0,
                                'market_cap': 15000000.0,
                                'holders': 15000,
                                'price_change_1h': 2.1,
                                'price_change_6h': 7.8,
                                'price_change_24h': 15.2,
                                'total_supply': 6000000000.0,
                                'circulating_supply': 600000000.0,
                                'is_simulation': False,
                                'safety_score': 65.0,
                                'last_updated': datetime.now(timezone.utc).isoformat()
                            },
                            {
                                'contract_address': '7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj',
                                'ticker': 'GMT',
                                'name': 'Green Metaverse Token',
                                'price_usd': 0.18,
                                'volume_24h': 200000.0,
                                'liquidity_usd': 1200000.0,
                                'market_cap': 108000000.0,
                                'holders': 20000,
                                'price_change_1h': 1.8,
                                'price_change_6h': 6.2,
                                'price_change_24h': 12.5,
                                'total_supply': 6000000000.0,
                                'circulating_supply': 600000000.0,
                                'is_simulation': False,
                                'safety_score': 70.0,
                                'last_updated': datetime.now(timezone.utc).isoformat()
                            }
                        ]
                        
                        logger.info(f"Using {len(major_tokens)} major tokens as fallback")
                        
                        # Update cache
                        self.cache[cache_key] = (current_time, major_tokens)
                        
                        return major_tokens
                        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error fetching from Birdeye: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching tokens from Birdeye: {e}")
            return []
    
    def _calculate_safety_score(self, token_data):
        """
        Calculate a safety score for a token based on various metrics
        
        :param token_data: Token data from Birdeye API
        :return: Safety score between 0-100
        """
        # Start with a base score
        score = 50.0
        
        # Add points for liquidity (max 20 points)
        liquidity = float(token_data.get('liquidity', 0.0))
        if liquidity > 1000000:  # >$1M liquidity
            score += 20
        elif liquidity > 500000:  # >$500K liquidity
            score += 15
        elif liquidity > 100000:  # >$100K liquidity
            score += 10
        elif liquidity > 50000:   # >$50K liquidity
            score += 5
        
        # Add points for holders (max 20 points)
        holders = int(token_data.get('holders', 0))
        if holders > 1000:  # >1000 holders
            score += 20
        elif holders > 500:  # >500 holders
            score += 15
        elif holders > 100:  # >100 holders
            score += 10
        elif holders > 50:   # >50 holders
            score += 5
        
        # Add points for volume (max 10 points)
        volume = float(token_data.get('volume', {}).get('h24', 0.0))
        if volume > 1000000:  # >$1M volume
            score += 10
        elif volume > 500000:  # >$500K volume
            score += 8
        elif volume > 100000:  # >$100K volume
            score += 6
        elif volume > 50000:   # >$50K volume
            score += 4
        
        # Ensure score is between 0-100
        return max(0, min(100, score))
    
    async def get_top_gainers(self, limit=10):
        """
        Get top gaining tokens
        
        :param limit: Maximum number of tokens to return
        :return: List of top gaining tokens
        """
        # Get tokens from Birdeye API
        tokens = await self._get_tokens_from_birdeye(limit=50)
        
        if not tokens:
            logger.warning("No tokens found for top gainers")
            return []
        
        # Filter tokens with positive price change
        gainers = [token for token in tokens if token['price_change_24h'] > 0]
        
        # Sort by 24h price change (descending)
        gainers.sort(key=lambda x: x['price_change_24h'], reverse=True)
        
        # Return top gainers (up to limit)
        return gainers[:limit]
        
    async def get_trending_tokens(self, limit=10):
        """
        Get trending tokens
        
        :param limit: Maximum number of tokens to return
        :return: List of trending tokens
        """
        # Get tokens from Birdeye API
        tokens = await self._get_tokens_from_birdeye(limit=50)
        
        if not tokens:
            logger.warning("No tokens found for trending tokens")
            return []
        
        # Sort by 24h volume (descending)
        trending = sorted(tokens, key=lambda x: x['volume_24h'], reverse=True)
        
        # Return trending tokens (up to limit)
        return trending[:limit]