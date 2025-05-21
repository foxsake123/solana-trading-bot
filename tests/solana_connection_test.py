#!/usr/bin/env python
"""
Test script to verify Solana RPC connection with proper method
"""

import asyncio
import logging
from solana.rpc.async_api import AsyncClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_solana_connection():
    """Test connection to Solana RPC"""
    rpc_endpoint = "https://mainnet.helius-rpc.com/?api-key=YOUR_API_KEY"
    
    client = AsyncClient(rpc_endpoint)
    
    # Try different methods to get blockhash
    try:
        logger.info("Trying get_latest_blockhash()...")
        response = await client.get_latest_blockhash()
        logger.info(f"Success with get_latest_blockhash(): {response}")
        return True
    except Exception as e:
        logger.warning(f"get_latest_blockhash() failed: {e}")
        
        try:
            logger.info("Trying get_recent_blockhash()...")
            response = await client.get_recent_blockhash()
            logger.info(f"Success with get_recent_blockhash(): {response}")
            return True
        except Exception as e:
            logger.warning(f"get_recent_blockhash() failed: {e}")
            
            try:
                logger.info("Trying get_health()...")
                response = await client.get_health()
                logger.info(f"Success with get_health(): {response}")
                return True
            except Exception as e:
                logger.error(f"All connection methods failed: {e}")
                return False

if __name__ == "__main__":
    asyncio.run(test_solana_connection())
