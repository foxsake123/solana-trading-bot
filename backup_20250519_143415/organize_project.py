# organize_project.py - Script to organize the Solana trading bot project directory

import os
import shutil
import re
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('organize_project')

# Define directory structure
DIRS = {
    'core': 'core',                   # Core application files
    'dashboard': 'dashboard',         # Dashboard-related files
    'backups': 'backups',             # Backup files
    'patches': 'patches',             # Patch files
    'tests': 'tests',                 # Test files
    'utils': 'utils',                 # Utility scripts
    'docs': 'docs',                   # Documentation
    'old': 'old_files',               # Old/deprecated files
    'temp': 'temp'                    # Temporary location
}

# Core files that should stay in the main directory
CORE_FILES = [
    'main.py',
    'database.py',
    'token_analyzer.py',
    'token_scanner.py',
    'solana_trader.py',
    'trading_bot.py',
    'config.py',
    'birdeye.py',
    'requirements.txt',
    'requirements_solana.txt',
    '.env',
    'bot_control.json',
    'README.md',
    'RUNNING INSTRUCTIONS',
    '.gitignore'
]

# File pattern categorization
FILE_PATTERNS = {
    r'^dashboard': 'dashboard',
    r'^backup_': 'backups',
    r'^patch': 'patches',
    r'^test_': 'tests',
    r'^fix_': 'utils',
    r'^generate_': 'utils',
    r'^convert_': 'utils',
    r'^validate_': 'utils',
    r'^simplified_': 'dashboard',
    r'^enhanced_': 'dashboard',
    r'^reset_': 'utils',
    r'^run_': 'utils',
    r'^install_': 'utils',
    r'^load_': 'utils',
    r'^timestamp': 'utils',
    r'^logger': 'utils',
    r'^logging': 'utils',
    r'^robust_': 'dashboard',
    r'^simple_': 'dashboard',
    r'^alternative_': 'utils',
    r'^combined_': 'patches'
}

# Directories to leave alone (don't move or categorize)
EXCLUDE_DIRS = [
    '__pycache__',
    'venv',
    'env',
    '.git',
    'data',
    'logs'
]

def create_directories():
    """Create the directory structure"""
    for dir_name in DIRS.values():
        os.makedirs(dir_name, exist_ok=True)
        logger.info(f"Created directory: {dir_name}")

def categorize_file(filename):
    """Categorize a file based on its name"""
    # Skip directories
    if os.path.isdir(filename) and not filename.endswith('.py'):
        return None
    
    # Core files stay in the main directory
    if filename in CORE_FILES:
        return 'core'
    
    # Check against patterns
    for pattern, category in FILE_PATTERNS.items():
        if re.match(pattern, filename):
            return category
    
    # Default: if it ends with .py, it's likely a core file, otherwise utils
    if filename.endswith('.py'):
        return 'core'
    
    return 'utils'

def backup_directory():
    """Create a backup of the entire directory"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f"full_backup_{timestamp}"
    
    logger.info(f"Creating full backup in {backup_dir}")
    os.makedirs(backup_dir, exist_ok=True)
    
    # Copy all files except the backup directory itself
    for item in os.listdir('.'):
        if item != backup_dir and item not in EXCLUDE_DIRS:
            if os.path.isdir(item):
                shutil.copytree(item, os.path.join(backup_dir, item), dirs_exist_ok=True)
            else:
                shutil.copy2(item, os.path.join(backup_dir, item))
    
    logger.info(f"Full backup created in {backup_dir}")
    return backup_dir

def move_files():
    """Organize files into appropriate directories"""
    # Track how many files moved to each category
    stats = {dir_type: 0 for dir_type in DIRS.keys()}
    
    # Get all files in current directory
    all_files = [f for f in os.listdir('.') if f not in EXCLUDE_DIRS and not f.startswith('organize_')]
    
    for filename in all_files:
        # Skip directories in the exclusion list
        if os.path.isdir(filename) and filename in EXCLUDE_DIRS:
            continue
        
        # Skip the script itself
        if filename == 'organize_project.py':
            continue
            
        # Categorize the file
        category = categorize_file(filename)
        
        if category is None:
            continue
        
        # Skip core files - they'll be copied but stay in place
        if category == 'core':
            # Copy to core directory
            dest = os.path.join(DIRS['core'], filename)
            try:
                if os.path.isdir(filename):
                    shutil.copytree(filename, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(filename, dest)
                logger.info(f"Copied {filename} to {dest}")
                stats[category] += 1
            except Exception as e:
                logger.error(f"Error copying {filename} to {dest}: {e}")
            continue
        
        # Move the file to its category directory
        dest = os.path.join(DIRS[category], filename)
        try:
            if os.path.exists(dest):
                # If destination exists, check if it's a directory
                if os.path.isdir(filename) and os.path.isdir(dest):
                    # Merge directories
                    for item in os.listdir(filename):
                        item_path = os.path.join(filename, item)
                        dest_item_path = os.path.join(dest, item)
                        if os.path.isdir(item_path):
                            shutil.copytree(item_path, dest_item_path, dirs_exist_ok=True)
                        else:
                            shutil.copy2(item_path, dest_item_path)
                    shutil.rmtree(filename)
                else:
                    # Rename destination to avoid conflicts
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    new_dest = f"{dest}_{timestamp}"
                    shutil.move(filename, new_dest)
            else:
                # Move the file
                shutil.move(filename, dest)
            
            logger.info(f"Moved {filename} to {DIRS[category]}")
            stats[category] += 1
            
        except Exception as e:
            logger.error(f"Error moving {filename} to {DIRS[category]}: {e}")
    
    return stats

def create_setup_script():
    """Create a script to set up the core environment with links to utilities"""
    setup_script = """#!/usr/bin/env python
