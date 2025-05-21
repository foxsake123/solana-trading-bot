# Create this as cleanup.py
import os
import shutil
import datetime

# Create timestamp for backup
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir = f'backup_{timestamp}'

print(f"Creating backup directory: {backup_dir}")
if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)

# Define essential files to keep
essential_files = [
    'main.py',
    'solana_trader.py',
    'solders_adapter.py',
    'token_scanner.py',
    'token_analyzer.py',
    'database.py',
    'config.py',
    'utils.py',
    'bot_control.json',
    '.env'
]

# Copy important files to backup
print("Backing up important files...")
for root, dirs, files in os.walk('.'):
    # Skip the backup directory, virtual environments and git
    if backup_dir in root or 'venv' in root or '.git' in root:
        continue
        
    for file in files:
        # Skip __pycache__ and other unwanted files
        if '__pycache__' in root or file.endswith('.pyc'):
            continue
            
        # Backup Python files and important config files
        if file.endswith('.py') or file in ['bot_control.json', '.env']:
            source_path = os.path.join(root, file)
            
            # Create the directory structure in backup
            rel_dir = os.path.dirname(os.path.relpath(source_path))
            if rel_dir:
                os.makedirs(os.path.join(backup_dir, rel_dir), exist_ok=True)
            
            # Copy the file
            dest_path = os.path.join(backup_dir, os.path.relpath(source_path))
            shutil.copy2(source_path, dest_path)
            print(f"Backed up: {source_path}")

# Create simplified directory structure
print("\nCreating simplified directory structure...")
required_dirs = ['core', 'data', 'utils']
for dir_name in required_dirs:
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
        print(f"Created directory: {dir_name}")

# Move core files to their simplified locations
print("\nCleaning up adapter files and organizing directories...")
for file in os.listdir('.'):
    if file.endswith('_adapter.py') and file not in essential_files:
        # Move adapter files to utils directory
        if os.path.isfile(file):
            shutil.move(file, os.path.join('utils', file))
            print(f"Moved adapter file to utils: {file}")
    
    # Ensure essential files are in the right place
    if file in essential_files and file != 'main.py':
        if os.path.isfile(file):
            # Move to core directory
            if not os.path.exists(os.path.join('core', file)):
                shutil.copy2(file, os.path.join('core', file))
                print(f"Copied to core directory: {file}")

print("\nCleanup complete! Original files backed up to:", backup_dir)
print("\nNext step: Implement Jupiter client for real trading")