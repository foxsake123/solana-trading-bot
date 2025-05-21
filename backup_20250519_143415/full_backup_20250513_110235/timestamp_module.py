
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
