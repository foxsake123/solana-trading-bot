import asyncio
import tweepy
import aiohttp
import re
import json
import time
import logging
from datetime import datetime, UTC
from typing import Dict, List, Optional, Set

from config import BotConfiguration
from database import Database
from token_analyzer import TokenAnalyzer
from utils import fetch_with_retries, is_valid_solana_address, is_fake_token

logger = logging.getLogger('trading_bot.token_scanner')

class TokenScanner:
    """
    Scans various sources to discover potential tokens for trading
    """
    
    def __init__(self):
        """
        Initialize token scanner
        """
        self.db = Database()
        self.analyzer = TokenAnalyzer()
        self.api_cache = {}
        self.twitter_client = self._setup_twitter_client()
        self.twitter_requests_this_window = 0
        self.twitter_window_reset = int(time.time()) + 900
        self.discovered_tokens = set()
    
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
            logger.info("Twitter client initialized")
            return client
        
        except Exception as e:
            logger.error(f"Failed to set up Twitter client: {e}")
            return None
    
    def _check_twitter_rate_limit(self):
        """
        Check Twitter rate limit and sleep if needed
        """
        current_time = int(time.time())
        
        # Reset counter if window expired
        if current_time > self.twitter_window_reset:
            self.twitter_requests_this_window = 0
            self.twitter_window_reset = current_time + 900
        
        # Sleep if approaching rate limit
        buffer = BotConfiguration.TRADING_PARAMETERS['TWITTER_RATE_LIMIT_BUFFER']
        if self.twitter_requests_this_window >= 175 - buffer:
            wait_time = self.twitter_window_reset - current_time + 5
            logger.warning(f"Twitter rate limit approaching. Sleeping for {wait_time} seconds.")
            time.sleep(wait_time)
            self.twitter_requests_this_window = 0
            self.twitter_window_reset = current_time + 900
    
    async def scan_twitter_for_tokens(self) -> Set[str]:
        """
        Scan Twitter for potential token mentions
        
        :return: Set of discovered token contract addresses
        """
        discovered_contracts = set()
        
        if not self.twitter_client:
            logger.warning("Twitter client not initialized. Skipping Twitter scan.")
            return discovered_contracts
        
        try:
            # Check rate limit
            self._check_twitter_rate_limit()
            
            # Search for tweets mentioning Solana memecoins
            query = "solana memecoin -is:retweet"
            tweets = self.twitter_client.search_recent_tweets(
                query=query,
                max_results=50,
                tweet_fields=['public_metrics', 'created_at']
            )
            self.twitter_requests_this_window += 1
            
            if not tweets.data:
                logger.info("No recent relevant tweets found.")
                return discovered_contracts
            
            for tweet in tweets.data:
                # Extract potential contract addresses
                words = tweet.text.split()
                for i, word in enumerate(words):
                    # Clean up word
                    word = word.strip('.,!?:;"\'()[]{}')
                    
                    # Check if word looks like a Solana address
                    if is_valid_solana_address(word):
                        # Filter out fake tokens
                        if is_fake_token(word):
                            logger.debug(f"Skipping likely fake token: {word}")
                            continue
                            
                        # Look for potential ticker nearby
                        ticker = "UNKNOWN"
                        for j in range(max(0, i-5), min(len(words), i+6)):
                            w = words[j].strip('.,!?:;"\'()[]{}')
                            if w.startswith('$') and w[1:].isalpha():
                                ticker = w[1:]
                                break
                            elif w.isupper() and len(w) >= 2 and len(w) <= 8 and w.isalpha():
                                ticker = w
                                break
                        
                        # Calculate engagement score
                        engagement = (
                            tweet.public_metrics.get('retweet_count', 0) +
                            tweet.public_metrics.get('like_count', 0) +
                            tweet.public_metrics.get('reply_count', 0) * 2
                        )
                        
                        # Store token in database
                        self.db.store_token(
                            contract_address=word,
                            ticker=ticker,
                            name="UNKNOWN",
                            launch_date=tweet.created_at.isoformat(),
                            safety_score=50.0 + (engagement / 10),  # Basic initial score
                            volume_24h=0.0
                        )
                        
                        discovered_contracts.add(word)
                        logger.debug(f"Discovered token from Twitter: {ticker} ({word})")
            
            logger.info(f"Discovered {len(discovered_contracts)} tokens from Twitter")
            return discovered_contracts
        
        except Exception as e:
            logger.error(f"Twitter scan failed: {e}")
            return discovered_contracts
    
    async def scan_dexscreener_for_launches(self) -> Set[str]:
        """
        Scan DexScreener for new token launches
        
        :return: Set of discovered token contract addresses
        """
        discovered_contracts = set()
        
        try:
            # Scan for latest tokens (NOT pairs/solana which doesn't work)
            url = f"{BotConfiguration.API_KEYS['DEXSCREENER_BASE_URL']}/latest/dex/tokens/solana"
            data = await fetch_with_retries(url)
            
            if not data or 'tokens' not in data or not data['tokens']:
                logger.warning("Invalid DexScreener response")
                return discovered_contracts
            
            # Process recent tokens
            for token in data['tokens'][:50]:  # Focus on most recent 50 tokens
                contract_address = token.get('address')
                
                if not contract_address or not is_valid_solana_address(contract_address):
                    continue
                
                # Filter out fake tokens
                if is_fake_token(contract_address):
                    logger.debug(f"Skipping likely fake token: {contract_address}")
                    continue
                
                ticker = token.get('symbol', 'UNKNOWN')
                name = token.get('name', ticker)
                
                # Set launch date to now (DexScreener doesn't provide this)
                launch_date = datetime.now(UTC).isoformat()
                
                # Get volume if available from pairs
                volume_24h = 0.0
                if 'pairs' in token and token['pairs']:
                    first_pair = token['pairs'][0]
                    volume_24h = float(first_pair.get('volume', {}).get('h24', 0.0))
                    
                    # Use more accurate creation date if available
                    if 'pairCreatedAt' in first_pair:
                        timestamp = first_pair.get('pairCreatedAt')
                        launch_date = datetime.fromtimestamp(timestamp / 1000, tz=UTC).isoformat()
                
                # Determine if liquidity is locked
                liquidity_usd = 0.0
                if 'pairs' in token and token['pairs']:
                    first_pair = token['pairs'][0]
                    liquidity_usd = float(first_pair.get('liquidity', {}).get('usd', 0.0))
                
                # Store token in database
                self.db.store_token(
                    contract_address=contract_address,
                    ticker=ticker,
                    name=name,
                    launch_date=launch_date,
                    volume_24h=volume_24h,
                    safety_score=50.0,  # Base score, will be analyzed later
                    liquidity_locked=(liquidity_usd > 5000)  # Assume locked if significant liquidity
                )
                
                discovered_contracts.add(contract_address)
                logger.debug(f"Discovered token from DexScreener: {ticker} ({contract_address})")
            
            logger.info(f"Discovered {len(discovered_contracts)} tokens from DexScreener")
            return discovered_contracts
        
        except Exception as e:
            logger.error(f"DexScreener scan failed: {e}")
            return set()
    
    async def scan_top_gainers(self) -> List[Dict]:
        """
        Scan for top gaining tokens
        
        :return: List of top gainer tokens
        """
        gainers = []
        
        try:
            # Get top gainers for different timeframes
            gainers_1h = await self.analyzer.get_top_gainers('1h', 5)
            gainers_6h = await self.analyzer.get_top_gainers('6h', 5)
            gainers_24h = await self.analyzer.get_top_gainers('24h', 5)
            
            # Combine all gainers, removing duplicates
            seen_contracts = set()
            for token in gainers_1h + gainers_6h + gainers_24h:
                contract = token.get('contract_address')
                if contract and contract not in seen_contracts:
                    seen_contracts.add(contract)
                    gainers.append(token)
            
            logger.info(f"Found {len(gainers)} top gainer tokens")
            
            # Store tokens in database
            for token in gainers:
                self.db.store_token(
                    contract_address=token.get('contract_address'),
                    ticker=token.get('ticker', 'UNKNOWN'),
                    name=token.get('name', 'UNKNOWN'),
                    launch_date=datetime.now(UTC).isoformat(),
                    volume_24h=token.get('volume_24h', 0.0),
                    safety_score=70.0,  # Higher base score for top gainers
                    liquidity_locked=False
                )
            
            return gainers
        
        except Exception as e:
            logger.error(f"Error scanning for top gainers: {e}")
            return []
    
