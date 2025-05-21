#!/usr/bin/env python
"""
Test script to verify private key format and create a Solana keypair
"""

import logging
import os
import base58
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Solana packages
try:
    from solders.pubkey import Pubkey
    from solders.keypair import Keypair
    logger.info("Successfully imported Solana packages")
except ImportError as e:
    logger.error(f"Failed to import Solana packages: {e}")
    logger.error("Please install with: pip install solana solders base58")
    exit(1)

def test_private_key(private_key_str):
    """
    Test if a private key string can be used to create a valid Keypair
    
    :param private_key_str: Private key as string
    :return: Keypair object or None
    """
    logger.info(f"Testing private key (length: {len(private_key_str)})")
    
    # Try to determine format and convert to bytes
    try:
        # 1. Try as hex string
        if len(private_key_str) == 64 and all(c in '0123456789abcdefABCDEF' for c in private_key_str):
            private_key_bytes = bytes.fromhex(private_key_str)
            logger.info("Interpreted as hex string")
        
        # 2. Try as base58 encoded string
        elif (len(private_key_str) == 44 or len(private_key_str) == 88) and all(c in base58.alphabet.decode() for c in private_key_str):
            private_key_bytes = base58.b58decode(private_key_str)
            logger.info("Interpreted as base58 string")
        
        # 3. Try as comma-separated bytes
        elif ',' in private_key_str:
            try:
                private_key_bytes = bytes([int(x.strip()) for x in private_key_str.split(',')])
                logger.info("Interpreted as comma-separated bytes")
            except ValueError:
                logger.error("Invalid comma-separated bytes format")
                return None
        
        # 4. Try as space-separated bytes
        elif ' ' in private_key_str:
            try:
                private_key_bytes = bytes([int(x.strip()) for x in private_key_str.split()])
                logger.info("Interpreted as space-separated bytes")
            except ValueError:
                logger.error("Invalid space-separated bytes format")
                return None
        
        # 5. Try as array-like format [21,34,...]
        elif private_key_str.startswith('[') and private_key_str.endswith(']'):
            try:
                content = private_key_str.strip('[]')
                private_key_bytes = bytes([int(x.strip()) for x in content.split(',')])
                logger.info("Interpreted as array-like format")
            except ValueError:
                logger.error("Invalid array-like format")
                return None
        
        # 6. Try long format - attempt to clean and parse
        elif len(private_key_str) > 64:
            cleaned_key = ''.join(c for c in private_key_str if c.isalnum())
            if len(cleaned_key) == 64 and all(c in '0123456789abcdefABCDEF' for c in cleaned_key):
                private_key_bytes = bytes.fromhex(cleaned_key)
                logger.info("Interpreted as cleaned hex string")
            else:
                # Try to interpret as a list of decimal values
                try:
                    # Extract numbers from the string
                    import re
                    numbers = re.findall(r'\d+', private_key_str)
                    if numbers:
                        private_key_bytes = bytes([int(x) for x in numbers[:32]])
                        logger.info(f"Interpreted as extracted decimal values (found {len(numbers)} numbers)")
                    else:
                        logger.error("Could not extract numerical values from long format")
                        return None
                except Exception as e:
                    logger.error(f"Failed to parse long format: {e}")
                    return None
        
        else:
            logger.error(f"Unrecognized private key format")
            return None
        
        # Ensure we have the right length
        logger.info(f"Extracted private key bytes (length: {len(private_key_bytes)})")
        
        if len(private_key_bytes) != 32:
            if len(private_key_bytes) > 32:
                # If we have more than 32 bytes, take first 32
                private_key_bytes = private_key_bytes[:32]
                logger.info(f"Trimmed to 32 bytes")
            else:
                logger.error(f"Invalid private key length: {len(private_key_bytes)} bytes (need 32)")
                return None
        
        # Try different methods to create a keypair
        methods_to_try = [
            ('from_bytes', lambda: Keypair.from_bytes(private_key_bytes)),
            ('direct constructor', lambda: Keypair(private_key_bytes)),
            ('from_seed', lambda: Keypair.from_seed(private_key_bytes))
        ]
        
        for method_name, method_func in methods_to_try:
            try:
                logger.info(f"Trying method: {method_name}")
                keypair = method_func()
                pubkey = keypair.pubkey()
                logger.info(f"SUCCESS! Created keypair with public key: {pubkey}")
                
                # Also print in various formats for reference
                logger.info(f"Private key in base58: {base58.b58encode(private_key_bytes).decode()}")
                logger.info(f"Private key in hex: {private_key_bytes.hex()}")
                logger.info(f"Public key in base58: {pubkey}")
                
                return keypair
            except Exception as e:
                logger.error(f"Method {method_name} failed: {e}")
        
        logger.error("All keypair creation methods failed")
        return None
        
    except Exception as e:
        logger.error(f"Error testing private key: {e}")
        return None

def main():
    # Get private key from environment variable
    private_key_str = os.getenv('WALLET_PRIVATE_KEY')
    
    if not private_key_str:
        logger.error("No WALLET_PRIVATE_KEY found in environment variables")
        return
    
    logger.info("Testing private key from environment variable")
    keypair = test_private_key(private_key_str)
    
    if keypair:
        logger.info("✅ Successfully created keypair from private key")
    else:
        logger.error("❌ Failed to create keypair from private key")
        
        # Show alternative formats for manual testing
        logger.info("\nYou can try setting your private key in these formats:")
        logger.info("1. Hex string (64 characters): [0-9a-f]{64}")
        logger.info("2. Base58 string (usually ~44 characters)")
        logger.info("3. Comma-separated bytes: 21,34,56,...")
        logger.info("4. Space-separated bytes: 21 34 56 ...")
        logger.info("5. Array format: [21,34,56,...]")

if __name__ == "__main__":
    main()
