# fix_token_analyzer_recommendations.py
import os
import shutil

def update_token_analyzer():
    """Update token analyzer to have more reasonable buy criteria"""
    
    # First, backup the original
    for file_path in ['token_analyzer.py', 'core/token_analyzer.py']:
        if os.path.exists(file_path):
            shutil.copy(file_path, f"{file_path}.bak")
            print(f"✅ Backed up {file_path}")
    
    # Find and update the analyze_token method
    for file_path in ['token_analyzer.py', 'core/token_analyzer.py']:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find the section with buy recommendation logic
            if 'if (safety_score >= 50 and' in content:
                # Replace the buy recommendation logic
                old_logic = '''if (safety_score >= 50 and 
            price_change_24h >= 10.0 and 
            volume_24h >= 50000 and 
            liquidity_usd >= 25000):'''
                
                new_logic = '''if (safety_score >= 30 and 
            price_change_24h >= 1.0 and 
            volume_24h >= 5000 and 
            liquidity_usd >= 10000):'''
                
                content = content.replace(old_logic, new_logic)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"✅ Updated buy criteria in {file_path}")

if __name__ == "__main__":
    update_token_analyzer()