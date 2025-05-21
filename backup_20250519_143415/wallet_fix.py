# Open solana_trader.py
with open('core/solana_trader.py', 'r') as file:
    lines = file.readlines()

# Check for global wallet_initialized variable
has_global_wallet = False
for line in lines:
    if 'wallet_initialized = ' in line and not 'self.' in line:
        has_global_wallet = True

if not has_global_wallet:
    print("WARNING: Global wallet_initialized variable not found!")

# Add debug logging
new_lines = []
for line in lines:
    new_lines.append(line)
    
    # Add debug logging after simulation_mode is set
    if 'self.simulation_mode = simulation_mode' in line:
        new_lines.append('        logger.info(f"Bot running in {'simulation' if self.simulation_mode else 'real trading'} mode")\n')
    
    # Add global import if needed
    if 'def _initialize_wallet(self):' in line:
        new_lines.append('        global wallet_initialized\n')

# Write changes back
with open('core/solana_trader.py', 'w') as file:
    file.writelines(new_lines)

print("Added debug logging to solana_trader.py")