"""
Fix existing bot_control.json file to match new parameter ranges
"""
import json
import os
from datetime import datetime

def fix_bot_control():
    """Fix the bot_control.json file to use proper parameter values"""
    
    # Find the bot control file
    control_files = [
        'data/bot_control.json',
        'bot_control.json',
        'core/bot_control.json'
    ]
    
    control_file = None
    for file_path in control_files:
        if os.path.exists(file_path):
            control_file = file_path
            break
    
    if not control_file:
        print("❌ No bot_control.json file found")
        return False
    
    print(f"📁 Found control file: {control_file}")
    
    try:
        # Load existing settings
        with open(control_file, 'r') as f:
            settings = json.load(f)
        
        print("📋 Current settings:")
        for key, value in settings.items():
            print(f"  {key}: {value}")
        
        # Create backup
        backup_file = f"{control_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with open(backup_file, 'w') as f:
            json.dump(settings, f, indent=4)
        print(f"💾 Backup created: {backup_file}")
        
        # Fix problematic values
        fixes_applied = []
        
        # Fix take profit target (minimum 1.1)
        if settings.get('take_profit_target', 0) < 1.1:
            old_value = settings.get('take_profit_target', 0)
            settings['take_profit_target'] = 15.0  # Your actual target
            fixes_applied.append(f"take_profit_target: {old_value} → 15.0")
        
        # Fix stop loss percentage (convert to percentage if needed)
        if settings.get('stop_loss_percentage', 0) < 1.0:
            old_value = settings.get('stop_loss_percentage', 0)
            # If it's 0.25, convert to 25% 
            if old_value == 0.25:
                settings['stop_loss_percentage'] = 25.0
                fixes_applied.append(f"stop_loss_percentage: {old_value} → 25.0")
        
        # Fix slippage tolerance (convert to percentage if needed)
        if settings.get('slippage_tolerance', 0) < 1.0:
            old_value = settings.get('slippage_tolerance', 0)
            # If it's 0.30, convert to 30%
            if old_value == 0.30:
                settings['slippage_tolerance'] = 30.0
                fixes_applied.append(f"slippage_tolerance: {old_value} → 30.0")
        
        # Ensure max investment is reasonable
        if settings.get('max_investment_per_token', 0) < 0.01:
            old_value = settings.get('max_investment_per_token', 0)
            settings['max_investment_per_token'] = 1.0
            fixes_applied.append(f"max_investment_per_token: {old_value} → 1.0")
        
        # Ensure min investment is reasonable
        if settings.get('min_investment_per_token', 0) < 0.001:
            settings['min_investment_per_token'] = 0.02
            fixes_applied.append(f"min_investment_per_token: → 0.02")
        
        # Add missing ML parameters
        if 'ml_confidence_threshold' not in settings:
            settings['ml_confidence_threshold'] = 0.7
            fixes_applied.append("ml_confidence_threshold: → 0.7")
        
        if 'ml_retrain_interval_hours' not in settings:
            settings['ml_retrain_interval_hours'] = 24
            fixes_applied.append("ml_retrain_interval_hours: → 24")
        
        if 'ml_min_training_samples' not in settings:
            settings['ml_min_training_samples'] = 10
            fixes_applied.append("ml_min_training_samples: → 10")
        
        # Ensure safety score is reasonable
        if settings.get('MIN_SAFETY_SCORE', 0) < 15.0:
            old_value = settings.get('MIN_SAFETY_SCORE', 0)
            settings['MIN_SAFETY_SCORE'] = 50.0
            fixes_applied.append(f"MIN_SAFETY_SCORE: {old_value} → 50.0")
        
        # Fix volume if too low
        if settings.get('MIN_VOLUME', 0) < 1.0:
            old_value = settings.get('MIN_VOLUME', 0)
            settings['MIN_VOLUME'] = 10.0
            fixes_applied.append(f"MIN_VOLUME: {old_value} → 10.0")
        
        # Fix liquidity if too low
        if settings.get('MIN_LIQUIDITY', 0) < 1000.0:
            old_value = settings.get('MIN_LIQUIDITY', 0)
            settings['MIN_LIQUIDITY'] = 25000.0
            fixes_applied.append(f"MIN_LIQUIDITY: {old_value} → 25000.0")
        
        # Fix price change if too low
        if settings.get('MIN_PRICE_CHANGE_24H', 0) < 5.0:
            old_value = settings.get('MIN_PRICE_CHANGE_24H', 0)
            settings['MIN_PRICE_CHANGE_24H'] = 20.0
            fixes_applied.append(f"MIN_PRICE_CHANGE_24H: {old_value} → 20.0")
        
        # Save the fixed settings
        with open(control_file, 'w') as f:
            json.dump(settings, f, indent=4)
        
        print("\n✅ Fixed settings:")
        for fix in fixes_applied:
            print(f"  {fix}")
        
        print(f"\n📁 Updated file: {control_file}")
        print("\n🎉 Bot control file has been fixed!")
        print("You can now run the dashboard without errors.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing bot control file: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Fixing bot_control.json file...")
    fix_bot_control()