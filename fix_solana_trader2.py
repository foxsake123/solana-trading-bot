file_path = 'core/solana_trader.py'

# Read the file
with open(file_path, 'r') as file:
    lines = file.readlines()

# New content
new_content = []
wallet_initialized_added = False

# Process line by line
for line in lines:
    # Replace core.solders_adapter import
    if "from core.solders_adapter import" in line:
        line = line.replace("from core.solders_adapter", "from solders_adapter")
    
    # Add wallet_initialized = False before try block
    if "# Import Solana libraries" in line and not wallet_initialized_added:
        new_content.append(line)
        new_content.append("# Define initialization flag\n")
        new_content.append("wallet_initialized = False\n")
        wallet_initialized_added = True
        continue
    
    # Replace HAS_SOLANA_LIBS with wallet_initialized
    if "if not HAS_SOLANA_LIBS:" in line:
        line = line.replace("if not HAS_SOLANA_LIBS:", "if not wallet_initialized:")
    
    new_content.append(line)

# Remove the standalone HAS_SOLANA_LIBS assignment if it exists
final_content = []
for line in new_content:
    if "HAS_SOLANA_LIBS = wallet_initialized" not in line:
        final_content.append(line)

# Write the changes back to the file
with open(file_path, 'w') as file:
    file.writelines(final_content)

print("Fixed solana_trader.py successfully!")