# dashboard_patch.py - Run this to create a patched version of your dashboard

import os
import sys
import re
from datetime import datetime

def create_patched_dashboard():
    """
    Create a patched version of the dashboard with timestamp fixes
    """
    # Input and output files
    input_file = "enhanced_dashboard.py"
    output_file = "enhanced_dashboard_patched.py"
    
    if not os.path.exists(input_file):
        print(f"❌ Input file {input_file} not found")
        return False
    
    # Create timestamp_fix.py file
    timestamp_fix_code = '''
# Timestamp fix module - Provides robust timestamp parsing
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
'''
    
    with open("timestamp_fix.py", "w", encoding="utf-8") as f:
        f.write(timestamp_fix_code)
    
    print("✅ Created timestamp_fix.py module with safe timestamp parsing")
    
    # Read the dashboard file with different encodings
    content = None
    for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
        try:
            with open(input_file, 'r', encoding=encoding) as f:
                content = f.read()
            print(f"✅ Read {input_file} using {encoding} encoding")
            break
        except UnicodeDecodeError:
            print(f"❌ Failed to read with {encoding} encoding")
    
    if content is None:
        print(f"❌ Could not read {input_file} with any encoding")
        return False
    
    # Add import for timestamp_fix module
    import_line = "from timestamp_fix import safe_parse_timestamp\n"
    
    # Check if import already exists
    if "from timestamp_fix import safe_parse_timestamp" not in content:
        # Find import section
        import_section_end = content.find("\n\n", content.find("import "))
        if import_section_end == -1:
            # Couldn't find clear end of import section, just add at top
            content = import_line + content
        else:
            # Add after import section
            content = content[:import_section_end] + "\n" + import_line + content[import_section_end:]
    
    # Replace timestamp parsing function calls
    # 1. Replace convert_to_et calls
    content = re.sub(r'\.apply\(convert_to_et\)', '.apply(safe_parse_timestamp)', content)
    
    # 2. Replace parse_timestamp calls
    content = re.sub(r'\.apply\(parse_timestamp\)', '.apply(safe_parse_timestamp)', content)
    
    # Write patched file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✅ Created patched dashboard at {output_file}")
    print("To use the patched version, run:")
    print(f"streamlit run {output_file}")
    
    return True

if __name__ == "__main__":
    print("Creating patched dashboard with timestamp fixes...")
    create_patched_dashboard()
