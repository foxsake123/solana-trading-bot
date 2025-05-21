
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
