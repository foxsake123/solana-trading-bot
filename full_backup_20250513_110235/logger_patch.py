
# logger_patch.py - Ensure consistent logger access
import logging
import sys

# Create the logger
dashboard_logger = logging.getLogger('trading_bot.dashboard')

# Function to patch modules
def patch_module(module_name):
    if module_name in sys.modules:
        mod = sys.modules[module_name]
        if not hasattr(mod, 'logger'):
            mod.logger = dashboard_logger
            return True
    return False

# Patch common modules
modules_to_patch = [
    'simplified_dashboard',
    'token_scanner',
    'solana_trader',
    'trading_bot',
    'token_analyzer'
]

for module in modules_to_patch:
    patch_module(module)

# Export the logger for direct import
logger = dashboard_logger