async def scan_trending_tokens(self) -> List[Dict]:
    """
    Scan for trending tokens
    
    :return: List of trending tokens
    """
    trending = []
    
    try:
        # Get trending tokens
        trending = await self.analyzer.get_trending_tokens(10)
        
        # Make sure we got a valid list
        if not trending:
            trending = []
            logger.info("No trending tokens found")
            return trending
            
        logger.info(f"Found {len(trending)} trending tokens")
        
        # Store tokens in database
        for token in trending:
            self.db.store_token(
                contract_address=token.get('contract_address'),
                ticker=token.get('ticker', 'UNKNOWN'),
                name=token.get('name', 'UNKNOWN'),
                launch_date=datetime.now(UTC).isoformat(),
                volume_24h=token.get('volume_24h', 0.0),
                safety_score=65.0,  # Higher base score for trending tokens
                liquidity_locked=False
            )
        
        return trending
    
    except Exception as e:
        logger.error(f"Error scanning for trending tokens: {e}")
        return []
        
    async def analyze_tokens(self) -> List[Dict]:
        """
        Analyze discovered tokens for trading potential
        
        :return: List of tradable tokens
        """
        tradable_tokens = []
        
        try:
            # Get recent tokens with minimum safety score
            min_safety = BotConfiguration.TRADING_PARAMETERS['MIN_SAFETY_SCORE']
            tokens_df = self.db.get_tokens(limit=20, min_safety_score=min_safety)
            
            if tokens_df.empty:
                logger.info("No tokens to analyze")
                return tradable_tokens
            
            # Analyze each token
            for _, token in tokens_df.iterrows():
                contract_address = token['contract_address']
                
                # Skip if already analyzed recently
                if contract_address in self.discovered_tokens:
                    continue
                
                # Skip likely fake tokens
                if is_fake_token(contract_address):
                    logger.debug(f"Skipping likely fake token during analysis: {contract_address}")
                    continue
                
                # Evaluate trading potential
                evaluation = await self.analyzer.evaluate_trading_potential(contract_address)
                
                if evaluation['tradable']:
                    tradable_tokens.append(evaluation)
                    logger.info(f"Tradable token found: {token['ticker']} ({contract_address})")
                
                # Mark as analyzed
                self.discovered_tokens.add(contract_address)
                
                # Prevent rate limiting
                await asyncio.sleep(1)
            
            # Prune discovered tokens list if too large
            if len(self.discovered_tokens) > 100:
                self.discovered_tokens = set(list(self.discovered_tokens)[-100:])
            
            return tradable_tokens
        
        except Exception as e:
            logger.error(f"Token analysis failed: {e}")
            return []
    
    async def get_tokens_by_criteria(self) -> List[Dict]:
        """
        Get tokens that meet specific trading criteria
        
        :return: List of qualified tokens that meet all criteria
        """
        qualified_tokens = []
        
        try:
            # Get configuration parameters
            params = BotConfiguration.TRADING_PARAMETERS
            min_volume = params.get('MIN_VOLUME', 50000)       # $50K
            min_liquidity = params.get('MIN_LIQUIDITY', 250000) # $250K
            min_mcap = params.get('MIN_MCAP', 500000)           # $500K
            min_holders = params.get('MIN_HOLDERS', 100)        # 100 holders
            
            # Scan top gainers and trending tokens
            top_gainers = await self.scan_top_gainers()
            trending_tokens = await self.scan_trending_tokens()
            
            # Combine potential tokens
            all_tokens = top_gainers + trending_tokens
            
            # Check each token against criteria
            for token in all_tokens:
                contract_address = token.get('contract_address')
                
                # Skip if contract is missing
                if not contract_address:
                    continue
                
                # Get full token data
                token_data = await self.analyzer.fetch_token_data(contract_address)
                if not token_data:
                    continue
                
                # Apply filtering criteria
                if (token_data.get('volume_24h', 0) >= min_volume and
                    token_data.get('liquidity_usd', 0) >= min_liquidity and
                    token_data.get('mcap', 0) >= min_mcap and
                    token_data.get('holders', 0) >= min_holders):
                    
                    # Calculate safety score
                    safety_score = await self.analyzer.calculate_safety_score(contract_address)
                    token_data['safety_score'] = safety_score
                    
                    # Add to qualified tokens
                    qualified_tokens.append({
                        'token_data': token_data,
                        'tradable': True,
                        'reason': 'Meets screening criteria',
                        'recommendation': {
                            'action': 'BUY',
                            'confidence': min(100, safety_score),
                            'max_investment': params['MAX_INVESTMENT_PER_TOKEN'],
                            'take_profit': params['TAKE_PROFIT_TARGET'],
                            'stop_loss': params['STOP_LOSS_PERCENTAGE']
                        }
                    })
                    
                    logger.info(f"Qualified token found: {token_data.get('ticker')} ({contract_address})")
            
            return qualified_tokens
        
        except Exception as e:
            logger.error(f"Error filtering tokens by criteria: {e}")
            return []

