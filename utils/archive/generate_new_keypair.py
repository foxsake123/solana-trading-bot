#!/usr/bin/env python
"""
Generate a new Solana keypair for the trading bot
"""

import os
import sys
import logging
import base58
from pathlib import Path
from dotenv import load_dotenv, set_key

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import Solana packages
try:
    from solders.keypair import Keypair
    from solana.rpc.async_api import AsyncClient
    import asyncio
    logger.info("Successfully imported Solana packages")
except ImportError as e:
    logger.error(f"Failed to import Solana packages: {e}")
    logger.error("Please install with: pip install solana solders base58")
    sys.exit(1)

async def check_connection(endpoint, pubkey):
    """Check connection to Solana network and verify the account exists"""
    try:
        logger.info(f"Checking connection to {endpoint}")
        client = AsyncClient(endpoint)
        
        # Test connection
        try:
            response = await client.get_latest_blockhash()
            logger.info(f"Connection successful: {response}")
        except:
            try:
                response = await client.get_health()
                logger.info(f"Connection health check: {response}")
            except Exception as e:
                logger.error(f"Connection failed: {e}")
                return False
                
        # Check account info (to see if the account exists)
        try:
            account_info = await client.get_account_info(pubkey)
            logger.info(f"Account info: {account_info}")
        except Exception as e:
            logger.warning(f"Account info check failed (this is normal for new accounts): {e}")
            
        return True
    except Exception as e:
        logger.error(f"Error checking connection: {e}")
        return False
    finally:
        await client.close()

def generate_new_keypair():
    """
    Generate a new Solana keypair and update the .env file
    
    :return: (keypair, pubkey_str, private_key_hex)
    """
    # Generate new keypair
    keypair = Keypair()
    pubkey = keypair.pubkey()
    pubkey_str = str(pubkey)
    
    # Get private key bytes
    try:
        if hasattr(keypair, 'secret'):
            # Newer version of solders
            private_key_bytes = keypair.secret()
        else:
            # Older version
            private_key_bytes = bytes(keypair)[:32]
    except Exception as e:
        logger.error(f"Error extracting private key bytes: {e}")
        # Alternative approach
        private_key_bytes = bytes(keypair)[:32]
        
    # Format in different ways
    private_key_hex = private_key_bytes.hex()
    private_key_base58 = base58.b58encode(private_key_bytes).decode()
    
    logger.info(f"Generated new keypair with public key: {pubkey}")
    logger.info(f"Private key (hex): {private_key_hex}")
    logger.info(f"Private key (base58): {private_key_base58}")
    
    # Check if we're in a virtual environment
    in_venv = sys.prefix != sys.base_prefix
    venv_path = Path(sys.prefix)
    logger.info(f"Virtual environment: {'Yes' if in_venv else 'No'}")
    if in_venv:
        logger.info(f"Virtual environment path: {venv_path}")
    
    # Determine where to save the .env file
    script_dir = Path(__file__).parent.absolute()
    logger.info(f"Script directory: {script_dir}")
    
    env_paths = [
        # Current directory
        Path.cwd() / '.env',
        # Script directory
        script_dir / '.env',
        # Parent of script directory
        script_dir.parent / '.env'
    ]
    
    # Check if .env exists in any of these locations
    env_path = None
    for path in env_paths:
        if path.exists():
            env_path = path
            logger.info(f"Found existing .env file at: {env_path}")
            break
    
    # If not found, use current directory
    if not env_path:
        env_path = Path.cwd() / '.env'
        logger.info(f"Creating new .env file at: {env_path}")
    
    # Update .env file
    try:
        # Load existing .env to preserve other settings
        load_dotenv(env_path)
        
        # Update the content
        env_content = ""
        if env_path.exists():
            with open(env_path, 'r') as f:
                env_content = f.read()
        
        # Update or add WALLET_PRIVATE_KEY
        if 'WALLET_PRIVATE_KEY=' in env_content:
            # Replace existing key
            lines = env_content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('WALLET_PRIVATE_KEY='):
                    lines[i] = f'WALLET_PRIVATE_KEY={private_key_hex}'
                    break
            updated_content = '\n'.join(lines)
        else:
            # Add new key
            updated_content = env_content + f'\nWALLET_PRIVATE_KEY={private_key_hex}'
        
        # Write back to .env
        with open(env_path, 'w') as f:
            f.write(updated_content)
        
        logger.info(f"Updated {env_path} with new private key")
    except Exception as e:
        logger.error(f"Error updating .env file: {e}")
        logger.info("Please manually update your .env file with the following line:")
        logger.info(f"WALLET_PRIVATE_KEY={private_key_hex}")
    
    logger.info("⚠️ IMPORTANT: Back up your private key securely!")
    logger.info("⚠️ This keypair contains NO funds. To use it for real trading, you need to fund it.")
    
    return keypair, pubkey_str, private_key_hex

async def main():
    # Generate new keypair
    keypair, pubkey_str, private_key_hex = generate_new_keypair()
    
    # Load .env file to get RPC endpoint
    load_dotenv()
    rpc_endpoint = os.getenv('SOLANA_RPC_ENDPOINT', 'https://api.mainnet-beta.solana.com')
    
    # Check connection
    await check_connection(rpc_endpoint, pubkey_str)
    
    # Instructions for the user
    logger.info("\n===================== NEXT STEPS =====================")
    logger.info("1. Your .env file has been updated with the new private key")
    logger.info(f"2. Wallet address: {pubkey_str}")
    logger.info("3. To use this wallet for real trading, fund it with SOL")
    logger.info("4. Update your bot_control.json to use simulation_mode: true until you're ready for real trading")
    logger.info("5. Restart your trading bot")
    logger.info("=====================================================\n")

if __name__ == "__main__":
    asyncio.run(main())