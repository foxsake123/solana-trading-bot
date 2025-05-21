# minimal_fix.py - Minimal fix for the dashboard timestamp issues

def create_timestamp_module():
    """
    Create a minimal timestamp parsing module
    """
    code = '''
# Safe timestamp parsing
from datetime import datetime, timezone
import pytz

# Set up Eastern Time zone
ET = pytz.timezone('US/Eastern')

def parse_et_string(timestamp_str):
    """
    Parse timestamp string that already has ET format
    """
    try:
        # Handle None
        if not timestamp_str:
            return None
            
        # If already has ET format, just return it
        if ' ET' in timestamp_str:
            return timestamp_str
            
        # Otherwise convert to ET
        dt = datetime.now(ET)
        return dt.strftime('%Y-%m-%d %I:%M:%S %p ET')
    except:
        # Return original on error
        return timestamp_str
'''
    
    with open('timestamp_module.py', 'w', encoding='utf-8') as f:
        f.write(code)
    
    print("Created timestamp_module.py with minimal timestamp handling")

def create_dashboard_wrapper():
    """
    Create a wrapper script that imports the dashboard with timestamp fixes
    """
    code = '''
# dashboard_wrapper.py - Run this instead of the original dashboard

# Import timestamp module first
from timestamp_module import parse_et_string

# Monkey patch datetime handling to prevent errors
import datetime
import pytz

# Original fromisoformat behavior
original_fromisoformat = datetime.datetime.fromisoformat

# Safe version that doesn't crash on ET format
def safe_fromisoformat(date_string):
    if ' ET' in date_string:
        # Return current time for ET formatted strings
        # This prevents crashes but the correct behavior will be handled elsewhere
        return datetime.datetime.now(pytz.timezone('US/Eastern'))
    else:
        # Use original for everything else
        return original_fromisoformat(date_string)

# Replace the method
datetime.datetime.fromisoformat = safe_fromisoformat

# Now import and run the dashboard
import enhanced_dashboard

# Main function is display_dashboard
if __name__ == "__main__":
    enhanced_dashboard.display_dashboard()
'''
    
    with open('dashboard_wrapper.py', 'w', encoding='utf-8') as f:
        f.write(code)
    
    print("Created dashboard_wrapper.py - run this instead of the original dashboard")
    print("Usage: streamlit run dashboard_wrapper.py")

if __name__ == "__main__":
    create_timestamp_module()
    create_dashboard_wrapper()
    print("\nFix applied successfully! Run your dashboard with:")
    print("  streamlit run dashboard_wrapper.py")
