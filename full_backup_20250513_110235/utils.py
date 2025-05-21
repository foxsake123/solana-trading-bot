import asyncio
import aiohttp
import json
import time
import logging
import re
import base64
import random
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta, UTC
from solders.pubkey import Pubkey
from config import BotConfiguration

logger = logging.getLogger('trading_bot.utils')

# Rate limiting tracking for different API endpoints
RATE_LIMIT_STATE = {
    'dexscreener': {
        'consecutive_limits': 0,
        'backoff_until': 0,
        'last_request_time': 0,
        'request_count': 0,
        'window_start': time.time(),
        'max_requests_per_minute': 30
    },
    'coingecko': {
        'consecutive_limits': 0,
        'backoff_until': 0,
        'last_request_time': 0,
        'request_count': 0,
        'window_start': time.time(),
        'max_requests_per_minute': 10  # CoinGecko's free tier is very limited
    }
}

# Cache for price data
PRICE_CACHE = {
    'sol_usd': {
        'price': 0.0,
        'timestamp': 0,
        'ttl': 600  # 10 minutes
    }
}

def is_valid_solana_address(address: str) -> bool:
    """
    Check if a string is a valid Solana address
    
    :param address: String to check
    :return: True if valid Solana address, False otherwise
    """
    if not isinstance(address, str) or len(address) < 32 or len(address) > 44:
        return False
    
    try:
        Pubkey.from_string(address)
        return True
    except Exception:
        return False

