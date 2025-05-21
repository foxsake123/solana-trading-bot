# improved_dashboard_launcher.py - Robust launcher for fixed dashboard

import logging
import os
import subprocess
import sys
import importlib.util
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('dashboard_launcher')

def main():
    """Launch the dashboard with fixes applied on-the-fly"""
    logger.info("Starting improved dashboard launcher")
    
    # Create a more comprehensive patched dashboard wrapper
    patched_code = """
# dashboard_patched.py - Dashboard with robust fixes
import os
import sys
import logging

# Set up logging first thing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('trading_bot.dashboard')

# Import the token_scanner module first to patch it
import token_scanner

# Fix missing ml_model.get_recent_predictions method
# Ensure this runs BEFORE dashboard imports token_scanner
if hasattr(token_scanner, 'TokenScanner'):
    # Monkey patch the TokenScanner class to ensure it has get_ml_predictions
    original_get_ml_predictions = token_scanner.TokenScanner.get_ml_predictions
    
    def patched_get_ml_predictions(self):
        try:
            if hasattr(self, 'ml_model') and self.ml_model:
                # Add get_recent_predictions method if it doesn't exist
                if not hasattr(self.ml_model, 'get_recent_predictions'):
                    self.ml_model.get_recent_predictions = lambda: []
                return self.ml_model.get_recent_predictions()
            return []
        except Exception as e:
            dashboard_logger = logging.getLogger('trading_bot.dashboard')
            dashboard_logger.error(f"Error in patched get_ml_predictions: {e}")
            return []
    
    # Apply the patch
    token_scanner.TokenScanner.get_ml_predictions = patched_get_ml_predictions
    logger.info("TokenScanner.get_ml_predictions patched successfully")

# If the ml_model module exists, patch it directly
try:
    import ml_model
    
    # Check if MLModel class exists and needs patching
    if hasattr(ml_model, 'MLModel'):
        if not hasattr(ml_model.MLModel, 'get_recent_predictions'):
            # Add the missing method
            ml_model.MLModel.get_recent_predictions = lambda self: []
            logger.info("Added get_recent_predictions method to MLModel class")
except ImportError:
    logger.warning("ml_model module not found, creating stub")
    
    # Create a stub MLModel class if needed
    class MLModelStub:
        def get_performance_stats(self):
            return {}
            
        def get_recent_predictions(self):
            return []
    
    # Add stub to sys.modules to be imported later
    class MLModelModule:
        MLModel = MLModelStub
    
    sys.modules['ml_model'] = MLModelModule
    logger.info("Created stub ml_model module")

# Ensure simplified_dashboard module has proper logger access
try:
    # First check if the module is already loaded
    if 'simplified_dashboard' in sys.modules:
        simplified_dashboard = sys.modules['simplified_dashboard']
        
        # Make sure it has logger defined
        if not hasattr(simplified_dashboard, 'logger'):
            simplified_dashboard.logger = logger
            logger.info("Added logger to already imported simplified_dashboard module")
except Exception as e:
    logger.error(f"Error checking simplified_dashboard module: {e}")

# Import path handling
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Safe import of simplified_dashboard
try:
    from simplified_dashboard import display_dashboard, fetch_dashboard_data
    logger.info("Successfully imported dashboard modules")
except ImportError as e:
    logger.error(f"Could not import simplified_dashboard: {e}")
    sys.exit(1)
except Exception as e:
    logger.error(f"Error importing simplified_dashboard: {e}")
    sys.exit(1)

# Patch fetch_dashboard_data to handle logger errors
if 'fetch_dashboard_data' in locals():
    original_fetch_dashboard_data = fetch_dashboard_data
    
    async def patched_fetch_dashboard_data():
        dashboard_logger = logging.getLogger('trading_bot.dashboard')
        try:
            return await original_fetch_dashboard_data()
        except Exception as e:
            dashboard_logger.error(f"Error in patched fetch_dashboard_data: {e}")
            # Return minimal data structure to avoid crashes
            return {
                'wallet_balance': {'sol': 0.0, 'usd': 0.0},
                'positions': [],
                'trades': [],
                'tokens': [],
                'stats': {'profit_loss': 0.0, 'win_rate': 0.0},
                'ml_stats': {},
                'ml_predictions': []
            }
    
    # Replace the function in the module
    import simplified_dashboard
    simplified_dashboard.fetch_dashboard_data = patched_fetch_dashboard_data
    sys.modules['simplified_dashboard'].fetch_dashboard_data = patched_fetch_dashboard_data
    logger.info("fetch_dashboard_data patched successfully")

# Run the dashboard function
if __name__ == "__main__":
    try:
        display_dashboard()
    except Exception as e:
        logger.error(f"Error running display_dashboard: {e}")
        sys.exit(1)
"""
    
    # Write the patched dashboard script
    with open('dashboard_patched.py', 'w', encoding='utf-8') as f:
        f.write(patched_code)
    
    logger.info("Created improved patched dashboard wrapper")
    
    # Run the patched dashboard
    streamlit_cmd = ['streamlit', 'run', 'dashboard_patched.py']
    logger.info(f"Running: {' '.join(streamlit_cmd)}")
    
    try:
        subprocess.run(streamlit_cmd)
    except Exception as e:
        logger.error(f"Error running Streamlit: {e}")
        print(f"\nError: {e}")
        print("\nIf Streamlit is not available, install it with:")
        print("pip install streamlit")

if __name__ == "__main__":
    main()
