import os

def fix_indentation(filename):
    # Check if file exists
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        print(f"Current working directory: {os.getcwd()}")
        
        # Try to find the file in the current directory
        if os.path.exists(os.path.basename(filename)):
            filename = os.path.basename(filename)
            print(f"Found file as: {filename}")
        else:
            print("Available files in current directory:")
            print(os.listdir('.'))
            return False
    
    print(f"Processing file: {filename}")
    
    with open(filename, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    # Process lines to standardize indentation
    fixed_lines = []
    for line in lines:
        # Replace tabs with spaces (4 spaces per tab)
        line = line.replace('\t', '    ')
        fixed_lines.append(line)
    
    # Create backup
    backup_file = filename + '.bak'
    with open(backup_file, 'w', encoding='utf-8') as file:
        file.writelines(lines)
    print(f"Created backup at: {backup_file}")
    
    # Write fixed content
    with open(filename, 'w', encoding='utf-8') as file:
        file.writelines(fixed_lines)
    print(f"Fixed indentation in: {filename}")
    return True

# Since you're in the 'core' directory, but the path might be different
# Try different possible paths:
paths_to_try = [
    'enhanced_dashboard.py',              # If file is in current directory
    './enhanced_dashboard.py',            # Explicit current directory
    '../core/enhanced_dashboard.py',      # From parent directory
    'C:/Users/shorg/sol-bot_claude/core/enhanced_dashboard.py'  # Absolute path
]

fixed = False
for path in paths_to_try:
    if fix_indentation(path):
        fixed = True
        break

if not fixed:
    print("Could not find the file to fix. Please check the path.")