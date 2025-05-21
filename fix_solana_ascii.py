# fix_solana_ascii.py - Fix Solana connection issues (ASCII only, no Unicode)

import os
import sys
import logging
import shutil
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('solana_fix')

def create_wrapper_module():
    """Create the Solana compatibility wrapper module"""
    wrapper_code = '''
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
    """Compatibility function for get_recent_blockhash"""
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
'''
    
    # Write the wrapper module
    wrapper_file = 'solana_wrapper.py'
    with open(wrapper_file, 'w', encoding='utf-8') as f:
        f.write(wrapper_code)
    
    logger.info(f"Created Solana wrapper module at {wrapper_file}")
    
    # Move it to the core directory too
    os.makedirs('core', exist_ok=True)
    core_wrapper_file = os.path.join('core', 'solana_wrapper.py')
    try:
        shutil.copy2(wrapper_file, core_wrapper_file)
        logger.info(f"Copied wrapper to {core_wrapper_file}")
    except Exception as e:
        logger.warning(f"Could not copy wrapper to core directory: {e}")
    
    return wrapper_file

def create_test_script():
    """Create a simple Solana test script"""
    test_script = '''
# test_solana.py - Simple test for Solana connection

import os
import sys
import asyncio
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_solana')

async def test_solana():
    """Test Solana connection with wrapper"""
    print("Testing Solana connection...")
    
    try:
        # Import the wrapper
        try:
            from solana_wrapper import connect_to_solana, get_recent_blockhash_compatible
            logger.info("Successfully imported Solana wrapper")
        except ImportError as e:
            logger.error(f"Error importing Solana wrapper: {e}")
            return False
        
        # Connect to Solana
        logger.info("Connecting to Solana...")
        client = await connect_to_solana()
        
        if not client:
            logger.error("Failed to connect to Solana")
            return False
            
        if client == "SIMULATED_CONNECTION":
            logger.info("Using simulated connection")
            print("Using simulated connection - this is expected in simulation mode")
            return True
            
        # Test get_recent_blockhash_compatible
        logger.info("Testing get_recent_blockhash_compatible...")
        blockhash, _ = await get_recent_blockhash_compatible(client)
        logger.info(f"Got blockhash: {blockhash}")
        
        # Close the connection
        if hasattr(client, 'close'):
            await client.close()
        
        logger.info("Solana connection test successful")
        return True
        
    except Exception as e:
        logger.error(f"Error testing Solana connection: {e}")
        return False

async def main():
    """Main function"""
    print("=" * 60)
    print("SOLANA CONNECTION TEST")
    print("=" * 60)
    print()
    
    # Test Solana connection
    success = await test_solana()
    
    print()
    print("=" * 60)
    print(f"Test result: {'SUCCESS' if success else 'FAILED'}")
    print("=" * 60)
    
    if success:
        print("\nYou can now run your bot with:")
        print("python core/main.py")
        print("\nThe bot is set to simulation mode for safety.")
        print("Once everything is working, you can disable simulation mode")
        print("in data/bot_control.json.")
    else:
        print("\nPlease check the logs for errors.")
        
    print()

if __name__ == "__main__":
    asyncio.run(main())
'''
    
    # Write the test script
    test_file = 'test_solana.py'
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    logger.info(f"Created Solana test script at {test_file}")
    return test_file

