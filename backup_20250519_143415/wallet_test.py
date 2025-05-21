"""
Test script to verify Solana wallet connectivity
"""
import os
import sys
import logging
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('wallet_test')

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    # Try to import solders directly
    from solders.keypair import Keypair
    from solana.rpc.async_api import AsyncClient
    HAS_SOLDERS = True
    logger.info("Successfully imported Solders packages")
except ImportError as e:
    logger.error(f"Failed to import Solders packages: {e}")
    logger.error("Please install with: pip install solders solana")
    HAS_SOLDERS = False

# Import .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Loaded .env file")
except ImportError:
    logger.warning("dotenv not installed, not loading .env file")

# Load configuration from environment if available
rpc_url = os.getenv('MAINNET_RPC_URL', "https://api.mainnet-beta.solana.com")
private_key = os.getenv('WALLET_PRIVATE_KEY', "")

# Alternative: load from bot_control.json if available
try:
    import json
    if os.path.exists('bot_control.json'):
        with open('bot_control.json', 'r') as f:
            control_data = json.load(f)
            if 'rpc_url' in control_data:
                rpc_url = control_data['rpc_url']
                logger.info(f"Loaded RPC URL from bot_control.json")
except Exception as e:
    logger.warning(f"Error loading bot_control.json: {e}")

async def test_wallet_connection():
    """Test the connection to the Solana wallet"""
    if not HAS_SOLDERS:
        logger.error("Solders packages not available, cannot test wallet connection")
        return False
        
    if not private_key:
        logger.error("No private key provided")
        return False
        
    logger.info(f"Testing connection to RPC endpoint: {rpc_url}")
    
    try:
        # Create keypair from private key
        logger.info("Creating keypair from private key...")
        key_bytes = bytes.fromhex(private_key)
        keypair = Keypair.from_seed(key_bytes[:32])  # Use first 32 bytes as seed
        public_key = keypair.pubkey()
        logger.info(f"Public key: {public_key}")
        
        # Connect to Solana
        logger.info("Connecting to Solana network...")
        client = AsyncClient(rpc_url)
        
        # Get slot to verify connection
        slot = await client.get_slot()
        logger.info(f"Current slot: {slot}")
        
        # Get balance
        logger.info("Getting wallet balance...")
        balance_response = await client.get_balance(public_key)
        if balance_response.value is not None:
            balance_lamports = balance_response.value
            balance_sol = balance_lamports / 1_000_000_000  # Convert lamports to SOL
            logger.info(f"Wallet balance: {balance_sol} SOL ({balance_lamports} lamports)")
        else:
            logger.error("Failed to get balance")
            
        # Get transaction count
        logger.info("Getting transaction count...")
        tx_count = await client.get_transaction_count()
        logger.info(f"Network transaction count: {tx_count}")
        
        # Clean up
        await client.close()
        logger.info("Connection closed")
        
        return True
    except Exception as e:
        logger.error(f"Error testing wallet connection: {e}")
        return False

def validate_wallet_private_key(private_key):
    """Validate the wallet private key format"""
    if not private_key:
        logger.error("No private key provided")
        return False
        
    try:
        # Check for common formats
        if len(private_key) == 64 and all(c in '0123456789abcdefABCDEF' for c in private_key):
            logger.info("Private key appears to be a valid 32-byte hex string")
            return True
        elif len(private_key) == 128 and all(c in '0123456789abcdefABCDEF' for c in private_key):
            logger.info("Private key appears to be a valid 64-byte hex string")
            return True
        elif len(private_key) >= 86 and len(private_key) <= 88:  # Base58 encoded keys are usually 86-88 chars
            logger.info("Private key appears to be a valid base58 encoded string")
            return True
        else:
            logger.warning(f"Private key has unusual length: {len(private_key)}")
            return False
    except Exception as e:
        logger.error(f"Error validating private key: {e}")
        return False

def get_sol_price():
    """Get the current SOL price in USD"""
    try:
        import requests
        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd",
            timeout=10
        )
        data = response.json()
        price = float(data['solana']['usd'])
        logger.info(f"Current SOL price: ${price}")
        return price
    except Exception as e:
        logger.error(f"Error getting SOL price: {e}")
        return 0.0

def main():
    """Main function to run the wallet test"""
    logger.info("Starting Solana wallet connection test")
    
    # Validate the private key format
    if private_key:
        is_valid = validate_wallet_private_key(private_key)
        if not is_valid:
            logger.warning("Private key format may not be valid")
    else:
        logger.error("No private key found in environment variables or config")
        return
    
    # Get SOL price
    sol_price = get_sol_price()
    
    # Test wallet connection
    if asyncio.run(test_wallet_connection()):
        logger.info("Wallet connection test successful")
    else:
        logger.error("Wallet connection test failed")

if __name__ == "__main__":
    main()