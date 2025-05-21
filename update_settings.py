import json

# Create a script named update_settings.py
with open('bot_control.json', 'r') as f:
    settings = json.load(f)
    
print("Current settings:")
print(f"simulation_mode: {settings.get('simulation_mode', 'Not found')}")
print(f"running: {settings.get('running', 'Not found')}")

# Modify settings
settings['simulation_mode'] = False  # Set to real trading mode
settings['running'] = True  # Ensure bot is running

# Save changes
with open('bot_control.json', 'w') as f:
    json.dump(settings, f, indent=4)
    
print("\nSettings updated! The bot will now run in REAL trading mode.")