async def fetch_with_retries(url: str, method: str = 'GET', 
                           headers: Optional[Dict] = None,
                           params: Optional[Dict] = None, 
                           json_data: Optional[Dict] = None,
                           max_retries: int = 5,
                           base_delay: int = 2) -> Optional[Dict]:
    """
    Fetch data from API with improved retry and rate limiting mechanism
    
    :param url: URL to fetch
    :param method: HTTP method
    :param headers: HTTP headers
    :param params: Query parameters
    :param json_data: JSON data for POST requests
    :param max_retries: Maximum retry attempts
    :param base_delay: Base delay between retries
    :return: API response as dictionary or None
    """
    # First check for problematic tokens in URL
    suspicious_terms = ['pump', 'moon', 'scam', 'fake', 'elon', 'musk', 'inu', 'shib', 'doge']
    for term in suspicious_terms:
        if term in url.lower():
            logger.warning(f"Skipping URL with suspicious term '{term}': {url}")
            return None
    
    # Set default headers
    if headers is None:
        headers = {'accept': 'application/json'}
    
    # BUGFIX: DexScreener API endpoint fixes
    # Fix for DexScreener API - if using the invalid endpoint, switch to a valid one
    if 'dexscreener.com' in url:
        # Fix for '/pairs/solana' endpoint which doesn't exist - use search endpoint instead
        if '/pairs/solana' in url:
            url = "https://api.dexscreener.com/latest/dex/search?q=solana"
            logger.info(f"Corrected DexScreener endpoint to: {url}")
    
    # Fix for Jupiter API - ensure amount is a string
    if 'jup.ag' in url and params and 'amount' in params and not isinstance(params['amount'], str):
        params['amount'] = str(params['amount'])
    
    # Determine which API is being used
    api_type = None
    if 'dexscreener.com' in url:
        api_type = 'dexscreener'
    elif 'coingecko.com' in url:
        api_type = 'coingecko'
        
        # Special handling for CoinGecko SOL price - check cache first
        if 'solana' in url and 'price' in url:
            current_time = time.time()
            if (PRICE_CACHE['sol_usd']['price'] > 0 and 
                current_time - PRICE_CACHE['sol_usd']['timestamp'] < PRICE_CACHE['sol_usd']['ttl']):
                # Return cached price
                return {'solana': {'usd': PRICE_CACHE['sol_usd']['price']}}
            
            # Stricter rate limits for CoinGecko
            if RATE_LIMIT_STATE['coingecko']['request_count'] >= RATE_LIMIT_STATE['coingecko']['max_requests_per_minute']:
                # Instead of waiting, return cached value if available
                if PRICE_CACHE['sol_usd']['price'] > 0:
                    return {'solana': {'usd': PRICE_CACHE['sol_usd']['price']}}
                # Otherwise, use fallback price
                return {'solana': {'usd': 100.0}}  # Fallback price
    
    # Check if we're in a backoff period for this API
    current_time = time.time()
    if api_type and current_time < RATE_LIMIT_STATE[api_type]['backoff_until']:
        # Still in backoff period, wait longer
        wait_remaining = int(RATE_LIMIT_STATE[api_type]['backoff_until'] - current_time)
        logger.warning(f"Still in rate limit backoff period for {api_type}. Waiting {wait_remaining} seconds.")
        await asyncio.sleep(wait_remaining)
    
    # Track requests per minute for rate limiting
    if api_type:
        # Reset window if it's been more than a minute
        if current_time - RATE_LIMIT_STATE[api_type]['window_start'] > 60:
            RATE_LIMIT_STATE[api_type]['window_start'] = current_time
            RATE_LIMIT_STATE[api_type]['request_count'] = 0
        
        # Increment request count
        RATE_LIMIT_STATE[api_type]['request_count'] += 1
        RATE_LIMIT_STATE[api_type]['last_request_time'] = current_time
        
        # If approaching rate limit, add delay
        if RATE_LIMIT_STATE[api_type]['request_count'] >= RATE_LIMIT_STATE[api_type]['max_requests_per_minute']:
            # Calculate time until window resets
            time_to_reset = 60 - (current_time - RATE_LIMIT_STATE[api_type]['window_start'])
            logger.warning(f"Approaching rate limit for {api_type}. Sleeping {time_to_reset:.1f} seconds.")
            
            # For CoinGecko, if we hit rate limit and have cached data, return that
            if api_type == 'coingecko' and 'solana' in url and 'price' in url:
                if PRICE_CACHE['sol_usd']['price'] > 0:
                    return {'solana': {'usd': PRICE_CACHE['sol_usd']['price']}}
                # If no cached data, use fallback
                return {'solana': {'usd': 100.0}}
                
            await asyncio.sleep(time_to_reset)
            
            # Reset window
            RATE_LIMIT_STATE[api_type]['window_start'] = time.time()
            RATE_LIMIT_STATE[api_type]['request_count'] = 1
    
    # Add small delay between consecutive requests to the same API
    if api_type and current_time - RATE_LIMIT_STATE[api_type]['last_request_time'] < 0.5:
        # Add small jitter to prevent request bursts
        await asyncio.sleep(random.uniform(0.3, 0.7))
    
    # Perform request with retries
    try:
        async with aiohttp.ClientSession() as session:
            for attempt in range(max_retries):
                try:
                    if method.upper() == 'POST':
                        async with session.post(
                            url, 
                            headers=headers, 
                            params=params, 
                            json=json_data, 
                            timeout=30
                        ) as response:
                            # Check for rate limiting response
                            if response.status == 429:
                                logger.warning(f"Rate limited by {url}, waiting for retry")
                                
                                # Apply exponential backoff with jitter
                                if api_type:
                                    RATE_LIMIT_STATE[api_type]['consecutive_limits'] += 1
                                    backoff_seconds = min(900, base_delay * (2 ** RATE_LIMIT_STATE[api_type]['consecutive_limits']))
                                    jitter = random.uniform(0.8, 1.2)  # Add 20% jitter
                                    wait_time = int(backoff_seconds * jitter)
                                    
                                    # Set backoff timestamp
                                    RATE_LIMIT_STATE[api_type]['backoff_until'] = current_time + wait_time
                                    
                                    logger.warning(f"Rate limited by {api_type}, waiting {wait_time} seconds")
                                    
                                    # For CoinGecko, if we hit rate limit and have cached data, return that
                                    if api_type == 'coingecko' and 'solana' in url and 'price' in url:
                                        if PRICE_CACHE['sol_usd']['price'] > 0:
                                            return {'solana': {'usd': PRICE_CACHE['sol_usd']['price']}}
                                        # If no cached data, use fallback
                                        return {'solana': {'usd': 100.0}}
                                    
                                    await asyncio.sleep(wait_time)
                                else:
                                    # Generic backoff if API type not recognized
                                    wait_time = base_delay * (2 ** attempt)
                                    await asyncio.sleep(wait_time)
                                
                                continue
                            
                            # Reset consecutive limit counter on successful non-429 response
                            if api_type and response.status != 429:
                                RATE_LIMIT_STATE[api_type]['consecutive_limits'] = 0
                            
                            # For all other responses
                            response.raise_for_status()
                            try:
                                data = await response.json()
                                
                                # Update cache for SOL price
                                if api_type == 'coingecko' and 'solana' in url and 'price' in url:
                                    if data and 'solana' in data and 'usd' in data['solana']:
                                        PRICE_CACHE['sol_usd']['price'] = float(data['solana']['usd'])
                                        PRICE_CACHE['sol_usd']['timestamp'] = current_time
                                
                                return data
                            except Exception as e:
                                logger.error(f"Error parsing JSON response: {e}")
                                text_response = await response.text()
                                logger.error(f"Response content: {text_response[:200]}")
                                return None
                    else:
                        async with session.get(
                            url, 
                            headers=headers, 
                            params=params, 
                            timeout=30
                        ) as response:
                            # Check for rate limiting response
                            if response.status == 429:
                                logger.warning(f"Rate limited by {url}, waiting for retry")
                                
                                # Apply exponential backoff with jitter
                                if api_type:
                                    RATE_LIMIT_STATE[api_type]['consecutive_limits'] += 1
                                    backoff_seconds = min(900, base_delay * (2 ** RATE_LIMIT_STATE[api_type]['consecutive_limits']))
                                    jitter = random.uniform(0.8, 1.2)  # Add 20% jitter
                                    wait_time = int(backoff_seconds * jitter)
                                    
                                    # Set backoff timestamp
                                    RATE_LIMIT_STATE[api_type]['backoff_until'] = current_time + wait_time
                                    
                                    logger.warning(f"Rate limited by {api_type}, waiting {wait_time} seconds")
                                    
                                    # For CoinGecko, if we hit rate limit and have cached data, return that
                                    if api_type == 'coingecko' and 'solana' in url and 'price' in url:
                                        if PRICE_CACHE['sol_usd']['price'] > 0:
                                            return {'solana': {'usd': PRICE_CACHE['sol_usd']['price']}}
                                        # If no cached data, use fallback
                                        return {'solana': {'usd': 100.0}}
                                    
                                    await asyncio.sleep(wait_time)
                                else:
                                    # Generic backoff if API type not recognized
                                    wait_time = base_delay * (2 ** attempt)
                                    await asyncio.sleep(wait_time)
                                
                                continue
                            
                            # Reset consecutive limit counter on successful non-429 response
                            if api_type and response.status != 429:
                                RATE_LIMIT_STATE[api_type]['consecutive_limits'] = 0
                            
                            # For 404 errors on DexScreener, try an alternative endpoint
                            if response.status == 404 and 'dexscreener.com' in url:
                                if '/pairs/solana' in url:
                                    # Try alternative endpoint
                                    alternative_url = "https://api.dexscreener.com/latest/dex/search?q=solana"
                                    logger.warning(f"404 on {url}, trying alternative endpoint: {alternative_url}")
                                    return await fetch_with_retries(alternative_url, method, headers, params, json_data)
                                    
                            # For all other responses
                            response.raise_for_status()
                            try:
                                data = await response.json()
                                
                                # Update cache for SOL price
                                if api_type == 'coingecko' and 'solana' in url and 'price' in url:
                                    if data and 'solana' in data and 'usd' in data['solana']:
                                        PRICE_CACHE['sol_usd']['price'] = float(data['solana']['usd'])
                                        PRICE_CACHE['sol_usd']['timestamp'] = current_time
                                
                                return data
                            except Exception as e:
                                logger.error(f"Error parsing JSON response: {e}")
                                text_response = await response.text()
                                logger.error(f"Response content: {text_response[:200]}")
                                return None
                
                except aiohttp.ClientResponseError as e:
                    if e.status == 429:  # Rate limit exceeded
                        # This is now handled in the rate limit check above
                        pass
                    else:
                        logger.warning(f"Request error on attempt {attempt + 1}/{max_retries} for {url}: {e}")
                
                except Exception as e:
                    logger.warning(f"Fetch attempt {attempt + 1}/{max_retries} failed for {url}: {e}")
                
                # Apply exponential backoff with jitter
                if attempt < max_retries - 1:
                    backoff = base_delay * (2 ** attempt)
                    jitter = random.uniform(0.8, 1.2)  # Add 20% jitter
                    wait_time = backoff * jitter
                    await asyncio.sleep(wait_time)
    except Exception as e:
        # Catch any exceptions at the session level, which could cause the recursion error
        logger.error(f"Session-level error fetching {url}: {e}")
        return None
    
    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
    return None

