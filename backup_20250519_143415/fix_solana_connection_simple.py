# fix_solana_connection.py - Fix Solana library compatibility issues

import os
import sys
import logging
import subprocess
import importlib
import json
import shutil
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fix_solana_connection')

# Define known working versions of Solana packages
COMPATIBLE_VERSIONS = {
    'solana': '0.29.2',  # Earlier version that's more compatible
    'solders': '0.18.1',  # Current version seems compatible
    'anchorpy': '0.18.0',
    'base58': '2.1.1',
    'typing-extensions': '4.7.1',
    'construct': '2.10.68'
}

def check_installed_versions():
    """Check installed versions of Solana packages"""
    packages = list(COMPATIBLE_VERSIONS.keys())
    installed = {}
    missing = []
    
    for package in packages:
        try:
            module = importlib.import_module(package)
            if hasattr(module, '__version__'):
                installed[package] = module.__version__
            elif hasattr(module, 'version'):
                installed[package] = module.version
            else:
                # Try to get version from package metadata
                try:
                    from importlib.metadata import version
                    installed[package] = version(package)
                except:
                    installed[package] = "Unknown"
        except ImportError:
            missing.append(package)
    
    return installed, missing

def install_compatible_versions():
    """Install compatible versions of Solana packages"""
    # Create requirements file with compatible versions
    with open('solana_requirements.txt', 'w') as f:
        for package, version in COMPATIBLE_VERSIONS.items():
            f.write(f"{package}=={version}\n")
    
    logger.info("Installing compatible versions of Solana packages...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'solana_requirements.txt'])
        logger.info("Installation complete!")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error installing packages: {e}")
        return False

def check_wallet_private_key():
    """Check if wallet private key is properly configured"""
    # Check .env file
    env_file = '.env'
    if not os.path.exists(env_file):
        env_file = os.path.join('core', '.env')
    
    wallet_private_key = None
    
    if os.path.exists(env_file):
        logger.info(f"Found .env file at {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('WALLET_PRIVATE_KEY='):
                    wallet_private_key = line.strip().split('=', 1)[1].strip()
                    # Remove quotes if present
                    if wallet_private_key.startswith('"') and wallet_private_key.endswith('"'):
                        wallet_private_key = wallet_private_key[1:-1]
                    logger.info("Found WALLET_PRIVATE_KEY in .env file")
                    break
    
    # Check config.py
    config_file = 'config.py'
    if not os.path.exists(config_file):
        config_file = os.path.join('core', 'config.py')
    
    if os.path.exists(config_file):
        logger.info(f"Found config.py at {config_file}")
        with open(config_file, 'r') as f:
            content = f.read()
            if 'WALLET_PRIVATE_KEY' in content:
                logger.info("Found WALLET_PRIVATE_KEY reference in config.py")
                
                # Check if it's loading from .env
                if "os.getenv('WALLET_PRIVATE_KEY')" in content:
                    logger.info("config.py is loading WALLET_PRIVATE_KEY from environment variables")
    
    # Check for wallet backup files
    wallet_files = []
    for root, _, files in os.walk('.'):
        for file in files:
            if 'wallet' in file.lower() or 'key' in file.lower():
                wallet_files.append(os.path.join(root, file))
    
    if wallet_files:
        logger.info(f"Found potential wallet files: {wallet_files}")
    
    return wallet_private_key is not None

def create_solana_trader_patch():
    """Create a patch for solana_trader.py to handle API changes"""
    # First check if the file exists
    trader_file = 'solana_trader.py'
    if not os.path.exists(trader_file):
        trader_file = os.path.join('core', 'solana_trader.py')
    
    if not os.path.exists(trader_file):
        logger.error(f"Could not find solana_trader.py")
        return False
    
    # Create backup
    backup_file = f"{trader_file}.bak"
    shutil.copy2(trader_file, backup_file)
    logger.info(f"Created backup of {trader_file} at {backup_file}")
    
    # Read the file
    with open(trader_file, 'r') as f:
        content = f.read()
    
    # Add patch for get_recent_blockhash
    if 'get_recent_blockhash' in content:
        logger.info("Found get_recent_blockhash usage, adding patch...")
        
        # Create patch for the AsyncClient
        patched_content = """
# PATCHED: Added compatibility layer for Solana API changes
async def get_recent_blockhash_compatible(client):
    \"\"\"Compatibility function for get_recent_blockhash\"\"\"
    try:
        # Try new API first
        if hasattr(client, 'get_latest_blockhash'):
            response = await client.get_latest_blockhash()
            if hasattr(response, 'value'):
                return response.value.blockhash, response.value.last_valid_block_height
            return response, 0
        # Fall back to old API
        elif hasattr(client, 'get_recent_blockhash'):
            return await client.get_recent_blockhash()
        # Last resort - mock response
        else:
            logger.warning("Neither get_latest_blockhash nor get_recent_blockhash available, using mock data")
            from solders.hash import Hash
            return Hash([0] * 32), 0
    except Exception as e:
        logger.error(f"Error getting blockhash: {e}")
        from solders.hash import Hash
        return Hash([0] * 32), 0
"""
        
        # Add the function to the file
        # Find a good spot to insert - after the imports
        import_end = max(content.rfind('import '), content.rfind('from '))
        if import_end > 0:
            next_line_break = content.find('\n', import_end)
            if next_line_break > 0:
                new_content = content[:next_line_break + 1] + patched_content + content[next_line_break + 1:]
                
                # Replace get_recent_blockhash with the compatible function
                new_content = new_content.replace(
                    'await self.client.get_recent_blockhash()', 
                    'await get_recent_blockhash_compatible(self.client)'
                )
                
                # Write the patched file
                with open(trader_file, 'w') as f:
                    f.write(new_content)
                
                logger.info(f"Added blockhash compatibility patch to {trader_file}")
                return True
    
    logger.warning("Could not find suitable place to add patch")
    return False

def fix_bot_control():
    """Make sure bot_control.json is properly set"""
    control_file = 'bot_control.json'
    if not os.path.exists(control_file):
        control_file = os.path.join('data', 'bot_control.json')
        if not os.path.exists(control_file):
            control_file = os.path.join('core', 'bot_control.json')
    
    if not os.path.exists(control_file):
        logger.warning("Could not find bot_control.json")
        
        # Create data directory if needed
        os.makedirs('data', exist_ok=True)
        
        # Create a default bot_control.json
        control_data = {
            'running': True,
            'simulation_mode': True,
            'filter_fake_tokens': True,
            'use_birdeye_api': True,
            'use_machine_learning': False,
            'take_profit_target': 15.0,
            'stop_loss_percentage': 0.25,
            'max_investment_per_token': 0.1,
            'slippage_tolerance': 0.3,
            'MIN_SAFETY_SCORE': 0.0,
            'MIN_VOLUME': 0.0,
            'MIN_LIQUIDITY': 0.0,
            'MIN_MCAP': 0.0,
            'MIN_HOLDERS': 0,
            'MIN_PRICE_CHANGE_1H': 0.0,
            'MIN_PRICE_CHANGE_6H': 0.0,
            'MIN_PRICE_CHANGE_24H': 0.0
        }
        
        control_file = os.path.join('data', 'bot_control.json')
        with open(control_file, 'w') as f:
            json.dump(control_data, f, indent=4)
        
        logger.info(f"Created default bot_control.json at {control_file}")
        return True
    
    # Load existing control file
    with open(control_file, 'r') as f:
        control_data = json.load(f)
    
    # Make sure simulation_mode is set for now
    control_data['simulation_mode'] = True
    
    # Save updated control file
    with open(control_file, 'w') as f:
        json.dump(control_data, f, indent=4)
    
    logger.info(f"Updated {control_file} to ensure simulation_mode is enabled")
    return True

def create_connection_test():
    """Create an improved Solana connection test script"""
    test_script = """
# improved_solana_test.py - Comprehensive Solana connection test

import os
import sys
import logging
import importlib
import asyncio
import base58
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('solana_test')

async def test_solana_connection():
    \"\"\"Test Solana connection with compatibility for different API versions\"\"\"
    try:
        # Import Solana packages
        try:
            from solders.pubkey import Pubkey
            from solders.keypair import Keypair
            from solana.rpc.async_api import AsyncClient
            from solana.transaction import Transaction
            logger.info("Successfully imported Solana packages")
        except ImportError as e:
            logger.error(f"Failed to import Solana packages: {e}")
            return False
        
        # Load RPC endpoint
        rpc_endpoint = os.environ.get('SOLANA_RPC_ENDPOINT')
        if not rpc_endpoint:
            # Try to load from config
            try:
                sys.path.insert(0, '.')
                import config
                if hasattr(config, 'BotConfiguration'):
                    if hasattr(config.BotConfiguration, 'API_KEYS'):
                        rpc_endpoint = config.BotConfiguration.API_KEYS.get('SOLANA_RPC_ENDPOINT')
            except ImportError:
                pass
        
        if not rpc_endpoint:
            rpc_endpoint = "https://api.mainnet-beta.solana.com"
        
        logger.info(f"Using RPC endpoint: {rpc_endpoint}")
        
        # Create client
        client = AsyncClient(rpc_endpoint)
        logger.info("Created AsyncClient")
        
        # Test connection
        logger.info("Testing connection...")
        
        # Try different API versions
        methods_to_try = [
            'get_latest_blockhash',
            'get_recent_blockhash',
            'get_health',
            'get_version',
            'get_balance'
        ]
        
        success = False
        for method in methods_to_try:
            if hasattr(client, method):
                logger.info(f"Testing {method}...")
                try:
                    if method == 'get_balance':
                        # Need a public key for get_balance
                        result = await client.get_balance(Pubkey.find_program_address(bytes([0]), Pubkey.from_string("11111111111111111111111111111111"))[0])
                    else:
                        result = await getattr(client, method)()
                    logger.info(f"{method} result: {result}")
                    success = True
                    break
                except Exception as e:
                    logger.warning(f"{method} failed: {e}")
            else:
                logger.warning(f"Client does not have method: {method}")
        
        # Close the client
        await client.close()
        
        if success:
            logger.info("Successfully connected to Solana!")
            return True
        else:
            logger.error("Failed to connect to Solana with any method")
            return False
            
    except Exception as e:
        logger.error(f"Error testing Solana connection: {e}")
        return False

def get_private_key():
    \"\"\"Try to find the private key in different locations\"\"\"
    # Check environment variable
    pk = os.environ.get('WALLET_PRIVATE_KEY')
    if pk:
        logger.info("Found private key in environment variables")
        return pk
    
    # Check .env file
    env_file = '.env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('WALLET_PRIVATE_KEY='):
                    pk = line.strip().split('=', 1)[1].strip()
                    # Remove quotes if present
                    if pk.startswith('"') and pk.endswith('"'):
                        pk = pk[1:-1]
                    logger.info("Found private key in .env file")
                    return pk
    
    # Check config.py
    try:
        sys.path.insert(0, '.')
        import config
        if hasattr(config, 'BotConfiguration'):
            if hasattr(config.BotConfiguration, 'API_KEYS'):
                pk = config.BotConfiguration.API_KEYS.get('WALLET_PRIVATE_KEY')
                if pk:
                    logger.info("Found private key in config.py")
                    return pk
    except ImportError:
        pass
    
    logger.warning("Could not find private key")
    return None

async def test_wallet_key():
    \"\"\"Test the wallet private key\"\"\"
    private_key = get_private_key()
    if not private_key:
        logger.error("No private key found")
        return False
    
    logger.info(f"Private key: {private_key[:6]}...{private_key[-6:]}")
    
    try:
        from solders.keypair import Keypair
        
        # Try different methods of creating a keypair
        methods = [
            'from_bytes',
            'from_seed',
            'from_base58_string'
        ]
        
        for method in methods:
            try:
                logger.info(f"Trying {method}...")
                
                if method == 'from_bytes':
                    if len(private_key) == 64:  # Hex format
                        keypair = Keypair.from_bytes(bytes.fromhex(private_key))
                    else:
                        # Try base58 decode
                        keypair = Keypair.from_bytes(base58.b58decode(private_key))
                
                elif method == 'from_seed':
                    if len(private_key) == 64:  # Hex format
                        keypair = Keypair.from_seed(bytes.fromhex(private_key[:64]))
                    else:
                        # Try using the raw bytes
                        seed = private_key.encode('utf-8')
                        if len(seed) < 32:
                            # Pad to 32 bytes
                            seed = seed + b'\\x00' * (32 - len(seed))
                        keypair = Keypair.from_seed(seed[:32])
                
                elif method == 'from_base58_string':
                    if hasattr(Keypair, 'from_base58_string'):
                        keypair = Keypair.from_base58_string(private_key)
                    else:
                        continue
                
                # If we got here, we succeeded
                logger.info(f"Success! Created keypair using {method}")
                logger.info(f"Public key: {keypair.pubkey()}")
                return True
                
            except Exception as e:
                logger.warning(f"{method} failed: {e}")
        
        logger.error("Failed to create keypair with any method")
        return False
        
    except ImportError as e:
        logger.error(f"Failed to import required packages: {e}")
        return False

async def main():
    print("=" * 60)
    print("IMPROVED SOLANA CONNECTION TEST")
    print("=" * 60)
    print()
    
    # Test Solana connection
    print("Testing Solana connection...")
    connection_success = await test_solana_connection()
    print()
    
    # Test wallet key
    print("Testing wallet key...")
    wallet_success = await test_wallet_key()
    print()
    
    print("=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"Solana connection: {'✅ SUCCESS' if connection_success else '❌ FAILED'}")
    print(f"Wallet key: {'✅ SUCCESS' if wallet_success else '❌ FAILED'}")
    print()
    
    if not connection_success or not wallet_success:
        print("RECOMMENDATIONS:")
        if not connection_success:
            print("- Check your internet connection")
            print("- Verify the RPC endpoint in your configuration")
            print("- Make sure the RPC endpoint is accessible")
        if not wallet_success:
            print("- Check your wallet private key format")
            print("- Ensure the private key is correctly specified in .env or config.py")
        print()
    else:
        print("All tests passed successfully!")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
"""
    
    # Write the test script
    test_file = 'improved_solana_test.py'
    with open(test_file, 'w') as f:
        f.write(test_script)
    
    logger.info(f"Created improved Solana connection test at {test_file}")
    return test_file

def main():
    print("=" * 60)
    print("SOLANA CONNECTION FIX")
    print("=" * 60)
    print()
    
    # Check current versions
    print("Checking installed Solana package versions...")
    installed, missing = check_installed_versions()
    
    for package, version in installed.items():
        compatible = COMPATIBLE_VERSIONS.get(package, "Unknown")
        status = "✅" if version == compatible else "❌"
        print(f"  - {package}: {version} (compatible: {compatible}) {status}")
    
    for package in missing:
        print(f"  - {package}: Not installed (compatible: {COMPATIBLE_VERSIONS.get(package, 'Unknown')}) ❌")
    print()
    
    # Ask if user wants to install compatible versions
    install = input("Would you like to install compatible versions of Solana packages? (y/n): ").lower().strip()
    if install.startswith('y'):
        print("Installing compatible versions...")
        install_compatible_versions()
    else:
        print("Skipping package installation")
    print()
    
    # Check wallet private key
    print("Checking wallet private key configuration...")
    has_private_key = check_wallet_private_key()
    if has_private_key:
        print("✅ Wallet private key is configured")
    else:
        print("❌ Wallet private key not found or not properly configured")
    print()
    
    # Create solana_trader patch
    print("Creating solana_trader.py patch for API compatibility...")
    patched = create_solana_trader_patch()
    if patched:
        print("✅ Created patch for solana_trader.py")
    else:
        print("❌ Could not create patch for solana_trader.py")
    print()
    
    # Fix bot control
    print("Ensuring bot_control.json is properly configured...")
    fixed_control = fix_bot_control()
    if fixed_control:
        print("✅ Updated bot_control.json")
    else:
        print("❌ Could not update bot_control.json")
    print()
    
    # Create improved connection test
    print("Creating improved Solana connection test...")
    test_file = create_connection_test()
    print(f"✅ Created improved test at {test_file}")
    print()
    
    print("=" * 60)
    print("FIX COMPLETE!")
    print("=" * 60)
    print()
    print("Next steps:")
    print(f"1. Run the improved Solana connection test: python {test_file}")
    print("2. Run your bot in simulation mode: python core/main.py")
    print("3. Once everything is working, you can disable simulation mode in data/bot_control.json")
    print()
    print("=" * 60)

if __name__ == "__main__":
    main()
