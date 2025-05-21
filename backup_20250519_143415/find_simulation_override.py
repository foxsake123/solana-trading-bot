import os
import re

files_to_check = [
    'core/trading_bot.py',
    'trading_bot.py',
    'core/token_scanner.py',
    'token_scanner.py'
]

pattern = r'simulation_mode\s*=\s*(?:True|self\.config\.get\(.*\)|[^F].*)'

for file_path in files_to_check:
    if os.path.exists(file_path):
        print(f"Checking {file_path}...")
        with open(file_path, 'r') as file:
            content = file.read()
            matches = re.findall(pattern, content)
            for match in matches:
                print(f"  Found: {match.strip()}")