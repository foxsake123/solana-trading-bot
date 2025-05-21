import os
import re

# Path to solana_trader.py
file_path = 'core/solana_trader.py'

# Read the file
with open(file_path, 'r') as file:
    content = file.read()

# Fix 1: Replace "from core.solders_adapter" with "from solders_adapter"
content = content.replace("from core.solders_adapter", "from solders_adapter")

# Fix 2: Replace HAS_SOLANA_LIBS with wallet_initialized
content = content.replace("if not HAS_SOLANA_LIBS:", "if not wallet_initialized:")

# Write the changes back to the file
with open(file_path, 'w') as file:
    file.write(content)

print("Fixed solana_trader.py successfully!")