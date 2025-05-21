# complete_dashboard_fix.py - Full fix for enhanced_dashboard.py

import os
import logging
import shutil

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('dashboard_fix')

def fix_enhanced_dashboard():
    """Fix the enhanced_dashboard.py file completely"""
    # Find the dashboard file
    dashboard_file = os.path.join('dashboard', 'enhanced_dashboard.py')
    if not os.path.exists(dashboard_file):
        logger.error(f"Could not find {dashboard_file}")
        return False
    
    # Create a backup
    backup_file = f"{dashboard_file}.bak"
    if not os.path.exists(backup_file):
        try:
            shutil.copy2(dashboard_file, backup_file)
            logger.info(f"Created backup at {backup_file}")
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return False
    
    # Fixed version of get_sol_price function (remove await)
    fixed_get_sol_price = """def get_sol_price(trader):
    \"\"\"
    Get SOL price with caching to avoid rate limiting
    \"\"\"
    current_time = time.time()
    
    # Check if cache is valid
    if SOL_PRICE_CACHE['price'] > 0 and current_time - SOL_PRICE_CACHE['timestamp'] < SOL_PRICE_CACHE['ttl']:
        return SOL_PRICE_CACHE['price']
    
    # Cache expired or not set, get new price
    try:
        # Try to use alternative price source first to avoid CoinGecko rate limiting
        # Note: Removed await since this is not an async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        price = loop.run_until_complete(trader.get_sol_price())
        loop.close()
        
        # Update cache
        SOL_PRICE_CACHE['price'] = price
        SOL_PRICE_CACHE['timestamp'] = current_time
        
        return price
    except Exception as e:
        logger.error(f"Error getting SOL price: {e}")
        
        # If cache exists but is expired, return the old price rather than 0
        if SOL_PRICE_CACHE['price'] > 0:
            return SOL_PRICE_CACHE['price']
        
        # Fallback price if all else fails
        return 145.0  # Default SOL price as fallback
"""

    # Fixed version of parse_timestamp function (complete implementation)
    fixed_parse_timestamp = """        def parse_timestamp(ts_str):
            \"\"\"
            Parse timestamp string to datetime object - safely
            \"\"\"
            from datetime import datetime, timezone
            import pytz
            from logging import getLogger
            logger = getLogger('trading_bot')
            ET = pytz.timezone('US/Eastern')
            
            try:
                # If already a datetime, return it
                if isinstance(ts_str, datetime):
                    return ts_str.astimezone(ET) if ts_str.tzinfo else ET.localize(ts_str)
                    
                # Handle None
                if ts_str is None:
                    return datetime.now(ET)
                
                # Handle ET format strings specifically
                if isinstance(ts_str, str) and ' ET' in ts_str:
                    # Extract the date part
                    date_str = ts_str.replace(' ET', '')
                    try:
                        if 'AM' in date_str or 'PM' in date_str:
                            # 12-hour format
                            dt = datetime.strptime(date_str, '%Y-%m-%d %I:%M:%S %p')
                        else:
                            # 24-hour format
                            dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                        return ET.localize(dt)
                    except ValueError:
                        # Log but don't crash
                        logger.warning(f"Could not parse ET timestamp: {ts_str}")
                        return datetime.now(ET)
                
                # Try multiple formats
                formats = [
                    '%Y-%m-%dT%H:%M:%S.%fZ',
                    '%Y-%m-%dT%H:%M:%SZ',
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d %I:%M:%S %p',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%d',
                    '%m/%d/%Y %H:%M:%S',
                    '%m/%d/%Y'
                ]
                
                # Try each format
                for fmt in formats:
                    try:
                        dt = datetime.strptime(ts_str, fmt)
                        if fmt.endswith('Z'):
                            # Handle UTC timezone
                            dt = dt.replace(tzinfo=timezone.utc)
                        elif dt.tzinfo is None:
                            # Assume UTC for naive datetime
                            dt = dt.replace(tzinfo=timezone.utc)
                        # Convert to ET
                        return dt.astimezone(ET)
                    except ValueError:
                        continue
                
                # If all formats fail, try a last-resort approach
                try:
                    # Clean string and try split approach
                    clean_str = ts_str.replace('Z', '').replace('T', ' ')
                    parts = clean_str.split(' ')[0].split('-')
                    if len(parts) >= 3:
                        # At least have a date portion
                        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                        dt = datetime(year, month, day, tzinfo=timezone.utc)
                        return dt.astimezone(ET)
                except:
                    pass
                    
                # Complete fallback
                logger.warning(f"Failed to parse timestamp with all methods: {ts_str}")
                return datetime.now(ET)
            except Exception as e:
                logger.error(f"Error in parse_timestamp: {str(e)}")
                return datetime.now(ET)
"""

    # Fix for convert_to_et function that might be missing
    convert_to_et_function = """
def convert_to_et(timestamp_str):
    \"\"\"Convert timestamp to Eastern Time format\"\"\"
    return safe_parse_timestamp(timestamp_str)
"""

    # Read the current content
    try:
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Error reading dashboard file: {e}")
        return False
    
    # Apply fixes
    
    # 1. Replace get_sol_price function
    old_get_sol_price = content.find("def get_sol_price(trader):")
    if old_get_sol_price >= 0:
        # Find the end of the function
        next_def = content.find("def ", old_get_sol_price + 1)
        if next_def >= 0:
            # Replace the function
            content = content[:old_get_sol_price] + fixed_get_sol_price + content[next_def:]
            logger.info("Fixed get_sol_price function")
    
    # 2. Add convert_to_et function if not present
    if "def convert_to_et(" not in content:
        # Find a good spot to add it - after safe_parse_timestamp
        safe_parse_end = content.find("def safe_parse_timestamp(")
        if safe_parse_end >= 0:
            # Find the end of safe_parse_timestamp function
            next_def_after_safe = content.find("def ", safe_parse_end + 1)
            if next_def_after_safe >= 0:
                # Add convert_to_et function after safe_parse_timestamp
                content = content[:next_def_after_safe] + convert_to_et_function + content[next_def_after_safe:]
                logger.info("Added convert_to_et function")
    
    # 3. Fix the incomplete parse_timestamp function
    # First, find where it's defined
    parse_timestamp_pos = content.rfind("def parse_timestamp(")
    if parse_timestamp_pos >= 0:
        # Check if it's incomplete (if it's at the end of the file)
        if content.find("def ", parse_timestamp_pos + 1) == -1:
            # It's the last function and might be incomplete
            # Replace it with the complete implementation
            content = content[:parse_timestamp_pos] + fixed_parse_timestamp
            logger.info("Fixed incomplete parse_timestamp function")
    
    # Write the fixed content
    try:
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Successfully fixed {dashboard_file}")
        return True
    except Exception as e:
        logger.error(f"Error writing fixed dashboard: {e}")
        return False

def main():
    print("=" * 60)
    print("ENHANCED DASHBOARD COMPLETE FIX")
    print("=" * 60)
    print()
    
    success = fix_enhanced_dashboard()
    
    if success:
        print("Successfully fixed the enhanced dashboard!")
        print()
        print("You can now run:")
        print("streamlit run dashboard/enhanced_dashboard.py")
    else:
        print("Failed to fix the dashboard.")
        print("Please check the logs for more information.")
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    main()
