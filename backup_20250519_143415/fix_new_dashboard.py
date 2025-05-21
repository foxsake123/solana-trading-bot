# Create a file named fix_dashboard.py
import os

# Path to the dashboard file
dashboard_path = 'dashboard/new_dashboard.py'

# Read the dashboard file
with open(dashboard_path, 'r') as f:
    content = lines = f.readlines()

# Make necessary fixes
fixed_content = []
for line in lines:
    # Fix the stop_loss min_value
    if 'min_value=1.0,' in line and 'Stop Loss' in line:
        # Change min_value from 1.0 to 0.1
        fixed_line = line.replace('min_value=1.0,', 'min_value=0.1,')
        fixed_content.append(fixed_line)
    # Fix datetime parsing errors by adding proper conversion
    elif 'trades_df_copy.loc[:, \'timestamp\'] = pd.to_datetime(trades_df_copy[\'timestamp\'], utc=True)' in line:
        # Improve datetime parsing with error handling
        fixed_content.append('            # Handle different timestamp formats\n')
        fixed_content.append('            try:\n')
        fixed_content.append('                trades_df_copy.loc[:, \'timestamp\'] = pd.to_datetime(trades_df_copy[\'timestamp\'], utc=True, errors=\'coerce\')\n')
        fixed_content.append('            except Exception as e:\n')
        fixed_content.append('                logger.warning(f"Error converting timestamps: {e}")\n')
        fixed_content.append('                trades_df_copy[\'timestamp\'] = pd.to_datetime(trades_df_copy[\'timestamp\'].astype(str), errors=\'coerce\')\n')
    else:
        fixed_content.append(line)

# Create a backup of the original file
backup_path = dashboard_path + '.bak'
if not os.path.exists(backup_path):
    with open(backup_path, 'w') as f:
        f.writelines(content)
    print(f"Created backup of original dashboard at {backup_path}")

# Write the fixed content
with open(dashboard_path, 'w') as f:
    f.writelines(fixed_content)

print("Dashboard file fixed! You can now run it with: streamlit run dashboard/new_dashboard.py")