def format_sol_amount(amount: float) -> str:
    """
    Format SOL amount with appropriate precision
    
    :param amount: SOL amount as float
    :return: Formatted SOL amount string
    """
    if amount >= 1:
        return f"{amount:.4f}"
    elif amount >= 0.0001:
        return f"{amount:.6f}"
    else:
        return f"{amount:.8f}"

def format_price_change(change: float) -> str:
    """
    Format price change with color indicator
    
    :param change: Price change as percentage
    :return: Formatted price change string
    """
    if change > 0:
        return f"+{change:.2f}%"
    elif change < 0:
        return f"{change:.2f}%"
    else:
        return "0.00%"

def parse_timeframe(timeframe: str) -> Optional[datetime]:
    """
    Parse human-readable timeframe to datetime
    
    :param timeframe: Timeframe string (e.g., '1h', '1d', '7d')
    :return: Datetime object or None if invalid
    """
    try:
        now = datetime.now(UTC)
        value = int(timeframe[:-1])
        unit = timeframe[-1].lower()
        
        if unit == 'm':
            return now - timedelta(minutes=value)
        elif unit == 'h':
            return now - timedelta(hours=value)
        elif unit == 'd':
            return now - timedelta(days=value)
        elif unit == 'w':
            return now - timedelta(weeks=value)
        else:
            return None
    except (ValueError, IndexError):
        return None

