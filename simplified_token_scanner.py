# simplified_token_scanner.py
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger('simplified_token_scanner')

class TokenScanner:
    """Simplified token scanner that discovers real Solana tokens"""
    
    def __init__(self, db=None, trader=None, token_analyzer=None):
        self.db = db
        self.trader = trader
        self.token_analyzer = token_analyzer
        self.birdeye_api = None  # Will be set later
        logger.info("Initialized real token scanner")
    
    async def get_top_gainers(self) -> List[Dict[str, Any]]:
        """Get top gaining tokens from BirdeyeAPI"""
        if self.birdeye_api:
            try:
                # Get top gainers from BirdeyeAPI (which uses DexScreener)
                tokens = await self.birdeye_api.get_top_gainers(limit=10)
                logger.info(f"Found {len(tokens)} top gainers from BirdeyeAPI")
                return tokens
            except Exception as e:
                logger.error(f"Error getting top gainers: {e}")
        else:
            logger.warning("BirdeyeAPI not available, using empty list")
        
        return []
    
    async def get_trending_tokens(self) -> List[Dict[str, Any]]:
        """Get trending tokens from BirdeyeAPI"""
        if self.birdeye_api:
            try:
                # Get trending tokens from BirdeyeAPI
                tokens = await self.birdeye_api.get_trending_tokens(limit=10)
                logger.info(f"Found {len(tokens)} trending tokens from BirdeyeAPI")
                return tokens
            except Exception as e:
                logger.error(f"Error getting trending tokens: {e}")
        else:
            logger.warning("BirdeyeAPI not available, using empty list")
        
        return []
    
    async def start_scanning(self):
        """Start the token scanning process"""
        logger.info("Token scanner started")
        
        while True:
            try:
                logger.info("Scanning for real tokens on Solana network")
                
                # Get tokens from both sources
                top_gainers = await self.get_top_gainers()
                trending_tokens = await self.get_trending_tokens()
                
                # Combine and deduplicate
                all_tokens = []
                seen_addresses = set()
                
                for token in top_gainers + trending_tokens:
                    address = token.get('contract_address') or token.get('address')
                    if address and address not in seen_addresses:
                        seen_addresses.add(address)
                        all_tokens.append(token)
                
                logger.info(f"Found {len(all_tokens)} unique tokens")
                
                # Store tokens in database if available
                if self.db and all_tokens:
                    for token in all_tokens:
                        try:
                            # Ensure contract_address is set
                            if 'contract_address' not in token:
                                token['contract_address'] = token.get('address', '')
                            
                            self.db.store_token(token)
                        except Exception as e:
                            logger.error(f"Error storing token: {e}")
                
                # Wait before next scan
                await asyncio.sleep(60)  # Scan every minute
                
            except Exception as e:
                logger.error(f"Error in token scanning: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds on error
