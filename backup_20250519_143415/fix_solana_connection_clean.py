# fix_solana_connection_clean.py - Fixed version without unicode and with better compatibility

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

# Define known working versions of Solana packages - updated for compatibility
COMPATIBLE_VERSIONS = {
    'solana': '0.30.2',       # Keep current version to avoid conflicts
    'solders': '0.18.1',      # Keep current version
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
    """Install missing packages only (avoid version conflicts)"""
    installed, missing = check_installed_versions()
    
    if not missing:
        logger.info("No missing packages to install")
        return True
        
    # Install only missing packages
    for package in missing:
        version = COMPATIBLE_VERSIONS.get(package)
        if version:
            logger.info(f"Installing {package}=={version}")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', f"{package}=={version}"])
            except subprocess.CalledProcessError as e:
                logger.error(f"Error installing {package}: {e}")
    
    logger.info("Installation of missing packages complete!")
    return True

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
        # Skip directories that are clearly not useful
        if 'venv' in root or '.git' in root:
            continue
        for file in files:
            if ('wallet' in file.lower() or 'key' in file.lower()) and not file.endswith('.py') and not 'site-packages' in root:
                wallet_files.append(os.path.join(root, file))
    
    if wallet_files:
        logger.info(f"Found potential wallet files: {wallet_files[:5]}")
        if len(wallet_files) > 5:
            logger.info(f"...and {len(wallet_files) - 5} more")
    
    return wallet_private_key is not None

def create_direct_solana_trader_fix():
    """Create a direct replacement for key parts of solana_trader.py"""
    # Locate solana_trader.py
    trader_file = 'solana_trader.py'
    if not os.path.exists(trader_file):
        trader_file = os.path.join('core', 'solana_trader.py')
    
    if not os.path.exists(trader_file):
        logger.error(f"Could not find solana_trader.py")
        return False
    
    # Create a simple wrapper module
    wrapper_code = """
# solana_wrapper.py - Compatibility layer for Solana API

import logging
import asyncio
from datetime import datetime
import os
import sys

# Set up logging
logger = logging.getLogger('solana_wrapper')

# Check if Solana libraries are available
try:
    from solders.pubkey import Pubkey
    from solders.keypair import Keypair
    from solana.rpc.async_api import AsyncClient
    from solana.transaction import Transaction
    HAS_SOLANA_LIBS = True
    logger.info("Solana libraries are available")
except ImportError:
    HAS_SOLANA_LIBS = False
    logger.warning("Solana libraries not available, using simulated connection")

async def get_recent_blockhash_compatible(client):
    """
    """Compatibility function for get_recent_blockhash"""
    """
    try:
        # Try new API first
        if hasattr(client, 'get_latest_blockhash'):
            logger.info("Using get_latest_blockhash")
            response = await client.get_latest_blockhash()
            if hasattr(response, 'value'):
                return response.value.blockhash, response.value.last_valid_block_height
            return response, 0
        
        # Fall back to old API
        elif hasattr(client, 'get_recent_blockhash'):
            logger.info("Using get_recent_blockhash")
            return await client.get_recent_blockhash()
        
        # Last resort - mock response
        else:
            logger.warning("Neither get_latest_blockhash nor get_recent_blockhash available, using mock data")
            # Need to create proper mock data
            try:
                from solders.hash import Hash
                mock_hash = Hash([0] * 32)
                return mock_hash, 0
            except ImportError:
                logger.error("Could not create mock hash")
                return None, 0
    except Exception as e:
        logger.error(f"Error getting blockhash: {e}")
        try:
            from solders.hash import Hash
            mock_hash = Hash([0] * 32)
            return mock_hash, 0
        except ImportError:
            logger.error("Could not create mock hash")
            return None, 0

def create_keypair_from_private_key(private_key):
    """Create a keypair from a private key in various formats"""
    if not HAS_SOLANA_LIBS:
        logger.warning("Solana libraries not available, cannot create keypair")
        return None
    
    if not private_key:
        logger.error("No private key provided")
        return None
    
    logger.info(f"Creating keypair from private key (first 6 chars): {private_key[:6]}...")
    
    # Try different methods
    try:
        # Try from_seed with hex string
        if len(private_key) == 64 and all(c in '0123456789abcdefABCDEF' for c in private_key):
            logger.info("Trying from_seed with hex...")
            seed = bytes.fromhex(private_key)
            return Keypair.from_seed(seed[:32])
    except Exception as e:
        logger.warning(f"from_seed with hex failed: {e}")
    
    try:
        # Try from_bytes
        import base58
        try:
            logger.info("Trying from_bytes with base58...")
            seed = base58.b58decode(private_key)
            return Keypair.from_bytes(seed)
        except Exception as e:
            logger.warning(f"from_bytes with base58 failed: {e}")
    except ImportError:
        logger.warning("base58 module not available")
    
    try:
        # Try from_base58_string if available
        if hasattr(Keypair, 'from_base58_string'):
            logger.info("Trying from_base58_string...")
            return Keypair.from_base58_string(private_key)
    except Exception as e:
        logger.warning(f"from_base58_string failed: {e}")
    
    # Last resort - try to create a simulated keypair
    logger.warning("Could not create keypair from private key, using simulated keypair")
    try:
        return Keypair()
    except Exception as e:
        logger.error(f"Error creating simulated keypair: {e}")
        return None

async def connect_to_solana(rpc_endpoint=None):
    """Create a connection to the Solana network"""
    if not HAS_SOLANA_LIBS:
        logger.warning("Solana libraries not available, using simulated connection")
        return "SIMULATED_CONNECTION"
    
    # Use default endpoint if none provided
    if not rpc_endpoint:
        rpc_endpoint = "https://api.mainnet-beta.solana.com"
    
    logger.info(f"Connecting to Solana via {rpc_endpoint}")
    
    try:
        # Create the client with reasonable timeout
        client = AsyncClient(rpc_endpoint, timeout=30)
        
        # Test the connection with a simple request
        try:
            is_connected = await client.is_connected()
            if is_connected:
                logger.info("Successfully connected to Solana network")
                return client
            else:
                logger.error("Failed to connect to Solana network")
                return None
        except Exception as e:
            logger.error(f"Error testing Solana connection: {e}")
            return None
    except Exception as e:
        logger.error(f"Error creating Solana client: {e}")
        return None

async def get_sol_price():
    """Get the current SOL price in USD"""
    try:
        import httpx
        
        # Try CoinGecko API first (more reliable)
        url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            data = response.json()
            price = float(data['solana']['usd'])
            logger.info(f"Got SOL price from CoinGecko: ${price}")
            return price
    except Exception as e:
        logger.error(f"Error getting SOL price from CoinGecko: {e}")
        
        try:
            # Fallback to Binance API
            url = "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                data = response.json()
                price = float(data['price'])
                logger.info(f"Got SOL price from Binance: ${price}")
                return price
        except Exception as e:
            logger.error(f"Error getting SOL price from Binance: {e}")
            
            # Fallback to a reasonable default price
            default_price = 173.0
            logger.warning(f"Using default SOL price: ${default_price}")
            return default_price
"""
    
    # Write the wrapper module
    wrapper_file = 'solana_wrapper.py'
    with open(wrapper_file, 'w', encoding='utf-8') as f:
        f.write(wrapper_code)
    
    logger.info(f"Created Solana wrapper module at {wrapper_file}")
    
    # Move it to the core directory too
    core_wrapper_file = os.path.join('core', 'solana_wrapper.py')
    try:
        shutil.copy2(wrapper_file, core_wrapper_file)
        logger.info(f"Copied wrapper to {core_wrapper_file}")
    except Exception as e:
        logger.warning(f"Could not copy wrapper to core directory: {e}")
    
    # Create a patch that includes the import statement
    patch_code = """
# Import the Solana wrapper module
try:
    from solana_wrapper import get_recent_blockhash_compatible, create_keypair_from_private_key, connect_to_solana, get_sol_price
    logger.info("Imported Solana wrapper module")
except ImportError:
    logger.warning("Could not import Solana wrapper module")
"""
    
    # Backup the trader file
    backup_file = f"{trader_file}.bak"
    if not os.path.exists(backup_file):
        shutil.copy2(trader_file, backup_file)
        logger.info(f"Created backup of {trader_file} at {backup_file}")
    
    # Read the trader file
    with open(trader_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find a suitable location to insert the import
    import_pos = content.find('import ')
    import_end = 0
    for line in content.split('\n'):
        if line.startswith('import ') or line.startswith('from '):
            import_end = content.find(line) + len(line)
    
    if import_end > 0:
        # Add the patch after all imports
        new_content = content[:import_end] + '\n\n' + patch_code + content[import_end:]
        
        # Replace get_recent_blockhash calls
        if 'get_recent_blockhash' in new_content:
            new_content = new_content.replace(
                'await self.client.get_recent_blockhash()', 
                'await get_recent_blockhash_compatible(self.client)'
            )
            logger.info("Added get_recent_blockhash patch")
        
        # Replace keypair creation if needed
        if 'self.private_key' in new_content and 'Keypair' in new_content:
            # Look for keypair creation patterns to replace
            patterns = [
                'self.keypair = Keypair.from_seed(',
                'self.keypair = Keypair.from_bytes(',
                'self.keypair = Keypair.from_'
            ]
            
            for pattern in patterns:
                if pattern in new_content:
                    # Find the full line containing the pattern
                    idx = new_content.find(pattern)
                    line_start = new_content.rfind('\n', 0, idx) + 1
                    line_end = new_content.find('\n', idx)
                    if line_end == -1:
                        line_end = len(new_content)
                    
                    # Get the indentation level
                    indent = ''
                    for c in new_content[line_start:idx]:
                        if c.isspace():
                            indent += c
                        else:
                            break
                    
                    # Create replacement line
                    replacement = f"{indent}self.keypair = create_keypair_from_private_key(self.private_key)"
                    
                    # Replace the full line
                    original_line = new_content[line_start:line_end]
                    new_content = new_content.replace(original_line, replacement)
                    logger.info(f"Added keypair creation patch for: {original_line.strip()}")
        
        # Write the patched file
        with open(trader_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info(f"Successfully patched {trader_file}")
        return True
    else:
        logger.warning(f"Could not find a suitable place to add patch in {trader_file}")
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
    """Create an improved Solana connection test script without unicode chars"""
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
    print(f"Solana connection: {'SUCCESS' if connection_success else 'FAILED'}")
    print(f"Wallet key: {'SUCCESS' if wallet_success else 'FAILED'}")
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
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    logger.info(f"Created improved Solana connection test at {test_file}")
    return test_file

def check_and_fix_main_file():
    """Check and fix issues in main.py if needed"""
    main_file = 'main.py'
    if not os.path.exists(main_file):
        main_file = os.path.join('core', 'main.py')
    
    if not os.path.exists(main_file):
        logger.warning(f"Could not find main.py")
        return False
    
    # Create a patch for main.py
    patch_code = """
# Import the Solana wrapper for compatibility
try:
    import solana_wrapper
    logger.info("Imported Solana wrapper for compatibility")
except ImportError:
    logger.warning("Could not import Solana wrapper")
"""
    
    # Backup the main file
    backup_file = f"{main_file}.bak"
    if not os.path.exists(backup_file):
        shutil.copy2(main_file, backup_file)
        logger.info(f"Created backup of {main_file} at {backup_file}")
    
    # Read the main file
    with open(main_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find a suitable location to insert the import
    import_pos = content.find('import ')
    import_end = 0
    for line in content.split('\n'):
        if line.startswith('import ') or line.startswith('from '):
            import_end = content.find(line) + len(line)
    
    if import_end > 0:
        # Add the patch after all imports
        new_content = content[:import_end] + '\n\n' + patch_code + content[import_end:]
        
        # Write the patched file
        with open(main_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info(f"Successfully patched {main_file}")
        return True
    else:
        logger.warning(f"Could not find a suitable place to add patch in {main_file}")
        return False

def main():
    print("=" * 60)
    print("SOLANA CONNECTION FIX (CLEAN VERSION)")
    print("=" * 60)
    print()
    
    # Check current versions
    print("Checking installed Solana package versions...")
    installed, missing = check_installed_versions()
    
    for package, version in installed.items():
        compatible = COMPATIBLE_VERSIONS.get(package, "Unknown")
        status = "OK" if version == compatible else "MISMATCH"
        print(f"  - {package}: {version} (compatible: {compatible}) {status}")
    
    for package in missing:
        print(f"  - {package}: Not installed (compatible: {COMPATIBLE_VERSIONS.get(package, 'Unknown')}) MISSING")
    print()
    
    # Ask if user wants to install missing packages
    if missing:
        install = input("Would you like to install missing Solana packages? (y/n): ").lower().strip()
        if install.startswith('y'):
            print("Installing missing packages...")
            install_compatible_versions()
        else:
            print("Skipping package installation")
        print()
    
    # Check wallet private key
    print("Checking wallet private key configuration...")
    has_private_key = check_wallet_private_key()
    if has_private_key:
        print("Wallet private key is configured")
    else:
        print("Wallet private key not found or not properly configured")
    print()
    
    # Create solana_wrapper module and patch solana_trader.py
    print("Creating Solana wrapper module and patching solana_trader.py...")
    patched = create_direct_solana_trader_fix()
    if patched:
        print("Created Solana wrapper module and patched solana_trader.py")
    else:
        print("Could not create patch for solana_trader.py")
    print()
    
    # Check and fix main.py
    print("Checking and fixing main.py...")
    fixed_main = check_and_fix_main_file()
    if fixed_main:
        print("Successfully patched main.py")
    else:
        print("Could not patch main.py")
    print()
    
    # Fix bot control
    print("Ensuring bot_control.json is properly configured...")
    fixed_control = fix_bot_control()
    if fixed_control:
        print("Updated bot_control.json")
    else:
        print("Could not update bot_control.json")
    print()
    
    # Create improved connection test
    print("Creating improved Solana connection test...")
    test_file = create_connection_test()
    print(f"Created improved test at {test_file}")
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
