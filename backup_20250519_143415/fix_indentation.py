file_path = 'core/solana_trader.py'

# Read the file
with open(file_path, 'r') as file:
    lines = file.readlines()

# Find the SolanaTrader class definition
class_start_idx = -1
for i, line in enumerate(lines):
    if "class SolanaTrader:" in line:
        class_start_idx = i
        break

if class_start_idx == -1:
    print("Could not find SolanaTrader class!")
    exit(1)

# Create a new version of the file
new_lines = []
for i, line in enumerate(lines):
    # Add all lines up to the class definition as-is
    if i <= class_start_idx:
        new_lines.append(line)
        continue
        
    # Add the class methods, ensuring proper indentation
    # Each method should be indented with 4 spaces under the class
    if line.startswith("def ") and i > class_start_idx:
        new_lines.append("    " + line)  # Add 4 spaces indentation
        continue
        
    # Normal lines in methods should be indented with 8 spaces
    if line.strip() and not line.startswith("class "):
        new_lines.append("        " + line.lstrip())  # Add 8 spaces indentation
    else:
        new_lines.append(line)  # Empty lines stay as-is

# Write the fixed file
with open(file_path, 'w') as file:
    file.writelines(new_lines)

print("Fixed indentation in solana_trader.py successfully!")