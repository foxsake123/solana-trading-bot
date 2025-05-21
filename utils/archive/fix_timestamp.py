# timestamp_fix.py - Import this in your dashboard to fix timestamp parsing issues

from datetime import datetime, timezone, timedelta
import pytz
import logging

# Set up Eastern Time zone
ET = pytz.timezone('US/Eastern')

def safe_parse_timestamp(timestamp_str):
    """
    Parse timestamp string to datetime object - safely
    """
    logger = logging.getLogger('trading_bot')
    
    try:
        # If already a datetime, return it
        if isinstance(timestamp_str, datetime):
            return timestamp_str.astimezone(ET) if timestamp_str.tzinfo else ET.localize(timestamp_str)
            
        # Handle None
        if timestamp_str is None:
            return datetime.now(ET)
        
        # Handle ET format strings specifically
        if isinstance(timestamp_str, str) and ' ET' in timestamp_str:
            # Extract the date part
            date_str = timestamp_str.replace(' ET', '')
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
                logger.warning(f"Could not parse ET timestamp: {timestamp_str}")
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
                dt = datetime.strptime(timestamp_str, fmt)
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
            clean_str = timestamp_str.replace('Z', '').replace('T', ' ')
            parts = clean_str.split(' ')[0].split('-')
            if len(parts) >= 3:
                # At least have a date portion
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                dt = datetime(year, month, day, tzinfo=timezone.utc)
                return dt.astimezone(ET)
        except:
            pass
            
        # Complete fallback
        logger.warning(f"Failed to parse timestamp with all methods: {timestamp_str}")
        return datetime.now(ET)
    except Exception as e:
        logger.error(f"Error in safe_parse_timestamp: {str(e)}")
        return datetime.now(ET)

def fix_dashboard():
    """
    Apply the timestamp fix to the dashboard - run this function at startup
    """
    import sys
    import types
    
    # Check if dashboard module is loaded
    if "enhanced_dashboard" in sys.modules:
        dashboard = sys.modules["enhanced_dashboard"]
        
        # Replace the convert_to_et function
        if hasattr(dashboard, "convert_to_et"):
            dashboard.convert_to_et = safe_parse_timestamp
            print("✅ Replaced convert_to_et function with safe_parse_timestamp")
        
        # Replace the parse_timestamp function
        if hasattr(dashboard, "parse_timestamp"):
            dashboard.parse_timestamp = safe_parse_timestamp
            print("✅ Replaced parse_timestamp function with safe_parse_timestamp")
            
        return True
    else:
        print("❌ enhanced_dashboard module not found")
        return False

# Instructions to use this fix:
# 1. Save this file as timestamp_fix.py in the same directory as your dashboard
# 2. Add the following two lines to the top of your enhanced_dashboard.py file:
#
#    from timestamp_fix import safe_parse_timestamp
#    import timestamp_fix; timestamp_fix.fix_dashboard()
#
# 3. Restart your dashboard
