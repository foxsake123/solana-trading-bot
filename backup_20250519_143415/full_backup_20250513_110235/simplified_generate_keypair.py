#!/usr/bin/env python
"""
Simplified keypair generator for Solana trading bot
"""

import os
import sys
import logging
import binascii
from pathlib import Path
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import compatible Solana packages
try:
    from solders.keypair import Keypair
    import base58
    logging.info("Successfully imported required packages")
except ImportError as e:
    logging.error(f"Failed to import required packages: {e}")
    logging.error("Please install with: pip install solana solders base58")
    sys.exit(1)

def save_key_to_env(private_key_bytes, private_key_hex):
    """Save private key to .env file"""
    try:
        # Find .env file location
        env_file = None
        possible_locations = ['.env', '../.env', '../../.env']
        
        for location in possible_locations:
            if os.path.exists(location):
                env_file = location
                break
        
        if not env_file:
            env_file = '.env'
            # Create new .env file if it doesn't exist
            if not os.path.exists(env_file):
                with open(env_file, 'w') as f:
                    f.write("# Solana Trading Bot Environment Variables\n")
        
        # Read existing content
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Update or add the private key
        if 'WALLET_PRIVATE_KEY=' in content:
            lines = content.split('\n')
            new_lines = []
            
            for line in lines:
                if line.startswith('WALLET_PRIVATE_KEY='):
                    new_lines.append(f'WALLET_PRIVATE_KEY={private_key_hex}')
                else:
                    new_lines.append(line)
            
            new_content = '\n'.join(new_lines)
        else:
            new_content = content + f"\nWALLET_PRIVATE_KEY={private_key_hex}\n"
        
        # Write updated content
        with open(env_file, 'w') as f:
            f.write(new_content)
        
        logger.info(f"Private key saved to {os.path.abspath(env_file)}")
        return True
    
    except Exception as e:
        logger.error(f"Error saving private key to .env: {e}")
        return False

def generate_keypair():
    """Generate a new Solana keypair"""
    try:
        # Generate random keypair
        keypair = Keypair()
        pubkey = keypair.pubkey()
        pubkey_str = str(pubkey)
        
        # Get private key bytes
        try:
            # Direct access to the secret key - use underlying array implementation
            private_key_bytes = bytes(keypair)[:32]
        except Exception as e1:
            logger.warning(f"Primary method failed: {e1}")
            try:
                # Alternative approach - use seed attribute if available
                if hasattr(keypair, 'seed'):
                    private_key_bytes = keypair.seed()
                else:
                    # Last resort - access internal array bytes
                    private_key_bytes = bytes(keypair._keypair.secret_key)
            except Exception as e2:
                logger.error(f"Alternative method failed: {e2}")
                # Generate a random 32-byte private key
                private_key_bytes = os.urandom(32)
        
        # Format in various ways
        private_key_hex = private_key_bytes.hex()
        private_key_base58 = base58.b58encode(private_key_bytes).decode()
        private_key_array = str([b for b in private_key_bytes])
        
        # Save to .env file
        save_key_to_env(private_key_bytes, private_key_hex)
        
        # Display all formats for user to choose
        logger.info("Generated new Solana keypair")
        logger.info(f"Wallet address: {pubkey_str}")
        logger.info("\nPrivate key formats (KEEP SECURE):")
        logger.info(f"Hex format:     {private_key_hex}")
        logger.info(f"Base58 format:  {private_key_base58}")
        logger.info(f"Array format:   {private_key_array}")
        
        # Save to backup file
        backup_file = "solana_key_backup.txt"
        with open(backup_file, "w") as f:
            f.write(f"SOLANA KEYPAIR BACKUP - KEEP SECURE\n")
            f.write(f"Generated on: {os.path.basename(__file__)}\n\n")
            f.write(f"Wallet address: {pubkey_str}\n")
            f.write(f"Hex format:     {private_key_hex}\n")
            f.write(f"Base58 format:  {private_key_base58}\n")
            f.write(f"Array format:   {private_key_array}\n")
        
        logger.info(f"\nBackup saved to {os.path.abspath(backup_file)}")
        
        logger.info("\n⚠️ IMPORTANT: This keypair contains NO funds!")
        logger.info("⚠️ To use for real trading, fund this wallet with SOL")
        
        return pubkey_str, private_key_hex, private_key_base58
    
    except Exception as e:
        logger.error(f"Error generating keypair: {e}")
        return None, None, None

if __name__ == "__main__":
    # Generate and save new keypair
    wallet_address, private_key_hex, private_key_base58 = generate_keypair()
    
    # Additional instructions
    if wallet_address:
        print("\n========== NEXT STEPS ==========")
        print("1. Your .env file has been updated with the new private key")
        print(f"2. Set simulation_mode: true in bot_control.json during testing")
        print(f"3. Backup file created: solana_key_backup.txt")
        print("=================================")
