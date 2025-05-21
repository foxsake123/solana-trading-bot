
# dashboard_patched.py - Dashboard with on-the-fly fixes
import os
import sys
import logging

# Set up logging first thing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('trading_bot.dashboard')

# Import the original dashboard
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Apply ML model patches

# Create a simple patch for ML model
try:
    class MLModelPatch:
        def get_performance_stats(self):
            return {}
            
        def get_recent_predictions(self):
            return []
    
    # Apply patch to scanner
    if hasattr(scanner, 'ml_model') and scanner.ml_model:
        if not hasattr(scanner.ml_model, 'get_recent_predictions'):
            scanner.ml_model.get_recent_predictions = lambda: []
except:
    pass


# Apply logger fixes

# Fix logger access
import logging
dashboard_logger = logging.getLogger('trading_bot.dashboard')

# Replace logger with dashboard_logger
try:
    logger = dashboard_logger
except:
    pass


# Now import and run the dashboard
from simplified_dashboard import display_dashboard

# Run the dashboard
if __name__ == "__main__":
    display_dashboard()