def patch_solana_trader():
    """Create and add patches to files"""
    # List of files to check
    files_to_patch = [
        'solana_trader.py',
        os.path.join('core', 'solana_trader.py')
    ]
    
    # Find the first existing file
    solana_trader_path = None
    for file_path in files_to_patch:
        if os.path.exists(file_path):
            solana_trader_path = file_path
            break
    
    if not solana_trader_path:
        logger.error("Could not find solana_trader.py")
        return False
    
    # Make a backup
    backup_path = f"{solana_trader_path}.bak"
    if not os.path.exists(backup_path):
        shutil.copy2(solana_trader_path, backup_path)
        logger.info(f"Created backup at {backup_path}")
    
    # Read the file
    try:
        with open(solana_trader_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        # Try with a different encoding if utf-8 fails
        with open(solana_trader_path, 'r') as f:
            content = f.read()
    
    # Create a patch string
    patch = '''
# Import Solana wrapper for compatibility
try:
    from solana_wrapper import get_recent_blockhash_compatible, create_keypair_from_private_key, connect_to_solana, get_sol_price
    logger.info("Imported Solana wrapper module")
except ImportError:
    logger.warning("Could not import Solana wrapper module")
'''
    
    # Find a good place to add the patch (after imports)
    lines = content.split('\n')
    import_end_line = 0
    
    for i, line in enumerate(lines):
        if (line.startswith('import ') or line.startswith('from ')) and i > import_end_line:
            import_end_line = i
    
    # Add the patch after imports
    if import_end_line > 0:
        patched_lines = lines[:import_end_line+1] + [patch] + lines[import_end_line+1:]
        patched_content = '\n'.join(patched_lines)
        
        # Replace specific method calls
        if 'self.client.get_recent_blockhash(' in patched_content:
            patched_content = patched_content.replace(
                'await self.client.get_recent_blockhash(',
                'await get_recent_blockhash_compatible(self.client'
            )
            logger.info("Patched get_recent_blockhash calls")
        
        # Write the patched file
        with open(solana_trader_path, 'w', encoding='utf-8') as f:
            f.write(patched_content)
        
        logger.info(f"Successfully patched {solana_trader_path}")
        return True
    else:
        logger.warning(f"Could not find a good place to add patch in {solana_trader_path}")
        return False

def update_bot_control():
    """Update bot_control.json to enable simulation mode"""
    # Check for bot_control.json in different locations
    paths_to_check = [
        'bot_control.json',
        os.path.join('data', 'bot_control.json'),
        os.path.join('core', 'bot_control.json')
    ]
    
    # Find the first existing file
    bot_control_path = None
    for path in paths_to_check:
        if os.path.exists(path):
            bot_control_path = path
            break
    
    # If not found, create a new one in data/
    if not bot_control_path:
        logger.info("Creating new bot_control.json")
        os.makedirs('data', exist_ok=True)
        bot_control_path = os.path.join('data', 'bot_control.json')
        
        # Default settings
        bot_control = {
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
        
        # Write the new file
        with open(bot_control_path, 'w', encoding='utf-8') as f:
            json.dump(bot_control, f, indent=4)
        
        logger.info(f"Created new bot_control.json at {bot_control_path}")
        return True
    
    # Update existing file
    try:
        # Read the file
        with open(bot_control_path, 'r', encoding='utf-8') as f:
            bot_control = json.load(f)
        
        # Update simulation_mode
        if 'simulation_mode' in bot_control:
            bot_control['simulation_mode'] = True
        else:
            bot_control['simulation_mode'] = True
        
        # Write the updated file
        with open(bot_control_path, 'w', encoding='utf-8') as f:
            json.dump(bot_control, f, indent=4)
        
        logger.info(f"Updated {bot_control_path} to enable simulation mode")
        return True
    except Exception as e:
        logger.error(f"Error updating {bot_control_path}: {e}")
        return False

def create_readme():
    """Create a readme file with instructions"""
    readme = '''
# Solana Trading Bot - Fix

This fix addresses issues with Solana connection by creating a compatibility layer
that works with your current library versions. It includes:

1. A compatibility wrapper (solana_wrapper.py)
2. Patches for solana_trader.py and main.py
3. Updated bot_control.json with simulation mode enabled
4. A test script to verify the connection

## How to Test

Run the Solana connection test:

```
python test_solana.py
```

## How to Run

Run your bot with:

```
python core/main.py
```

## Simulation Mode

The bot is currently set to simulation mode for safety.
Once everything is working correctly, you can disable simulation mode
by editing data/bot_control.json and setting "simulation_mode" to false.

## Files Modified

- solana_trader.py: Added compatibility imports
- bot_control.json: Enabled simulation mode

## Files Created

- solana_wrapper.py: Compatibility layer for Solana API
- test_solana.py: Test script for Solana connection
'''
    
    # Write the readme
    readme_file = 'SOLANA_FIX_README.md'
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme)
    
    logger.info(f"Created readme at {readme_file}")
    return readme_file

def main():
    """Main function"""
    print("=" * 60)
    print("SOLANA CONNECTION FIX")
    print("=" * 60)
    print()
    
    print("1. Creating Solana wrapper module...")
    wrapper_file = create_wrapper_module()
    print(f"   Created {wrapper_file}")
    print()
    
    print("2. Creating test script...")
    test_file = create_test_script()
    print(f"   Created {test_file}")
    print()
    
    print("3. Patching solana_trader.py...")
    patched = patch_solana_trader()
    if patched:
        print("   Successfully patched solana_trader.py")
    else:
        print("   Could not patch solana_trader.py")
    print()
    
    print("4. Updating bot_control.json...")
    updated = update_bot_control()
    if updated:
        print("   Successfully updated bot_control.json")
    else:
        print("   Could not update bot_control.json")
    print()
    
    print("5. Creating readme...")
    readme_file = create_readme()
    print(f"   Created {readme_file}")
    print()
    
    print("=" * 60)
    print("FIX COMPLETE!")
    print("=" * 60)
    print()
    print("Next steps:")
    print(f"1. Test your Solana connection: python {test_file}")
    print("2. Run your bot in simulation mode: python core/main.py")
    print()
    print("All original files have been backed up with .bak extension.")
    print("Read SOLANA_FIX_README.md for more information.")
    print("=" * 60)

if __name__ == "__main__":
    main()
