#!/usr/bin/env python3
"""
Quick fix script to update simulation mode to use real tokens instead of fake ones
Run this from your project root directory
"""

import os
import re
import shutil
from datetime import datetime
import json

# Backup directory
BACKUP_DIR = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def create_backup(files):
    """Create backup of files before modifying"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    for file in files:
        if os.path.exists(file):
            shutil.copy2(file, os.path.join(BACKUP_DIR, os.path.basename(file)))
            print(f"Backed up {file}")

def fix_token_scanner():
    """Fix token_scanner.py to use real tokens"""
    file_path = "token_scanner.py"
    if not os.path.exists(file_path):
        file_path = "core/token_scanner.py"
    
    if not os.path.exists(file_path):
        print(f"Warning: Could not find {file_path}")
        return
    
    print(f"Fixing {file_path}...")
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Find and update get_top_gainers method
    in_method = False
    method_indent = 0
    new_lines = []
    skip_lines = False
    
    for i, line in enumerate(lines):
        if 'async def get_top_gainers(self)' in line:
            in_method = True
            method_indent = len(line) - len(line.lstrip())
            new_lines.append(line)
            # Add new method content
            indent = ' ' * (method_indent + 4)
            new_lines.append(f'{indent}"""\n')
            new_lines.append(f'{indent}Get top gaining tokens - ALWAYS use real tokens\n')
            new_lines.append(f'{indent}\n')
            new_lines.append(f'{indent}:return: List of top gaining tokens\n')
            new_lines.append(f'{indent}"""\n')
            new_lines.append(f'{indent}top_gainers = []\n')
            new_lines.append(f'{indent}\n')
            new_lines.append(f'{indent}# ALWAYS get real tokens from BirdeyeAPI regardless of mode\n')
            new_lines.append(f'{indent}if self.birdeye_api:\n')
            new_lines.append(f'{indent}    try:\n')
            new_lines.append(f'{indent}        real_top_gainers = await self.birdeye_api.get_top_gainers()\n')
            new_lines.append(f'{indent}        top_gainers.extend(real_top_gainers)\n')
            new_lines.append(f'{indent}        logger.info(f"Found {{len(top_gainers)}} real top gainer tokens")\n')
            new_lines.append(f'{indent}    except Exception as e:\n')
            new_lines.append(f'{indent}        logger.error(f"Error fetching top gainers: {{e}}")\n')
            new_lines.append(f'{indent}else:\n')
            new_lines.append(f'{indent}    logger.warning("BirdeyeAPI not available - cannot fetch real tokens")\n')
            new_lines.append(f'{indent}\n')
            new_lines.append(f'{indent}return top_gainers\n')
            skip_lines = True
            continue
        
        if skip_lines:
            # Skip old method content
            if line.strip() and not line[method_indent].isspace() and i > 0:
                # Found next method or class
                skip_lines = False
                new_lines.append(line)
            continue
        else:
            new_lines.append(line)
    
    with open(file_path, 'w') as f:
        f.writelines(new_lines)
    
    print(f"✅ Fixed {file_path}")

def fix_bot_control():
    """Update bot_control.json to ensure proper settings"""
    file_path = "bot_control.json"
    if not os.path.exists(file_path):
        file_path = "data/bot_control.json"
    
    if not os.path.exists(file_path):
        print(f"Warning: Could not find {file_path}")
        return
    
    with open(file_path, 'r') as f:
        config = json.load(f)
    
    # Ensure BirdEye API is enabled
    config['use_birdeye_api'] = True
    
    # Save updated config
    with open(file_path, 'w') as f:
        json.dump(config, f, indent=4)
    
    print(f"✅ Updated {file_path} - enabled use_birdeye_api")

def update_run_bot():
    """Update run_bot_updated.py to initialize BirdeyeAPI"""
    file_path = "run_bot_updated.py"
    if not os.path.exists(file_path):
        print(f"Warning: Could not find {file_path}")
        return
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if BirdeyeAPI needs to be added
    if 'BirdeyeAPI' not in content:
        # Add import
        old_imports = """from core.database_adapter import DatabaseAdapter"""
        new_imports = """from core.database_adapter import DatabaseAdapter
    from core.birdeye import BirdeyeAPI"""
        
        content = content.replace(old_imports, new_imports)
        
        # Add initialization
        old_scanner = """# Create and initialize token scanner
    token_scanner = TokenScanner(db=db_adapter)"""
        
        new_scanner = """# Initialize BirdeyeAPI for real token data
    birdeye_api = BirdeyeAPI()
    logger.info("BirdeyeAPI initialized for real token data")
    
    # Create and initialize token scanner with BirdeyeAPI
    token_scanner = TokenScanner(db=db_adapter, birdeye_api=birdeye_api)"""
        
        content = content.replace(old_scanner, new_scanner)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated {file_path}")
    else:
        print(f"✅ {file_path} already has BirdeyeAPI")

def create_instructions():
    """Create instruction file"""
    instructions = [
        "# Instructions for Using Real Tokens in Simulation Mode\n\n",
        "## What was changed:\n",
        "1. token_scanner.py - Now fetches real tokens from BirdeyeAPI/DexScreener\n",
        "2. bot_control.json - Enabled use_birdeye_api\n",
        "3. run_bot_updated.py - Added BirdeyeAPI initialization\n\n",
        "## How to verify it's working:\n",
        "1. Run your bot in simulation mode\n",
        "2. Check logs for 'Found X real top gainer tokens'\n",
        "3. Look at trades - no more 'Sim*' addresses\n",
        "4. All tokens should have real Solana addresses\n\n",
        "## If you need to manually update token_analyzer.py:\n",
        "Find the fetch_token_data method and remove the section that creates fake data for simulation tokens.\n",
        "Always use self.birdeye_api.get_token_info() to get real data.\n"
    ]
    
    with open("REAL_TOKENS_INSTRUCTIONS.txt", 'w') as f:
        f.writelines(instructions)
    
    print("✅ Created REAL_TOKENS_INSTRUCTIONS.txt")

def main():
    print("🔧 Fixing Simulation Mode to Use Real Tokens")
    print("=" * 50)
    
    # Files to update
    files_to_update = [
        "token_scanner.py",
        "core/token_scanner.py",
        "bot_control.json",
        "data/bot_control.json",
        "run_bot_updated.py"
    ]
    
    # Create backup
    existing_files = [f for f in files_to_update if os.path.exists(f)]
    if existing_files:
        print(f"\n📁 Creating backup in {BACKUP_DIR}/")
        create_backup(existing_files)
    
    print("\n🛠️  Applying fixes...")
    
    # Apply fixes
    fix_token_scanner()
    fix_bot_control()
    update_run_bot()
    create_instructions()
    
    print("\n✅ Main fixes applied!")
    print("\n⚠️  IMPORTANT: You still need to manually update token_analyzer.py")
    print("In token_analyzer.py, find fetch_token_data() and remove the fake data generation.")
    print("The method should always use self.birdeye_api.get_token_info() for real data.")
    
    print(f"\n📋 Backup created in: {BACKUP_DIR}/")
    print("Read REAL_TOKENS_INSTRUCTIONS.txt for more details")

if __name__ == "__main__":
    main()