# setup.py - Setup script for Solana trading bot environment

import os
import sys
import shutil
import subprocess

def create_symlinks():
    \"\"\"Create symlinks to utility scripts\"\"\"
    # Core directory
    core_dir = 'core'
    
    # Utility directories to link from
    util_dirs = ['utils', 'dashboard', 'patches']
    
    # Create links in core directory
    for util_dir in util_dirs:
        if not os.path.exists(util_dir):
            continue
            
        for file in os.listdir(util_dir):
            if file.endswith('.py'):
                # Source and destination paths
                src = os.path.abspath(os.path.join(util_dir, file))
                dst = os.path.abspath(os.path.join(core_dir, file))
                
                # Create symlink
                try:
                    if os.path.exists(dst):
                        os.remove(dst)
                    os.symlink(src, dst)
                    print(f"Created link to {src} in {dst}")
                except Exception as e:
                    print(f"Error creating link for {file}: {e}")

def setup_environment():
    \"\"\"Set up Python environment\"\"\"
    # Check if venv exists
    if not os.path.exists('venv'):
        print("Creating virtual environment...")
        try:
            subprocess.run([sys.executable, '-m', 'venv', 'venv'])
            print("Virtual environment created successfully")
        except Exception as e:
            print(f"Error creating virtual environment: {e}")
            return False
    
    # Activate virtual environment and install requirements
    if os.path.exists('venv'):
        if sys.platform == 'win32':
            pip_path = os.path.join('venv', 'Scripts', 'pip')
        else:
            pip_path = os.path.join('venv', 'bin', 'pip')
            
        # Install requirements if they exist
        req_files = ['requirements.txt', 'requirements_solana.txt']
        for req_file in req_files:
            if os.path.exists(req_file):
                print(f"Installing {req_file}...")
                try:
                    subprocess.run([pip_path, 'install', '-r', req_file])
                    print(f"Installed {req_file} successfully")
                except Exception as e:
                    print(f"Error installing {req_file}: {e}")
    
    return True

def main():
    \"\"\"Main setup function\"\"\"
    print("Setting up Solana trading bot environment...")
    
    # Set up Python environment
    setup_environment()
    
    # Create symlinks to utility scripts
    create_symlinks()
    
    print("Setup complete!")
    print("To run the bot, use: python core/main.py")
    print("To run the dashboard, use: streamlit run core/dashboard.py")

if __name__ == "__main__":
    main()
"""
    
    with open('setup.py', 'w') as f:
        f.write(setup_script)
    
    logger.info("Created setup.py script")

def create_readme():
    """Create a README.md file with project structure information"""
    readme = """# Solana Trading Bot

## Project Structure

This project has been organized into the following directory structure:

- `core/`: Core application files (main.py, database.py, etc.)
- `dashboard/`: Dashboard-related files
- `utils/`: Utility scripts and tools
- `patches/`: Patch files to fix issues
- `tests/`: Test files and scripts
- `backups/`: Backup files
- `docs/`: Documentation
- `old_files/`: Old/deprecated files

## Running the Bot

To run the bot:

```
python core/main.py
```

To run the dashboard:

```
streamlit run core/dashboard.py
```

## Setting Up the Environment

Run the setup script to set up the environment:

```
python setup.py
```

This will:
1. Create a virtual environment if needed
2. Install requirements
3. Create symlinks to utility scripts

## Diagnostics

If you encounter issues with the bot, you can run diagnostics:

```
python core/solana_diagnostic.py
```

## Solana Connection Test

To test your Solana connection:

```
python core/solana_connection_test.py
```
"""
    
    with open('README.md', 'w') as f:
        f.write(readme)
    
    logger.info("Created README.md")

def main():
    print("=" * 60)
    print("SOLANA TRADING BOT - PROJECT ORGANIZER")
    print("=" * 60)
    print()
    
    print("This script will organize your project files into a structured directory.")
    print("A full backup will be created before any changes are made.")
    print()
    
    # Create a full backup first
    backup_dir = backup_directory()
    print(f"Created backup in: {backup_dir}")
    print()
    
    # Create directory structure
    print("Creating directory structure...")
    create_directories()
    print()
    
    # Move files
    print("Organizing files...")
    stats = move_files()
    print()
    
    # Create setup script
    print("Creating setup script...")
    create_setup_script()
    print()
    
    # Create README
    print("Creating README...")
    create_readme()
    print()
    
    # Print stats
    print("=" * 60)
    print("ORGANIZATION COMPLETE!")
    print("=" * 60)
    print()
    print("Files organized:")
    for category, count in stats.items():
        if count > 0:
            print(f"  - {category}: {count} files")
    print()
    print("Next steps:")
    print("1. Run the diagnostics to check Solana connection:")
    print("   python core/solana_diagnostic.py")
    print()
    print("2. Test your Solana connection:")
    print("   python core/solana_connection_test.py")
    print()
    print("3. If needed, set up the environment:")
    print("   python setup.py")
    print()
    print("Your project is now organized!")
    print("=" * 60)

if __name__ == "__main__":
    main()
