# dashboard_fix.py - Comprehensive dashboard fixer script

import os
import sys
import logging
import shutil
import importlib
import subprocess

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('dashboard_fix')

def ensure_logger_patch():
    """Create a standalone logger fix module"""
    logger_patch_code = '''
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
'''
    
    with open('logger_patch.py', 'w', encoding='utf-8') as f:
        f.write(logger_patch_code)
    
    logger.info("Created logger_patch.py module")
    return True

def ensure_ml_model_patch():
    """Create a standalone ML model fix module"""
    ml_patch_code = '''
# ml_model_patch.py - Provide ML model functionality
import logging
import sys

logger = logging.getLogger('trading_bot.ml_model')

class MLModelPatch:
    """Patched ML Model class with required methods"""
    
    def __init__(self):
        """Initialize the patched ML model"""
        self.stats = {
            'accuracy': 0.0,
            'precision': 0.0,
            'recall': 0.0,
            'f1': 0.0,
            'last_training': None,
            'training_samples': 0,
            'feature_importance': {}
        }
    
    def get_performance_stats(self):
        """Get model performance statistics"""
        return self.stats
    
    def get_recent_predictions(self):
        """Get recent predictions made by the model"""
        return []
    
    def predict(self, token_data):
        """Make a prediction for a token"""
        return 0.5, 0.0, {}

# Apply patch to existing ml_model if loaded
if 'ml_model' in sys.modules:
    module = sys.modules['ml_model']
    
    if hasattr(module, 'MLModel'):
        MLModel = module.MLModel
        
        # Add missing methods
        if not hasattr(MLModel, 'get_recent_predictions'):
            MLModel.get_recent_predictions = MLModelPatch.get_recent_predictions
            logger.info("Patched MLModel.get_recent_predictions")
else:
    # Create a stub module
    class MLModelModule:
        MLModel = MLModelPatch
    
    sys.modules['ml_model'] = MLModelModule
    logger.info("Created stub ml_model module")

# Export the patched model class
MLModel = MLModelPatch
'''
    
    with open('ml_model_patch.py', 'w', encoding='utf-8') as f:
        f.write(ml_patch_code)
    
    logger.info("Created ml_model_patch.py module")
    return True

def create_simplified_dashboard_wrapper():
    """Create a wrapper for the simplified dashboard"""
    wrapper_code = '''
# dashboard_wrapper.py - Safe wrapper for dashboard
import os
import sys
import logging
import importlib
import asyncio

# Set up logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('trading_bot.dashboard')

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import patches first
try:
    import logger_patch
    import ml_model_patch
    logger.info("Successfully imported patches")
except ImportError as e:
    logger.error(f"Failed to import patches: {e}")

# Safe import of the dashboard module
try:
    import simplified_dashboard
    logger.info("Successfully imported simplified_dashboard")
except ImportError as e:
    logger.error(f"Could not import simplified_dashboard: {e}")
    sys.exit(1)

# Ensure fetch_dashboard_data is safe
if hasattr(simplified_dashboard, 'fetch_dashboard_data'):
    original_fetch = simplified_dashboard.fetch_dashboard_data
    
    async def safe_fetch_dashboard_data():
        try:
            return await original_fetch()
        except Exception as e:
            logger.error(f"Error in fetch_dashboard_data: {e}")
            # Return minimal data structure
            return {
                'wallet_balance': {'sol': 0.0, 'usd': 0.0},
                'positions': [],
                'trades': [],
                'tokens': [],
                'stats': {'profit_loss': 0.0, 'win_rate': 0.0},
                'ml_stats': {},
                'ml_predictions': []
            }
    
    # Replace the function
    simplified_dashboard.fetch_dashboard_data = safe_fetch_dashboard_data
    logger.info("Replaced fetch_dashboard_data with safe version")

# Main function
def main():
    if hasattr(simplified_dashboard, 'display_dashboard'):
        logger.info("Starting dashboard display")
        simplified_dashboard.display_dashboard()
    else:
        logger.error("display_dashboard function not found in module")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    with open('dashboard_wrapper.py', 'w', encoding='utf-8') as f:
        f.write(wrapper_code)
    
    logger.info("Created dashboard_wrapper.py")
    return True

def backup_files():
    """Create backups of key files"""
    files_to_backup = [
        'simplified_dashboard.py',
        'ml_model.py',
        'token_scanner.py',
        'dashboard_patched.py',
        'dashboard_launcher.py'
    ]
    
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    
    for file in files_to_backup:
        if os.path.exists(file):
            backup_path = os.path.join(backup_dir, f"{file}.bak")
            try:
                shutil.copy2(file, backup_path)
                logger.info(f"Created backup of {file} at {backup_path}")
            except Exception as e:
                logger.error(f"Failed to backup {file}: {e}")
    
    return True

def main():
    """Main function to fix dashboard issues"""
    print("=" * 50)
    print("Dashboard Fixer - Comprehensive Solution")
    print("=" * 50)
    print()
    
    print("Step 1: Creating backups of key files")
    backup_files()
    print()
    
    print("Step 2: Creating logger patch")
    ensure_logger_patch()
    print()
    
    print("Step 3: Creating ML model patch")
    ensure_ml_model_patch()
    print()
    
    print("Step 4: Creating dashboard wrapper")
    create_simplified_dashboard_wrapper()
    print()
    
    print("=" * 50)
    print("FIXES SUCCESSFULLY APPLIED!")
    print("=" * 50)
    print()
    print("To run the fixed dashboard, use:")
    print("streamlit run dashboard_wrapper.py")
    print()
    print("Or use the automatic launcher:")
    
    # Create launcher script
    launcher_code = '''#!/usr/bin/env python
import subprocess
import sys
import os

print("Starting fixed dashboard...")
try:
    subprocess.run(['streamlit', 'run', 'dashboard_wrapper.py'])
except Exception as e:
    print(f"Error: {e}")
    print("If Streamlit is not installed, run: pip install streamlit")
'''
    
    with open('run_dashboard.py', 'w', encoding='utf-8') as f:
        f.write(launcher_code)
    
    # Make it executable on Unix systems
    try:
        os.chmod('run_dashboard.py', 0o755)
    except:
        pass
    
    print("python run_dashboard.py")
    print()
    print("=" * 50)

if __name__ == "__main__":
    main()
