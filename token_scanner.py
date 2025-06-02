# token_scanner.py - Updated to filter simulation tokens in real mode

import os
import json
import time
import asyncio
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

# Setup logging
logger = logging.getLogger('trading_bot.token_scanner')

class TokenScanner:
    def __init__(self, db=None, trader=None, token_analyzer=None, birdeye_api=None):
        """
        Initialize the token scanner
        
        :param db: Database instance
        :param trader: SolanaTrader instance
        :param token_analyzer: TokenAnalyzer instance
        :param birdeye_api: BirdeyeAPI instance
        """
        self.db = db
        self.trader = trader
        self.token_analyzer = token_analyzer
        self.birdeye_api = birdeye_api
        
        # Import configuration
        from config import BotConfiguration
        self.config = BotConfiguration
        
        # Load Twitter API credentials if available
        self.twitter_api_key = self.config.API_KEYS.get('TWITTER_API_KEY')
        self.twitter_api_secret = self.config.API_KEYS.get('TWITTER_API_SECRET')
        self.twitter_bearer_token = self.config.API_KEYS.get('TWITTER_BEARER_TOKEN')
        
        # Initialize Twitter client if we have credentials
        self.twitter_client = None
        if self.twitter_api_key and self.twitter_api_secret and self.twitter_bearer_token:
            try:
                import tweepy
                self.twitter_client = tweepy.Client(
                    bearer_token=self.twitter_bearer_token,
                    consumer_key=self.twitter_api_key,
                    consumer_secret=self.twitter_api_secret
                )
                logger.info("Twitter client initialized")
            except ImportError:
                logger.warning("Tweepy module not found, Twitter functionality will be disabled")
            except Exception as e:
                logger.error(f"Error initializing Twitter client: {e}")
                
        # Initialize the machine learning model if requested
        self.ml_model = None
        self.use_machine_learning = False
        
        # Try to load control settings
        if os.path.exists(self.config.BOT_CONTROL_FILE):
            try:
                with open(self.config.BOT_CONTROL_FILE, 'r') as f:
                    control = json.load(f)
                    self.use_machine_learning = control.get('use_machine_learning', False)
                    
                if self.use_machine_learning:
                    try:
                        from ml_model import MLModel
                        self.ml_model = MLModel()
                        logger.info("ML model initialized")
                    except ImportError:
                        logger.warning("ML model module not found, ML functionality will be disabled")
                    except Exception as e:
                        logger.error(f"Error initializing ML model: {e}")
            except Exception as e:
                logger.error(f"Error loading control settings: {e}")
                
    def is_simulation_token(self, token_address: str) -> bool:
        """
        Check if a token address is a simulation token
        
        :param token_address: Token contract address
        :return: True if it's a simulation token, False otherwise
        """
        # Check address format first
        if token_address is None or not isinstance(token_address, str):
            return False
            
        # Check for simulation indicators in the address or name
        lower_address = token_address.lower()
        sim_indicators = ["sim", "test", "demo", "dummy", "fake", "mock", "placeholder"]
        
        # Check if the address starts with or contains any simulation indicators
        for indicator in sim_indicators:
            if token_address.startswith(indicator) or indicator in lower_address:
                return True
                
        # Check for generated simulation tokens (common in our codebase)
        if "topgainer" in lower_address and any(prefix in token_address for prefix in ["Sim0", "Sim1", "Sim2", "Sim3", "Sim4"]):
            return True
            
        # Additional checks for simulation tokens in our system
        return False
                
    async def start_scanning(self):
        """Start the token scanner process"""
        logger.info("Starting token scanner")
        
        # Check if the bot is paused
        try:
            if os.path.exists(self.config.BOT_CONTROL_FILE):
                with open(self.config.BOT_CONTROL_FILE, 'r') as f:
                    control = json.load(f)
                    
                if not control.get('running', False):
                    logger.info("Bot paused by control settings")
                    return
        except Exception as e:
            logger.error(f"Error checking control settings: {e}")
            
        # Get scanning parameters from control settings
        scan_interval = 60  # Default interval in seconds
        if os.path.exists(self.config.BOT_CONTROL_FILE):
            try:
                with open(self.config.BOT_CONTROL_FILE, 'r') as f:
                    control = json.load(f)
                    scan_interval = control.get('scan_interval', 60)
            except Exception as e:
                logger.error(f"Error loading scan interval: {e}")
                
        # Main scanning loop
        while True:
            try:
                # Get tokens from various sources
                top_gainers = await self.get_top_gainers()
                trending_tokens = await self.get_trending_tokens()
                twitter_tokens = await self.get_twitter_tokens()
                
                # Combine all tokens
                all_tokens = []
                all_tokens.extend(top_gainers)
                all_tokens.extend(trending_tokens)
                all_tokens.extend(twitter_tokens)
                
                # Filter out simulation tokens if in real trading mode
                simulation_mode = True  # Default to simulation mode
                if os.path.exists(self.config.BOT_CONTROL_FILE):
                    try:
                        with open(self.config.BOT_CONTROL_FILE, 'r') as f:
                            control = json.load(f)
                            simulation_mode = control.get('simulation_mode', True)
                    except Exception as e:
                        logger.error(f"Error loading simulation mode setting: {e}")
                
                # Filter tokens based on trading mode
                filtered_tokens = []
                for token in all_tokens:
                    token_address = token.get('contract_address')
                    is_sim = self.is_simulation_token(token_address)
                    
                    # Only include simulation tokens in simulation mode
                    # Only include real tokens in real trading mode
                    if (simulation_mode and is_sim) or (not simulation_mode and not is_sim):
                        filtered_tokens.append(token)
                    elif not simulation_mode and is_sim:
                        logger.info(f"Filtered out simulation token {token.get('ticker')} ({token_address}) in real trading mode")
                
                # Analyze and evaluate each token
                qualified_tokens = []
                for token in filtered_tokens:
                    if await self.evaluate_token(token):
                        qualified_tokens.append(token)
                        
                # Log the results
                logger.info(f"Found {len(qualified_tokens)} qualified tokens")
                
                # Check if we need to keep scanning
                if os.path.exists(self.config.BOT_CONTROL_FILE):
                    with open(self.config.BOT_CONTROL_FILE, 'r') as f:
                        control = json.load(f)
                        
                    if not control.get('running', False):
                        logger.info("Bot paused by control settings")
                        break
                
                # Wait for the next scan
                await asyncio.sleep(scan_interval)
                
            except Exception as e:
                logger.error(f"Error in token scanning: {e}")
                await asyncio.sleep(10)  # Short wait before retrying
                
    async def get_top_gainers(self) -> List[Dict[str, Any]]:
        """
        Get top gaining tokens - ALWAYS use real tokens
        
        :return: List of top gaining tokens
        """
        top_gainers = []
        
        # ALWAYS get real tokens from BirdeyeAPI regardless of mode
        if self.birdeye_api:
            try:
                real_top_gainers = await self.birdeye_api.get_top_gainers()
                top_gainers.extend(real_top_gainers)
                logger.info(f"Found {len(top_gainers)} real top gainer tokens")
            except Exception as e:
                logger.error(f"Error fetching top gainers: {e}")
        else:
            logger.warning("BirdeyeAPI not available - cannot fetch real tokens")
        
        return top_gainers
    async def get_trending_tokens(self) -> List[Dict[str, Any]]:
        """
        Get trending tokens
        
        :return: List of trending tokens
        """
        trending_tokens = []
        
        # Check if simulation mode is enabled
        simulation_mode = True
        if os.path.exists(self.config.BOT_CONTROL_FILE):
            try:
                with open(self.config.BOT_CONTROL_FILE, 'r') as f:
                    control = json.load(f)
                    simulation_mode = control.get('simulation_mode', True)
            except Exception as e:
                logger.error(f"Error loading simulation mode setting: {e}")
                
        # In real mode, get actual trending tokens from BirdeyeAPI
        if not simulation_mode:
            if self.birdeye_api:
                real_trending = await self.birdeye_api.get_trending_tokens()
                for token in real_trending:
                    # Skip if it's a simulation token in real mode
                    if not self.is_simulation_token(token.get('contract_address')):
                        trending_tokens.append(token)
        else:
            # In simulation mode, we might also generate some trending tokens
            # But we'll leave this empty for now to avoid too many simulation tokens
            pass
                    
        logger.info(f"Found {len(trending_tokens)} trending tokens")
        return trending_tokens
        
    async def get_twitter_tokens(self) -> List[Dict[str, Any]]:
        """
        Get tokens mentioned on Twitter
        
        :return: List of tokens mentioned on Twitter
        """
        # This would use the Twitter API to find tokens
        # For now, we'll return an empty list
        return []
        
    async def evaluate_token(self, token: Dict[str, Any]) -> bool:
        """
        Evaluate a token to see if it meets the trading criteria
        
        :param token: Token information
        :return: True if the token meets the criteria, False otherwise
        """
        # Get evaluation parameters from control settings
        min_safety_score = 15.0
        min_volume = 10.0
        min_liquidity = 5000.0
        min_mcap = 10000.0
        min_holders = 10
        min_price_change_1h = 1.0
        min_price_change_6h = 2.0
        min_price_change_24h = 5.0
        
        if os.path.exists(self.config.BOT_CONTROL_FILE):
            try:
                with open(self.config.BOT_CONTROL_FILE, 'r') as f:
                    control = json.load(f)
                    min_safety_score = control.get('MIN_SAFETY_SCORE', 15.0)
                    min_volume = control.get('MIN_VOLUME', 10.0)
                    min_liquidity = control.get('MIN_LIQUIDITY', 5000.0)
                    min_mcap = control.get('MIN_MCAP', 10000.0)
                    min_holders = control.get('MIN_HOLDERS', 10)
                    min_price_change_1h = control.get('MIN_PRICE_CHANGE_1H', 1.0)
                    min_price_change_6h = control.get('MIN_PRICE_CHANGE_6H', 2.0)
                    min_price_change_24h = control.get('MIN_PRICE_CHANGE_24H', 5.0)
            except Exception as e:
                logger.error(f"Error loading token evaluation parameters: {e}")
                
        # Get token safety score from token analyzer
        safety_score = 0.0
        if self.token_analyzer:
            safety_score = await self.token_analyzer.get_safety_score(token.get('contract_address'))
            
        # Get token metrics
        volume_24h = token.get('volume_24h', 0.0)
        liquidity_usd = token.get('liquidity_usd', 0.0)
        market_cap = token.get('market_cap', 0.0)
        holders = token.get('holders', 0)
        price_change_1h = token.get('price_change_1h', 0.0)
        price_change_6h = token.get('price_change_6h', 0.0)
        price_change_24h = token.get('price_change_24h', 0.0)
        
        # Check if the token meets the criteria
        if (safety_score >= min_safety_score and
            volume_24h >= min_volume and
            liquidity_usd >= min_liquidity and
            market_cap >= min_mcap and
            holders >= min_holders and
            price_change_1h >= min_price_change_1h and
            price_change_6h >= min_price_change_6h and
            price_change_24h >= min_price_change_24h):
            
            # Token passes basic criteria
            token_name = token.get('ticker')
            contract_address = token.get('contract_address')
            logger.info(f"Qualified token found: {token_name} ({contract_address})")
            return True
            
        return False
        
    def get_ml_stats(self) -> Dict[str, Any]:
        """
        Get machine learning model statistics
        
        :return: ML model statistics
        """
        if self.ml_model:
            return self.ml_model.get_performance_stats()
        
        return {}
        
    def get_ml_predictions(self) -> List[Dict[str, Any]]:
        """
        Get recent machine learning predictions
        
        :return: List of recent ML predictions
        """
        if self.ml_model:
            return self.ml_model.get_recent_predictions()
            
        return []
