"""
fix_structure.py - Fix directory and import structure for the Solana trading bot
"""
import os
import sys
import shutil
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('fix_structure')

def ensure_dir_exists(dir_path):
    """Ensure a directory exists, creating it if necessary"""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        logger.info(f"Created directory: {dir_path}")

def copy_file_if_exists(src, dest):
    """Copy a file if it exists"""
    if os.path.exists(src):
        # Create destination directory if needed
        dest_dir = os.path.dirname(dest)
        ensure_dir_exists(dest_dir)
        
        # Copy the file
        shutil.copy2(src, dest)
        logger.info(f"Copied {src} to {dest}")
        return True
    return False

def main():
    """Fix the structure of the project"""
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Create necessary directories
    core_dir = os.path.join(project_root, 'core')
    ensure_dir_exists(core_dir)
    
    data_dir = os.path.join(project_root, 'data')
    ensure_dir_exists(data_dir)
    
    logs_dir = os.path.join(project_root, 'logs')
    ensure_dir_exists(logs_dir)
    
    dashboard_dir = os.path.join(project_root, 'dashboard')
    ensure_dir_exists(dashboard_dir)
    
    utils_dir = os.path.join(project_root, 'utils')
    ensure_dir_exists(utils_dir)
    
    tests_dir = os.path.join(project_root, 'tests')
    ensure_dir_exists(tests_dir)
    
    # Create __init__.py files in each directory
    for dir_path in [core_dir, dashboard_dir, utils_dir, tests_dir]:
        init_file = os.path.join(dir_path, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write(f"# {os.path.basename(dir_path)} package\n")
            logger.info(f"Created {init_file}")
    
    # Copy core files to the core directory
    core_files = [
        'SoldersAdapter.py',
        'solders_adapter.py',
        'solana_trader.py',
        'SolanaTrader_adapter.py',
        'AsyncSolanaTrader_adapter.py',
        'TradingBot_adapter.py',
        'database.py',
        'token_scanner.py',
        'token_analyzer.py',
        'birdeye.py',
        'utils.py',
        'config.py',
        'trading_bot.py',
        'ml_model.py',
    ]
    
    for file in core_files:
        src = os.path.join(project_root, file)
        dest = os.path.join(core_dir, file)
        copy_file_if_exists(src, dest)
    
    # Copy dashboard files to the dashboard directory
    dashboard_files = [
        'new_dashboard.py',
        'advanced_dashboard.py',
        'simple_status.py',
        'status_monitor.py',
    ]
    
    for file in dashboard_files:
        src = os.path.join(project_root, file)
        dest = os.path.join(dashboard_dir, file)
        copy_file_if_exists(src, dest)
    
    # Copy test files to the tests directory
    test_files = [
        'test_real_trading.py',
        'check_trades.py',
        'check_real_trades.py',
        'wallet_test.py',
        'solana_connection_test.py',
        'test_solana.py',
        'test_solders.py',
    ]
    
    for file in test_files:
        src = os.path.join(project_root, file)
        dest = os.path.join(tests_dir, file)
        copy_file_if_exists(src, dest)
    
    # Copy bot_control.json to data directory if it exists
    src = os.path.join(project_root, 'bot_control.json')
    dest = os.path.join(data_dir, 'bot_control.json')
    if copy_file_if_exists(src, dest):
        logger.info("Copied bot_control.json to data directory")
    
    # Create a symlink to bot_control.json in the root directory
    if os.path.exists(dest) and not os.path.exists(src):
        try:
            os.symlink(dest, src)
            logger.info("Created symlink to bot_control.json in root directory")
        except Exception as e:
            # On Windows, symlinks might not work without admin privileges
            logger.warning(f"Could not create symlink: {e}")
            # Just copy the file instead
            shutil.copy2(dest, src)
            logger.info("Copied bot_control.json to root directory")
    
    logger.info("File structure fixed. You can now run these scripts directly from the root directory.")

if __name__ == "__main__":
    main()
