# apply_all_fixes.py
import os
import json

print("🔧 Applying all recommended fixes...")

# Fix 1: Database method
print("\n1. Fixing database method...")
files_to_fix = ["token_analyzer.py", "core/token_analyzer.py"]
for file_path in files_to_fix:
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            content = f.read()
        content = content.replace('self.db.save_token(', 'self.db.store_token(')
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"  ✅ Fixed {file_path}")

# Fix 3: Relax filters
print("\n2. Relaxing filters in bot_control.json...")
control_file = "bot_control.json"
if not os.path.exists(control_file):
    control_file = "data/bot_control.json"

with open(control_file, 'r') as f:
    settings = json.load(f)

# Update with relaxed filters
settings.update({
    "MIN_SAFETY_SCORE": 0.0,
    "MIN_VOLUME": 100.0,
    "MIN_LIQUIDITY": 100.0,
    "MIN_MCAP": 100.0,
    "MIN_HOLDERS": 1,
    "MIN_PRICE_CHANGE_1H": -100.0,
    "MIN_PRICE_CHANGE_6H": -100.0,
    "MIN_PRICE_CHANGE_24H": -100.0,
    "filter_fake_tokens": False
})

with open(control_file, 'w') as f:
    json.dump(settings, f, indent=4)
print(f"  ✅ Updated {control_file}")

# Fix 4: Temporarily disable pump filter
print("\n3. Disabling aggressive pump filter...")
utils_files = ["utils.py", "core/utils.py"]
for utils_file in utils_files:
    if os.path.exists(utils_file):
        with open(utils_file, 'r') as f:
            content = f.read()
        
        # Comment out the pump filter
        content = content.replace(
            "if 'pump' in contract_address_lower:",
            "# Temporarily disabled for testing\n    # if 'pump' in contract_address_lower:"
        )
        content = content.replace(
            '        logger.warning(f"Detected \'pump\' in token address: {contract_address}")\n        return True',
            '    #     logger.warning(f"Detected \'pump\' in token address: {contract_address}")\n    #     return True'
        )
        
        with open(utils_file, 'w') as f:
            f.write(content)
        print(f"  ✅ Updated {utils_file}")

print("\n✅ All fixes applied!")
print("\nNow run: python test_real_tokens.py")
print("\nYou should see real tokens being discovered!")