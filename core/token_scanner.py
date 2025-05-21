"""
Updated simplified token scanner with database adapter
"""
import os
import json
import random
import logging
import time
from datetime import datetime, timezone
import asyncio

logger = logging.getLogger('simplified_token_scanner')

# Try to import the database adapter
try:
    from core.database_adapter import DatabaseAdapter
    HAS_ADAPTER = True
    logger.info("Successfully imported DatabaseAdapter")
except ImportError:
    HAS_ADAPTER = False
    logger.warning("DatabaseAdapter not available, will use direct database access")

class TokenScanner:
    """
    Simplified token scanner that generates simulation tokens
    """
    
    def __init__(self, db=None):
        """
        Initialize the token scanner
        
        :param db: Database instance (optional)
        """
        # Set up database - using adapter if available
        if db is not None:
            if HAS_ADAPTER:
                self.db = DatabaseAdapter(db)
                logger.info("Using DatabaseAdapter for database operations")
            else:
                self.db = db
                logger.info("Using direct database access")
        else:
            self.db = None
            logger.warning("No database provided")
            
        self.running = False
        self.token_count = 0
        
        logger.info("Initialized simplified token scanner")
    
    async def start_scanning(self):
        """Start scanning for tokens"""
        self.running = True
        logger.info("Token scanner started")
        
        # Start the token generation loop
        asyncio.create_task(self._generate_tokens())
        
    async def stop_scanning(self):
        """Stop scanning for tokens"""
        self.running = False
        logger.info("Token scanner stopped")
    
    async def _generate_tokens(self):
        """Generate simulation tokens periodically"""
        while self.running:
            try:
                # Generate 1-3 tokens every 30 seconds
                num_tokens = random.randint(1, 3)
                logger.info(f"Generating {num_tokens} simulation tokens")
                
                tokens = []
                for _ in range(num_tokens):
                    token = self._create_simulation_token()
                    tokens.append(token)
                    
                    # Store token in database if available
                    if self.db is not None:
                        try:
                            if hasattr(self.db, 'save_token'):
                                # Use adapter's save_token method
                                self.db.save_token(token)
                            elif hasattr(self.db, 'store_token'):
                                # Try direct store_token method
                                self.db.store_token(token)
                            else:
                                logger.warning("No compatible method found to save token")
                        except Exception as e:
                            logger.error(f"Error saving token to database: {e}")
                
                # Wait for next cycle
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Error generating tokens: {e}")
                await asyncio.sleep(5)
    
    def _create_simulation_token(self):
        """Create a simulation token with realistic properties"""
        self.token_count += 1
        current_time = time.time()
        
        # Create a unique token address based on count and time
        token_address = f"Sim{self.token_count}TopGainer{int(current_time)}"
        
        # Generate names from lists of adjectives and nouns
        adjectives = ["Super", "Mega", "Ultra", "Hyper", "Quantum", "Cosmic", "Solar", "Lunar", "Stellar", "Astral"]
        nouns = ["Dog", "Cat", "Rocket", "Moon", "Mars", "Star", "Coin", "Cash", "Gold", "Silver", "Diamond", "Pearl"]
        
        # Pick random name components
        adjective = random.choice(adjectives)
        noun = random.choice(nouns)
        
        # Format the token ticker and name
        ticker = f"{adjective[:1]}{noun[:3]}".upper()
        name = f"{adjective} {noun} Token"
        
        # Set realistic metrics
        price_usd = random.uniform(0.0000001, 0.001)
        volume_24h = random.uniform(5000, 100000)  # $5K-$100K volume
        liquidity_usd = random.uniform(5000, 50000)  # $5K-$50K liquidity
        market_cap = random.uniform(100000, 1000000)  # $100K-$1M market cap
        holders = random.randint(50, 500)
        
        # Set price changes (more likely to be positive to simulate "promising" tokens)
        price_change_1h = random.uniform(1.0, 20.0)
        price_change_6h = random.uniform(5.0, 30.0)
        price_change_24h = random.uniform(10.0, 50.0)
        
        # Create token data
        token = {
            'contract_address': token_address,
            'ticker': ticker,
            'name': name,
            'price_usd': price_usd,
            'volume_24h': volume_24h,
            'liquidity_usd': liquidity_usd,
            'market_cap': market_cap,
            'holders': holders,
            'price_change_1h': price_change_1h,
            'price_change_6h': price_change_6h,
            'price_change_24h': price_change_24h,
            'total_supply': 1_000_000_000,
            'circulating_supply': 750_000_000,
            'is_simulation': True,
            'safety_score': random.uniform(50.0, 90.0),
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Created simulation token: {ticker} ({token_address})")
        return token
    
    async def get_top_gainers(self, limit=10):
        """Get top gaining tokens"""
        # Generate some top gainers
        tokens = []
        for i in range(limit):
            token = self._create_simulation_token()
            # Ensure high price change for top gainers
            token['price_change_24h'] = random.uniform(30.0, 100.0)
            tokens.append(token)
        
        return tokens
        
    async def get_trending_tokens(self, limit=10):
        """Get trending tokens"""
        # Generate some trending tokens
        tokens = []
        for i in range(limit):
            token = self._create_simulation_token()
            # Ensure high volume for trending tokens
            token['volume_24h'] = random.uniform(50000, 200000)
            tokens.append(token)
        
        return tokens