async def start_scanning(self):
    """
    Start token scanning process
    """
    logger.info("Starting token scanner")
    
    while True:
        try:
            # Check if bot should be running
            running = BotConfiguration.load_trading_parameters()
            if not running:
                logger.info("Bot paused by control settings")
                await asyncio.sleep(60)
                continue
            
            # Scan Twitter
            logger.info("Scanning Twitter for tokens...")
            await self.scan_twitter_for_tokens()
            
            # Scan DexScreener
            logger.info("Scanning DexScreener for tokens...")
            await self.scan_dexscreener_for_launches()
            
            # Get tokens by screening criteria 
            logger.info("Analyzing tokens by screening criteria...")
            qualified_tokens = await self.get_tokens_by_criteria()
            
            # Analyze other discovered tokens
            logger.info("Analyzing other discovered tokens...")
            other_tradable = await self.analyze_tokens()
            
            # Combine all tradable tokens
            all_tradable = qualified_tokens + other_tradable
            
            # Wait for next scan
            scan_interval = BotConfiguration.TRADING_PARAMETERS['SCAN_INTERVAL']
            logger.info(f"Scan complete, waiting {scan_interval} seconds for next scan")
            await asyncio.sleep(scan_interval)
            
        except Exception as e:
            logger.error(f"Error during token scanning: {e}")
            await asyncio.sleep(60)  # Wait a minute before retrying