def truncate_address(address: str, chars: int = 4) -> str:
    """
    Truncate address for display
    
    :param address: Full address
    :param chars: Number of characters to keep at each end
    :return: Truncated address
    """
    if not address or len(address) <= chars * 2 + 2:
        return address
    return f"{address[:chars]}...{address[-chars:]}"

def calculate_profit_loss(buy_price: float, current_price: float) -> Dict:
    """
    Calculate profit/loss metrics
    
    :param buy_price: Buy price
    :param current_price: Current price
    :return: Dictionary with profit/loss metrics
    """
    if buy_price <= 0:
        return {'percentage': 0, 'multiple': 1}
    
    percentage = ((current_price - buy_price) / buy_price) * 100
    multiple = current_price / buy_price
    
    return {
        'percentage': percentage,
        'multiple': multiple
    }

def is_fake_token(contract_address: str) -> bool:
    """
    Check if token address is likely a scam/fake
    
    :param contract_address: Token contract address
    :return: True if likely fake, False otherwise
    """
    # Validate input first
    if not contract_address or not isinstance(contract_address, str):
        logger.warning(f"Invalid contract address in is_fake_token: {contract_address}")
        return True  # Consider invalid addresses as fake
    
    # Convert to lowercase for case-insensitive comparison
    contract_address_lower = contract_address.lower()
    
    # Get control settings
    try:
        with open(BotConfiguration.BOT_CONTROL_FILE, 'r') as f:
            control = json.load(f)
            
        # Skip filtering if disabled in settings
        if not control.get('filter_fake_tokens', True):
            return False
    except:
        # Default to filtering enabled if settings can't be loaded
        pass
    
    # Check for common patterns in fake pump tokens
    if 'pump' in contract_address_lower:  # Changed from endswith to in
        logger.warning(f"Detected 'pump' in token address: {contract_address}")
        return True
    
    # Check for 'moon' in the address
    if 'moon' in contract_address_lower:
        logger.warning(f"Detected 'moon' in token address: {contract_address}")
        return True
    
    # Additional suspicious terms
    suspicious_terms = ['scam', 'fake', 'elon', 'musk', 'inu', 'shib', 'doge']
    for term in suspicious_terms:
        if term in contract_address_lower:
            logger.warning(f"Detected suspicious term '{term}' in token address: {contract_address}")
            return True
    
    return False