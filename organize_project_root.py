# organize_project_root.py - Create this file in your root directory
import os
import shutil
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('organize_project_root')

# Get the project root directory
project_root = os.path.dirname(os.path.abspath(__file__))

# Create necessary directories at the project root level
directories = ['core', 'data', 'dashboard', 'utils', 'tests', 'logs']
for directory in directories:
    dir_path = os.path.join(project_root, directory)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        logger.info(f"Created directory: {dir_path}")

# Create __init__.py files in each directory
for directory in directories:
    init_file = os.path.join(project_root, directory, '__init__.py')
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write(f"# {directory} package\n")
        logger.info(f"Created {init_file}")

# Move any nested folders back to the root
nested_utils = os.path.join(project_root, 'utils', 'utils')
if os.path.exists(nested_utils):
    # Move the contents back up
    for item in os.listdir(nested_utils):
        src = os.path.join(nested_utils, item)
        dest = os.path.join(project_root, 'utils', item)
        if os.path.isfile(src):
            shutil.copy2(src, dest)
            logger.info(f"Moved {item} to correct utils directory")

nested_core = os.path.join(project_root, 'utils', 'core')
if os.path.exists(nested_core):
    # Move the contents to actual core directory
    for item in os.listdir(nested_core):
        src = os.path.join(nested_core, item)
        dest = os.path.join(project_root, 'core', item)
        if os.path.isfile(src):
            shutil.copy2(src, dest)
            logger.info(f"Moved {item} to correct core directory")

nested_tests = os.path.join(project_root, 'utils', 'tests')
if os.path.exists(nested_tests):
    # Move the contents to actual tests directory
    for item in os.listdir(nested_tests):
        src = os.path.join(nested_tests, item)
        dest = os.path.join(project_root, 'tests', item)
        if os.path.isfile(src):
            shutil.copy2(src, dest)
            logger.info(f"Moved {item} to correct tests directory")

# Check for our prepared files and move them accordingly
def move_file_if_exists(src_file, dest_dir, new_name=None):
    src_path = os.path.join(project_root, src_file)
    if os.path.exists(src_path):
        dest_name = new_name if new_name else os.path.basename(src_file)
        dest_path = os.path.join(project_root, dest_dir, dest_name)
        shutil.copy2(src_path, dest_path)
        logger.info(f"Copied {src_file} to {dest_dir}/{dest_name}")
        return True
    return False

# Core files
move_file_if_exists('SoldersAdapter.py', 'core')
move_file_if_exists('solders_adapter.py', 'core')
move_file_if_exists('solana_trader.py', 'core')
move_file_if_exists('database.py', 'core')
move_file_if_exists('birdeye.py', 'core')
move_file_if_exists('token_scanner.py', 'core')
move_file_if_exists('token_analyzer.py', 'core')
move_file_if_exists('trading_bot.py', 'core')
move_file_if_exists('config.py', 'core')
move_file_if_exists('utils.py', 'core')
move_file_if_exists('ml_model.py', 'core')

# Utils files
move_file_if_exists('fix_jupiter.py', 'utils')
move_file_if_exists('fix_structure.py', 'utils')
move_file_if_exists('setup_real_trading.py', 'utils')

# Tests files
move_file_if_exists('test_real_trading.py', 'tests')
move_file_if_exists('check_trades.py', 'tests')
move_file_if_exists('solana_connection_test.py', 'tests')
move_file_if_exists('test_solana.py', 'tests')
move_file_if_exists('test_solders.py', 'tests')

# Dashboard files
move_file_if_exists('new_dashboard.py', 'dashboard')
move_file_if_exists('simple_status.py', 'dashboard')
move_file_if_exists('status_monitor.py', 'dashboard')

# Data files
move_file_if_exists('bot_control.json', 'data')

# Create symlinks or copies for bot_control.json
bot_control_data = os.path.join(project_root, 'data', 'bot_control.json')
bot_control_root = os.path.join(project_root, 'bot_control.json')
if os.path.exists(bot_control_data) and not os.path.exists(bot_control_root):
    try:
        # Try to create a symlink
        os.symlink(bot_control_data, bot_control_root)
        logger.info("Created symlink to bot_control.json in root directory")
    except:
        # If symlink fails, just copy the file
        shutil.copy2(bot_control_data, bot_control_root)
        logger.info("Copied bot_control.json to root directory")

logger.info("Project structure fixed!")